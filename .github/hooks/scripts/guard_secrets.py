#!/usr/bin/env python3
"""PreToolUse guard: block access to credential files and commands that leak secrets."""

import json
import re
import sys

SECRET_FILES = (
    re.compile(r"(^|/)\.env($|\.)"),
    re.compile(r"(^|/)(credentials|service[-_]?account)[^/]*\.json$", re.I),
    re.compile(r"[-_]key\.json$", re.I),
    re.compile(r"\.(pem|p12|pfx|key)$", re.I),
)
SECRET_FILE_EXCEPTIONS = re.compile(r"(^|/)\.env\.(example|sample|template)$")
HOOK_FILES = re.compile(r"(^|/)\.github/hooks/")

SECRET_COMMANDS = (
    (re.compile(r"\b(cat|less|more|head|tail|bat|open|code)\b[^|;&\n]*\.env\b"), "would print .env into the transcript"),
    (re.compile(r"gcloud\s+auth\s+print-(access|identity)-token"), "would print a live auth token"),
    (re.compile(r"(^|[|;&]\s*)(env|printenv)\s*($|[|;&])"), "would dump the whole environment"),
    (re.compile(r"gcloud\s+iam\s+service-accounts\s+keys\s+create"), "creates a service-account key file, which this project forbids"),
)

PATH_KEYS = {"filepath", "file_path", "path", "uri", "target_file", "filename", "new_path", "newpath", "old_path"}
COMMAND_KEYS = {"command", "cmd", "script"}
CONTENT_KEYS = {"content", "newstring", "new_string", "oldstring", "old_string", "file_text", "edits", "replacements"}


def collect(node, keys, found):
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() in keys and isinstance(value, str):
                found.append(value)
            else:
                collect(value, keys, found)
    elif isinstance(node, list):
        for item in node:
            collect(item, keys, found)


def has_key(node, keys):
    if isinstance(node, dict):
        return any(k.lower() in keys for k in node) or any(has_key(v, keys) for v in node.values())
    if isinstance(node, list):
        return any(has_key(item, keys) for item in node)
    return False


def respond(decision, reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    paths, commands = [], []
    collect(tool_input, PATH_KEYS, paths)
    collect(tool_input, COMMAND_KEYS, commands)

    for path in paths:
        normalized = path.replace("\\", "/")
        if SECRET_FILE_EXCEPTIONS.search(normalized):
            continue
        if any(pattern.search(normalized) for pattern in SECRET_FILES):
            respond("deny", f"'{path}' holds credentials. Never read, write, or commit it — see .github/copilot-instructions.md.")

    if has_key(tool_input, CONTENT_KEYS):
        for path in paths:
            if HOOK_FILES.search(path.replace("\\", "/")):
                respond("ask", f"'{path}' is a security guard for this workspace. Confirm before the agent modifies it.")

    for command in commands:
        for pattern, why in SECRET_COMMANDS:
            if pattern.search(command):
                respond("deny", f"Blocked: this command {why}.")

    sys.exit(0)


if __name__ == "__main__":
    main()

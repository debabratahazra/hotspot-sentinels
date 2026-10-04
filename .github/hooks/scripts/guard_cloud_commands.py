#!/usr/bin/env python3
"""PreToolUse guard: deny destructive cloud/git commands, gate ones that mutate GCP or cost money."""

import json
import re
import sys

DENY = (
    (r"gcloud\s+projects\s+delete", "deletes the entire GCP project"),
    (r"gcloud\s+run\s+services\s+delete", "deletes the Cloud Run service — roll back traffic to a previous revision instead"),
    (r"gcloud\s+firestore\s+databases\s+delete", "deletes the Firestore database and every hotspot scan"),
    (r"gcloud\s+pubsub\s+topics\s+delete", "deletes the heat-resilience alert topic"),
    (r"gcloud\s+artifacts\s+repositories\s+delete", "deletes the container image repository"),
    (r"(gcloud\s+storage|gsutil)\s+rm\b[^\n]*\s(-r|-R|--recursive)\b", "recursively deletes Cloud Storage objects"),
    (r"gcloud\s+storage\s+buckets\s+delete", "deletes the project data bucket"),
    (r"\brm\s+-[a-z]*[rR][a-z]*f|\brm\s+-[a-z]*f[a-z]*[rR]", "force-recursive delete"),
    (r"git\s+push\b[^\n]*(--force\b|-f\b)", "force-pushes and can destroy published history"),
    (r"git\s+reset\s+--hard", "discards uncommitted work"),
    (r"git\s+clean\s+-[a-z]*f", "deletes untracked files, which may include in-progress work"),
    (r"add-iam-policy-binding[^\n]*roles/(owner|editor)", "grants project-wide owner/editor — grant the narrow role instead"),
    (r"--no-verify\b", "bypasses commit hooks"),
)

ASK = (
    (r"gcloud\s+run\s+deploy", "deploys a new Cloud Run revision"),
    (r"gcloud\s+builds\s+submit", "starts a billable Cloud Build"),
    (r"gcloud\s+services\s+enable", "enables billable GCP APIs"),
    (r"(docker\s+push|gcloud\s+artifacts\s+repositories\s+create)", "pushes to or creates an Artifact Registry repository"),
    (r"add-iam-policy-binding", "changes IAM permissions"),
    (r"setup_gcp\.sh", "provisions cloud resources and requires an interactive login — better run by hand"),
    (r"gcloud\s+auth\s+(login|application-default\s+login)", "starts an interactive browser login"),
    (r"git\s+(push|commit)\b", "writes to version control"),
)

COMMAND_KEYS = {"command", "cmd", "script"}


def collect(node, found):
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() in COMMAND_KEYS and isinstance(value, str):
                found.append(value)
            else:
                collect(value, found)
    elif isinstance(node, list):
        for item in node:
            collect(item, found)


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

    commands = []
    collect(payload.get("tool_input") or {}, commands)

    for command in commands:
        for pattern, why in DENY:
            if re.search(pattern, command, re.I):
                respond("deny", f"Blocked — this command {why}. If it is genuinely needed, run it yourself in the terminal.")

    for command in commands:
        for pattern, why in ASK:
            if re.search(pattern, command, re.I):
                respond("ask", f"This command {why}. Confirm before running it.")

    sys.exit(0)


if __name__ == "__main__":
    main()

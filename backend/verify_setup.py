import os
import sys

from dotenv import load_dotenv
from google import genai

MAX_REPLY_CHARS = 200


def get_client(project: str, location: str) -> genai.Client:
    return genai.Client(vertexai=True, project=project, location=location)


def main() -> int:
    try:
        load_dotenv()
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        if not project:
            print("[ERROR] GOOGLE_CLOUD_PROJECT is required.")
            return 1

        region = os.getenv("GOOGLE_CLOUD_REGION", "asia-southeast1")
        model = os.getenv("MODEL_ID", "gemini-2.5-flash")
        client = get_client(project, region)
        response = client.models.generate_content(
            model=model,
            contents="Respond with exactly: 'HotSpot Sentinels environment operational.'",
        )
        reply = response.text
        if not reply or not reply.strip():
            print("[ERROR] Vertex AI returned no reply.")
            return 1

        # Bounded single line so an unexpected payload cannot flood the terminal.
        excerpt = " ".join(reply.split())[:MAX_REPLY_CHARS]
        print(f"[SUCCESS] Vertex AI Response: {excerpt}")
        return 0
    except Exception:
        print("[ERROR] Vertex AI connectivity check failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

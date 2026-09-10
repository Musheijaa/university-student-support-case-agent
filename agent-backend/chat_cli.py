"""Interactive terminal client for the /api/v1/student-support endpoint.

Not part of the API itself — a manual testing convenience so the Week 2
baseline can be exercised as a back-and-forth chat instead of one-off
curl commands.

Usage:
    python chat_cli.py [base_url]

    base_url defaults to http://127.0.0.1:8000; pass a different one if
    the backend is running on another port, e.g.:

    python chat_cli.py http://127.0.0.1:8001
"""

import sys

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    endpoint = f"{base_url.rstrip('/')}/api/v1/student-support"

    print("University Student-Support Case Agent — Week 2 baseline chat")
    print(f"Talking to: {endpoint}")
    print("Type your question and press Enter. Type 'exit' or Ctrl+C to quit.\n")

    with httpx.Client(timeout=30.0) as client:
        while True:
            try:
                message = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not message:
                continue
            if message.lower() in {"exit", "quit"}:
                break

            try:
                response = client.post(endpoint, json={"message": message})
            except httpx.RequestError as exc:
                print(f"[Could not reach backend at {base_url}: {exc}]\n")
                continue

            if response.status_code != 200:
                try:
                    detail = response.json().get("detail", response.text)
                except ValueError:
                    detail = response.text
                print(f"[HTTP {response.status_code}] {detail}\n")
                continue

            data = response.json()
            print(f"\nAssistant ({data['prompt_version']} / {data['model']}):")
            print(f"{data['response']}\n")


if __name__ == "__main__":
    main()

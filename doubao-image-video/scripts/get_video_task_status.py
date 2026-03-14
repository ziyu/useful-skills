# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx",
# ]
# ///
"""
Check the status of a Doubao Seedance video generation task.

Can optionally poll (--wait) until the task completes and download the video.

Usage:
    uv run get_video_task_status.py --task-id "task_abc123"
    uv run get_video_task_status.py --task-id "task_abc123" --wait --output ./video.mp4
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_API_KEY = None

# Status values that mean "done successfully"
SUCCESS_STATUSES = {"succeeded", "success", "completed"}
# Status values that mean "still working"
PENDING_STATUSES = {"pending", "processing", "running"}
# Maximum wait time when polling (seconds)
MAX_WAIT = 600
# Poll interval (seconds)
POLL_INTERVAL = 10


def extract_video_url(data: dict) -> str | None:
    """Extract video URL from various response formats."""
    # Try content.video_url
    content = data.get("content", {})
    if isinstance(content, dict) and content.get("video_url"):
        return content["video_url"]

    # Try data[0].video_url
    data_list = data.get("data", [])
    if isinstance(data_list, list) and len(data_list) > 0:
        entry = data_list[0]
        if isinstance(entry, dict) and entry.get("video_url"):
            return entry["video_url"]

    # Try output.video_url
    output = data.get("output", {})
    if isinstance(output, dict) and output.get("video_url"):
        return output["video_url"]

    # Try top-level video_url
    if data.get("video_url"):
        return data["video_url"]

    return None


def check_status(task_id: str, api_key: str, base_url: str) -> dict:
    """Check task status once. Returns the raw API response dict."""
    url = f"{base_url.rstrip('/')}/contents/generations/tasks/{task_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers=headers)

    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        return {"_error": f"API returned {resp.status_code}: {msg}"}

    return resp.json()


def download_video(video_url: str, output_path: Path) -> bool:
    """Download video from URL. Returns True on success."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=120.0) as client:
            resp = client.get(video_url)
        if resp.status_code == 200:
            output_path.write_bytes(resp.content)
            return True
    except Exception:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description="Check Doubao Seedance video task status")
    parser.add_argument("--task-id", required=True, help="Task ID from generate_video.py")
    parser.add_argument("--output", default="./generated_video.mp4", help="Output file path")
    parser.add_argument("--wait", action="store_true", help="Poll until complete (up to 10 min)")
    parser.add_argument("--api-key", default=None, help="API key (default: $ARK_API_KEY)")
    parser.add_argument("--base-url", default=None, help="API base URL")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ARK_API_KEY")
    base_url = args.base_url or os.environ.get("ARK_BASE_URL", DEFAULT_BASE_URL)

    if not api_key:
        print(json.dumps({"status": "error", "error": "No API key provided. Set ARK_API_KEY env var or pass --api-key."}))
        sys.exit(1)

    output_path = Path(args.output)

    start_time = time.time()

    while True:
        try:
            data = check_status(args.task_id, api_key, base_url)
        except Exception as e:
            print(json.dumps({"status": "error", "task_id": args.task_id, "error": str(e)}))
            sys.exit(1)

        # Handle HTTP error
        if "_error" in data:
            print(json.dumps({"status": "error", "task_id": args.task_id, "error": data["_error"]}))
            sys.exit(1)

        status = data.get("status", "unknown").lower()

        # Success
        if status in SUCCESS_STATUSES:
            video_url = extract_video_url(data)
            result = {
                "status": "succeeded",
                "task_id": args.task_id,
                "video_url": video_url,
            }

            if video_url:
                downloaded = download_video(video_url, output_path)
                if downloaded:
                    result["file"] = str(output_path)
                else:
                    result["download_error"] = "Failed to download video file. URL is still valid — try downloading manually."

            print(json.dumps(result))
            sys.exit(0)

        # Failed
        if status == "failed":
            error_msg = data.get("error", {})
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            print(json.dumps({
                "status": "failed",
                "task_id": args.task_id,
                "error": str(error_msg) or "Video generation failed",
            }))
            sys.exit(1)

        # Still processing
        if not args.wait:
            print(json.dumps({
                "status": status,
                "task_id": args.task_id,
                "message": "Still generating. Run with --wait to poll until complete.",
            }))
            sys.exit(0)

        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > MAX_WAIT:
            print(json.dumps({
                "status": "timeout",
                "task_id": args.task_id,
                "elapsed_seconds": int(elapsed),
                "message": f"Timed out after {int(elapsed)}s. Task may still be running — check again later.",
            }))
            sys.exit(1)

        # Wait and retry
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx",
# ]
# ///
"""
Submit a video generation task to Volcengine Doubao Seedance API.

Video generation is asynchronous. This script submits the task and returns a task_id.
Use get_video_task_status.py to poll for completion and download the result.

Usage:
    uv run generate_video.py --prompt "a running dog" --output ./dog.mp4
    uv run generate_video.py --prompt "animate this" --first-frame "https://img.png" --output ./out.mp4
"""

import argparse
import json
import os
import sys

import httpx

DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_API_KEY = None
DEFAULT_MODEL = "doubao-seedance-1-5-pro-251215"

VALID_RATIOS = {"16:9", "9:16", "1:1", "21:9"}


def main():
    parser = argparse.ArgumentParser(description="Generate video with Doubao Seedance")
    parser.add_argument("--prompt", required=True, help="Video description")
    parser.add_argument("--output", default="./generated_video.mp4", help="Output file path (used when polling)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--duration", type=int, default=5, choices=range(3, 9), help="Video length in seconds (3-8)")
    parser.add_argument("--ratio", default="16:9", help="Aspect ratio: 16:9, 9:16, 1:1, 21:9")
    parser.add_argument("--first-frame", default=None, help="Image URL for image-to-video")
    parser.add_argument("--ref-image", action="append", default=[], help="Reference image URL (lite i2v only, can pass multiple)")
    parser.add_argument("--watermark", action="store_true", help="Add watermark")
    parser.add_argument("--api-key", default=None, help="API key (default: $ARK_API_KEY)")
    parser.add_argument("--base-url", default=None, help="API base URL")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ARK_API_KEY")
    base_url = args.base_url or os.environ.get("ARK_BASE_URL", DEFAULT_BASE_URL)

    if not api_key:
        print(json.dumps({"status": "error", "error": "No API key provided. Set ARK_API_KEY env var or pass --api-key."}))
        sys.exit(1)

    if args.ratio not in VALID_RATIOS:
        print(json.dumps({
            "status": "error",
            "error": f"Invalid ratio '{args.ratio}'. Must be one of: {', '.join(sorted(VALID_RATIOS))}"
        }))
        sys.exit(1)

    # Build content array
    # Embed parameters in text prompt as the API expects
    text_prompt = f"{args.prompt} --dur {args.duration} --ratio {args.ratio}"
    content: list[dict] = [{"type": "text", "text": text_prompt}]

    # Add first frame image for image-to-video
    if args.first_frame:
        content.append({
            "type": "image_url",
            "image_url": {"url": args.first_frame},
        })

    # Add reference images (for lite i2v models)
    for ref_url in args.ref_image:
        content.append({
            "type": "image_url",
            "image_url": {"url": ref_url},
            "role": "reference_image",
        })

    # Build request body
    body = {
        "model": args.model,
        "content": content,
    }

    # Make API request
    url = f"{base_url.rstrip('/')}/contents/generations/tasks"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=body, headers=headers)

        if resp.status_code not in (200, 201):
            try:
                err = resp.json()
                msg = err.get("error", {}).get("message", resp.text)
            except Exception:
                msg = resp.text

            # Provide helpful guidance for 404 (model not activated)
            if resp.status_code == 404:
                msg += (
                    "\n\nHint: This model may not be activated on your account. "
                    "Visit the Volcengine ARK Console (https://console.volcengine.com/ark) "
                    "to activate Seedance models. You can also try a different model with --model."
                )

            print(json.dumps({"status": "error", "error": f"API returned {resp.status_code}: {msg}"}))
            sys.exit(1)

        data = resp.json()
        task_id = data.get("id", "")

        if not task_id:
            print(json.dumps({"status": "error", "error": f"No task_id in response: {json.dumps(data)}"}))
            sys.exit(1)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        poll_script = os.path.join(script_dir, "get_video_task_status.py")

        result = {
            "status": "submitted",
            "task_id": task_id,
            "model": args.model,
            "message": f"Video generation started. Use get_video_task_status.py --task-id {task_id} --wait --output {args.output} to check.",
            "poll_command": f"uv run {poll_script} --task-id {task_id} --wait --output {args.output}",
        }
        print(json.dumps(result))

    except httpx.TimeoutException:
        print(json.dumps({"status": "error", "error": "Request timed out (30s)."}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()

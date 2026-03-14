# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx",
#     "rembg[cpu]",
#     "pillow",
# ]
# ///
"""
Generate images using Volcengine Doubao Seedream API.

Usage:
    uv run generate_image.py --prompt "a cute cat" --output ./cat.png
    uv run generate_image.py --prompt "winter version" --image "https://ref.png" --output ./out.png
    uv run generate_image.py --prompt "a warrior sprite" --remove-bg --output ./warrior.png
"""

import argparse
import base64
import json
import os
import sys
from io import BytesIO
from pathlib import Path

import httpx

DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_API_KEY = None

VERSION_TO_MODEL = {
    "4.0": "doubao-seedream-4-0-250828",
    "4.5": "doubao-seedream-4-5-251128",
    "5.0": "doubao-seedream-5-0-260128",
}

ALLOWED_SIZES = {
    "4.0": {"1K", "2K", "4K"},
    "4.5": {"2K", "4K"},
    "5.0": {"2K", "3K"},
}


def remove_background(image_bytes: bytes) -> bytes:
    """Remove background from image using rembg, returning RGBA PNG bytes."""
    from PIL import Image
    from rembg import remove

    img = Image.open(BytesIO(image_bytes))
    output = remove(img)
    buf = BytesIO()
    output.save(buf, format="PNG")
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Generate images with Doubao Seedream")
    parser.add_argument("--prompt", required=True, help="Image description")
    parser.add_argument("--output", default="./generated_image.png", help="Output file path")
    parser.add_argument("--version", default="4.5", choices=["4.0", "4.5", "5.0"], help="Seedream version")
    parser.add_argument("--size", default="2K", help="Image size: 1K, 2K, 3K, 4K (varies by version)")
    parser.add_argument("--image", action="append", default=[], help="Reference image URL (can pass multiple)")
    parser.add_argument("--watermark", action="store_true", help="Add watermark")
    parser.add_argument("-n", type=int, default=1, help="Number of images to generate (Seedream 4.x only, 1-4)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility (-1 for random)")
    parser.add_argument("--response-format", default="url", choices=["url", "b64_json"], help="API response format")
    parser.add_argument("--remove-bg", action="store_true", help="Remove background using rembg (outputs transparent PNG)")
    parser.add_argument("--api-key", default=None, help="API key (default: $ARK_API_KEY)")
    parser.add_argument("--base-url", default=None, help="API base URL")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ARK_API_KEY")
    base_url = args.base_url or os.environ.get("ARK_BASE_URL", DEFAULT_BASE_URL)

    if not api_key:
        print(json.dumps({"status": "error", "error": "No API key provided. Set ARK_API_KEY env var or pass --api-key."}))
        sys.exit(1)

    # Validate size for version
    if args.size not in ALLOWED_SIZES[args.version]:
        allowed = ", ".join(sorted(ALLOWED_SIZES[args.version]))
        print(json.dumps({
            "status": "error",
            "error": f"Size '{args.size}' not allowed for Seedream {args.version}. Allowed: {allowed}"
        }))
        sys.exit(1)

    model = VERSION_TO_MODEL[args.version]

    # Build request body
    body = {
        "model": model,
        "prompt": args.prompt,
        "size": args.size,
        "watermark": args.watermark,
        "response_format": args.response_format,
    }

    if args.n > 1:
        body["n"] = args.n

    if args.seed is not None:
        body["seed"] = args.seed

    if args.image:
        body["image"] = args.image

    # Make API request
    url = f"{base_url.rstrip('/')}/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=body, headers=headers)

        if resp.status_code != 200:
            try:
                err = resp.json()
                msg = err.get("error", {}).get("message", resp.text)
            except Exception:
                msg = resp.text
            print(json.dumps({"status": "error", "error": f"API returned {resp.status_code}: {msg}"}))
            sys.exit(1)

        data = resp.json()

        if not data.get("data") or len(data["data"]) == 0:
            print(json.dumps({"status": "error", "error": "No image data in response"}))
            sys.exit(1)

        usage = data.get("usage", {})
        results = []

        for i, image_entry in enumerate(data["data"]):
            # Determine output path for this image
            output_path = Path(args.output)
            if len(data["data"]) > 1:
                stem = output_path.stem
                suffix = output_path.suffix
                output_path = output_path.with_name(f"{stem}_{i+1}{suffix}")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            image_size = image_entry.get("size", "unknown")

            # Get image bytes depending on response format
            if args.response_format == "b64_json":
                b64_data = image_entry.get("b64_json", "")
                if not b64_data:
                    print(json.dumps({"status": "error", "error": f"No b64_json in response for image {i+1}"}))
                    sys.exit(1)
                image_bytes = base64.b64decode(b64_data)
                content_type = "image/jpeg"  # API returns JPEG data
            else:
                image_url = image_entry.get("url", "")
                with httpx.Client(timeout=60.0) as client:
                    img_resp = client.get(image_url)
                if img_resp.status_code != 200:
                    print(json.dumps({"status": "error", "error": f"Failed to download image {i+1}: HTTP {img_resp.status_code}"}))
                    sys.exit(1)
                image_bytes = img_resp.content
                content_type = img_resp.headers.get("content-type", "")

            # Remove background if requested
            if args.remove_bg:
                image_bytes = remove_background(image_bytes)
                # Force .png extension for transparent output
                output_path = output_path.with_suffix(".png")
            else:
                # Detect actual content type and adjust extension if needed
                actual_ext = output_path.suffix.lower()
                if "jpeg" in content_type or "jpg" in content_type:
                    if actual_ext == ".png":
                        output_path = output_path.with_suffix(".jpg")
                elif "png" in content_type:
                    if actual_ext in (".jpg", ".jpeg"):
                        output_path = output_path.with_suffix(".png")

            output_path.write_bytes(image_bytes)

            results.append({
                "file": str(output_path),
                "size": image_size,
                "transparent": args.remove_bg,
            })

        # Report success
        result = {
            "status": "success",
            "model": data.get("model", model),
            "tokens_used": usage.get("total_tokens", 0),
            "images": results,
            # Backward compat: single image fields
            "file": results[0]["file"],
            "size": results[0]["size"],
        }
        if args.remove_bg:
            result["background_removed"] = True
        print(json.dumps(result))

    except httpx.TimeoutException:
        print(json.dumps({"status": "error", "error": "Request timed out (120s). Try a smaller size or simpler prompt."}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()

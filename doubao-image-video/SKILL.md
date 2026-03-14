---
name: doubao-image-video
description: "Generate images and videos using Volcengine Doubao (豆包) AI models — Seedream for images and Seedance for videos. Use this skill whenever the user asks to generate, create, or produce images or videos with Doubao/豆包, Seedream, Seedance, or Volcengine/火山引擎. Also use when the user needs AI-generated game sprites, pixel art, concept art, character designs, scene illustrations, or any visual asset generation where Doubao is the preferred provider. Triggers on: '生成图片', '生成视频', 'generate image', 'generate video', 'create artwork', 'make a sprite', 'doubao', '豆包', 'seedream', 'seedance', or any request involving AI image/video generation that should use the Volcengine platform."
---

# Doubao Image & Video Generation

Generate images with **Seedream** and videos with **Seedance** via the Volcengine ARK API.

## Quick Reference

| Capability | Model | Script |
|---|---|---|
| Text-to-Image | Seedream 4.0 / 4.5 / 5.0 | `scripts/generate_image.py` |
| Image-to-Image | Seedream (with reference images) | `scripts/generate_image.py` |
| Transparent PNG | Seedream + rembg post-processing | `scripts/generate_image.py --remove-bg` |
| Text-to-Video | Seedance 1.5 Pro / 1.0 variants | `scripts/generate_video.py` |
| Image-to-Video | Seedance (with first frame) | `scripts/generate_video.py` |
| Check Video Status | — | `scripts/get_video_task_status.py` |

## Configuration

The scripts read the API key from the `ARK_API_KEY` environment variable. If not set, they fall back to a built-in default key.

You can also pass `--api-key` and `--base-url` as CLI arguments to override.

**Default base URL:** `https://ark.cn-beijing.volces.com/api/v3`

## Image Generation (Seedream)

### When to Use

- User wants to generate an image from a text description
- User wants to create game sprites, concept art, icons, character designs
- User wants to transform or blend reference images into a new image
- User says "生成图片", "画一张", "create an image", etc.

### How to Run

```bash
uv run <skill-path>/scripts/generate_image.py \
  --prompt "a cute orange cat sitting on a wooden barrel, pixel art style" \
  --output ./output.png
```

### Parameters

| Parameter | Flag | Default | Description |
|---|---|---|---|
| Prompt | `--prompt` | (required) | Image description. English or Chinese both work well. |
| Output | `--output` | `./generated_image.png` | Where to save the image |
| Model version | `--version` | `4.5` | Seedream version: `4.0`, `4.5`, or `5.0` |
| Size | `--size` | `2K` | Resolution: see table below |
| Reference images | `--image` | (none) | URL(s) for img2img / style reference. Can pass multiple times. |
| Watermark | `--watermark` | `false` | Add watermark |
| Count | `-n` | `1` | Number of images to generate (Seedream 4.x only, 1-4) |
| Seed | `--seed` | (none) | Random seed for reproducibility (-1 for random) |
| Response format | `--response-format` | `url` | `url` (download link) or `b64_json` (inline base64) |
| Remove background | `--remove-bg` | `false` | Remove background → outputs transparent RGBA PNG |
| API key | `--api-key` | `$ARK_API_KEY` | Override API key |
| Base URL | `--base-url` | (default) | Override API endpoint |

### Size Options by Version

| Version | Allowed Sizes |
|---|---|
| 4.0 | 1K, 2K, 4K |
| 4.5 | 2K, 4K |
| 5.0 | 2K, 3K |

### Examples

**Basic text-to-image:**
```bash
uv run scripts/generate_image.py \
  --prompt "a post-apocalyptic vehicle driving through desert ruins, dramatic lighting" \
  --output ./vehicle_concept.png \
  --size 2K
```

**Game sprite generation:**
```bash
uv run scripts/generate_image.py \
  --prompt "top-down 2D game sprite of a rusty armored truck, pixel art, 64x64, transparent background" \
  --output ./sprite_truck.png \
  --version 5.0 \
  --size 2K
```

**Image-to-image with reference:**
```bash
uv run scripts/generate_image.py \
  --prompt "same style but in winter setting with snow" \
  --image "https://example.com/reference.png" \
  --output ./winter_version.png
```

**Multiple reference images (style fusion):**
```bash
uv run scripts/generate_image.py \
  --prompt "combine these styles into a new character design" \
  --image "https://example.com/style1.png" \
  --image "https://example.com/style2.png" \
  --output ./fused_design.png
```

**Transparent game sprite (background removal):**
```bash
uv run scripts/generate_image.py \
  --prompt "a warrior character holding a sword, game sprite, white background" \
  --remove-bg \
  --output ./warrior_sprite.png
```

**Batch generation with seed:**
```bash
uv run scripts/generate_image.py \
  --prompt "a sci-fi weapon icon, game UI, clean design" \
  -n 4 \
  --seed 42 \
  --version 4.5 \
  --output ./weapon_icon.png
# Outputs: weapon_icon_1.png, weapon_icon_2.png, weapon_icon_3.png, weapon_icon_4.png
```

### Transparent PNG (Background Removal)

The Seedream API **always outputs JPEG** — there is no native transparency support. When you include "transparent background" in the prompt, the API renders a checkerboard pattern (simulating transparency visually), but the image is still opaque RGB JPEG.

To produce **true RGBA PNG with an alpha channel**, use the `--remove-bg` flag:

```bash
uv run scripts/generate_image.py \
  --prompt "a cute robot character, game sprite, white background" \
  --remove-bg \
  --output ./robot.png
```

**How it works:**
1. Seedream generates the image as usual (JPEG)
2. `rembg` (AI background removal) strips the background and creates an alpha channel
3. The result is saved as a true RGBA PNG file

**Tips for best results:**
- Include "white background" or "solid color background" in the prompt — this gives `rembg` a cleaner edge to detect
- Avoid "transparent background" in the prompt (it creates checkerboard patterns that confuse `rembg`)
- Works best for isolated subjects: characters, items, sprites, icons
- First run may be slow (~30s extra) as `rembg` downloads its model (~180MB)

**Dependencies:** `--remove-bg` requires `rembg` and `pillow` (auto-installed by `uv run` via inline script metadata).

### Output

The script prints a JSON summary on success:
```json
{
  "status": "success",
  "file": "./output.png",
  "size": "3136x1344",
  "model": "doubao-seedream-4-5-251128",
  "tokens_used": 4197376
}
```

On error, it prints a JSON error and exits with code 1:
```json
{
  "status": "error",
  "error": "API returned 400: invalid size for model version 4.5"
}
```

## Video Generation (Seedance)

### When to Use

- User wants to generate a video from a text prompt
- User wants to animate a still image (image-to-video)
- User says "生成视频", "做一个动画", "create a video", "animate this", etc.

### How to Run

Video generation is **asynchronous** — it takes 1-5 minutes. The workflow is:

1. **Submit** the task with `generate_video.py` → get a `task_id`
2. **Poll** the status with `get_video_task_status.py` → get the video URL when done

```bash
# Step 1: Submit
uv run <skill-path>/scripts/generate_video.py \
  --prompt "a rusted vehicle driving through a sandstorm" \
  --output ./video_output.mp4

# Step 2: Check status (the task_id is printed by step 1)
uv run <skill-path>/scripts/get_video_task_status.py \
  --task-id "task_abc123" \
  --output ./video_output.mp4
```

### Parameters for generate_video.py

| Parameter | Flag | Default | Description |
|---|---|---|---|
| Prompt | `--prompt` | (required) | Video description |
| Output | `--output` | `./generated_video.mp4` | Where to save the video |
| Model | `--model` | `doubao-seedance-1-5-pro-251215` | Model name |
| Duration | `--duration` | `5` | Video length in seconds (3-8) |
| Ratio | `--ratio` | `16:9` | Aspect ratio: `16:9`, `9:16`, `1:1`, `21:9` |
| First frame | `--first-frame` | (none) | Image URL for image-to-video |
| Reference images | `--ref-image` | (none) | Reference image URLs (lite i2v models only). Can pass multiple. |
| Watermark | `--watermark` | `false` | Add watermark |
| API key | `--api-key` | `$ARK_API_KEY` | Override API key |
| Base URL | `--base-url` | (default) | Override API endpoint |

### Parameters for get_video_task_status.py

| Parameter | Flag | Default | Description |
|---|---|---|---|
| Task ID | `--task-id` | (required) | The task ID from generate_video.py |
| Output | `--output` | `./generated_video.mp4` | Where to save when complete |
| Wait | `--wait` | `false` | Poll until complete (up to 10 min) |
| API key | `--api-key` | `$ARK_API_KEY` | Override API key |
| Base URL | `--base-url` | (default) | Override API endpoint |

### Available Models

| Model | Description |
|---|---|
| `doubao-seedance-1-5-pro-251215` | Latest pro model (default, best quality) |
| `doubao-seedance-1-0-pro` | Pro v1.0 |
| `doubao-seedance-1-0-pro-fast` | Faster pro generation |
| `doubao-seedance-1-0-lite-t2v` | Lightweight text-to-video |
| `doubao-seedance-1-0-lite-i2v-250428` | Lightweight image-to-video (supports multiple ref images) |

### Examples

**Text-to-video:**
```bash
uv run scripts/generate_video.py \
  --prompt "a convoy of armored vehicles crossing a desert, dust clouds, cinematic" \
  --duration 5 \
  --ratio 16:9 \
  --output ./convoy.mp4
```

**Image-to-video (animate a still):**
```bash
uv run scripts/generate_video.py \
  --prompt "the vehicle starts moving forward, dust kicks up" \
  --first-frame "https://example.com/vehicle_still.png" \
  --output ./vehicle_moving.mp4
```

**Poll with auto-wait:**
```bash
uv run scripts/get_video_task_status.py \
  --task-id "task_abc123" \
  --output ./convoy.mp4 \
  --wait
```

### Output

**generate_video.py** prints:
```json
{
  "status": "submitted",
  "task_id": "task_abc123",
  "model": "doubao-seedance-1-5-pro-251215",
  "message": "Video generation started. Use get_video_task_status.py --task-id task_abc123 --wait to check."
}
```

**get_video_task_status.py** prints:
```json
{
  "status": "succeeded",
  "task_id": "task_abc123",
  "video_url": "https://...",
  "file": "./convoy.mp4"
}
```
Or if still processing:
```json
{
  "status": "processing",
  "task_id": "task_abc123",
  "message": "Still generating..."
}
```

## Prompting Tips

1. **Be descriptive** — Seedream and Seedance respond well to detailed prompts with style, lighting, and composition details.
2. **Language** — Both Chinese and English work. For game assets, English tends to yield more consistent pixel art / game art styles.
3. **Game sprites** — Include keywords like "pixel art", "game sprite", "top-down", "side-view", specific pixel dimensions. Use `--remove-bg` for transparent sprites.
4. **Transparent images** — Use `--remove-bg` flag + "white background" or "solid color background" in the prompt. Do NOT say "transparent background" (causes checkerboard artifacts).
5. **Video** — Describe motion explicitly: "the camera slowly pans left", "the character walks forward".
6. **Aspect ratios** — For game assets, square (1:1) or landscape (16:9) work best. For character sprites, try portrait images then crop.
7. **Batch generation** — Use `-n 4` to get multiple variations at once (Seedream 4.x only). Add `--seed` for reproducibility.

## Error Handling

All scripts exit with code 0 on success, 1 on error. Errors are printed as JSON to stdout for easy parsing. Common issues:

- **Invalid size for version**: Check the size table above
- **API key invalid**: Verify `ARK_API_KEY` is set correctly
- **Rate limited**: Wait a moment and retry
- **Video task failed**: Re-submit with a simpler prompt or different model

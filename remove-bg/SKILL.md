---
name: remove-bg
description: "Remove image backgrounds using rembg CLI via uv. Produces transparent PNG output from any image. Use when the user asks to remove a background, make an image transparent, extract a subject from a photo, cut out an object, or create a sticker/sprite from a photo. Triggers on: 'remove background', 'remove bg', 'transparent background', 'cut out', 'extract subject', 'make transparent', 'background removal', 'rembg', or any request involving removing or replacing image backgrounds."
---

# Image Background Removal with rembg

Remove backgrounds from images locally using `rembg` — produces transparent PNG output. No API keys, no cloud services. Runs entirely on CPU via ONNX Runtime.

## Prerequisites

- **uv** installed (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- No other setup needed — `uvx` handles the Python environment and dependencies automatically

## How It Works

`rembg` uses deep learning models (U2-Net, BiRefNet, ISNet, etc.) to detect foreground subjects and remove backgrounds. Models auto-download to `~/.u2net/` on first use (170–380 MB depending on model).

All commands use `uvx` to run in an isolated environment — no global pip installs, no dependency conflicts.

## Quick Start

```bash
# Basic background removal (default model: u2net)
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i input.jpg output.png

# Best quality for general images
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -m birefnet-general input.jpg output.png

# Best quality for portraits/people
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -m birefnet-portrait input.jpg output.png
```

> **First run note:** The selected model downloads automatically to `~/.u2net/` on first use. This is a one-time cost per model (170–380 MB). Subsequent runs use the cached model instantly.

## Available Models

Pick the model based on your use case. When in doubt, use `birefnet-general` for best quality or `u2net` for fastest first-run (smallest download).

| Model | Size | Best For | Quality |
|-------|------|----------|---------|
| `u2net` | ~176 MB | General (default, fast) | Good |
| `u2netp` | ~4 MB | Quick previews, low-res | Fastest, lower quality |
| `u2net_human_seg` | ~176 MB | Human portraits (legacy) | Good for people |
| `u2net_cloth_seg` | ~176 MB | Clothing segmentation | Specialized |
| `silueta` | ~43 MB | General (compact) | Good, small download |
| `isnet-general-use` | ~178 MB | General (ISNet architecture) | Very good |
| `isnet-anime` | ~178 MB | Anime/cartoon characters | Best for anime |
| `birefnet-general` | ~374 MB | General (BiRefNet SOTA) | Highest quality |
| `birefnet-general-lite` | ~100 MB | General (lighter BiRefNet) | Good quality, faster |
| `birefnet-portrait` | ~374 MB | Human portraits | Best for portraits |
| `birefnet-dis` | ~374 MB | Detailed/complex objects | Very precise edges |
| `birefnet-hrsod` | ~374 MB | High-resolution inputs | Best for large images |
| `birefnet-massive` | ~374 MB | Robustness across domains | Most versatile |
| `bria-rmbg` | ~178 MB | BRIA AI RMBG-2.0 | State of the art |
| `sam` | ~375 MB | Interactive (prompt-based) | Requires point/box prompts |

### Model Selection Guide

| Scenario | Recommended Model |
|----------|-------------------|
| **General purpose, best quality** | `birefnet-general` |
| **People/portraits** | `birefnet-portrait` |
| **Anime/cartoon characters** | `isnet-anime` |
| **Quick preview or batch processing** | `u2netp` (4 MB, fastest) |
| **Game sprites from photos** | `birefnet-dis` (precise edges) |
| **First time, want fast setup** | `u2net` (default, reasonable size) |
| **Smallest download, decent quality** | `silueta` (43 MB) |

## CLI Reference

### Single Image: `rembg i`

```bash
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i [OPTIONS] INPUT OUTPUT
```

| Flag | Description | Default |
|------|-------------|---------|
| `-m MODEL` | Model name (see table above) | `u2net` |
| `-a` | Enable alpha matting (better edges for hair/fur) | off |
| `-af N` | Alpha matting foreground threshold | 240 |
| `-ab N` | Alpha matting background threshold | 10 |
| `-ae N` | Alpha matting erode size | 10 |
| `-om` | Output only the mask (grayscale PNG) | off |
| `-ppm` | Post-process the mask | off |
| `-bgc R G B A` | Replace background with solid color (RGBA 0-255) | transparent |
| `-x JSON` | Extra model-specific params (JSON string) | none |

### Batch Folder: `rembg p`

```bash
uvx --from "rembg[cpu,cli]" --python 3.12 rembg p [OPTIONS] INPUT_DIR OUTPUT_DIR
```

Processes all images in the input folder. Same flags as `rembg i` apply.

| Additional Flag | Description |
|----------------|-------------|
| `-w` | Watch mode — auto-process new/changed files |

### Stdin/Stdout (Pipe)

```bash
cat input.jpg | uvx --from "rembg[cpu,cli]" --python 3.12 rembg i > output.png
```

## Common Patterns

### Remove background (basic)

```bash
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i photo.jpg result.png
```

Output: transparent PNG.

### Remove background (best quality)

```bash
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -m birefnet-general photo.jpg result.png
```

Use `birefnet-general` for the highest quality on arbitrary images.

### Portrait with fine hair edges

```bash
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -m birefnet-portrait -a photo.jpg result.png
```

The `-a` flag enables alpha matting — significantly improves edges around hair, fur, and semi-transparent areas.

### Replace background with solid color

```bash
# White background
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -bgc 255 255 255 255 photo.jpg result.png

# Red background
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -bgc 255 0 0 255 photo.jpg result.png
```

### Extract only the mask

```bash
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -om photo.jpg mask.png
```

Returns a grayscale PNG: white = foreground, black = background. Useful for compositing workflows.

### Batch process a folder

```bash
uvx --from "rembg[cpu,cli]" --python 3.12 rembg p -m birefnet-general ./input_photos/ ./output_transparent/
```

### Pre-download a model (avoid first-run delay)

```bash
uvx --from "rembg[cpu,cli]" --python 3.12 rembg d -m birefnet-general
```

## Complete Example: Remove Background from a Photo

```bash
# 1. Remove background with best quality model
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -m birefnet-general /path/to/photo.jpg /path/to/output.png

# 2. Verify output exists and has transparency
file /path/to/output.png
# → should show: PNG image data, ... 8-bit/color RGBA

# 3. If edges look rough (hair/fur), retry with alpha matting
uvx --from "rembg[cpu,cli]" --python 3.12 rembg i -m birefnet-general -a /path/to/photo.jpg /path/to/output.png
```

## Shell Alias (Optional)

The `uvx` command is long. For convenience, define an alias:

```bash
alias rembg='uvx --from "rembg[cpu,cli]" --python 3.12 rembg'
```

Then use simply:
```bash
rembg i -m birefnet-general input.jpg output.png
```

> **Note:** This alias is for interactive use. In skill instructions, always use the full `uvx` command to ensure reproducibility regardless of shell configuration.

## Troubleshooting

### Model download fails or hangs
Models are downloaded from Hugging Face Hub. If behind a proxy or firewall:
```bash
export HF_HUB_DISABLE_SYMLINKS=1
uvx --from "rembg[cpu,cli]" --python 3.12 rembg d -m u2net
```

### "No module named numba" or llvmlite errors
This happens when using system Python (3.11) with broken numba/llvmlite. The `uvx --python 3.12` approach in this skill avoids this entirely by using an isolated environment.

### Output has jagged edges
Try these in order:
1. Use a better model: `-m birefnet-general` or `-m birefnet-dis`
2. Enable alpha matting: `-a`
3. Adjust alpha matting thresholds: `-af 220 -ab 20 -ae 15`

### Output is all black or all transparent
The model may not detect the subject. Try:
1. A different model (`birefnet-general` is most robust)
2. Ensure the input image is not corrupted: `file input.jpg`
3. For very small subjects, try `birefnet-hrsod`

### Slow processing
- `u2netp` is the fastest model (~4 MB, lower quality)
- `birefnet-general-lite` is a good quality/speed tradeoff (~100 MB)
- GPU acceleration: install with `rembg[gpu,cli]` instead of `rembg[cpu,cli]` (requires NVIDIA CUDA)

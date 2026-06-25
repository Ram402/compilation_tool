"""
Frame Interpolator for 360° Car Viewer
---------------------------------------
Takes your 20 existing frames and generates smooth in-between frames
using pixel-level blending (cross-dissolve interpolation).

Result: 20 original frames → 80 or 120 smooth frames (configurable)

Usage:
    python generate_extra_frames.py

Output folder: same directory as input, named 'frames_interpolated'
"""

import os
import sys
from PIL import Image
import numpy as np

# ── CONFIG ─────────────────────────────────────────────────────────────────────
INPUT_DIR   = r"C:\Users\AinavilliRamaDurgaPr\Pictures\l\vcast_app_2 (2)\vcast_app_2\output_images"
OUTPUT_DIR  = r"C:\Users\AinavilliRamaDurgaPr\Pictures\l\vcast_app_2 (2)\vcast_app_2\frames_interpolated"

# How many frames to INSERT between each pair of originals.
# 3 → 20 frames become 80  (20 × 4 steps)   ← recommended
# 4 → 20 frames become 100 (20 × 5 steps)
# 5 → 20 frames become 120 (20 × 6 steps)
STEPS_BETWEEN = 3   # change to 4 or 5 for even smoother result
# ───────────────────────────────────────────────────────────────────────────────


def load_frames(input_dir: str) -> list[tuple[str, Image.Image]]:
    """Load all frame_XX.png files sorted by number."""
    import re
    files = []
    for fname in os.listdir(input_dir):
        if re.match(r"^frame_\d+\.png$", fname, re.IGNORECASE):
            files.append(fname)
    files.sort()

    if not files:
        print(f"ERROR: No frame_XX.png files found in:\n  {input_dir}")
        sys.exit(1)

    frames = []
    for fname in files:
        path = os.path.join(input_dir, fname)
        img = Image.open(path).convert("RGBA")
        frames.append((fname, img))
        print(f"  Loaded: {fname}  ({img.size[0]}×{img.size[1]})")

    return frames


def interpolate(img_a: Image.Image, img_b: Image.Image, t: float) -> Image.Image:
    """
    Blend img_a → img_b using pixel-level alpha crossfade.
    t=0.0 → pure img_a,  t=1.0 → pure img_b
    Both images are resized to the same size before blending.
    """
    # Ensure same size
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.LANCZOS)

    arr_a = np.asarray(img_a, dtype=np.float32)
    arr_b = np.asarray(img_b, dtype=np.float32)

    blended = arr_a * (1.0 - t) + arr_b * t
    return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8), "RGBA")


def main():
    print(f"\n{'='*60}")
    print("  360° Frame Interpolator")
    print(f"{'='*60}")
    print(f"\nInput  dir : {INPUT_DIR}")
    print(f"Output dir : {OUTPUT_DIR}")
    print(f"Steps between each pair: {STEPS_BETWEEN}")

    if not os.path.isdir(INPUT_DIR):
        print(f"\nERROR: Input directory does not exist:\n  {INPUT_DIR}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\nLoading source frames...")
    frames = load_frames(INPUT_DIR)
    n = len(frames)
    print(f"\n✓ Loaded {n} source frames")

    total_steps = STEPS_BETWEEN + 1   # e.g. 3+1=4 slots between each pair
    total_output = n * total_steps
    print(f"  Generating {total_output} output frames ({n} × {total_steps})\n")

    out_idx = 1
    for i in range(n):
        name_a, img_a = frames[i]
        name_b, img_b = frames[(i + 1) % n]   # wrap around at end

        for step in range(total_steps):
            t = step / total_steps   # 0.0, 0.25, 0.5, 0.75  (for STEPS=3)

            if t == 0.0:
                out_img = img_a.copy()
            else:
                out_img = interpolate(img_a, img_b, t)

            out_name = f"frame_{out_idx:03d}.png"
            out_path = os.path.join(OUTPUT_DIR, out_name)
            out_img.save(out_path, "PNG")
            print(f"  [{out_idx:03d}/{total_output}] {name_a} → {name_b}  t={t:.2f}  →  {out_name}")
            out_idx += 1

    print(f"\n{'='*60}")
    print(f"✓ Done! {total_output} frames saved to:")
    print(f"  {OUTPUT_DIR}")
    print(f"\nNow update car_viewer_360.py to point to this folder:")
    print(f'  _HARDCODED_CAR_IMAGES_DIR = r"{OUTPUT_DIR}"')
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")

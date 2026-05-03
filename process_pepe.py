from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from rembg import remove

SRC_DIR = Path(r"C:\Users\mick\economic-dashboard\frontend\Design\character")
OUT_DIR = Path(r"C:\Users\mick\economic-dashboard\frontend\public\characters")
OUT_DIR.mkdir(parents=True, exist_ok=True)

JOBS = [
    ("pepe1.jpg",  "pepe-analyst.png"),
    ("pepe2.jpg",  "pepe-money.png"),
    ("pepe43.jpg", "pepe-laugh.png"),
    ("pepe5.jpg",  "pepe-rich.png"),
]

BORDER_PX = 8          # black border thickness
CANVAS = 400           # output square size

def clean_alpha(img_rgba: Image.Image) -> Image.Image:
    """
    Hard-threshold alpha to binary, then erode aggressively.
    Kills all semi-transparent white fringe that rembg leaves behind.
    """
    arr = np.array(img_rgba)
    # Step 1: hard threshold — anything below 200 alpha becomes fully transparent
    arr[:, :, 3] = np.where(arr[:, :, 3] >= 200, 255, 0).astype(np.uint8)
    img = Image.fromarray(arr, 'RGBA')
    # Step 2: erode the hard mask multiple passes to pull edge inward
    r, g, b, a = img.split()
    for _ in range(4):
        a = a.filter(ImageFilter.MinFilter(size=5))
    return Image.merge('RGBA', (r, g, b, a))

def add_black_border(img_rgba: Image.Image, border: int) -> Image.Image:
    """Stroke the alpha channel outward with a black fill."""
    r, g, b, a = img_rgba.split()

    # dilate the alpha mask to create a slightly larger silhouette
    dilated = a.filter(ImageFilter.MaxFilter(size=border * 2 + 1))

    # build border layer: black where dilated but not original
    border_arr = np.array(dilated).astype(np.uint8)
    orig_arr   = np.array(a).astype(np.uint8)
    stroke_mask = np.clip(border_arr.astype(int) - orig_arr.astype(int), 0, 255).astype(np.uint8)

    black_arr = np.zeros((*img_rgba.size[::-1], 4), dtype=np.uint8)
    black_arr[:, :, 3] = stroke_mask
    black_layer = Image.fromarray(black_arr, "RGBA")

    # composite: black border behind subject
    result = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    result = Image.alpha_composite(result, black_layer)
    result = Image.alpha_composite(result, img_rgba)
    return result


def process(src_name: str, out_name: str):
    src_path = SRC_DIR / src_name
    out_path = OUT_DIR / out_name
    print(f"  {src_name} -> {out_name}", flush=True)

    with open(src_path, "rb") as f:
        raw = f.read()

    # rembg: remove background -> RGBA PNG bytes
    result_bytes = remove(raw)
    img = Image.open(__import__("io").BytesIO(result_bytes)).convert("RGBA")

    # hard-threshold + erode to strip white fringe entirely
    img = clean_alpha(img)

    # crop tightly to the subject (remove transparent padding)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # add black stroke border
    img = add_black_border(img, BORDER_PX)

    # fit onto a square canvas with padding so border isn't clipped
    padding = BORDER_PX + 4
    target = CANVAS - padding * 2
    img.thumbnail((target, target), Image.LANCZOS)

    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    offset_x = (CANVAS - img.width)  // 2
    offset_y = (CANVAS - img.height) // 2
    canvas.paste(img, (offset_x, offset_y), img)

    canvas.save(out_path, "PNG")
    print(f"    saved {out_path} ({canvas.size})", flush=True)


print("Processing Pepe images...")
for src, out in JOBS:
    process(src, out)
print("Done.")

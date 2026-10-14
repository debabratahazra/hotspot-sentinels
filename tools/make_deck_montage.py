"""Compose the prototype-snapshot montage for slide 11.

The live dashboard renders in a narrow responsive column, so a full-page capture
is mostly empty space. These are element-scoped captures laid out on one canvas
instead, which is what makes them legible on a slide.

Run with:  uv run --with pillow --no-project python tools/make_deck_montage.py
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "deck-assets"
OUTPUT = ASSETS / "montage-prototype.png"

CANVAS = (2000, 1180)
BACKGROUND = "#0e1117"
INK = "#e6edf3"
MUTED = "#8b98a9"
PAD = 28


def font(size, bold=False):
    for name in (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
                 ("Arial Bold.ttf" if bold else "Arial.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def autocrop(image):
    """Trim uniform background. Element screenshots carry large empty margins."""
    background = Image.new("RGB", image.size, image.getpixel((image.width - 1, image.height - 1)))
    bbox = ImageChops.difference(image, background).getbbox()
    return image.crop(bbox) if bbox else image


def place(canvas, filename, box, caption, draw):
    """Fit an asset inside box (x, y, w, h), captioned beneath."""
    source = ASSETS / filename
    if not source.exists():
        return
    x, y, w, h = box
    caption_space = 34
    frame_h = h - caption_space
    image = autocrop(Image.open(source).convert("RGB"))
    scale = min(w / image.width, frame_h / image.height)
    size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    image = image.resize(size, Image.LANCZOS)
    offset = (x + (w - size[0]) // 2, y + (frame_h - size[1]) // 2)
    canvas.paste(image, offset)
    draw.rectangle([offset, (offset[0] + size[0], offset[1] + size[1])],
                   outline="#2a3344", width=2)
    draw.text((x + w // 2, y + h - caption_space + 8), caption,
              fill=MUTED, font=font(19), anchor="ma")


def main() -> None:
    canvas = Image.new("RGB", CANVAS, BACKGROUND)
    draw = ImageDraw.Draw(canvas)

    draw.text((PAD, 18), "HotSpot Sentinels — live prototype", fill=INK, font=font(34, bold=True))
    draw.text((PAD, 62),
              "Pasir Panjang Terminal, Singapore, analysed from Google satellite imagery, 2026-10-14",
              fill=MUTED, font=font(20))

    # Two columns of two: a narrow sidebar or a thin banner is unreadable once
    # scaled into a six-up grid, so only the four legible panels are shown.
    top = 112
    col_w = (CANVAS[0] - PAD * 3) // 2
    row_h = (CANVAS[1] - top - PAD * 2) // 2

    place(canvas, "02-hvi-metrics.png", (PAD, top, col_w, row_h),
          "HVI 8.6 CRITICAL · 31.0 °C measured from NOAA GSOD · alert dispatched", draw)
    place(canvas, "09-alert-wall.png", (PAD * 2 + col_w, top, col_w, row_h),
          "Public alert wall — citizens see CRITICAL zones live, no sign-in", draw)

    bottom = top + row_h + PAD
    place(canvas, "08-surface-chart.png", (PAD, bottom, col_w, row_h),
          "Surface breakdown driving the score: 65% asphalt, 0% canopy", draw)
    place(canvas, "03-breakdown-and-blueprint.png", (PAD * 2 + col_w, bottom, col_w, row_h),
          "Passive cooling blueprint, in metric quantities", draw)

    canvas.save(OUTPUT)
    print("wrote", OUTPUT.relative_to(ROOT), canvas.size)


if __name__ == "__main__":
    main()

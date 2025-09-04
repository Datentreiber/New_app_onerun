# blocks/components/visual/gif_label_overlay.py
"""
Purpose
-------
Überlagert pro GIF-Frame Textlabels (z. B. Monat) und setzt die Frame-Dauer
gemäß fps. Generische Visual-Komponente ohne UC-spezifische Konstanten.

Contracts
---------
def label_gif(gif_bytes, labels, fps: int, xy=(10, 10)) -> io.BytesIO

Args
----
gif_bytes : BytesIO | bytes-like
labels : List[str]
fps : int
xy : Tuple[int, int]
    Position links/oben für das Label.

Returns
-------
io.BytesIO : gelabeltes GIF

Side Effects
------------
Keine.
"""

import io
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from typing import List, Tuple

def label_gif(gif_bytes, labels: list, fps: int, xy: Tuple[int, int] = (10, 10)) -> io.BytesIO:
    im = Image.open(gif_bytes)
    frames = []
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except Exception:
        font = ImageFont.load_default()

    for i, frame in enumerate(ImageSequence.Iterator(im)):
        frame_rgba = frame.convert("RGBA")
        overlay = Image.new("RGBA", frame_rgba.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        label = labels[i % len(labels)] if labels else ""
        tw, th = draw.textbbox((0, 0), label, font=font)[2:]
        x, y = xy
        draw.rectangle((x - 6, y - 6, x + tw + 6, y + th + 6), fill=(0, 0, 0, 120))
        draw.text((x, y), label, font=font, fill=(255, 255, 255, 255))

        frames.append(Image.alpha_composite(frame_rgba, overlay).convert("P"))

    out = io.BytesIO()
    duration = max(1, int(1000 / max(1, int(fps))))  # ms per frame
    frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:], loop=0,
                   duration=duration, disposal=2)
    out.seek(0)
    return out

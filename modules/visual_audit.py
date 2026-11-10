"""Deterministic visual checks: dimensions, dominant colours vs palette, WCAG contrast, alt text, optional logo match.

OpenCV template matching is used for logo presence when a reference logo is supplied. These are basic, explainable
checks — not visual AI — and the UI says so.
"""
import io

import numpy as np
from PIL import Image

CHANNEL_SIZES = {"Instagram": [(1080, 1080), (1080, 1350), (1080, 1920)], "LinkedIn": [(1200, 627), (1080, 1080)],
                 "X / Twitter": [(1600, 900), (1200, 675)], "Website": [(1920, 1080), (1200, 630)]}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(hex_to_rgb(a)), luminance(hex_to_rgb(b))
    return round((max(la, lb) + 0.05) / (min(la, lb) + 0.05), 2)


def wcag(ratio, large=False):
    return {"AA": ratio >= (3 if large else 4.5), "AAA": ratio >= (4.5 if large else 7)}


def colour_distance(a, b):
    r1, g1, b1 = hex_to_rgb(a)
    r2, g2, b2 = hex_to_rgb(b)
    rm = (r1 + r2) / 2
    return round((((512 + rm) * (r1 - r2) ** 2) / 256 + 4 * (g1 - g2) ** 2 + ((767 - rm) * (b1 - b2) ** 2) / 256) ** 0.5, 1)


def load(data: bytes):
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as e:
        raise ValueError(f"This image could not be opened ({str(e)[:80]}).") from e


def dominant_colours(im, n=6):
    small = im.copy()
    small.thumbnail((200, 200))
    q = small.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: n * 3]
    total = small.width * small.height
    return [(rgb_to_hex(tuple(pal[i * 3:i * 3 + 3])), round(100 * cnt / total, 1)) for cnt, i in sorted(q.getcolors(), reverse=True)]


def logo_match(im, logo_data):
    """Best normalised template-matching score (0-1) of the logo inside the image, over several scales."""
    import cv2
    img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
    logo = cv2.cvtColor(np.array(load(logo_data)), cv2.COLOR_RGB2GRAY)
    best = 0.0
    for scale in np.linspace(0.2, 1.2, 11):
        w, h = int(logo.shape[1] * scale), int(logo.shape[0] * scale)
        if w < 12 or h < 12 or w > img.shape[1] or h > img.shape[0]:
            continue
        res = cv2.matchTemplate(img, cv2.resize(logo, (w, h)), cv2.TM_CCOEFF_NORMED)
        best = max(best, float(res.max()))
    return round(best, 3)


def audit(data, channel="Instagram", alt_text="", palette=None, min_contrast=4.5, text_hex=None, bg_hex=None, logo_data=None):
    im = load(data)
    cols = dominant_colours(im)
    findings = []
    sizes = CHANNEL_SIZES.get(channel)
    if sizes and im.size not in sizes:
        findings.append(("low", f"{im.width}×{im.height}px is not a standard {channel} size ({', '.join(f'{w}×{h}' for w, h in sizes)})."))
    if not (alt_text or "").strip():
        findings.append(("medium", "No alternative text provided for this image."))
    ratio = None
    if text_hex and bg_hex:
        ratio = contrast(text_hex, bg_hex)
        if ratio < min_contrast:
            findings.append(("high", f"Text contrast {ratio}:1 is below the brand minimum of {min_contrast}:1."))
    off = []
    if palette:
        for hx, pct in cols:
            name, ref = min(palette.items(), key=lambda kv: colour_distance(hx, kv[1]))
            d = colour_distance(hx, ref)
            neutral = max(hex_to_rgb(hx)) - min(hex_to_rgb(hx)) < 18  # greys/whites are not brand-colour violations
            if d > 80 and pct >= 8 and not neutral:
                off.append(hx)
                findings.append(("low", f"{hx} covers {pct}% of the image and is far from any brand colour (nearest: {name} {ref})."))
    logo = None
    if logo_data:
        logo = logo_match(im, logo_data)
        if logo < 0.6:
            findings.append(("medium", f"The approved logo was not clearly found (best match {logo:.2f}; 0.60 needed)."))
    return {"size": im.size, "colours": cols, "contrast": ratio, "logo_score": logo, "findings": findings}

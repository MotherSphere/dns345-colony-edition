#!/usr/bin/env python3
"""Generate the Colony Edition PNG assets that replace D-Link's UI sprites.

Each asset is produced at the **exact pixel dimensions** of the D-Link
file it replaces - this is mandatory because D-Link's CSS hardcodes width
and height. Use ``../../docs/dlink-ui-catalogue.md`` as the source of
truth for dimensions.

Outputs land under ``../assets/`` mirroring the path under D-Link's
``/usr/local/modules/web/`` so the bind-mount layout is one-to-one.

Run: ``python3 build-assets.py``  (requires Pillow + JetBrainsMono Nerd Font)
"""

from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------------------
# Colony palette (matches ../css/colony-tokens.css)
# ---------------------------------------------------------------------------
INK              = (46,  26,  20, 255)
INK_DIM          = (102, 66,  51, 255)
INK_VERY_DIM     = (140, 107, 82,  242)  # ~95% alpha
RED              = (125, 35,  51, 255)
RED_HOVER        = (150, 45,  62, 255)
RED_PRESSED      = (100, 25,  42, 255)
RED_SOFT         = (125, 35,  51,  77)   # ~30% alpha
RED_VERY_SOFT    = (125, 35,  51,  31)   # ~12% alpha
PARCHMENT        = (255, 252, 242, 255)
PARCHMENT_HOVER  = (252, 239, 219, 255)
PARCHMENT_PRESSED = (242, 225, 199, 255)
PARCHMENT_SOFT   = (247, 237, 217, 255)
PARCHMENT_DISABLED = (245, 240, 227, 153)  # 60% alpha


# ---------------------------------------------------------------------------
# Fonts - JetBrainsMono Nerd Font
# ---------------------------------------------------------------------------
FONT_DIR = Path("/usr/share/fonts/TTF")
FONT_REGULAR = FONT_DIR / "JetBrainsMonoNerdFont-Regular.ttf"
FONT_MEDIUM  = FONT_DIR / "JetBrainsMonoNerdFont-Medium.ttf"
FONT_BOLD    = FONT_DIR / "JetBrainsMonoNerdFont-Bold.ttf"

# ---------------------------------------------------------------------------
# Output layout - mirror of /usr/local/modules/web/ subset we override
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
OUT_ROOT = HERE.parent / "assets"


def out(rel_path: str) -> Path:
    """Resolve and ensure parent dirs for an output asset path."""
    p = OUT_ROOT / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Button factory
# ---------------------------------------------------------------------------
def button(
    width: int,
    height: int,
    *,
    bg=PARCHMENT,
    border_color=INK_DIM,
    accent_color=None,        # bottom 2px accent line, e.g. RED
    text: str = "",
    text_color=INK,
    font_size: int = 12,
    font_path: Path = FONT_MEDIUM,
    radius: int = 3,
):
    """Render a Colony-styled button as a flat PNG with rounded corners."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded rect background
    d.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=bg, outline=border_color, width=1)

    # Optional accent bar at the bottom (2px tall, leaves the corner radius)
    if accent_color is not None:
        d.rounded_rectangle((1, height - 4, width - 2, height - 2), radius=1, fill=accent_color)

    # Centered text
    if text:
        font = ImageFont.truetype(str(font_path), font_size)
        # Use textbbox for accurate measurement (Pillow >= 8)
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (width - tw) // 2 - bbox[0]
        y = (height - th) // 2 - bbox[1]
        d.text((x, y), text, font=font, fill=text_color)

    return img


# ---------------------------------------------------------------------------
# Parchment texture fill
# ---------------------------------------------------------------------------
def parchment_fill(width: int, height: int, *, base=PARCHMENT, vignette: bool = True):
    """Solid parchment with optional subtle vignette for paper feel."""
    img = Image.new("RGBA", (width, height), base)
    if vignette and width > 6 and height > 6:
        # Very subtle inner shadow
        d = ImageDraw.Draw(img)
        for i in range(3):
            alpha = 18 - i * 6
            d.rectangle((i, i, width - 1 - i, height - 1 - i), outline=(46, 26, 20, alpha))
    return img


# ===========================================================================
# Generators
# ===========================================================================

def gen_buttons():
    """Replace D-Link's button sprites with Colony equivalents."""
    sizes = {
        # filename relative to web root, dimensions, label
        "pages/images/button/button.png":           (80,  25, "OK",       12),
        "pages/images/button/button-h.png":         (80,  25, "OK",       12),
        "pages/images/button/button-display.png":   (80,  25, "OK",       12),
        "pages/images/button/min-button.png":       (100, 31, "Next",     13),
        "pages/images/button/min-h-button.png":     (100, 31, "Next",     13),
        "pages/images/button/min-button-display.png":(100,31, "Next",     13),
        "pages/images/button/medium-button.png":    (131, 25, "Apply",    12),
        "pages/images/button/medium-h-button.png":  (131, 25, "Apply",    12),
        "pages/images/button/middle-button-display.png": (131,25, "Apply",12),
        "pages/images/button/max-button.png":       (189, 25, "",          12),
        "pages/images/button/max-h-button.png":     (189, 25, "",          12),
        "pages/images/button/max-button-display.png":(189,25, "",          12),
        "pages/images/button/max-generic-button.png":(189,25, "",          12),
        "pages/images/button/max-generic-h-button.png":(189,25,"",         12),
        "pages/images/button/max-wizard-button.png":(189, 25, "",          12),
        "pages/images/button/max-wizard-h-button.png":(189,25,"",          12),
        "pages/images/button/large-button.png":     (385, 25, "",          12),
        "pages/images/button/large-h-button.png":   (385, 25, "",          12),
        "pages/images/button/large-button-display.png":(385,25,"",         12),
    }

    for rel, (w, h, label, fs) in sizes.items():
        # Buttons render WITHOUT inline text by default (label is set in HTML).
        # We just provide the surface. But for the smaller test buttons we
        # keep a placeholder label in case the HTML doesn't override.
        is_hover = "-h-" in rel or rel.endswith("-h.png")
        is_disabled = "display" in rel

        if is_disabled:
            bg = PARCHMENT_DISABLED
            border = INK_VERY_DIM
            accent = None
        elif is_hover:
            bg = PARCHMENT_PRESSED
            border = RED
            accent = RED
        else:
            bg = PARCHMENT_HOVER
            border = INK_DIM
            accent = RED

        # No text on the button surface itself - the HTML <div> child renders the label.
        img = button(w, h, bg=bg, border_color=border, accent_color=accent, text="")
        path = out(rel)
        img.save(path, "PNG", optimize=True)
        print(f"  button   {w:>3}x{h:<3}  {rel}")


def gen_login_button():
    """Login screen button 170x38. Same image is used by .menu_off for top nav.

    Also produces button_over.png (the .menu_hover variant).
    """
    for rel, hover in [
        ("pages/images/button.png", False),      # normal (.menu_off too)
        ("pages/images/light_bt.png", True),     # login hover
        ("pages/images/button_over.png", True),  # .menu_hover variant
    ]:
        bg = PARCHMENT_PRESSED if hover else PARCHMENT_HOVER
        accent = RED_HOVER if hover else RED
        img = button(170, 38, bg=bg, border_color=accent, accent_color=accent, radius=4)
        img.save(out(rel), "PNG", optimize=True)
        print(f"  login    170x38   {rel}  hover={hover}")


def gen_menu_top_button():
    """Top-nav .menu_on button background, 180x48 - the wider/selected variant."""
    rel = "pages/images/button-on.png"
    img = button(180, 48, bg=PARCHMENT_PRESSED, border_color=RED, accent_color=RED, radius=6)
    img.save(out(rel), "PNG", optimize=True)
    print(f"  menu_on  180x48   {rel}")


def gen_panel_backgrounds():
    """Side-panel backgrounds (.device_status, .volume_info)."""
    for rel, (w, h) in {
        "pages/images/lbox_bg.jpg": (260, 475),
        "pages/images/v_bg.png":    (253, 65),
    }.items():
        img = parchment_fill(w, h, base=PARCHMENT_SOFT, vignette=True)
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, 3, h), fill=RED)  # burgundy left edge
        if rel.endswith(".jpg"):
            img.convert("RGB").save(out(rel), "JPEG", quality=92, optimize=True)
        else:
            img.save(out(rel), "PNG", optimize=True)
        print(f"  panel    {w:>3}x{h:<3}  {rel}")


def gen_close_button():
    """Modal close X button - 32x35."""
    for rel, hover in [
        ("pages/images/close.png", False),
        ("pages/images/close_o.png", True),
    ]:
        img = Image.new("RGBA", (32, 35), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # circular X background
        cx, cy, r = 16, 17, 11
        bg = RED if hover else INK_DIM
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=bg)
        # X glyph
        d.line((cx - 5, cy - 5, cx + 5, cy + 5), fill=PARCHMENT, width=2)
        d.line((cx - 5, cy + 5, cx + 5, cy - 5), fill=PARCHMENT, width=2)
        img.save(out(rel), "PNG", optimize=True)
        print(f"  close    32x35    {rel}  hover={hover}")


def gen_login_panel():
    """The 383x325 'login.png' contains the dim "Login" watermark + the grey
    metallic panel in a single composite image. We replace with a small
    "Login" watermark at the very top and a tall parchment panel taking up
    most of the image, so the form content fits inside the visible box.
    """
    rel = "pages/images/login.png"
    w, h = 383, 325
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Compact "Login" watermark in upper-left corner, leaves room for the panel
    title_font = ImageFont.truetype(str(FONT_BOLD), 40)
    d.text((6, 0), "Login", font=title_font, fill=(125, 35, 51, 90))

    # Panel covers most of the image: starts just below watermark, ends at bottom
    panel_top = 48
    d.rounded_rectangle(
        (3, panel_top, w - 4, h - 4),
        radius=8,
        fill=PARCHMENT,
        outline=RED,
        width=2,
    )
    # Subtle inner shadow for depth
    d.rounded_rectangle(
        (5, panel_top + 2, w - 6, h - 6),
        radius=7,
        outline=(46, 26, 20, 25),
        width=1,
    )
    img.save(out(rel), "PNG", optimize=True)
    print(f"  login    {w:>3}x{h:<3}  {rel}  (panel + watermark)")


def gen_body_bg():
    """1x768 vertical strip used as body background repeat-x. Simple parchment."""
    rel = "pages/images/bg.png"
    img = Image.new("RGB", (1, 768), (255, 252, 242))
    img.save(out(rel), "PNG", optimize=True)
    print(f"  body_bg  1x768    {rel}")


def gen_pop_bg():
    """Modal popup background - 4x550 tile, repeats horizontally.

    D-Link uses repeat-x so the *width* is small and the *height* covers
    the popup. We provide a parchment vertical strip.
    """
    rel = "pages/images/pop_bg.png"
    img = parchment_fill(4, 550, base=PARCHMENT, vignette=False)
    img.save(out(rel), "PNG", optimize=True)
    print(f"  pop_bg   4x550    {rel}")


def gen_logos():
    """Main logo (207x28) and small variant (73x18). Burgundy "Colony NAS" text on transparent bg."""
    for rel, (w, h, text, fs) in {
        "pages/images/logo.png":  (207, 28, "COLONY NAS",  16),
        "pages/images/logo2.png": (73,  18, "COLONY",       11),
    }.items():
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        font = ImageFont.truetype(str(FONT_BOLD), fs)
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (w - tw) // 2 - bbox[0]
        y = (h - th) // 2 - bbox[1]
        # Slight shadow for embossed effect
        d.text((x + 1, y + 1), text, font=font, fill=(46, 26, 20, 60))
        d.text((x, y), text, font=font, fill=RED)
        img.save(out(rel), "PNG", optimize=True)
        print(f"  logo     {w:>3}x{h:<3}  {rel}")


def gen_banner_pieces():
    """Header banner ornaments. These are tiny strips used as decorative caps.

    banner_left.png / banner_right.png are 10x110 (the tall main header).
    banner_left2.png / banner_right2.png / banner_center2.png are 10x36
    (the slimmer secondary banner under the main one).
    The center2 file tiles horizontally via repeat-x.
    """
    pieces = {
        "pages/images/management/banner_left.png":    (10, 110, "left",  False),
        "pages/images/management/banner_right.png":   (10, 110, "right", False),
        "pages/images/management/banner_left2.png":   (10, 36,  "left",  True),
        "pages/images/management/banner_right2.png":  (10, 36,  "right", True),
        "pages/images/management/banner_center2.png": (10, 36,  "center", True),
    }
    for rel, (w, h, kind, slim) in pieces.items():
        img = Image.new("RGBA", (w, h), PARCHMENT_SOFT if slim else PARCHMENT)
        d = ImageDraw.Draw(img)
        if kind == "left":
            # rounded left, straight right
            for y in range(h):
                # paint a burgundy left edge 2px wide
                d.line((0, y, 1, y), fill=RED)
        elif kind == "right":
            for y in range(h):
                d.line((w - 2, y, w - 1, y), fill=RED)
        else:  # center
            # thin burgundy line at the bottom
            d.line((0, h - 1, w - 1, h - 1), fill=RED)
        img.save(out(rel), "PNG", optimize=True)
        print(f"  banner   {w:>3}x{h:<3}  {rel}  kind={kind}")


def _draw_icon_disk(d, cx, cy, size, color):
    """Stacked hard-drive platters icon."""
    w = int(size * 1.1)
    h = size
    x0, y0 = cx - w // 2, cy - h // 2
    plate_h = h // 4
    for i in range(3):
        y = y0 + i * (plate_h + 4)
        d.rounded_rectangle((x0, y, x0 + w, y + plate_h), radius=3, outline=color, width=3)
        d.ellipse((x0 + w - plate_h + 4, y + plate_h // 2 - 2,
                   x0 + w - plate_h + 8, y + plate_h // 2 + 2), fill=color)


def _draw_icon_account(d, cx, cy, size, color):
    """Person silhouette."""
    head_r = size // 5
    head_cy = cy - size // 4
    d.ellipse((cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r),
              outline=color, width=3)
    body_w = size // 2
    body_top = head_cy + head_r + size // 12
    body_bot = cy + size // 3
    d.polygon([
        (cx - body_w // 2, body_bot),
        (cx + body_w // 2, body_bot),
        (cx + body_w // 3, body_top),
        (cx - body_w // 3, body_top),
    ], outline=color, width=3)


def _draw_icon_network(d, cx, cy, size, color):
    """Three connected nodes."""
    r = size // 8
    top = (cx, cy - size // 3)
    left = (cx - size // 3, cy + size // 4)
    right = (cx + size // 3, cy + size // 4)
    for a, b in [(top, left), (top, right), (left, right)]:
        d.line([a, b], fill=color, width=3)
    for (nx, ny) in (top, left, right):
        d.ellipse((nx - r, ny - r, nx + r, ny + r), fill=color)


def _draw_icon_app(d, cx, cy, size, color):
    """2x2 grid of rounded squares."""
    cell = size // 3
    gap = size // 12
    x0 = cx - cell - gap // 2
    y0 = cy - cell - gap // 2
    for ix in range(2):
        for iy in range(2):
            x = x0 + ix * (cell + gap)
            y = y0 + iy * (cell + gap)
            d.rounded_rectangle((x, y, x + cell, y + cell), radius=3, fill=color)


def _draw_icon_system(d, cx, cy, size, color):
    """Gear / cog (8 teeth as star polygon)."""
    import math
    outer = size // 2
    inner = int(outer * 0.7)
    teeth_outer = int(outer * 1.05)
    pts = []
    for i in range(16):
        angle = i * (2 * math.pi / 16) - math.pi / 2
        r = teeth_outer if i % 2 == 0 else inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    d.polygon(pts, outline=color, width=3)
    d.ellipse((cx - outer // 3, cy - outer // 3, cx + outer // 3, cy + outer // 3),
              outline=color, width=3)


def _draw_icon_status(d, cx, cy, size, color):
    """Ascending 3-bar chart."""
    bar_w = size // 6
    gap = size // 12
    base_y = cy + size // 3
    heights = [size // 3, size // 2, int(size * 0.7)]
    x = cx - (bar_w * 3 + gap * 2) // 2
    for h in heights:
        d.rectangle((x, base_y - h, x + bar_w, base_y), fill=color)
        x += bar_w + gap


def gen_menu_icons():
    """Top-nav menu icons 140x156, on/off.

    Drawn as vector shapes in PIL (no Nerd Font codepoint dependency
    so reproducible across machines).
    """
    drawers = {
        "disk":    _draw_icon_disk,
        "account": _draw_icon_account,
        "network": _draw_icon_network,
        "app":     _draw_icon_app,
        "system":  _draw_icon_system,
        "status":  _draw_icon_status,
    }
    labels = {
        "disk": "Disk", "account": "Account", "network": "Network",
        "app": "Application", "system": "System", "status": "Status",
    }
    for kind, drawer in drawers.items():
        for on in (True, False):
            state = "on" if on else "off"
            rel = f"pages/images/management/{kind}_{state}.png"
            w, h = 140, 156
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            bg = PARCHMENT_PRESSED if on else PARCHMENT_HOVER
            border = RED if on else INK_VERY_DIM
            d.rounded_rectangle((2, 2, w - 3, h - 3), radius=6, fill=bg,
                                outline=border, width=2 if on else 1)
            drawer(d, w // 2, 60, 64, RED if on else INK_DIM)
            label_font = ImageFont.truetype(str(FONT_MEDIUM), 13)
            bbox = d.textbbox((0, 0), labels[kind], font=label_font)
            lw = bbox[2] - bbox[0]; lh = bbox[3] - bbox[1]
            lx = (w - lw) // 2 - bbox[0]
            ly = h - lh - 14
            d.text((lx, ly), labels[kind], font=label_font, fill=INK if on else INK_DIM)
            img.save(out(rel), "PNG", optimize=True)
            print(f"  menu     140x156  {rel}  on={on}")




def gen_logout_icon():
    rel = "pages/images/management/logout.png"
    w, h = 87, 46
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, w - 3, h - 3), radius=4, fill=PARCHMENT_HOVER, outline=RED, width=1)
    font = ImageFont.truetype(str(FONT_MEDIUM), 12)
    text = "Log out"
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
    x = (w - tw) // 2 - bbox[0]
    y = (h - th) // 2 - bbox[1]
    d.text((x, y), text, font=font, fill=RED)
    img.save(out(rel), "PNG", optimize=True)
    print(f"  logout   87x46    {rel}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    print("Generating Colony Edition assets ->", OUT_ROOT)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    gen_buttons()
    gen_login_button()
    gen_menu_top_button()
    gen_login_panel()
    gen_body_bg()
    gen_close_button()
    gen_pop_bg()
    gen_logos()
    gen_banner_pieces()
    gen_menu_icons()
    gen_logout_icon()
    gen_panel_backgrounds()

    total = sum(1 for _ in OUT_ROOT.rglob("*.png"))
    print(f"\nDone. {total} PNG files under {OUT_ROOT}")


if __name__ == "__main__":
    main()

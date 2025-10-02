from PIL import Image, ImageDraw, ImageFont
from config import (label_area_mm, grid_label_font_mm, project_name,
                    font_path, grid_line_width, font_scale, letters)
from utils import center_in_cell

def make_grid(img, cols, rows, tile_size, px_per_mm, dpi, output_grid):
    label_area_px = int(label_area_mm * px_per_mm)

    grid_w = tile_size * cols + tile_size
    grid_h = tile_size * rows + tile_size
    grid_img = Image.new("RGBA", (grid_w, grid_h + label_area_px), (255, 255, 255, 255))

    grid_img.paste(img, (tile_size, tile_size + label_area_px))
    draw = ImageDraw.Draw(grid_img)

    for c in range(cols + 1):
        x = tile_size + c * tile_size
        draw.line([(x, tile_size + label_area_px), (x, grid_h + label_area_px)], fill="black", width=grid_line_width)
    for r in range(rows + 1):
        y = tile_size + r * tile_size
        draw.line([(tile_size, y + label_area_px), (grid_w, y + label_area_px)], fill="black", width=grid_line_width)

    font_size_grid = int(tile_size * font_scale)
    try:
        font_grid = ImageFont.truetype(font_path, font_size_grid)
    except OSError:
        font_grid = ImageFont.load_default()

    for c in range(cols):
        txt = str(c + 1)
        x, y = center_in_cell(draw, txt, tile_size + c * tile_size, 0, tile_size, tile_size, font_grid)
        draw.text((x, y + label_area_px), txt, fill="black", font=font_grid)

    for r in range(rows):
        txt = letters[r]
        x, y = center_in_cell(draw, txt, 0, tile_size + r * tile_size, tile_size, tile_size, font_grid)
        draw.text((x, y + label_area_px), txt, fill="black", font=font_grid)

    draw_label = ImageDraw.Draw(grid_img)
    grid_label_font_size = int(grid_label_font_mm * px_per_mm)
    label_font = ImageFont.truetype(font_path, grid_label_font_size)
    bbox = draw_label.textbbox((0, 0), project_name, font=label_font)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw_label.text(((grid_w - lw) // 2, (label_area_px - lh) // 2),
                    project_name, font=label_font, fill="black")

    grid_img.save(output_grid, dpi=(dpi, dpi))

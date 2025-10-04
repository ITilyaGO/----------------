from PIL import Image, ImageDraw, ImageFont
import config  # ✅ вместо импорта отдельных переменных
from utils import center_in_cell

def make_grid(img, cols, rows, tile_size, px_per_mm, dpi, output_grid):
    label_area_px = int(config.label_area_mm * px_per_mm)

    grid_w = tile_size * cols + tile_size
    grid_h = tile_size * rows + tile_size
    grid_img = Image.new("RGBA", (grid_w, grid_h + label_area_px), (255, 255, 255, 255))

    grid_img.paste(img, (tile_size, tile_size + label_area_px))
    draw = ImageDraw.Draw(grid_img)

    # === линии сетки ===
    for c in range(cols + 1):
        x = tile_size + c * tile_size
        draw.line([(x, tile_size + label_area_px), (x, grid_h + label_area_px)],
                  fill="black", width=config.grid_line_width)
    for r in range(rows + 1):
        y = tile_size + r * tile_size
        draw.line([(tile_size, y + label_area_px), (grid_w, y + label_area_px)],
                  fill="black", width=config.grid_line_width)

    # === подписи ===
    font_size_grid = int(tile_size * config.font_scale)
    try:
        font_grid = ImageFont.truetype(config.font_path, font_size_grid)
    except OSError:
        font_grid = ImageFont.load_default()

    # цифры сверху
    for c in range(cols):
        txt = str(c + 1)
        x, y = center_in_cell(draw, txt,
                              tile_size + c * tile_size, 0,
                              tile_size, tile_size, font_grid)
        draw.text((x, y + label_area_px), txt, fill="black", font=font_grid)

    # буквы слева
    for r in range(rows):
        txt = config.letters[r]
        x, y = center_in_cell(draw, txt,
                              0, tile_size + r * tile_size,
                              tile_size, tile_size, font_grid)
        draw.text((x, y + label_area_px), txt, fill="black", font=font_grid)

    # === подпись проекта ===
    draw_label = ImageDraw.Draw(grid_img)
    grid_label_font_size = int(config.grid_label_font_mm * px_per_mm)
    label_font = ImageFont.truetype(config.font_path, grid_label_font_size)
    bbox = draw_label.textbbox((0, 0), config.project_name, font=label_font)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw_label.text(((grid_w - lw) // 2, (label_area_px - lh) // 2),
                    config.project_name, font=label_font, fill="black")

    # === сохранение ===
    grid_img.save(output_grid, dpi=(dpi, dpi))
    print(f"📏 Сохранён файл сетки: {output_grid}")

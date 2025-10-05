from PIL import Image, ImageDraw, ImageFont
from utils import center_in_cell


def make_grid(cfg, img, tile_size, px_per_mm, dpi, output_path):
    """
    Создаёт изображение с сеткой и подписями по данным из cfg.
    Сохраняет результат в указанный файл (например, grid.png).
    """
    print("📏 Генерация сетки...")

    label_area_px = int(cfg.label_area_mm * px_per_mm)
    grid_w = tile_size * cfg.cols + tile_size
    grid_h = tile_size * cfg.rows + tile_size
    grid_img = Image.new("RGBA", (grid_w, grid_h + label_area_px), (255, 255, 255, 255))

    grid_img.paste(img, (tile_size, tile_size + label_area_px))
    draw = ImageDraw.Draw(grid_img)

    # === линии сетки ===
    for c in range(cfg.cols + 1):
        x = tile_size + c * tile_size
        draw.line([(x, tile_size + label_area_px), (x, grid_h + label_area_px)],
                  fill="black", width=cfg.grid_line_width)
    for r in range(cfg.rows + 1):
        y = tile_size + r * tile_size
        draw.line([(tile_size, y + label_area_px), (grid_w, y + label_area_px)],
                  fill="black", width=cfg.grid_line_width)

    # === шрифты ===
    font_size_grid = int(tile_size * cfg.font_scale)
    try:
        print(f"🧮 grid_label_font_mm={cfg.grid_label_font_mm}, px_per_mm={px_per_mm}, font_px={cfg.grid_label_font_mm * px_per_mm}")
        font_grid = ImageFont.truetype(cfg.font_path, font_size_grid)
    except OSError:
        font_grid = ImageFont.load_default()

    # === цифры сверху ===
    for c in range(cfg.cols):
        txt = str(c + 1)
        x, y = center_in_cell(draw, txt,
                              tile_size + c * tile_size, 0,
                              tile_size, tile_size, font_grid)
        draw.text((x, y + label_area_px), txt, fill="black", font=font_grid)

    # === буквы слева ===
    for r in range(cfg.rows):
        txt = cfg.letters[r]
        x, y = center_in_cell(draw, txt,
                              0, tile_size + r * tile_size,
                              tile_size, tile_size, font_grid)
        draw.text((x, y + label_area_px), txt, fill="black", font=font_grid)

    # === подпись проекта ===
    
    grid_label_font_size = int(cfg.grid_label_font_mm * px_per_mm)
    label_font = ImageFont.truetype(cfg.font_path, grid_label_font_size)
    bbox = draw.textbbox((0, 0), cfg.project_name, font=label_font)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((grid_w - lw) // 2, (label_area_px - lh) // 2),
                    cfg.project_name, font=label_font, fill="black")
    
    # try:
    #     label_font = ImageFont.truetype(cfg.font_path, int(cfg.grid_label_font_mm * px_per_mm))
    # except OSError:
    #     print("⚠️ Не удалось загрузить шрифт для подписи проекта, будет использован шрифт по умолчанию.")
    #     label_font = ImageFont.load_default()

    # bbox = label_font.getbbox(cfg.project_name)
    # lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # draw.text(((grid_w - lw) // 2, (label_area_px - lh) // 2),
    #         cfg.project_name, font=label_font, fill="black")


    # === сохранение ===
    grid_img.save(output_path, dpi=(dpi, dpi))
    print(f"💾 Сетка сохранена → {output_path}")

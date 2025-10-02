from PIL import Image

def load_image(path, cols, rows):
    print("📂 Загружаем изображение...")
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    dpi = img.info.get("dpi", (96, 96))[0]
    px_per_mm = dpi / 25.4

    # обрезаем под целое число тайлов
    tile_w = w // cols
    tile_h = h // rows
    tile_size = min(tile_w, tile_h)
    new_w = tile_size * cols
    new_h = tile_size * rows
    if w != new_w or h != new_h:
        img = img.crop((0, 0, new_w, new_h))

    return img, tile_size, px_per_mm, dpi

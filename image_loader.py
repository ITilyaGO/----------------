from PIL import Image

def load_image(path, cols, rows):
    """
    Загружает изображение и подгоняет его под целое число тайлов.
    Возвращает (img, tile_size, px_per_mm, dpi)
    """
    print(f"📂 Загружаем изображение: {path}")
    img = Image.open(path).convert("RGBA")

    w, h = img.size
    dpi = img.info.get("dpi", (96, 96))[0]
    px_per_mm = dpi / 25.4

    # обрезаем, чтобы размеры кратно делились
    tile_w = w // cols
    tile_h = h // rows
    tile_size = min(tile_w, tile_h)
    new_w = tile_size * cols
    new_h = tile_size * rows

    if w != new_w or h != new_h:
        print(f"⚠️ Изображение будет обрезано до {new_w}×{new_h}px")
        img = img.crop((0, 0, new_w, new_h))

    return img, tile_size, px_per_mm, dpi

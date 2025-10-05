import os
from PIL import Image
from tqdm import tqdm


def detect_white_tiles(img, cfg, threshold=250):
    """
    Анализирует изображение и возвращает список координат тайлов,
    которые считаются «белыми» (равномерно светлыми).
    """
    print("🔍 Поиск белых тайлов...")
    tile_size = img.width // cfg.cols
    whites = []

    for row in tqdm(range(cfg.rows), desc="Проверка строк"):
        for col in range(cfg.cols):
            box = (col * tile_size, row * tile_size,
                   (col + 1) * tile_size, (row + 1) * tile_size)
            tile = img.crop(box)
            min_val, max_val = tile.convert("L").getextrema()
            if min_val >= threshold:
                coord = f"{cfg.letters[row]}{col+1}"
                whites.append(coord)

    print(f"📄 Найдено белых тайлов: {len(whites)}")
    return whites


def save_white_tiles(cfg, whites):
    """
    Сохраняет список белых тайлов в out/<project>/white_tiles.txt
    в виде Python-совместимого списка.
    """
    os.makedirs(cfg.project_dir, exist_ok=True)
    with open(cfg.white_tiles_file, "w", encoding="utf-8") as f:
        f.write("exclude_coords = [\n")
        for coord in whites:
            f.write(f'    "{coord}",\n')
        f.write("]\n")
    print(f"💾 Сохранён список белых тайлов → {cfg.white_tiles_file}")


def load_white_tiles(cfg):
    """
    Загружает exclude_coords из out/<project>/white_tiles.txt (если существует).
    Возвращает список координат.
    """
    if not os.path.exists(cfg.white_tiles_file):
        print(f"⚠️ Файл {cfg.white_tiles_file} не найден — белые тайлы не исключаются.")
        return []

    local_vars = {}
    with open(cfg.white_tiles_file, "r", encoding="utf-8") as f:
        code = f.read()
        exec(code, {}, local_vars)
    exclude_coords = local_vars.get("exclude_coords", [])
    print(f"📖 Загружено {len(exclude_coords)} исключений: {exclude_coords}")
    return exclude_coords

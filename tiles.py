import os
import json
import random
import math
import hashlib
from tqdm import tqdm

from PIL import Image


def split_tiles(img, cfg, exclude_coords):
    """Разбивает исходное изображение на тайлы (фильтрует исключённые)."""
    tiles = []
    tile_size = img.width // cfg.cols
    for row in range(cfg.rows):
        for col in range(cfg.cols):
            coord = f"{cfg.letters[row]}{col+1}"
            if coord in exclude_coords:
                continue
            box = (col * tile_size, row * tile_size, (col + 1) * tile_size, (row + 1) * tile_size)
            tile = img.crop(box)
            tiles.append(((row, col), coord, tile))
    return tiles


# ====================================================================== #
# ====================== RANDOM STATE CONTROL ========================== #
# ====================================================================== #

def generate_random_state(cfg, tiles):
    """
    Создаёт и возвращает структуру random_state.json:
      - matrix с координатами тайлов
      - rotation_matrix с углами поворота
      - распределение по страницам
    """
    print("🎲 Генерация нового random_state.json ...")

    # Фиксируем сид (гарантирует повторяемость)
    cfg.init_random()

    total_tiles = len(tiles)
    print(f"Всего тайлов: {total_tiles}")

    # Считаем сколько тайлов помещается на один лист
    px_per_mm = cfg.sheet_export_dpi / 25.4
    shuffled_tile_px = int(cfg.shuffled_tile_mm * px_per_mm)
    gap_px = int(cfg.gap_mm * px_per_mm)
    margin_px = int(cfg.margin_mm * px_per_mm)
    sheet_w_px = int(cfg.sheet_w_mm * px_per_mm)
    sheet_h_px = int(cfg.sheet_h_mm * px_per_mm)

    tiles_per_row = (sheet_w_px - 2 * margin_px + gap_px) // (shuffled_tile_px + gap_px)
    tiles_per_col = (sheet_h_px - 2 * margin_px + gap_px) // (shuffled_tile_px + gap_px)
    tiles_per_sheet = tiles_per_row * tiles_per_col

    print(f"📐 Лист вмещает {tiles_per_row} × {tiles_per_col} = {tiles_per_sheet} тайлов")

    random.shuffle(tiles)
    pages = []

    # распределяем тайлы по страницам
    total_pages = math.ceil(total_tiles / tiles_per_sheet)
    for page_idx in tqdm(range(total_pages), desc="📄 Формирование страниц"):
        start = page_idx * tiles_per_sheet
        end = min(start + tiles_per_sheet, total_tiles)
        page_tiles = tiles[start:end]

        # Создаём пустые матрицы
        matrix = []
        rotation_matrix = []

        for r in range(tiles_per_col):
            row_coords = []
            row_rotations = []
            for c in range(tiles_per_row):
                idx = r * tiles_per_row + c
                if idx < len(page_tiles):
                    (_, coord, _) = page_tiles[idx]
                    row_coords.append(coord)

                    # Генерация поворотов
                    if cfg.rotate_tiles:
                        angle = random.choice([0, 90, 180, 270])
                    elif cfg.rotate_tiles is None:
                        # 50% листов с поворотами
                        angle = random.choice([0, 0, 90, 180, 270])
                    else:
                        angle = 0
                    row_rotations.append(angle)
                else:
                    row_coords.append(None)
                    row_rotations.append(0)

            matrix.append(row_coords)
            rotation_matrix.append(row_rotations)

        pages.append({
            "index": page_idx + 1,
            "rotated": any(any(a != 0 for a in row) for row in rotation_matrix),
            "matrix": matrix,
            "rotation_matrix": rotation_matrix
        })

    # финальная структура
    state = {
        "config_hash": cfg.compute_hash(),
        "seed": cfg.random_seed,
        "tiles_per_row": tiles_per_row,
        "tiles_per_col": tiles_per_col,
        "pages": pages
    }

    save_random_state(cfg, state)
    return state


def save_random_state(cfg, state):
    """Сохраняет random_state.json в проектной папке."""
    with open(cfg.random_state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
    print(f"💾 Сохранён random_state.json → {cfg.random_state_file}")


def load_random_state(cfg):
    """Загружает random_state.json и проверяет его соответствие текущему конфигу."""
    if not os.path.exists(cfg.random_state_file):
        print("⚠️ random_state.json не найден — будет создан новый.")
        return None

    with open(cfg.random_state_file, "r", encoding="utf-8") as f:
        state = json.load(f)

    # проверка хэша
    current_hash = cfg.compute_hash()
    if state.get("config_hash") != current_hash:
        print("⚠️ Конфиг изменился, random_state.json устарел.")
        return None

    print(f"📖 Загружен random_state.json ({len(state['pages'])} страниц)")
    return state

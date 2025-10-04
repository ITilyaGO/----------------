import multiprocessing
multiprocessing.freeze_support()

import argparse
import os
import random
import datetime
from concurrent.futures import ProcessPoolExecutor

from config_manager import auto_load_project, save_config, apply_config_overrides
from image_loader import load_image
from white_tiles import detect_white_tiles
from tiles import split_tiles
from sheets import make_shuffled_sheets
from grid import make_grid
from io_helpers import save_answers
import config  # ✅ импортируем сам модуль, а не отдельные переменные


if __name__ == "__main__":  # 🧩 ВСЁ строго внутри этого блока

    # === Аргументы ===
    parser = argparse.ArgumentParser()
    parser.add_argument("--detect-whites", action="store_true",
                        help="Режим: только поиск белых тайлов и вывод в файл white_tiles.txt")
    args = parser.parse_args()

    # === Загружаем проект ===
    project_name, config_dict = auto_load_project()
    apply_config_overrides(config_dict, "config")  # ✅ исправлено: передаём сам модуль config
    print(f"📁 Текущий проект: {project_name}")

    # === Проверяем входной файл ===
    if not config.input_file or not os.path.exists(config.input_file):
        print(f"❌ Ошибка: файл '{config.input_file}' не найден. Укажите корректный путь в конфиге проекта '{project_name}'.")
        exit(1)

    # === Инициализация сида ===
    if config.random_seed is not None:
        random.seed(config.random_seed)
        print(f"🔑 Используется фиксированный сид: {config.random_seed}")
    else:
        print("🎲 Сид не задан (будет случайный порядок)")

    # === Папки ===
    timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    output_dir = os.path.join("out", project_name, timestamp)
    os.makedirs(output_dir, exist_ok=True)

    output_grid = os.path.join(output_dir, "grid.png")
    output_answers_txt = os.path.join(output_dir, "answers.txt")

    # === Загрузка изображения ===
    print("📂 Загружаем изображение...")
    img, tile_size, px_per_mm, dpi = load_image(config.input_file, config.cols, config.rows)

    # === Авто-DPI ===
    w_px, h_px = img.size
    dpi_x = w_px / (config.sheet_w_mm / 25.4)
    dpi_y = h_px / (config.sheet_h_mm / 25.4)
    export_dpi = (dpi_x + dpi_y) / 2
    print(f"📐 Авто-DPI для печати: {export_dpi:.2f}")

    px_per_mm = export_dpi / 25.4

    # === Белые тайлы ===
    inputs_dir = "inputs"
    os.makedirs(inputs_dir, exist_ok=True)
    whites_file = config_dict.get("exclude_file") or os.path.join(inputs_dir, f"{project_name}_white_tiles.txt")
    config_dict["exclude_file"] = whites_file
    save_config(project_name, config_dict)

    # === Режим поиска белых ===
    if args.detect_whites:
        whites = detect_white_tiles(img, config.cols, config.rows, tile_size)
        with open(whites_file, "w", encoding="utf-8") as f:
            f.write("exclude_coords = [\n")
            for w in whites:
                f.write(f'    "{w}",\n')
            f.write("]\n")
        print(f"📄 Найдено {len(whites)} белых тайлов → {whites_file}")
        exit(0)

    # === Загрузка исключений ===
    exclude_coords = []
    if os.path.exists(whites_file):
        local_vars = {}
        exec(open(whites_file, encoding="utf-8").read(), {}, local_vars)
        exclude_coords = local_vars.get("exclude_coords", [])
        print(f"📖 Загружены исключения ({len(exclude_coords)}): {exclude_coords}")
    else:
        print(f"⚠️ Файл {whites_file} не найден. Можно создать его через whites_gui.py")

    # === Разбиение тайлов ===
    tiles = split_tiles(img, config.cols, config.rows, tile_size, exclude_coords)

    # === Параллельная генерация ===
    with ProcessPoolExecutor() as executor:
        fut_sheets = executor.submit(make_shuffled_sheets, tiles, px_per_mm, export_dpi, output_dir)
        fut_grid = executor.submit(make_grid, img, config.cols, config.rows, tile_size, px_per_mm, export_dpi, output_grid)

        answers_log = fut_sheets.result()
        fut_grid.result()

    # === Сохранение ===
    save_answers(answers_log, config.random_seed, output_answers_txt)
    print("\n✅ Готово!")
    print(f"📂 Папка: {output_dir}")
    print(f"📄 Ответы: {output_answers_txt}")

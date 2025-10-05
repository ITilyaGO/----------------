import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from config import Config
from image_loader import load_image
from tiles import split_tiles, load_random_state, generate_random_state
from white_tiles import detect_white_tiles, save_white_tiles, load_white_tiles
from grid import make_grid
from sheets import make_sheets_from_state
from io_helpers import save_answers


def task_grid(cfg, img, tile_size, px_per_mm, dpi, output_dir):
    """Параллельная задача — генерация сетки."""
    output_path = os.path.join(output_dir, "grid.png")
    make_grid(cfg, img, tile_size, px_per_mm, dpi, output_path)
    return f"💾 Сетка сохранена → {output_path}"


def task_sheets(cfg, img_tiles, state, px_per_mm, dpi, output_dir, threads, selected_pages):
    """Параллельная задача — генерация shuffled и answers-листов."""
    results = make_sheets_from_state(cfg, img_tiles, state, px_per_mm, dpi, output_dir,
                                     threads=threads, pages=selected_pages)
    # results = [(shuffled_path, answers_path), ...]
    answers_log = [f"{os.path.basename(s)}, {os.path.basename(a)}" for s, a in results]

    answers_txt = os.path.join(output_dir, "answers.txt")
    save_answers(answers_log, cfg.random_seed, answers_txt)
    return f"💾 Сгенерированы shuffled/answers-листы → {answers_txt}"



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="🧩 Генератор листов проекта")
    parser.add_argument("--project", type=str, help="Имя проекта (папка в out/)")
    parser.add_argument("--detect-whites", action="store_true", help="Только поиск белых тайлов")
    parser.add_argument("--reshuffle", action="store_true", help="Пересоздать random_state.json")
    parser.add_argument("--pages", type=str, help="Список страниц через запятую (например 1,3,5)")
    parser.add_argument("--threads", type=int, default=None, help="Количество потоков для листов")

    args = parser.parse_args()

    # === Конфиг ===
    project_name = args.project or Config.get_last_project() or input("Введите имя проекта: ").strip()
    cfg = Config().load(project_name)
    Config.set_last_project(project_name)
    cfg.init_random()

    # === Проверяем входной файл ===
    if not cfg.input_file or not os.path.exists(cfg.input_file):
        print(f"❌ Ошибка: файл '{cfg.input_file}' не найден.")
        exit(1)

    # === Загружаем изображение ===
    img, tile_size, px_per_mm, dpi = load_image(cfg.input_file, cfg.cols, cfg.rows)
    output_dir = cfg.make_output_dir()
    # === Авто-DPI как в старом коде ===
    w_px, h_px = img.size
    dpi_x = w_px / (cfg.sheet_w_mm / 25.4)
    dpi_y = h_px / (cfg.sheet_h_mm / 25.4)
    export_dpi = (dpi_x + dpi_y) / 2
    px_per_mm = export_dpi / 25.4

    # Разделяем только на случай, если ты всё же хочешь разное
    px_per_mm_grid = px_per_mm
    px_per_mm_sheets = px_per_mm
    dpi_grid = export_dpi
    dpi_sheets = export_dpi

    print(f"📐 Авто-DPI для печати: {export_dpi:.2f}")
    print(f"ℹ️ px_per_mm: {px_per_mm:.3f}")


    # === Режим: поиск белых тайлов ===
    if args.detect_whites:
        whites = detect_white_tiles(img, cfg)
        save_white_tiles(cfg, whites)
        print("✅ Белые тайлы сохранены. Завершено.")
        exit(0)

    # === Загружаем white_tiles и state ===
    exclude_coords = load_white_tiles(cfg)
    tiles = split_tiles(img, cfg, exclude_coords)
    img_tiles = {coord: tile for (_, coord, tile) in tiles}

    state = load_random_state(cfg)
    if args.reshuffle or not state:
        state = generate_random_state(cfg, tiles)

    # === Список страниц (если указан) ===
    if args.pages:
        selected_indices = [int(x) for x in args.pages.split(",")]
        selected_pages = [p for p in state["pages"] if p["index"] in selected_indices]
    else:
        selected_pages = None

    print("🚀 Запуск параллельной генерации...")

    # === Параллельно запускаем grid и sheets ===
    tasks = []
    with ProcessPoolExecutor(max_workers=2) as pool:
        # GRID рендерим со своим dpi_grid/px_per_mm_grid
        tasks.append(pool.submit(task_grid, cfg, img, tile_size, px_per_mm_grid, dpi_grid, output_dir))

        # SHEETS рендерим с dpi_sheets/px_per_mm_sheets
        tasks.append(pool.submit(task_sheets, cfg, img_tiles, state,
                                px_per_mm_sheets, dpi_sheets, output_dir,
                                args.threads, selected_pages))


        for fut in as_completed(tasks):
            print(fut.result())

    print("\n✅ Готово!")
    print(f"📂 Папка проекта: {output_dir}")

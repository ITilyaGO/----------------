import argparse, os, random
from config import *                     # настройки проекта
from config import make_output_dir       # функция для создания папки
from image_loader import load_image
from white_tiles import detect_white_tiles
from tiles import split_tiles
from sheets import make_shuffled_sheets
from grid import make_grid
from io_helpers import save_answers
from concurrent.futures import ProcessPoolExecutor, as_completed

if random_seed is not None:
    random.seed(random_seed)
    print(f"🔑 Используется фиксированный сид: {random_seed}")
else:
    print("🎲 Сид не задан")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--detect-whites", action="store_true",
                        help="Режим: только поиск белых тайлов и вывод в файл white_tiles.txt")
    args = parser.parse_args()

    # 1) создаём единую папку В ОДНОМ месте
    output_dir = make_output_dir()
    output_grid = os.path.join(output_dir, "grid.png")
    output_answers_txt = os.path.join(output_dir, "answers.txt")

    # 2) грузим изображение
    img, tile_size, px_per_mm, dpi = load_image(input_file, cols, rows)
    # размеры в мм по заданным параметрам
    target_w_mm = sheet_w_mm
    target_h_mm = sheet_h_mm

    # фактические пиксели изображения (с учётом кропа под тайлы)
    w_px, h_px = img.size

    dpi_x = w_px / (target_w_mm / 25.4)
    dpi_y = h_px / (target_h_mm / 25.4)

    export_dpi = (dpi_x + dpi_y) / 2  # усреднённый DPI
    print(f"📐 Авто-DPI для печати: {export_dpi:.2f}")
    
    px_per_mm = export_dpi / 25.4 
    
    # формируем путь к файлу исключений
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    inputs_dir = "inputs"
    os.makedirs(inputs_dir, exist_ok=True)
    whites_file = os.path.join(inputs_dir, f"{base_name}_white_tiles.txt")

    if args.detect_whites:
        whites = detect_white_tiles(img, cols, rows, tile_size)
        with open(whites_file, "w", encoding="utf-8") as f:
            f.write("exclude_coords = [\n")
            for w in whites:
                f.write(f'    "{w}",\n')
            f.write("]\n")
        print(f"📄 Найдено {len(whites)} белых тайлов → {whites_file}")
    else:
        exclude_coords = []
        if os.path.exists(whites_file):
            local_vars = {}
            exec(open(whites_file, encoding="utf-8").read(), {}, local_vars)
            exclude_coords = local_vars.get("exclude_coords", [])
            print(f"📖 Загружены исключения из {whites_file}: {exclude_coords}")
        else:
            # файл не найден → спросим
            answer = input(f"⚠️ Файл исключений {whites_file} не найден. Создать новый? (y/n): ").strip().lower()
            if answer == "y":
                with open(whites_file, "w", encoding="utf-8") as f:
                    f.write("exclude_coords = []\n")
                print(f"🆕 Создан пустой файл исключений: {whites_file}")
            else:
                print("➡️ Продолжаем без исключений.")


        tiles = split_tiles(img, cols, rows, tile_size, exclude_coords)
        with ProcessPoolExecutor() as executor:
            fut_sheets = executor.submit(make_shuffled_sheets, tiles, px_per_mm, export_dpi, output_dir)
            fut_grid = executor.submit(make_grid, img, cols, rows, tile_size, px_per_mm, export_dpi, output_grid)

            answers_log = fut_sheets.result()
            fut_grid.result()

        save_answers(answers_log, random_seed, output_answers_txt)
        print("\n✅ Готово!")
        print(f"📂 Папка: {output_dir}")
        print(f"📄 Ответы: {output_answers_txt}")

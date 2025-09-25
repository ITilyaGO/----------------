from PIL import Image, ImageDraw, ImageFont
import random
import os
import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


random_seed = 654352   # None = случайно, число = фиксированный порядок

if random_seed is not None:
    random.seed(random_seed)
    print(f"🔑 Используется фиксированный сид: {random_seed}")
else:
    print("🎲 Сид не задан, будет случайная генерация")


# === НАСТРОЙКИ ===
input_file = "Хмельники (10 000)_без линий.tif"
cols = 9
rows = 13
grid_line_width = 16
font_scale = 1
save_tiles = False
exclude_coords = ["А2","А3","А4","А5","Б3","Б4","Б5","В4","В5"]
tile_mm_target = 30.0

# путь к шрифту
font_path = "DearType - Lifehack Sans Medium.otf"
Image.MAX_IMAGE_PIXELS = None
letters = list("АБВГДЕЖИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

# === НАСТРОЙКИ ЛИСТОВ ДЛЯ SHUFFLED ===
sheet_w_mm = 210
sheet_h_mm = 297
shuffled_tile_mm = 30
gap_mm = 2.5
margin_mm = 3
rotate_tiles = None       # False/True/None (None = 2 версии)
answer_scale = 0.25
answer_font_scale = 0.9
answer_font_min = 12
answer_outline = True
answer_outline_width = 10
answer_outline_fill = "white"
answer_text_fill = "black"

# === ВЫВОД ===
timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
output_dir = os.path.join(os.getcwd(), "out", timestamp)
os.makedirs(output_dir, exist_ok=True)
output_folder = os.path.join(output_dir, "tiles")
if save_tiles:
    os.makedirs(output_folder, exist_ok=True)

output_grid = os.path.join(output_dir, "grid.png")
output_answers_txt = os.path.join(output_dir, "answers.txt")


# === УТИЛИТЫ ===
def center_in_cell(draw, text, x0, y0, cell_w, cell_h, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = x0 + (cell_w - tw) // 2 - bbox[0]
    y = y0 + (cell_h - th) // 2 - bbox[1]
    return x, y


def draw_text_with_outline(draw, pos, text, font, fill, outline_fill, outline_width):
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx*dx + dy*dy <= outline_width*outline_width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_fill)
    draw.text((x, y), text, font=font, fill=fill)


# === ОСНОВНЫЕ ФУНКЦИИ ===
def load_image(path, cols, rows, tile_mm_target):
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


def split_tiles(img, cols, rows, tile_size, exclude_coords):
    tiles = []
    for row in range(rows):
        for col in range(cols):
            box = (col * tile_size, row * tile_size,
                   (col + 1) * tile_size, (row + 1) * tile_size)
            tile = img.crop(box)
            coord = f"{letters[row]}{col+1}"
            if coord not in exclude_coords:
                tiles.append(((row, col), tile))
    return tiles


def make_shuffled_sheets(tiles, px_per_mm, dpi):
    shuffled_tile_px = int(shuffled_tile_mm * px_per_mm)
    gap_px = int(gap_mm * px_per_mm)
    margin_px = int(margin_mm * px_per_mm)
    sheet_w_px = int(sheet_w_mm * px_per_mm)
    sheet_h_px = int(sheet_h_mm * px_per_mm)

    tiles_per_row = (sheet_w_px - 2*margin_px + gap_px) // (shuffled_tile_px + gap_px)
    tiles_per_col = (sheet_h_px - 2*margin_px + gap_px) // (shuffled_tile_px + gap_px)
    tiles_per_sheet = tiles_per_row * tiles_per_col

    print(f"📄 Лист {sheet_w_mm}x{sheet_h_mm} мм → {tiles_per_row}×{tiles_per_col} тайлов")
    if rotate_tiles is None:
        rotate_modes = [False, True]
    else:
        rotate_modes = [rotate_tiles]

    answers_log = []

    shuf_tiles = tiles[:]
    random.shuffle(shuf_tiles)

    # шрифт для мини-версий
    t_s = int(shuffled_tile_px * answer_scale)
    ans_font_size = max(answer_font_min, int(t_s * answer_font_scale))
    try:
        ans_font = ImageFont.truetype(font_path, ans_font_size)
    except OSError:
        ans_font = ImageFont.load_default()

    for rot_mode in rotate_modes:
        for sheet_idx in range(0, len(shuf_tiles), tiles_per_sheet):
            page_tiles = shuf_tiles[sheet_idx:sheet_idx + tiles_per_sheet]
            sheet_img = Image.new("RGBA", (sheet_w_px, sheet_h_px), (255, 255, 255, 255))

            ans_sheet_w = int(sheet_w_px * answer_scale)
            ans_sheet_h = int(sheet_h_px * answer_scale)
            answer_img = Image.new("RGBA", (ans_sheet_w, ans_sheet_h), (255, 255, 255, 255))
            draw_ans = ImageDraw.Draw(answer_img)

            page_table = [["" for _ in range(tiles_per_row)] for _ in range(tiles_per_col)]

            for i, (orig_pos, tile) in enumerate(page_tiles):
                row_o, col_o = orig_pos
                orig_label = f"{letters[row_o]}{col_o+1}"

                if rot_mode:
                    angle = random.choice([0, 90, 180, 270])
                    tile = tile.rotate(angle, expand=True)

                row = i // tiles_per_row
                col = i % tiles_per_row

                grid_w_used = tiles_per_row * shuffled_tile_px + (tiles_per_row - 1) * gap_px
                grid_h_used = tiles_per_col * shuffled_tile_px + (tiles_per_col - 1) * gap_px
                offset_x = margin_px + (sheet_w_px - 2*margin_px - grid_w_used) // 2
                offset_y = margin_px + (sheet_h_px - 2*margin_px - grid_h_used) // 2

                x = offset_x + col * (shuffled_tile_px + gap_px)
                y = offset_y + row * (shuffled_tile_px + gap_px)
                sheet_img.paste(tile.resize((shuffled_tile_px, shuffled_tile_px)), (x, y))

                # мини версия
                x_s = int(x * answer_scale)
                y_s = int(y * answer_scale)
                tile_small = tile.resize((t_s, t_s))
                answer_img.paste(tile_small, (x_s, y_s))

                tx, ty = center_in_cell(draw_ans, orig_label, x_s, y_s, t_s, t_s, ans_font)
                if answer_outline:
                    draw_text_with_outline(draw_ans, (tx, ty), orig_label,
                                           font=ans_font,
                                           fill=answer_text_fill,
                                           outline_fill=answer_outline_fill,
                                           outline_width=answer_outline_width)
                else:
                    draw_ans.text((tx, ty), orig_label, fill=answer_text_fill, font=ans_font)

                page_table[row][col] = orig_label

            suffix = "_rot" if rot_mode else ""
            
            out_path = os.path.join(output_dir, f"shuffled_{sheet_idx//tiles_per_sheet+1}{suffix}.png")
            sheet_img.save(out_path, dpi=(dpi, dpi))

            # answers_sheet делаем только если rot_mode == False
            if not rot_mode:
                ans_path = os.path.join(output_dir, f"answers_sheet_{sheet_idx//tiles_per_sheet+1}.png")
                answer_img.save(ans_path, dpi=(dpi, dpi))


            answers_log.append(f"\n=== Лист {sheet_idx//tiles_per_sheet+1}{suffix} ===\n")
            for r in page_table:
                answers_log.append("\t".join(r))

    return answers_log


def make_grid(img, cols, rows, tile_size):
    grid_w = tile_size * cols + tile_size
    grid_h = tile_size * rows + tile_size
    grid_img = Image.new("RGBA", (grid_w, grid_h), (255, 255, 255, 255))
    grid_img.paste(img, (tile_size, tile_size))
    draw = ImageDraw.Draw(grid_img)

    for c in range(cols + 1):
        x = tile_size + c * tile_size
        draw.line([(x, tile_size), (x, grid_h)], fill="black", width=grid_line_width)
    for r in range(rows + 1):
        y = tile_size + r * tile_size
        draw.line([(tile_size, y), (grid_w, y)], fill="black", width=grid_line_width)

    font_size_grid = int(tile_size * font_scale)
    try:
        font_grid = ImageFont.truetype(font_path, font_size_grid)
    except OSError:
        font_grid = ImageFont.load_default()

    # цифры сверху
    for c in range(cols):
        txt = str(c + 1)
        x, y = center_in_cell(draw, txt, tile_size + c * tile_size, 0, tile_size, tile_size, font_grid)
        draw.text((x, y), txt, fill="black", font=font_grid)

    # буквы слева
    for r in range(rows):
        txt = letters[r]
        x, y = center_in_cell(draw, txt, 0, tile_size + r * tile_size, tile_size, tile_size, font_grid)
        draw.text((x, y), txt, fill="black", font=font_grid)

    grid_img.save(output_grid)


def save_answers(log, seed):
    with open(output_answers_txt, "w", encoding="utf-8") as f:
        if seed is None:
            f.write("Сид: случайный (не задан пользователем)\n")
        else:
            f.write(f"Сид: {seed}\n")
        f.write("\n".join(log))


# === MAIN ===
if __name__ == "__main__":
    img, tile_size, px_per_mm, dpi = load_image(input_file, cols, rows, tile_mm_target)
    tiles = split_tiles(img, cols, rows, tile_size, exclude_coords)
    answers_log = make_shuffled_sheets(tiles, px_per_mm, dpi)
    save_answers(answers_log, random_seed)
    make_grid(img, cols, rows, tile_size)
    print("\n✅ Готово!")
    print(f"📂 Папка: {output_dir}")
    print(f"📄 Ответы: {output_answers_txt}")

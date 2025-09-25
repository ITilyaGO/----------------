from PIL import Image, ImageDraw, ImageFont
import random
import os
import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm   # pip install tqdm

# === НАСТРОЙКИ ===
# input_file = "Карта квадраты SRA3.png"
input_file = "Хмельники (10 000)_без линий.tif"
cols = 9    # сколько тайлов по горизонтали в исходной карте
rows = 13   # сколько тайлов по вертикали
gap = 80    # расстояние между тайлами (px)
grid_line_width = 16  # толщина линий сетки (px)
font_scale = 1 # доля от размера квадрата (0.35 = 35%)
save_tiles = False
exclude_coords = ["А2","А3","А4","А5","Б3","Б4","Б5","В4","В5"]
tile_mm_target = 30.0

# путь к шрифту
font_path = "DearType - Lifehack Sans Medium.otf"
Image.MAX_IMAGE_PIXELS = None
letters = list("АБВГДЕЖИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

# === НАСТРОЙКИ ЛИСТОВ ДЛЯ SHUFFLED ===
sheet_w_mm = 210   # ширина листа в мм (например, A2 = 420)
sheet_h_mm = 297   # высота листа в мм (например, A2 = 594)
shuffled_tile_mm = 30   # размер тайла на листе в мм
rotate_tiles = False       # поворачивать ли тайлы случайно (0/90/180/270)
answer_scale = 0.25       # масштаб мини-версии листа с ответами
answer_font_scale = 0.9   # доля от размера квадрата (0.35 = 35%)
answer_font_min = 12       # минимальный размер шрифта в px
answer_outline = True      # включить/выключить обводку
answer_outline_width = 10   # толщина обводки (px)
answer_outline_fill = "white"  # цвет обводки
answer_text_fill = "black"   # основной цвет текста
# === ДИРЕКТОРИИ ===
timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
output_dir = os.path.join(os.getcwd(), "out" , timestamp)
os.makedirs(output_dir, exist_ok=True)

output_folder = os.path.join(output_dir, "tiles")
if save_tiles:
    os.makedirs(output_folder, exist_ok=True)

output_grid = os.path.join(output_dir, "grid.png")
output_answers_txt = os.path.join(output_dir, "answers.txt")

# === ВСПОМОГАТЕЛЬНЫЕ ===
def center_in_cell(draw, text, x0, y0, cell_w, cell_h, font):
    """Возвращает координаты для центрирования текста в ячейке"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = x0 + (cell_w - tw) // 2 - bbox[0]
    y = y0 + (cell_h - th) // 2 - bbox[1]
    return x, y

def draw_text_with_outline(draw, pos, text, font, fill, outline_fill, outline_width):
    x, y = pos
    # обводка (все смещения по окружности)
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx*dx + dy*dy <= outline_width*outline_width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_fill)
    # основной текст
    draw.text((x, y), text, font=font, fill=fill)

# === ЗАГРУЗКА ===
print("📂 Загружаем изображение...")
img = Image.open(input_file).convert("RGBA")
w, h = img.size

dpi = img.info.get("dpi", (96, 96))[0]
print("DPI - ", dpi)
px_per_mm = w / (cols * tile_mm_target)
px_per_mm = dpi / 25.4

# === РАСЧЁТ РАЗМЕРА КВАДРАТОВ ===
tile_w = w // cols
tile_h = h // rows
tile_size = min(tile_w, tile_h)
tile_w = tile_h = tile_size

new_w = tile_w * cols
new_h = tile_h * rows
crop_x = w - new_w
crop_y = h - new_h
if crop_x > 0 or crop_y > 0:
    print(f"⚠️ Отброшено справа: {crop_x}px, снизу: {crop_y}px")
img = img.crop((0, 0, new_w, new_h))

tile_mm = tile_size / px_per_mm
print(f"🔲 Размер квадрата: {tile_size}px ≈ {tile_mm:.2f} мм")

# === РАЗБИВАЕМ НА КУСОЧКИ ===
tiles = []
for row in range(rows):
    for col in range(cols):
        box = (col * tile_w, row * tile_h, (col + 1) * tile_w, (row + 1) * tile_h)
        tile = img.crop(box)
        tiles.append(((row, col), tile))  # сохраняем исходные координаты

# === УБИРАЕМ ИСКЛЮЧЁННЫЕ КООРДИНАТЫ ===

tiles_filtered = []
for (row, col), tile in tiles:
    coord = f"{letters[row]}{col+1}"
    if coord not in exclude_coords:
        tiles_filtered.append(((row, col), tile))

tiles = tiles_filtered

# === СОХРАНЯЕМ ТАЙЛЫ (по желанию) ===
if save_tiles:
    print("💾 Сохраняем тайлы...")
    def save_tile(data):
        idx, (pos, tile) = data
        path = os.path.join(output_folder, f"tile_{idx+1}.png")
        tile.save(path)

    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(save_tile, enumerate(tiles)), total=len(tiles)))

# === СОЗДАЁМ ЛИСТЫ SHUFFLED ===
print("🧩 Создаём shuffled листы...")

sheet_w_px = int(sheet_w_mm * px_per_mm)
sheet_h_px = int(sheet_h_mm * px_per_mm)
# Размер квадрата для shuffled в px
shuffled_tile_px = int(shuffled_tile_mm * px_per_mm)

tiles_per_row = sheet_w_px // (tile_w + gap)
tiles_per_col = sheet_h_px // (tile_h + gap)
tiles_per_sheet = tiles_per_row * tiles_per_col

print(f"📄 Лист {sheet_w_mm}x{sheet_h_mm} мм → {tiles_per_row}×{tiles_per_col} тайлов")

all_tiles = tiles[:]
random.shuffle(all_tiles)

answers_log = []

# Шрифт для мини-версий
t_s = int(tile_w * answer_scale)
ans_font_size = max(answer_font_min, int(t_s * answer_font_scale))
try:
    ans_font = ImageFont.truetype(font_path, ans_font_size)
except OSError:
    ans_font = ImageFont.load_default()

for sheet_idx in range(0, len(all_tiles), tiles_per_sheet):
    page_tiles = all_tiles[sheet_idx:sheet_idx + tiles_per_sheet]
    sheet_img = Image.new("RGBA", (sheet_w_px, sheet_h_px), (255, 255, 255, 255))

    ans_sheet_w = int(sheet_w_px * answer_scale)
    ans_sheet_h = int(sheet_h_px * answer_scale)
    answer_img = Image.new("RGBA", (ans_sheet_w, ans_sheet_h), (255, 255, 255, 255))
    draw_ans = ImageDraw.Draw(answer_img)

    page_table = [["" for _ in range(tiles_per_row)] for _ in range(tiles_per_col)]

    for i, (orig_pos, tile) in enumerate(page_tiles):
        row_o, col_o = orig_pos
        orig_label = f"{letters[row_o]}{col_o+1}"

        if rotate_tiles:
            angle = random.choice([0, 90, 180, 270])
            tile = tile.rotate(angle, expand=True)

        row = i // tiles_per_row
        col = i % tiles_per_row

        row = i // tiles_per_row
        col = i % tiles_per_row

        # реальные размеры сетки на этом листе
        used_cols = min(len(page_tiles) - row * tiles_per_row, tiles_per_row)
        used_rows = min((len(page_tiles) + tiles_per_row - 1) // tiles_per_row, tiles_per_col)

        grid_w_used = used_cols * tile_w + (used_cols - 1) * gap
        grid_h_used = used_rows * tile_h + (used_rows - 1) * gap

        offset_x = (sheet_w_px - grid_w_used) // 2
        offset_y = (sheet_h_px - grid_h_used) // 2

        x = offset_x + col * (tile_w + gap)
        y = offset_y + row * (tile_h + gap)
        sheet_img.paste(tile.resize((tile_w, tile_h)), (x, y))

        # мини версия
        grid_w_small = int(grid_w_used * answer_scale)
        grid_h_small = int(grid_h_used * answer_scale)
        offset_xs = (ans_sheet_w - grid_w_small) // 2
        offset_ys = (ans_sheet_h - grid_h_small) // 2

        x_s = offset_xs + int(col * (tile_w + gap) * answer_scale)
        y_s = offset_ys + int(row * (tile_h + gap) * answer_scale)

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

    out_path = os.path.join(output_dir, f"shuffled_{sheet_idx//tiles_per_sheet+1}.png")
    sheet_img.save(out_path)

    ans_path = os.path.join(output_dir, f"answers_sheet_{sheet_idx//tiles_per_sheet+1}.png")
    answer_img.save(ans_path)

    answers_log.append(f"\n=== Лист {sheet_idx//tiles_per_sheet+1} ===\n")
    for r in page_table:
        answers_log.append("\t".join(r))

# === СОХРАНЯЕМ ТЕКСТОВЫЙ ФАЙЛ С ОТВЕТАМИ ===
with open(output_answers_txt, "w", encoding="utf-8") as f:
    f.write("\n".join(answers_log))

# === СОЗДАЁМ СЕТКУ С ПОДПИСЯМИ ===
print("🗺️ Создаём изображение с сеткой...")
grid_w = new_w + tile_w
grid_h = new_h + tile_h
grid_img = Image.new("RGBA", (grid_w, grid_h), (255, 255, 255, 255))
grid_img.paste(img, (tile_w, tile_h))
draw = ImageDraw.Draw(grid_img)

for c in range(cols + 1):
    x = tile_w + c * tile_w
    draw.line([(x, tile_h), (x, grid_h)], fill="black", width=grid_line_width)
for r in range(rows + 1):
    y = tile_h + r * tile_h
    draw.line([(tile_w, y), (grid_w, y)], fill="black", width=grid_line_width)

# подписи
font_size_grid = int(tile_h * font_scale)
try:
    font_grid = ImageFont.truetype(font_path, font_size_grid)
except OSError:
    font_grid = ImageFont.load_default()

# цифры сверху
for c in range(cols):
    txt = str(c + 1)
    x, y = center_in_cell(draw, txt, tile_w + c * tile_w, 0, tile_w, tile_h, font_grid)
    draw.text((x, y), txt, fill="black", font=font_grid)

# буквы слева
for r in range(rows):
    txt = letters[r]
    x, y = center_in_cell(draw, txt, 0, tile_h + r * tile_h, tile_w, tile_h, font_grid)
    draw.text((x, y), txt, fill="black", font=font_grid)

grid_img.save(output_grid)

print("\n✅ Готово!")
print(f"📂 Папка: {output_dir}")
print(f"📄 Ответы: {output_answers_txt}")
from PIL import Image, ImageDraw, ImageFont
import random
import os
import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm   # pip install tqdm

# === НАСТРОЙКИ ===
input_file = "Карта квадраты SRA3.png"
cols = 9   # сколько тайлов по горизонтали
rows = 13  # сколько тайлов по вертикали
gap = 80   # расстояние между тайлами (px)
grid_line_width = 8  # толщина линий сетки
font_scale = 1
save_tiles = False   # сохранять ли отдельные кусочки

# путь к шрифту
font_path = "DearType - Lifehack Sans Medium.otf"
Image.MAX_IMAGE_PIXELS = None

# === ДИРЕКТОРИЯ ДЛЯ ВЫВОДА ===
timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
output_dir = os.path.join(os.getcwd(), timestamp)
os.makedirs(output_dir, exist_ok=True)   # ← вот этого не хватало

output_folder = os.path.join(output_dir, "tiles")
if save_tiles:
    os.makedirs(output_folder, exist_ok=True)


output_shuffled = os.path.join(output_dir, "shuffled.png")
output_grid = os.path.join(output_dir, "grid.png")

# === ЗАГРУЗКА ===
print("📂 Загружаем изображение...")
img = Image.open(input_file).convert("RGBA")
w, h = img.size

# Получаем DPI из метаданных (если есть)
dpi = img.info.get("dpi", (96, 96))[0]  # берём X DPI, по умолчанию 96
px_per_mm = dpi / 25.4

# === РАСЧЁТ РАЗМЕРА КВАДРАТОВ ===
tile_w = w // cols
tile_h = h // rows
tile_size = min(tile_w, tile_h)
tile_w = tile_h = tile_size

# === ОБРЕЗКА КАРТИНКИ ===
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
        tiles.append(tile)

# === СОХРАНЯЕМ ОТДЕЛЬНЫЕ (по желанию) ===
if save_tiles:
    print("💾 Сохраняем тайлы...")
    def save_tile(data):
        idx, tile = data
        path = os.path.join(output_folder, f"tile_{idx+1}.png")
        tile.save(path)

    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(save_tile, enumerate(tiles)), total=len(tiles), desc="Сохранение тайлов"))

# === СОЗДАЁМ ПЕРЕМЕШАННОЕ ===
print("🧩 Создаём перемешанное изображение...")
all_tiles = tiles[:]
random.shuffle(all_tiles)

shuffled_w = cols * tile_w + (cols - 1) * gap
shuffled_h = rows * tile_h + (rows - 1) * gap
shuffled_img = Image.new("RGBA", (shuffled_w, shuffled_h), (255, 255, 255, 255))

i = 0
for row in tqdm(range(rows), desc="Сборка shuffled"):
    for col in range(cols):
        x = col * (tile_w + gap)
        y = row * (tile_h + gap)
        shuffled_img.paste(all_tiles[i], (x, y))
        i += 1

shuffled_img.save(output_shuffled)

# === СОЗДАЁМ ИЗОБРАЖЕНИЕ С СЕТКОЙ ===
print("🗺️ Создаём изображение с сеткой...")
grid_w = new_w + tile_w
grid_h = new_h + tile_h
grid_img = Image.new("RGBA", (grid_w, grid_h), (255, 255, 255, 255))
grid_img.paste(img, (tile_w, tile_h))
draw = ImageDraw.Draw(grid_img)

# Линии сетки
for c in tqdm(range(cols + 1), desc="Рисование вертикальных линий"):
    x = tile_w + c * tile_w
    draw.line([(x, tile_h), (x, grid_h)], fill="black", width=grid_line_width)
for r in tqdm(range(rows + 1), desc="Рисование горизонтальных линий"):
    y = tile_h + r * tile_h
    draw.line([(tile_w, y), (grid_w, y)], fill="black", width=grid_line_width)

# Подписи
font_size = int(tile_h * font_scale)
font_mm = font_size / px_per_mm
print(f"🔤 Размер шрифта: {font_size}px ≈ {font_mm:.2f} мм")

try:
    font = ImageFont.truetype(font_path, font_size)
except OSError:
    print(f"⚠️ Не удалось загрузить {font_path}, используем шрифт по умолчанию")
    font = ImageFont.load_default()

ascent, descent = font.getmetrics()

# Центрирование по квадрату с учётом line gap
def center_text(draw, text, x0, y0, cell_w, cell_h, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = x0 + (cell_w - tw) // 2
    y = y0 + (cell_h - th) // 2 - bbox[1]   # вот тут -bbox[1] убирает "уезд"
    return x, y

# Цифры сверху
for c in tqdm(range(cols), desc="Подписи сверху"):
    text = str(c + 1)
    x, y = center_text(draw, text, tile_w + c * tile_w, 0, tile_w, tile_h, font)
    draw.text((x, y), text, fill="black", font=font)

# Буквы слева
letters = list("АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
for r in tqdm(range(rows), desc="Подписи слева"):
    text = letters[r]
    x, y = center_text(draw, text, 0, tile_h + r * tile_h, tile_w, tile_h, font)
    draw.text((x, y), text, fill="black", font=font)

grid_img.save(output_grid)

print(f"\n✅ Готово!")
print(f"📂 Папка: {output_dir}")
print(f"🧩 Перемешанное: {output_shuffled}")
print(f"🗺️ Сетка: {output_grid}")
if save_tiles:
    print(f"🖼️ Тайлы: {output_folder}")
else:
    print(f"🖼️ Тайлы не сохранялись (save_tiles=False)")

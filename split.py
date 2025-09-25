from PIL import Image
import random
import os

# === НАСТРОЙКИ ===
input_file = "Карта квадраты SRA3.png"
output_file = "shuffled.png"
output_folder = "tiles"
cols = 9   # сколько квадратов по горизонтали
rows = 13    # сколько квадратов по вертикали
gap = 50    # расстояние между квадратиками (в пикселях)

# === ОТКЛЮЧАЕМ ЛИМИТ PILLOW ===
Image.MAX_IMAGE_PIXELS = None

# === ЗАГРУЗКА ===
img = Image.open(input_file)
w, h = img.size

# === РАЗМЕР ОДНОГО КВАДРАТА ===
tile_w = w // cols
tile_h = h // rows

# === РАЗБИВАЕМ ===
tiles = []
for row in range(rows):
    for col in range(cols):
        box = (col * tile_w, row * tile_h, (col + 1) * tile_w, (row + 1) * tile_h)
        tile = img.crop(box)
        tiles.append(tile)

# === СОЗДАЁМ ПАПКУ ДЛЯ ЭКСПОРТА ===
os.makedirs(output_folder, exist_ok=True)
for i, t in enumerate(tiles):
    t.save(os.path.join(output_folder, f"tile_{i+1}.png"))

# === ПЕРЕМЕШАЕМ ===
random.shuffle(tiles)

# === НОВЫЙ РАЗМЕР КАРТИНКИ С ПРОМЕЖУТКАМИ ===
new_w = cols * tile_w + (cols - 1) * gap
new_h = rows * tile_h + (rows - 1) * gap
new_img = Image.new("RGBA", (new_w, new_h), (255, 255, 255, 0))  # прозрачный фон

# === СОБИРАЕМ ===
i = 0
for row in range(rows):
    for col in range(cols):
        x = col * (tile_w + gap)
        y = row * (tile_h + gap)
        new_img.paste(tiles[i], (x, y))
        i += 1

new_img.save(output_file)

print(f"Готово! Новый PNG: {output_file}, а куски в папке {output_folder}")
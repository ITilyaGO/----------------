from PIL import Image
import random
import os
Image.MAX_IMAGE_PIXELS = None
# === НАСТРОЙКИ ===
input_file = "Карта квадраты SRA3.png"
output_file = "shuffled.png"
output_folder = "tiles"
tile_size_cm = 3
dpi = 1200   # <-- укажи свой DPI картинки (обычно 300 или 96)

# === РАСЧЁТ В ПИКСЕЛЯХ ===
tile_size_px = int(tile_size_cm / 2.54 * dpi)

# === ЗАГРУЗКА ===
img = Image.open(input_file)
w, h = img.size

# === РАЗБИВАЕМ НА КВАДРАТЫ ===
tiles = []
for y in range(0, h, tile_size_px):
    for x in range(0, w, tile_size_px):
        box = (x, y, x + tile_size_px, y + tile_size_px)
        tile = img.crop(box)
        tiles.append(tile)

# === СОЗДАЁМ ПАПКУ ДЛЯ ЭКСПОРТА ===
os.makedirs(output_folder, exist_ok=True)
for i, t in enumerate(tiles):
    t.save(os.path.join(output_folder, f"tile_{i+1}.png"))

# === ПЕРЕМЕШАЕМ ===
random.shuffle(tiles)

# === СОБИРАЕМ НОВОЕ PNG ===
cols = w // tile_size_px
rows = h // tile_size_px
new_img = Image.new("RGBA", (cols * tile_size_px, rows * tile_size_px))

i = 0
for row in range(rows):
    for col in range(cols):
        new_img.paste(tiles[i], (col * tile_size_px, row * tile_size_px))
        i += 1

new_img.save(output_file)

print(f"Готово! Новый PNG: {output_file}, а куски в папке {output_folder}")

import os
import tkinter as tk
from PIL import Image, ImageTk, Image
from config import Config
from image_loader import load_image
from white_tiles import load_white_tiles, save_white_tiles
import warnings
import argparse


# === Безопасность Pillow ===
warnings.simplefilter('ignore', Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None


# === Аргументы ===
parser = argparse.ArgumentParser(description="GUI выбора белых тайлов")
parser.add_argument("--project", type=str, help="Имя проекта (папка в out/)")
args = parser.parse_args()


# === Загружаем проект ===
project_name = args.project or Config.get_last_project() or input("Введите имя проекта: ").strip()
cfg = Config().load(project_name)
Config.set_last_project(project_name)

if not os.path.exists(cfg.input_file):
    print(f"❌ Файл '{cfg.input_file}' не найден.")
    exit(1)

# === Загружаем изображение ===
img, tile_size, px_per_mm, dpi = load_image(cfg.input_file, cfg.cols, cfg.rows)

# === Загружаем/создаём список белых ===
excluded = set(load_white_tiles(cfg))
print(f"📖 Загружены исключения: {len(excluded)} шт.")

# === GUI ===
root = tk.Tk()
root.title(f"Белые тайлы — {cfg.project_name}")
root.geometry("1000x900")

canvas = tk.Canvas(root, bg="white")
canvas.pack(fill=tk.BOTH, expand=True)

scale = 1.0
tk_img = None
letters = list("АБВГДЕЖИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

# === Вспомогательные ===
def coord_to_label(x, y):
    row = int(y // (tile_size * scale))
    col = int(x // (tile_size * scale))
    if 0 <= row < cfg.rows and 0 <= col < cfg.cols:
        return f"{letters[row]}{col + 1}"
    return None

def redraw():
    global tk_img, scale
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    scale_x = w / (tile_size * cfg.cols)
    scale_y = h / (tile_size * cfg.rows)
    scale = min(scale_x, scale_y)

    disp_w = int(tile_size * cfg.cols * scale)
    disp_h = int(tile_size * cfg.rows * scale)
    disp_img = img.resize((disp_w, disp_h), Image.NEAREST)
    tk_img = ImageTk.PhotoImage(disp_img)

    canvas.delete("all")
    canvas.create_image(0, 0, anchor="nw", image=tk_img)

    # сетка
    for r in range(cfg.rows + 1):
        y = r * tile_size * scale
        canvas.create_line(0, y, tile_size * cfg.cols * scale, y, fill="black", width=1)
    for c in range(cfg.cols + 1):
        x = c * tile_size * scale
        canvas.create_line(x, 0, x, tile_size * cfg.rows * scale, fill="black", width=1)

    # выделенные
    for label in excluded:
        if not label or label[0] not in letters:
            continue
        row = letters.index(label[0])
        col = int(label[1:]) - 1
        x1 = col * tile_size * scale
        y1 = row * tile_size * scale
        x2 = x1 + tile_size * scale
        y2 = y1 + tile_size * scale
        canvas.create_rectangle(x1+1, y1+1, x2-1, y2-1, outline="red", width=2, tags=label)

def on_click(event):
    label = coord_to_label(event.x, event.y)
    if not label:
        return
    if label in excluded:
        excluded.remove(label)
    else:
        excluded.add(label)
    redraw()

def save_and_exit():
    save_white_tiles(cfg, sorted(excluded))
    whites_path = os.path.join(cfg.project_dir, "white_tiles.txt")
    print(f"💾 Сохранено {len(excluded)} исключений в {os.path.basename(whites_path)}")
    root.destroy()


# === Привязки ===
canvas.bind("<Button-1>", on_click)
canvas.bind("<Configure>", lambda e: redraw())

btn = tk.Button(root, text="💾 Сохранить и выйти", command=save_and_exit)
btn.pack(pady=5)

root.after(100, redraw)
root.mainloop()

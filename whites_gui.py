import os
import tkinter as tk
from PIL import Image, ImageTk, Image
from config_manager import auto_load_project, save_config
from image_loader import load_image
import warnings
import argparse


# === Отключаем предупреждения о "бомбах распаковки" ===
warnings.simplefilter('ignore', Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None

# --- Аргументы командной строки ---
parser = argparse.ArgumentParser()
parser.add_argument("--project", type=str, help="Имя проекта для открытия")
args = parser.parse_args()

# --- Загружаем проект через менеджер ---
project_name, config = auto_load_project(args.project)

input_file = config.get("input_file")
cols = config.get("cols", 9)
rows = config.get("rows", 13)

if not input_file or not os.path.exists(input_file):
    print(f"❌ Файл '{input_file}' не найден. Укажите корректный путь в конфиге проекта '{project_name}'.")
    exit(1)

# === Загружаем изображение ===
img, tile_size, px_per_mm, dpi = load_image(input_file, cols, rows)

# === Путь к файлу исключений ===
inputs_dir = "inputs"
os.makedirs(inputs_dir, exist_ok=True)
whites_file = config.get("exclude_file") or os.path.join(inputs_dir, f"{project_name}_white_tiles.txt")
config["exclude_file"] = whites_file
save_config(project_name, config)

# === Настройки ===
tile_w, tile_h = tile_size, tile_size
letters = list("АБВГДЕЖИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

# === GUI ===
root = tk.Tk()
root.title(f"Выбор белых тайлов — {project_name}")
root.geometry("1000x900")

canvas = tk.Canvas(root, bg="white")
canvas.pack(fill=tk.BOTH, expand=True)

excluded = set()
scale = 1.0
tk_img = None

# === Загружаем уже сохранённые исключения ===
if os.path.exists(whites_file):
    try:
        local_vars = {}
        exec(open(whites_file, encoding="utf-8").read(), {}, local_vars)
        excluded = set(local_vars.get("exclude_coords", []))
        print(f"📖 Загружены исключения из {whites_file}: {len(excluded)} шт.")
    except Exception as e:
        print(f"⚠️ Ошибка чтения {whites_file}: {e}")
else:
    print(f"ℹ️ Файл {whites_file} не найден, начнём с пустого списка.")

# === Функции ===
def coord_to_label(x, y):
    row = int(y // (tile_h * scale))
    col = int(x // (tile_w * scale))
    if 0 <= row < rows and 0 <= col < cols:
        return f"{letters[row]}{col+1}"
    return None

def redraw():
    global tk_img, scale
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    scale_x = w / (tile_w * cols)
    scale_y = h / (tile_h * rows)
    scale = min(scale_x, scale_y)

    disp_w = int(tile_w * cols * scale)
    disp_h = int(tile_h * rows * scale)
    disp_img = img.resize((disp_w, disp_h), Image.NEAREST)
    tk_img = ImageTk.PhotoImage(disp_img)

    canvas.delete("all")
    canvas.create_image(0, 0, anchor="nw", image=tk_img)

    # --- рисуем сетку ---
    for r in range(rows + 1):
        y = r * tile_h * scale
        canvas.create_line(0, y, tile_w * cols * scale, y, fill="black", width=1)
    for c in range(cols + 1):
        x = c * tile_w * scale
        canvas.create_line(x, 0, x, tile_h * rows * scale, fill="black", width=1)


    for label in excluded:
        if not label or label[0] not in letters:
            continue
        row = letters.index(label[0])
        col = int(label[1:]) - 1
        x1 = col * tile_w * scale
        y1 = row * tile_h * scale
        x2 = x1 + tile_w * scale
        y2 = y1 + tile_h * scale
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

def save_file():
    with open(whites_file, "w", encoding="utf-8") as f:
        f.write("exclude_coords = [\n")
        for w in sorted(excluded):
            f.write(f'    "{w}",\n')
        f.write("]\n")
    print(f"💾 Сохранено {len(excluded)} исключений в {whites_file}")
    config["exclude_file"] = whites_file
    save_config(project_name, config)
    root.destroy()

# === Привязки ===
canvas.bind("<Button-1>", on_click)
canvas.bind("<Configure>", lambda e: redraw())

btn = tk.Button(root, text="💾 Сохранить и выйти", command=save_file)
btn.pack(pady=5)

root.after(100, redraw)
root.mainloop()

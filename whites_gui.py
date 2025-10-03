import os
import tkinter as tk
from PIL import Image, ImageTk
from config import input_file, cols, rows
from image_loader import load_image

# === Загружаем изображение и параметры ===
img, tile_size, px_per_mm, dpi = load_image(input_file, cols, rows)

# === Папка и имя файла исключений ===
base_name = os.path.splitext(os.path.basename(input_file))[0]
inputs_dir = "inputs"
os.makedirs(inputs_dir, exist_ok=True)
whites_file = os.path.join(inputs_dir, f"{base_name}_white_tiles.txt")

# === Настройки ===
tile_w, tile_h = tile_size, tile_size
letters = list("АБВГДЕЖИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

# === GUI ===
root = tk.Tk()
root.title("Выбор белых тайлов")
root.geometry("900x900")  # стартовое окно

canvas = tk.Canvas(root, bg="white")
canvas.pack(fill=tk.BOTH, expand=True)

excluded = set()
scale = 1.0
tk_img = None

# --- Загружаем список исключений, если файл есть ---
if os.path.exists(whites_file):
    try:
        local_vars = {}
        exec(open(whites_file, encoding="utf-8").read(), {}, local_vars)
        excluded = set(local_vars.get("exclude_coords", []))
        print(f"📖 Загружены исключения из {whites_file}: {excluded}")
    except Exception as e:
        print(f"⚠️ Ошибка чтения {whites_file}: {e}")
else:
    print(f"ℹ️ Файл {whites_file} не найден, начнём с пустого списка.")

def coord_to_label(x, y):
    row = int(y // (tile_h * scale))
    col = int(x // (tile_w * scale))
    if 0 <= row < rows and 0 <= col < cols:
        return f"{letters[row]}{col+1}"
    return None

def redraw():
    """Перерисовать картинку и выделения"""
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

    # выделить красным уже исключённые клетки
    for label in excluded:
        if not label or label[0] not in letters:
            continue
        row = letters.index(label[0])
        col = int(label[1:]) - 1
        x1 = col * tile_w * scale
        y1 = row * tile_h * scale
        x2 = x1 + tile_w * scale
        y2 = y1 + tile_h * scale
        canvas.create_rectangle(x1+1, y1+1, x2-1, y2-1, outline="red", width=1, tags=label)

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
    root.destroy()

canvas.bind("<Button-1>", on_click)
canvas.bind("<Configure>", lambda e: redraw())

btn = tk.Button(root, text="Сохранить и выйти", command=save_file)
btn.pack(pady=5)

# первая отрисовка с учётом уже загруженных исключений
root.after(100, redraw)

root.mainloop()

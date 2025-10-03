import os, datetime
from PIL import Image

# Сид
random_seed = 63235212

# Основное
project_name = "Галахово"
input_file = "inputs/Галахово 1200_noroads.tif"

cols, rows = 9, 13
grid_line_width = 16
font_scale = 1
save_tiles = False
tile_mm_target = 30.0

# Шрифты
font_path = "resources/DearType - Lifehack Sans Medium.otf"
Image.MAX_IMAGE_PIXELS = None
letters = list("АБВГДЕЖИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

# Настройки листов
sheet_export_dpi = 1200
sheet_w_mm, sheet_h_mm = 210, 297
shuffled_tile_mm = 30
gap_mm, margin_mm = 2.5, 3
rotate_tiles = None
answer_scale = 0.25
answer_font_scale = 0.9
answer_font_min = 12
answer_outline = True
answer_outline_width = 10
answer_outline_fill = "white"
answer_text_fill = "black"

# Нумерация тайлов
circle_diametr_mm = 4
circle_font_mm = 4.5
answers_circle_scale = 1
circle_fill = "white"
circle_outline = "white"
circle_outline_width = 1
circle_text_fill = "black"

# Подписи
label_font_mm = 6.0
grid_label_font_mm = 8.0
label_area_mm = grid_label_font_mm

# === ВЫВОД ===
def make_output_dir():
    import os, datetime
    timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    output_dir = os.path.join(os.getcwd(), "out", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

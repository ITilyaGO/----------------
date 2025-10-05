import time as timemod  # ← важно: переименовали, чтобы избежать конфликта с datetime.time
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont
from utils import center_in_cell, draw_text_with_outline
from concurrent.futures import ThreadPoolExecutor, as_completed

# ──────────────────────────────
# 🔤 Подготовка шрифтов
# ──────────────────────────────
def prepare_fonts(cfg, px_per_mm):
    def load(size_px):
        try:
            return ImageFont.truetype(cfg.font_path, int(size_px))
        except OSError:
            return ImageFont.load_default()

    # базовый размер клетки (в пикселях для answer-листа)
    tile_px = cfg.shuffled_tile_mm * px_per_mm * cfg.answer_scale

    return {
        # цифры в кружках — фиксированный размер в мм
        "circle": load(cfg.circle_font_mm * px_per_mm),
        "circle_answer": load(cfg.circle_font_mm * px_per_mm * cfg.answer_scale * cfg.answers_circle_scale),
        # текст в клетках answer-листа — зависит от клетки и коэффициента
        "answer": load(tile_px * cfg.answer_font_scale),
        # подписи на shuffled — как раньше, в мм (не зависит от scale)
        "label": load(cfg.label_font_mm * px_per_mm),
        # подписи на shuffled — как раньше, в мм (не зависит от scale)
        "answer_label": load(cfg.label_font_mm * px_per_mm * cfg.answer_scale),
        # надпись проекта — тоже фиксированная в мм
        "project": load(cfg.grid_label_font_mm),
    }


# ──────────────────────────────
# 🧱 Создание пустых листов
# ──────────────────────────────
def create_blank_sheet(cfg, px_per_mm, scale=1.0):
    w = int(cfg.sheet_w_mm * px_per_mm * scale)
    h = int(cfg.sheet_h_mm * px_per_mm * scale)
    label_area = int(cfg.label_area_mm * px_per_mm * scale)
    return Image.new("RGBA", (w, h + label_area), (255, 255, 255, 255)), label_area


# ──────────────────────────────
# 🎨 Отрисовка одного тайла на shuffled-листе
# ──────────────────────────────
def draw_tile_on_sheet(cfg, draw, tile_number, base_x, base_y, tile_px, px_per_mm, font_circle,
                       scale=1.0, circle_scale=1.0):
    """Рисует кружок с номером в правом верхнем углу тайла (универсально для shuffled и answers)."""
    circle_r = int((cfg.circle_diametr_mm / 2) * px_per_mm * scale * circle_scale)
    cx = base_x + tile_px - circle_r - 4
    cy = base_y + circle_r + 4

    # белый кружок
    draw.ellipse(
        (cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r),
        fill=cfg.circle_fill,
        outline=cfg.circle_outline,
        width=cfg.circle_outline_width
    )

    # текст с корректировкой bbox[1]
    bbox = draw.textbbox((0, 0), tile_number, font=font_circle)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw // 2
    ty = cy - th // 2 - bbox[1]
    draw.text((tx, ty), tile_number, font=font_circle, fill=cfg.circle_text_fill)


# ──────────────────────────────
# 🖼️ Генерация одного shuffled-листа
# ──────────────────────────────
def render_page(cfg, page, img_tiles, px_per_mm, dpi, output_dir,
                use_rotation_matrix=False):
    """
    Рендер одного shuffled-листа.
    Если use_rotation_matrix=True — применяются углы из page["rotation_matrix"].
    Если False — без поворотов (прямая версия).
    """
    fonts = prepare_fonts(cfg, px_per_mm)
    sheet, label_area_px = create_blank_sheet(cfg, px_per_mm)
    draw = ImageDraw.Draw(sheet)

    matrix = page["matrix"]
    rotation_matrix = page.get("rotation_matrix", [[0] * len(matrix[0]) for _ in matrix])
    page_idx = page["index"]

    shuffled_tile_px = int(cfg.shuffled_tile_mm * px_per_mm)
    gap_px = int(cfg.gap_mm * px_per_mm)
    margin_px = int(cfg.margin_mm * px_per_mm)
    tiles_per_row = len(matrix[0])
    tiles_per_col = len(matrix)

    grid_w = tiles_per_row * shuffled_tile_px + (tiles_per_row - 1) * gap_px
    grid_h = tiles_per_col * shuffled_tile_px + (tiles_per_col - 1) * gap_px
    offset_x = margin_px + (sheet.width - 2 * margin_px - grid_w) // 2
    offset_y = margin_px + (sheet.height - label_area_px - 2 * margin_px - grid_h) // 2

    for r in range(tiles_per_col):
        for c in range(tiles_per_row):
            coord = matrix[r][c]
            if not coord or coord not in img_tiles:
                continue

            tile = img_tiles[coord].copy()
            ang = rotation_matrix[r][c] if use_rotation_matrix else 0
            if ang:
                tile = tile.rotate(ang, expand=True)
            tile_resized = tile.resize((shuffled_tile_px, shuffled_tile_px))

            x = offset_x + c * (shuffled_tile_px + gap_px)
            y = offset_y + r * (shuffled_tile_px + gap_px) + label_area_px
            sheet.paste(tile_resized, (x, y))

            draw_tile_on_sheet(cfg, draw, str(r * tiles_per_row + c + 1),
                               x, y, shuffled_tile_px, px_per_mm,
                               fonts["circle"], scale=1.0, circle_scale=1.0)

    # подпись
    suffix = "  с поворотом" if use_rotation_matrix else ""
    label_text = f"{cfg.project_name} - Лист {page_idx}{suffix}"
    bbox = draw.textbbox((0, 0), label_text, font=fonts["label"])
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((sheet.width - lw) // 2, (label_area_px - lh) // 2),
              label_text, font=fonts["label"], fill="black")

    suffix_file = "_rot" if use_rotation_matrix else ""
    out_path = os.path.join(output_dir, f"shuffled_{page_idx}{suffix_file}.png")
    sheet.save(out_path, dpi=(dpi, dpi))

    print(f"💾 Сохранён {os.path.basename(out_path)}")
    return out_path

# ──────────────────────────────
# 🧩 Генерация answers-листа
# ──────────────────────────────
def render_page_answers(cfg, page, img_tiles, px_per_mm, dpi, output_dir):
    scale = cfg.answer_scale
    fonts = prepare_fonts(cfg, px_per_mm)
    font_ans = fonts["answer"]
    font_ans_label = fonts["answer_label"]

    img, label_area = create_blank_sheet(cfg, px_per_mm, scale)
    draw = ImageDraw.Draw(img)

    matrix = page["matrix"]
    rotation = page["rotation_matrix"]
    page_idx = page["index"]

    shuffled_tile_px = int(cfg.shuffled_tile_mm * px_per_mm * scale)
    gap_px = int(cfg.gap_mm * px_per_mm * scale)
    margin_px = int(cfg.margin_mm * px_per_mm * scale)
    tiles_per_row = len(matrix[0])
    tiles_per_col = len(matrix)

    grid_w = tiles_per_row * shuffled_tile_px + (tiles_per_row - 1) * gap_px
    grid_h = tiles_per_col * shuffled_tile_px + (tiles_per_col - 1) * gap_px
    offset_x = margin_px + (img.width - 2 * margin_px - grid_w) // 2
    offset_y = margin_px + (img.height - label_area - 2 * margin_px - grid_h) // 2

    for r in range(tiles_per_col):
        for c in range(tiles_per_row):
            coord = matrix[r][c]
            if not coord or coord not in img_tiles:
                continue
            tile = img_tiles[coord].copy()
            ang = rotation[r][c]
            if ang:
                tile = tile.rotate(ang, expand=True)
            tile_resized = tile.resize((shuffled_tile_px, shuffled_tile_px))
            x = offset_x + c * (shuffled_tile_px + gap_px)
            y = offset_y + r * (shuffled_tile_px + gap_px) + label_area
            img.paste(tile_resized, (x, y))
            # --- кружок с номером в правом верхнем углу ---
            draw_tile_on_sheet(cfg, draw, str(r * tiles_per_row + c + 1),
                            x, y, shuffled_tile_px, px_per_mm,
                            fonts["circle_answer"],
                            scale=cfg.answer_scale,
                            circle_scale=cfg.answers_circle_scale)



            tx, ty = position_in_cell(
                draw, coord, x, y,
                shuffled_tile_px, shuffled_tile_px, font_ans,
                align_x=cfg.answer_align_x,
                align_y=cfg.answer_align_y,
                margin_px=cfg.answer_margin_px
            )


            if cfg.answer_outline:
                draw_text_with_outline(draw, (tx, ty), coord, font_ans,
                                       fill=cfg.answer_text_fill,
                                       outline_fill=cfg.answer_outline_fill,
                                       outline_width=cfg.answer_outline_width)
            else:
                draw.text((tx, ty), coord, fill=cfg.answer_text_fill, font=font_ans)

    label_text = f"{cfg.project_name} - Лист {page_idx}"
    bbox = draw.textbbox((0, 0), label_text, font=font_ans_label)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((img.width - lw) // 2, (label_area - lh) // 2),
              label_text, font=font_ans_label, fill="black")

    out_path = os.path.join(output_dir, f"answers_sheet_{page_idx}.png")
    img.save(out_path, dpi=(dpi, dpi))
    return out_path


# ──────────────────────────────
# ⚙️ Один комплект shuffled + answers
# ──────────────────────────────


def render_sheet_pair(cfg, img_tiles, page, px_per_mm, dpi, output_dir):
    """
    Рендерит shuffled и answers параллельно для одного листа.
    Работает внутри отдельного процесса (по одному на страницу).
    """
    page_id = page["index"]
    pid = os.getpid()

    print(f"🟢 [PID {pid}] ▶️ Старт страницы {page_id} ({timemod.strftime('%H:%M:%S')})")

    # Создаём потоки для двух задач — shuffled и answers
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(render_page, cfg, page, img_tiles, px_per_mm, dpi, output_dir, False): "shuffled",
            pool.submit(render_page, cfg, page, img_tiles, px_per_mm, dpi, output_dir, True): "shuffled_rot",
            pool.submit(render_page_answers, cfg, page, img_tiles, px_per_mm, dpi, output_dir): "answers",
        }

        results = {}

        for fut in as_completed(futures):
            task = futures[fut]
            try:
                results[task] = fut.result()
                print(f"   ✅ [PID {pid}] {task} готов для страницы {page_id} ({timemod.strftime('%H:%M:%S')})")
            except Exception as e:
                print(f"   ❌ [PID {pid}] Ошибка в {task} страницы {page_id}: {e}")
                results[task] = None

    print(f"🏁 [PID {pid}] Завершена страница {page_id} ({timemod.strftime('%H:%M:%S')})")

    return results.get("shuffled"), results.get("answers")
# ──────────────────────────────
# 🚀 Параллельная генерация всех листов
# ──────────────────────────────
def render_all_pages(cfg, img_tiles, state, px_per_mm, dpi, output_dir, pages=None, threads=None):
    os.makedirs(output_dir, exist_ok=True)
    pages_to_render = pages or state["pages"]

    results = []
    with ProcessPoolExecutor(max_workers=threads) as pool:
        futures = [
            pool.submit(render_sheet_pair, cfg, img_tiles, page, px_per_mm, dpi, output_dir)
            for page in pages_to_render
        ]
        for fut in as_completed(futures):
            shuffled, answers = fut.result()
            print(f"💾 {os.path.basename(shuffled)}, {os.path.basename(answers)} готовы")
            results.append((shuffled, answers))

    return results


# ──────────────────────────────
# 🧩 Публичная точка входа
# ──────────────────────────────
def make_sheets_from_state(cfg, img_tiles, state, px_per_mm, dpi, output_dir, threads=None, pages=None):
    print("🧩 Генерация shuffled и answers-листов (параллельно)...")
    return render_all_pages(cfg, img_tiles, state, px_per_mm, dpi, output_dir, pages, threads)

def position_in_cell(draw, text, x, y, w, h, font,
                     align_x="center", align_y="center", margin_px=24):
    """
    Возвращает координаты для текста внутри ячейки по двум осям.
    align_x: 'left' | 'center' | 'right'
    align_y: 'top'  | 'center' | 'bottom'
    margin_px — отступ от краёв (в пикселях).
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # === Горизонталь ===
    if align_x == "left":
        tx = x + margin_px
    elif align_x == "right":
        tx = x + w - tw - margin_px
    else:  # center
        tx = x + (w - tw) / 2

    # === Вертикаль ===
    if align_y == "top":
        ty = y + margin_px - bbox[1]
    elif align_y == "bottom":
        ty = y + h - th - margin_px - bbox[1]
    else:  # center
        ty = y + (h - th) / 2 - bbox[1]

    return tx, ty


def render_page_set(cfg, page, img_tiles, px_per_mm, dpi, output_dir,
                    what=("shuffled", "answers")):
    """
    Генерирует выбранные типы листов для страницы.
    what — кортеж: ('shuffled', 'answers', 'shuffled_rot', ...)
    """
    results = {}

    with ThreadPoolExecutor(max_workers=len(what)) as pool:
        futures = {}

        for kind in what:
            if kind == "shuffled":
                futures[pool.submit(render_page, cfg, page, img_tiles, px_per_mm, dpi, output_dir,
                                    type="shuffled", rotated=False)] = "shuffled"

            elif kind == "shuffled_rot":
                futures[pool.submit(render_page, cfg, page, img_tiles, px_per_mm, dpi, output_dir,
                                    type="shuffled", rotated=True)] = "shuffled_rot"

            elif kind == "answers":
                futures[pool.submit(render_page, cfg, page, img_tiles, px_per_mm, dpi, output_dir,
                                    type="answers", rotated=False)] = "answers"

        for fut in as_completed(futures):
            kind = futures[fut]
            try:
                results[kind] = fut.result()
                print(f"✅ {kind} готов: {os.path.basename(results[kind])}")
            except Exception as e:
                print(f"❌ Ошибка при генерации {kind}: {e}")

    return results

import os
import random
import math
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ProcessPoolExecutor, as_completed

import config  # ✅ теперь используем модуль, а не локальные копии
from utils import center_in_cell, draw_text_with_outline


def prepare_fonts(px_per_mm):
    circle_font_size = int(config.circle_diametr_mm * px_per_mm)
    label_font_size = int(config.label_font_mm * px_per_mm)
    return {
        "num": ImageFont.truetype(config.font_path, circle_font_size),
        "label": ImageFont.truetype(config.font_path, label_font_size),
    }


def layout_sheet_params(px_per_mm):
    shuffled_tile_px = int(config.shuffled_tile_mm * px_per_mm)
    gap_px = int(config.gap_mm * px_per_mm)
    margin_px = int(config.margin_mm * px_per_mm)
    sheet_w_px = int(config.sheet_w_mm * px_per_mm)
    sheet_h_px = int(config.sheet_h_mm * px_per_mm)
    return shuffled_tile_px, gap_px, margin_px, sheet_w_px, sheet_h_px


def generate_non_conflicting_rows(tiles, tiles_per_row, min_distance=1, max_attempts=50000):
    """
    Формирует строки shuffled-листа так, чтобы:
      • клетки не были ближе min_distance по оригинальной сетке
      • в строке не совпадали буквы (строки)
      • в строке не совпадали цифры (колонки)
    Если идеально не получается, берём лучший вариант и логируем конфликты.
    """
    rows = []
    available = tiles[:]
    random.shuffle(available)

    def count_conflicts(row_tiles):
        labels = [f"{config.letters[r]}{c + 1}" for (r, c), _ in row_tiles]
        conflicts = []
        used_rows = set()
        used_cols = set()
        for i, lab1 in enumerate(labels):
            r1, c1 = config.letters.index(lab1[0]), int(lab1[1:]) - 1

            # проверка совпадения строки или столбца
            if lab1[0] in used_rows:
                conflicts.append((lab1, f"строка {lab1[0]}"))
            if c1 in used_cols:
                conflicts.append((lab1, f"колонка {c1 + 1}"))

            used_rows.add(lab1[0])
            used_cols.add(c1)

            # проверка близости
            for j, lab2 in enumerate(labels):
                if i >= j:
                    continue
                r2, c2 = config.letters.index(lab2[0]), int(lab2[1:]) - 1
                if abs(r1 - r2) <= min_distance and abs(c1 - c2) <= min_distance:
                    conflicts.append((lab1, lab2))
        return conflicts

    for _ in range(math.ceil(len(tiles) / tiles_per_row)):
        best_row = None
        best_conflicts = None

        for attempt in range(max_attempts):
            row_tiles = random.sample(available, min(tiles_per_row, len(available)))
            conflicts = count_conflicts(row_tiles)
            if not conflicts:  # идеальная строка
                best_row, best_conflicts = row_tiles, conflicts
                break
            if best_conflicts is None or len(conflicts) < len(best_conflicts):
                best_row, best_conflicts = row_tiles, conflicts

        if best_conflicts:  # если всё-таки есть конфликты
            print(f"⚠️ Не удалось избежать {len(best_conflicts)} конфликт(ов) в строке:")
            for a, b in best_conflicts:
                print(f"   └─ {a} конфликтует с {b}")

        rows.append(best_row)
        for tile in best_row:
            available.remove(tile)

    return [t for row in rows for t in row]


def draw_tile_on_sheet(sheet_img, tile, i, x, y, shuffled_tile_px, circle_radius_px, num_font):
    draw_tile = ImageDraw.Draw(sheet_img)
    sheet_img.paste(tile.resize((shuffled_tile_px, shuffled_tile_px)), (x, y))
    tile_number = str(i + 1)
    cx = x + shuffled_tile_px - circle_radius_px - 4
    cy = y + circle_radius_px + 4
    draw_tile.ellipse(
        (cx - circle_radius_px, cy - circle_radius_px, cx + circle_radius_px, cy + circle_radius_px),
        fill=config.circle_fill,
        outline=config.circle_outline,
        width=config.circle_outline_width,
    )
    bbox = draw_tile.textbbox((0, 0), tile_number, font=num_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw // 2
    ty = cy - th // 2 - bbox[1]
    draw_tile.text((tx, ty), tile_number, font=num_font, fill=config.circle_text_fill)


def draw_tile_on_answer(answer_img, tile, i, x_s, y_s, t_s, px_per_mm, orig_label, ans_font):
    draw_ans = ImageDraw.Draw(answer_img)
    # миниатюра
    tile_small = tile.resize((t_s, t_s))
    answer_img.paste(tile_small, (x_s, y_s))

    # номер
    circle_radius_ans = int(config.circle_diametr_mm * config.answers_circle_scale * px_per_mm * config.answer_scale)
    circle_font_size_ans = int(
        2.0 * config.circle_diametr_mm * config.answers_circle_scale * px_per_mm * 0.9 * config.answer_scale
    )
    num_font_ans = ImageFont.truetype(config.font_path, circle_font_size_ans)
    tile_number = str(i + 1)
    cx_s = x_s + t_s - circle_radius_ans - 2
    cy_s = y_s + circle_radius_ans + 2
    draw_ans.ellipse(
        (cx_s - circle_radius_ans, cy_s - circle_radius_ans, cx_s + circle_radius_ans, cy_s + circle_radius_ans),
        fill=config.circle_fill,
        outline=config.circle_outline,
        width=max(1, int(config.circle_outline_width * config.answer_scale)),
    )
    bbox = draw_ans.textbbox((0, 0), tile_number, font=num_font_ans)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx_s - tw // 2
    ty = cy_s - th // 2 - bbox[1]
    draw_ans.text((tx, ty), tile_number, font=num_font_ans, fill=config.circle_text_fill)

    # подпись координаты
    tx, ty = center_in_cell(draw_ans, orig_label, x_s, y_s, t_s, t_s, ans_font)
    if config.answer_outline:
        draw_text_with_outline(
            draw_ans,
            (tx, ty),
            orig_label,
            ans_font,
            fill="black",
            outline_fill=config.answer_outline_fill,
            outline_width=config.answer_outline_width,
        )
    else:
        draw_ans.text((tx, ty), orig_label, fill="black", font=ans_font)


def make_sheet_page(
    page_tiles,
    rot_mode,
    px_per_mm,
    dpi,
    tiles_per_row,
    tiles_per_col,
    shuffled_tile_px,
    gap_px,
    margin_px,
    sheet_w_px,
    sheet_h_px,
    page_idx,
    output_dir,
):
    # шрифты — внутри процесса!
    num_font = ImageFont.truetype(config.font_path, int(config.circle_diametr_mm * px_per_mm))
    ans_font_size = max(
        config.answer_font_min, int(int(shuffled_tile_px * config.answer_scale) * config.answer_font_scale)
    )
    try:
        ans_font = ImageFont.truetype(config.font_path, ans_font_size)
    except OSError:
        ans_font = ImageFont.load_default()
    label_font_size = int(config.label_font_mm * px_per_mm)
    label_font = ImageFont.truetype(config.font_path, label_font_size)

    label_area_px = int(config.label_area_mm * px_per_mm)
    sheet_img = Image.new("RGBA", (sheet_w_px, sheet_h_px + label_area_px), (255, 255, 255, 255))

    ans_label_area_px = int(config.label_area_mm * px_per_mm * config.answer_scale)
    ans_sheet_w = int(sheet_w_px * config.answer_scale)
    ans_sheet_h = int(sheet_h_px * config.answer_scale) + ans_label_area_px
    answer_img = Image.new("RGBA", (ans_sheet_w, ans_sheet_h), (255, 255, 255, 255))
    draw_ans = ImageDraw.Draw(answer_img)

    page_table = [["" for _ in range(tiles_per_row)] for _ in range(tiles_per_col)]
    circle_radius_px = int((config.circle_diametr_mm / 2) * px_per_mm)
    t_s = int(shuffled_tile_px * config.answer_scale)

    for i, (orig_pos, tile) in enumerate(page_tiles):
        row_o, col_o = orig_pos
        orig_label = f"{config.letters[row_o]}{col_o + 1}"

        if rot_mode:
            angle = random.choice([90, 180, 270])
            tile = tile.rotate(angle, expand=True)

        row = i // tiles_per_row
        col = i % tiles_per_row

        grid_w_used = tiles_per_row * shuffled_tile_px + (tiles_per_row - 1) * gap_px
        grid_h_used = tiles_per_col * shuffled_tile_px + (tiles_per_col - 1) * gap_px
        offset_x = margin_px + (sheet_w_px - 2 * margin_px - grid_w_used) // 2
        offset_y = margin_px + (sheet_h_px - 2 * margin_px - grid_h_used) // 2

        base_x = offset_x + col * (shuffled_tile_px + gap_px)
        base_y = offset_y + row * (shuffled_tile_px + gap_px)

        draw_tile_on_sheet(sheet_img, tile, i, base_x, base_y + label_area_px, shuffled_tile_px, circle_radius_px, num_font)

        # answers
        x_s = int(base_x * config.answer_scale)
        y_s = int(base_y * config.answer_scale) + ans_label_area_px
        draw_tile_on_answer(answer_img, tile, i, x_s, y_s, t_s, px_per_mm, orig_label, ans_font)

        page_table[row][col] = orig_label

    suffix = " с поворотом" if rot_mode else ""
    label = f"{config.project_name} - Лист {page_idx}{suffix}"

    draw_label = ImageDraw.Draw(sheet_img)
    bbox = draw_label.textbbox((0, 0), label, font=label_font)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw_label.text(((sheet_w_px - lw) // 2, (label_area_px - lh) // 2), label, font=label_font, fill="black")

    out_path = os.path.join(output_dir, f"shuffled_{page_idx}{suffix}.png")
    sheet_img.save(out_path, dpi=(dpi, dpi))
    print(f"   ↳ Сохранён {os.path.basename(out_path)}")

    # подпись и сохранение answers (только без поворота)
    if not rot_mode:
        ans_label_font_size = int(config.label_font_mm * px_per_mm * config.answer_scale)
        ans_label_font = ImageFont.truetype(config.font_path, ans_label_font_size)
        bbox = draw_ans.textbbox((0, 0), label, font=ans_label_font)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw_ans.text(((ans_sheet_w - lw) // 2, (ans_label_area_px - lh) // 2), label, font=ans_label_font, fill="black")

        ans_path = os.path.join(output_dir, f"answers_sheet_{page_idx}.png")
        answer_img.save(ans_path, dpi=(dpi, dpi))
        print(f"   ↳ Сохранён {os.path.basename(ans_path)}")

    return page_table, suffix, page_idx, rot_mode


def make_shuffled_sheets(tiles, px_per_mm, dpi, output_dir):
    shuffled_tile_px = int(config.shuffled_tile_mm * px_per_mm)
    gap_px = int(config.gap_mm * px_per_mm)
    margin_px = int(config.margin_mm * px_per_mm)
    sheet_w_px = int(config.sheet_w_mm * px_per_mm)
    sheet_h_px = int(config.sheet_h_mm * px_per_mm)

    tiles_per_row = (sheet_w_px - 2 * margin_px + gap_px) // (shuffled_tile_px + gap_px)
    tiles_per_col = (sheet_h_px - 2 * margin_px + gap_px) // (shuffled_tile_px + gap_px)
    tiles_per_sheet = max(1, tiles_per_row * tiles_per_col)

    if config.rotate_tiles is None:
        modes = [False, True]
    elif config.rotate_tiles is True:
        modes = [True]
    else:
        modes = [False]

    shuf_tiles = generate_non_conflicting_rows(tiles, tiles_per_row, min_distance=1)

    total_pages = math.ceil(len(shuf_tiles) / tiles_per_sheet)
    print(f"🧩 Генерация shuffled-листов... (всего {total_pages} страниц, {len(tiles)} тайлов)")

    jobs = []
    with ProcessPoolExecutor() as executor:
        for idx in range(1, total_pages + 1):
            print(f"  • Планируем лист {idx}")
            start = (idx - 1) * tiles_per_sheet
            end = start + tiles_per_sheet
            page_tiles = shuf_tiles[start:end]
            print(f"  • Планируем лист {idx} ({len(page_tiles)} тайлов)")

            for rot_mode in modes:
                jobs.append(
                    executor.submit(
                        make_sheet_page,
                        page_tiles,
                        rot_mode,
                        px_per_mm,
                        dpi,
                        tiles_per_row,
                        tiles_per_col,
                        shuffled_tile_px,
                        gap_px,
                        margin_px,
                        sheet_w_px,
                        sheet_h_px,
                        idx,
                        output_dir,
                    )
                )

        collected = []
        for fut in as_completed(jobs):
            page_table, suffix, idx, rot_mode = fut.result()
            collected.append((idx, rot_mode, suffix, page_table))

        collected.sort(key=lambda t: (t[0], t[1]))

    answers_log = []
    for idx, rot_mode, suffix, page_table in collected:
        answers_log.append(f"\n=== Лист {idx}{suffix} ===\n")
        for r in page_table:
            answers_log.append("\t".join(r))

    print("✅ Shuffled-листы готовы")
    return answers_log

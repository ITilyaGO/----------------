from PIL import ImageDraw

def center_in_cell(draw, text, x0, y0, cell_w, cell_h, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = x0 + (cell_w - tw) // 2 - bbox[0]
    y = y0 + (cell_h - th) // 2 - bbox[1]
    return x, y

def draw_text_with_outline(draw, pos, text, font, fill, outline_fill, outline_width):
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx*dx + dy*dy <= outline_width*outline_width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_fill)
    draw.text((x, y), text, font=font, fill=fill)

from config import letters

def detect_white_tiles(img, cols, rows, tile_size, threshold=250):
    whites = []
    for row in range(rows):
        for col in range(cols):
            box = (col * tile_size, row * tile_size,
                   (col + 1) * tile_size, (row + 1) * tile_size)
            tile = img.crop(box)
            min_val, max_val = tile.convert("L").getextrema()
            if min_val >= threshold:
                coord = f"{letters[row]}{col+1}"
                whites.append(coord)
    return whites

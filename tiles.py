from config import letters

def split_tiles(img, cols, rows, tile_size, exclude_coords):
    tiles = []
    for row in range(rows):
        for col in range(cols):
            box = (col * tile_size, row * tile_size,
                   (col + 1) * tile_size, (row + 1) * tile_size)
            tile = img.crop(box)
            coord = f"{letters[row]}{col+1}"
            if coord not in exclude_coords:
                tiles.append(((row, col), tile))
    return tiles

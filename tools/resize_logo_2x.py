import os
from PIL import Image

base = r"C:\Scanly"
search_dirs = [os.path.join(base, 'bahan'), os.path.join(base, 'Bahan'), base]

found = None
for d in search_dirs:
    if not os.path.isdir(d):
        continue
    for ext in ['png','jpg','jpeg','jpe','bmp','svg']:
        for p in sorted(__import__('glob').glob(os.path.join(d, f"*.{ext}"))):
            if os.path.isfile(p):
                found = p
                break
        if found:
            break
    if found:
        break

if not found:
    print('NO_IMAGE_FOUND')
    raise SystemExit(1)

print('FOUND:', found)

try:
    img = Image.open(found).convert('RGBA')
except Exception as e:
    print('OPEN_ERROR', e)
    raise

# helper to create square canvas and center resized image
def make_square(im, size, bg=(255,255,255,0)):
    from PIL import Image
    w, h = im.size
    ratio = min(size/w, size/h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    im2 = im.resize((new_w, new_h), resample=Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), bg)
    paste_x = (size - new_w)//2
    paste_y = (size - new_h)//2
    canvas.paste(im2, (paste_x, paste_y), im2)
    return canvas

logo_2x_path = os.path.join(base, 'logo@2x.png')
logo_small_2x_path = os.path.join(base, 'logo_small@2x.png')

big = make_square(img, 240, bg=(255,255,255,0))
big.save(logo_2x_path, format='PNG')
print('SAVED_BIG', logo_2x_path, big.size)

small = make_square(img, 112, bg=(255,255,255,0))
small.save(logo_small_2x_path, format='PNG')
print('SAVED_SMALL', logo_small_2x_path, small.size)

# Also copy into bahan folder for convenience
try:
    bahan_dir = os.path.join(base, 'bahan')
    if os.path.isdir(bahan_dir):
        big2 = os.path.join(bahan_dir, 'logo@2x.png')
        small2 = os.path.join(bahan_dir, 'logo_small@2x.png')
        big.save(big2)
        small.save(small2)
        print('COPIED_TO_BAHAN', big2, small2)
except Exception as e:
    print('COPY_BAHAN_FAILED', e)

import os
from PIL import Image
base = r"C:\Scanly"
logo = os.path.join(base, 'logo.png')
logo_small = os.path.join(base, 'logo_small.png')

if os.path.exists(logo):
    img = Image.open(logo).convert('RGBA')
    big = img.resize((240,240), Image.LANCZOS)
    big.save(os.path.join(base,'logo@2x.png'))
    print('SAVED', os.path.join(base,'logo@2x.png'))
else:
    print('NO logo.png')

if os.path.exists(logo_small):
    img = Image.open(logo_small).convert('RGBA')
    small = img.resize((112,112), Image.LANCZOS)
    small.save(os.path.join(base,'logo_small@2x.png'))
    print('SAVED', os.path.join(base,'logo_small@2x.png'))
else:
    print('NO logo_small.png')

# copy to bahan
bahan = os.path.join(base,'bahan')
if os.path.isdir(bahan):
    if os.path.exists(os.path.join(base,'logo@2x.png')):
        Image.open(os.path.join(base,'logo@2x.png')).save(os.path.join(bahan,'logo@2x.png'))
    if os.path.exists(os.path.join(base,'logo_small@2x.png')):
        Image.open(os.path.join(base,'logo_small@2x.png')).save(os.path.join(bahan,'logo_small@2x.png'))
    print('COPIED_TO_BAHAN')

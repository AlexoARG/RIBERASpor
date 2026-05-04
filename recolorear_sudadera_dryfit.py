"""Recolorea imagenes/sudadera-dryfit-original.png a FUCSIA y AMARILLO FLUOR.
La base es una sudadera lila — la variante LILA usa la original sin recolor.
Usa rembg (U2Net) para segmentar la prenda; cachea la mascara en disco.
"""
import os
import numpy as np
from PIL import Image, ImageFilter
from rembg import remove, new_session

SRC = 'imagenes/sudadera-dryfit-original.png'
MASK_CACHE = 'imagenes/sudadera-dryfit-mask.png'
LUM_PRENDA = 0.55  # luminancia tipica del lila base

def get_mask():
    if os.path.exists(MASK_CACHE):
        return np.asarray(Image.open(MASK_CACHE).convert('L'), dtype=np.float32) / 255.0
    src_img = Image.open(SRC)
    session = new_session('u2net')
    out = remove(src_img, session=session)
    alpha = np.asarray(out.split()[-1], dtype=np.float32) / 255.0
    Image.fromarray((alpha * 255).astype(np.uint8)).save(MASK_CACHE)
    return alpha

def feather(mask, radius=2):
    img = Image.fromarray((mask * 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(img, dtype=np.float32) / 255.0

def recolor(arr, mask, target_rgb):
    target = np.array(target_rgb, dtype=np.float32) / 255.0
    lum = arr.mean(axis=-1, keepdims=True)
    factor = lum / LUM_PRENDA
    new = np.clip(target[None, None, :] * factor, 0, 1)
    a = mask[..., None]
    return arr * (1 - a) + new * a

def main():
    img = Image.open(SRC).convert('RGB')
    arr = np.asarray(img, dtype=np.float32) / 255.0
    mask = feather(get_mask(), radius=2)
    print(f'mask promedio: {float(mask.mean()):.3f}')
    Image.fromarray((np.clip(recolor(arr, mask, (220, 60, 140)), 0, 1) * 255).astype(np.uint8)) \
        .save('imagenes/sudadera-dryfit-fucsia.jpg', quality=92)
    Image.fromarray((np.clip(recolor(arr, mask, (240, 240, 60)), 0, 1) * 255).astype(np.uint8)) \
        .save('imagenes/sudadera-dryfit-amarillo-fluor.jpg', quality=92)
    print('  -> imagenes/sudadera-dryfit-{fucsia,amarillo-fluor}.jpg')

if __name__ == '__main__':
    main()

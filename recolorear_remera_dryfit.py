"""Recolorea imagenes/remera-dryfit-original.jpeg a NEGRO/BEIGE/LILA.
Usa rembg (U2Net) para segmentar la prenda del fondo, luego recolorea
preservando pliegues y sombras via factor multiplicativo.
"""
import os
import numpy as np
from PIL import Image, ImageFilter
from rembg import remove, new_session

SRC = 'imagenes/remera-dryfit-original.jpeg'
MASK_CACHE = 'imagenes/remera-dryfit-mask.png'
LUM_PRENDA = 0.56

def get_mask(arr):
    """Devuelve mascara (H, W) en 0..1 de la prenda usando rembg.
    Cachea el resultado en disco para no reprocesar."""
    if os.path.exists(MASK_CACHE):
        return np.asarray(Image.open(MASK_CACHE).convert('L'), dtype=np.float32) / 255.0
    src_img = Image.open(SRC)
    session = new_session('u2net')
    out = remove(src_img, session=session)  # RGBA
    alpha = np.asarray(out.split()[-1], dtype=np.float32) / 255.0
    Image.fromarray((alpha * 255).astype(np.uint8)).save(MASK_CACHE)
    return alpha

def feather(mask, radius=2):
    img = Image.fromarray((mask * 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(img, dtype=np.float32) / 255.0

def recolor_negro(arr, mask, target_lum=0.06):
    lum = arr.mean(axis=-1, keepdims=True)
    factor = target_lum / np.maximum(lum, 0.05)
    new = arr * factor
    a = mask[..., None]
    return arr * (1 - a) + new * a

def recolor_color(arr, mask, target_rgb):
    target = np.array(target_rgb, dtype=np.float32) / 255.0
    lum = arr.mean(axis=-1, keepdims=True)
    factor = lum / LUM_PRENDA
    new = np.clip(target[None, None, :] * factor, 0, 1)
    a = mask[..., None]
    return arr * (1 - a) + new * a

def main():
    img = Image.open(SRC).convert('RGB')
    arr = np.asarray(img, dtype=np.float32) / 255.0
    mask = get_mask(arr)
    mask = feather(mask, radius=2)
    print(f'mask promedio: {float(mask.mean()):.3f} (cobertura prenda)')
    Image.fromarray((np.clip(recolor_negro(arr, mask), 0, 1) * 255).astype(np.uint8)) \
        .save('imagenes/remera-dryfit-negro.jpg', quality=92)
    Image.fromarray((np.clip(recolor_color(arr, mask, (215, 195, 160)), 0, 1) * 255).astype(np.uint8)) \
        .save('imagenes/remera-dryfit-beige.jpg', quality=92)
    Image.fromarray((np.clip(recolor_color(arr, mask, (180, 155, 210)), 0, 1) * 255).astype(np.uint8)) \
        .save('imagenes/remera-dryfit-lila.jpg', quality=92)
    print('  -> imagenes/remera-dryfit-{negro,beige,lila}.jpg')

if __name__ == '__main__':
    main()

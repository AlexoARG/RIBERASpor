"""
Toma una imagen original (típicamente una prenda violeta/uva) y genera variantes
recolorando los píxeles del tejido a colores destino: celeste, blanca, gris-topo, etc.

Uso:
    python recolorear.py imagenes/musculosa-drifit.jpeg
"""
import sys
import os
import numpy as np
from PIL import Image

# Define los presets de color destino. Tupla HSV (h en 0-1, s en 0-1, v_factor donde
# 1.0 mantiene brillo original, <1 oscurece, >1 aclara) o lambda para casos especiales.
PRESETS = {
    # Celeste/sky blue saturado. Tolerancia estrecha para no incluir uñas violetas pero
    # con borde suave para que la prenda no quede con halo violeta.
    'celeste':  {'target_h': 0.555, 'sat_mult': 1.5, 'sat_min_after': 0.45, 'v_offset': 0.10,
                 'hue_tol_inner': 0.06, 'hue_tol_outer': 0.14,
                 'sat_min_orig': 0.10, 'sat_full_orig': 0.22},
    # Blanca: tolerancia amplia para que toda la prenda quede blanca uniforme
    'blanca':   {'target_h': 0.0, 'sat_mult': 0.02, 'sat_min_after': 0.0, 'v_offset': 0.55,
                 'hue_tol_inner': 0.10, 'hue_tol_outer': 0.22,
                 'sat_min_orig': 0.04, 'sat_full_orig': 0.15},
    # Gris topo: gris cálido neutro
    'gris-topo': {'target_h': 0.08, 'sat_mult': 0.08, 'sat_min_after': 0.0, 'v_offset': -0.05,
                  'hue_tol_inner': 0.10, 'hue_tol_outer': 0.22,
                  'sat_min_orig': 0.04, 'sat_full_orig': 0.15},
    # Negro: matar saturacion y escalar V para preservar pliegues/sombras pero llevar todo a oscuro.
    'negro':    {'target_h': 0.0, 'sat_mult': 0.0, 'sat_min_after': 0.0,
                 'v_mult': 0.10, 'v_offset': 0.0,
                 'hue_tol_inner': 0.18, 'hue_tol_outer': 0.32,
                 'sat_min_orig': 0.06, 'sat_full_orig': 0.18},
    # Crema: hue cálido apenas, saturacion baja, brillo alto.
    'crema':    {'target_h': 0.10, 'sat_mult': 0.10, 'sat_min_after': 0.07,
                 'v_mult': 0.95, 'v_offset': 0.18,
                 'hue_tol_inner': 0.12, 'hue_tol_outer': 0.25,
                 'sat_min_orig': 0.08, 'sat_full_orig': 0.20},
}


def rgb_to_hsv_np(arr):
    """arr: (H, W, 3) float 0..1 RGB → returns (H, W, 3) HSV con cada componente en 0..1."""
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    maxc = np.max(arr, axis=-1)
    minc = np.min(arr, axis=-1)
    v = maxc
    delta = maxc - minc
    s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-10), 0)

    rc = np.where(delta > 0, (maxc - r) / np.maximum(delta, 1e-10), 0)
    gc = np.where(delta > 0, (maxc - g) / np.maximum(delta, 1e-10), 0)
    bc = np.where(delta > 0, (maxc - b) / np.maximum(delta, 1e-10), 0)
    h = np.zeros_like(maxc)
    h = np.where(r == maxc, bc - gc, h)
    h = np.where(g == maxc, 2.0 + rc - bc, h)
    h = np.where(b == maxc, 4.0 + gc - rc, h)
    h = (h / 6.0) % 1.0
    return np.stack([h, s, v], axis=-1)


def hsv_to_rgb_np(arr):
    h, s, v = arr[..., 0], arr[..., 1], arr[..., 2]
    i = np.floor(h * 6.0).astype(int) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def alpha_tejido(hsv, hue_centro=0.78, hue_tol_inner=0.08, hue_tol_outer=0.18,
                 sat_min=0.05, sat_full=0.20):
    """Devuelve alpha (H, W, 1) en 0..1 para mezcla suave: 1 = pintar a fondo,
    0 = preservar original. Permite transiciones suaves en los bordes."""
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    diff = np.abs(h - hue_centro)
    diff = np.minimum(diff, 1.0 - diff)
    hue_alpha = np.clip((hue_tol_outer - diff) / max(hue_tol_outer - hue_tol_inner, 1e-6), 0, 1)
    sat_alpha = np.clip((s - sat_min) / max(sat_full - sat_min, 1e-6), 0, 1)
    v_alpha = np.clip((v - 0.06) / 0.05, 0, 1)
    alpha = hue_alpha * sat_alpha * v_alpha
    return alpha[..., None]


def recolorear(input_path, target_name, output_path,
               hue_centro_origen=0.78):
    if target_name not in PRESETS:
        raise ValueError(f"Preset '{target_name}' desconocido. Disponibles: {list(PRESETS)}")
    preset = PRESETS[target_name]

    img = Image.open(input_path).convert('RGB')
    arr = np.asarray(img, dtype=np.float32) / 255.0
    hsv = rgb_to_hsv_np(arr)

    alpha = alpha_tejido(hsv,
                         hue_centro=hue_centro_origen,
                         hue_tol_inner=preset.get('hue_tol_inner', preset.get('hue_tol', 0.10) * 0.6),
                         hue_tol_outer=preset.get('hue_tol_outer', preset.get('hue_tol', 0.18)),
                         sat_min=preset.get('sat_min_orig', 0.05),
                         sat_full=preset.get('sat_full_orig', 0.20))

    # Calcular HSV destino para todos los píxeles (aún los que no son tejido)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    new_hsv = hsv.copy()
    new_hsv[..., 0] = preset['target_h']
    new_s = np.clip(s * preset['sat_mult'], 0, 1)
    sat_min_after = preset.get('sat_min_after', 0.0)
    if sat_min_after > 0:
        new_s = np.maximum(new_s, sat_min_after)
    new_hsv[..., 1] = new_s
    v_mult = preset.get('v_mult', 1.0)
    new_hsv[..., 2] = np.clip(v * v_mult + preset['v_offset'], 0, 1)

    # Convertir ambos a RGB y blendear según alpha (en RGB para evitar artefactos en hue)
    rgb_orig = hsv_to_rgb_np(hsv)
    rgb_new = hsv_to_rgb_np(new_hsv)
    out_rgb = rgb_orig * (1 - alpha) + rgb_new * alpha
    out_arr = (np.clip(out_rgb, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(out_arr).save(output_path, quality=92)
    print(f'  → {output_path} (alpha promedio: {float(alpha.mean()):.3f})')


def main():
    if len(sys.argv) < 2:
        print('Uso: python recolorear.py <imagen_original>')
        sys.exit(1)
    src = sys.argv[1]
    if not os.path.exists(src):
        print(f'No existe: {src}')
        sys.exit(1)
    base, _ = os.path.splitext(src)
    print(f'Recoloreando {src}...')
    for nombre in PRESETS:
        out = f'{base}-{nombre}.jpg'
        recolorear(src, nombre, out)


if __name__ == '__main__':
    main()

"""
Genera catalogo.html con todos los productos en stock, agrupados por proveedor,
matcheando cada producto contra el sitemap del sitio del proveedor para obtener
imagen y URL directa.

Uso: python generar_catalogo.py
"""
import json
import re
import ssl
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

SUPABASE_URL = 'https://bovuhrcqrhhrbmktmnkj.supabase.co'
SUPABASE_KEY = 'sb_publishable_Imhg703t018wXcJw6uNxKQ_o_UxUQsh'

# Overrides manuales: cuando el matcher automático no acierta, mapear acá.
# Clave: (NOMBRE, COLOR, TALLE, proveedor_id)  — todo en MAYÚSCULAS, sin acentos
# Valor:
#   - string: URL exacta del producto en el sitio del proveedor (toma imagen del sitemap)
#   - dict {'image': 'imagenes/foo.jpg' | 'https://...', 'url': 'opcional'}:
#       imagen pinned (local o URL remota) + link opcional
OVERRIDES = {
    ('CALZA CORTA LYCRA', 'AZUL', 'S', 1): 'https://www.factionshop.com.ar/calzas/calzas-cortas/calza-corta-microfibra-marino',
    ('CAMPERA BRAVE', 'AZUL MARINO', 'XXL', 4): {
        'image': 'imagenes/campera-brave-azul-marino.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/campera-brave-smr-fa0eb98eb971542d6d4e1e8f676e3a16236d5487',
    },
    ('BUZO INSPIRE', 'NEGRO', 'L', 4): {
        'image': 'https://assets.domun.co/prod/catalogue/0705d4eb2880907143a7bf4c14e4f934dd230bad/image1rvzv1prpqumnsvtp0q.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/buzo-inspire-smr-76de8fdaafa07dbc323072a5752f34af781db0e4',
    },
    # BUZO TRUST: la galeria solo tiene fotos en aero gris y marron, no en negro real.
    # Foto descargada manualmente del sitio del proveedor.
    ('BUZO TRUST', 'NEGRO', 'XL', 4): {
        'image': 'imagenes/buzo-trust-negro.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/buzo-trust-smr-f6b0146b0e64d3d00f313da67e3180674775fcf0',
    },
    # REMERA TERMICA HOMBRE VERDE: foto provista por el cliente.
    ('REMERA TERMICA HOMBRE', 'VERDE', 'L', 4): {
        'image': 'imagenes/remera-termica-hombre-verde.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/remera-termica-hombre-s-m-l-xl-smr-2bf1f88bfb6c3ad6849523ec521e9e8b441d6b21',
    },
    # JOGGING FLORIDA CREMA: foto provista por el cliente.
    ('JOGGING FLORIDA', 'CREMA', 'L', 4): {
        'image': 'imagenes/jogging-florida-crema.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/chupin-dama-algodon--florida-smr-4f40705785eebc5cbdd10f59de3cffa1f1e3fd5c',
    },
    # TOP PULSE NEGRO: el matcher elige la foto 1 (modelo de espaldas), pero la
    # foto 4 muestra mejor el producto.
    ('TOP PULSE', 'NEGRO', 'S', 4): {
        'image': 'https://assets.domun.co/prod/catalogue/0705d4eb2880907143a7bf4c14e4f934dd230bad/image4eu7w3nu6fjomi7icojt.png',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/top-pulse-smr-53e46b827131a9e4aada533fd8ba47c9788a85ea',
    },
    # TOP MAUI NEGRO: el matcher por color elige una foto que no es negra y la
    # URL directa de la foto 1 (sumer-app-90b8f con token) tira 404. Bajamos la
    # imagen via el proxy image-tool-lambda de Domun y la pineamos local.
    ('TOP MAUI', 'NEGRO', 'L', 4): {
        'image': 'imagenes/top-maui-negro.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/top-maui-s-l-xl-xxl-smr-f3917b143210689934581d82f61680cb49b2f7db',
    },
    # BUZO MANHATAN: la galeria solo tiene foto en rosa/mint (no en negro/crema solos),
    # asi que recoloreamos la rosa con recolorear.py a negro y crema.
    ('BUZO MANHATAN', 'NEGRO', 'M', 4): {
        'image': 'imagenes/buzo-manhatan-negro.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/buzo-manhatan-frisado-unisex-smr-bc861f50bd233ddfefcf7dc2df2a03afbc9b5b2f',
    },
    ('BUZO MANHATAN', 'NEGRO', 'L', 4): {
        'image': 'imagenes/buzo-manhatan-negro.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/buzo-manhatan-frisado-unisex-smr-bc861f50bd233ddfefcf7dc2df2a03afbc9b5b2f',
    },
    ('BUZO MANHATAN', 'CREMA', 'XL', 4): {
        'image': 'imagenes/buzo-manhatan-crema.jpg',
        'url': 'https://nobrand-54113928092018s.domun.co/producto/buzo-manhatan-frisado-unisex-smr-bc861f50bd233ddfefcf7dc2df2a03afbc9b5b2f',
    },
    ('MUSCULOSA DRIFIT', 'CELESTE', '2', 1): {
        'image': 'imagenes/musculosa-drifit-celeste.jpg',
        'url': 'https://www.factionshop.com.ar/'
    },
    ('MUSCULOSA DRIFIT', 'BLANCA', '3', 1): {
        'image': 'imagenes/musculosa-drifit-blanca.jpg',
        'url': 'https://www.factionshop.com.ar/'
    },
    ('MUSCULOSA DRIFIT', 'GRIS TOPO', '3', 1): {
        'image': 'imagenes/musculosa-drifit-gris-topo.jpg',
        'url': 'https://www.factionshop.com.ar/'
    },
    # REMERA DRYFIT (FactionShop): no esta en el sitemap, asi que usamos la foto del
    # cliente recoloreada con recolorear_remera_dryfit.py.
    ('REMERA DRYFIT', 'NEGRA', '2', 1): {
        'image': 'imagenes/remera-dryfit-negro.jpg',
        'url': 'https://www.factionshop.com.ar/remeras',
    },
    ('REMERA DRYFIT', 'NEGRA', '4', 1): {
        'image': 'imagenes/remera-dryfit-negro.jpg',
        'url': 'https://www.factionshop.com.ar/remeras',
    },
    ('REMERA DRYFIT', 'BEIGE', '4', 1): {
        'image': 'imagenes/remera-dryfit-beige.jpg',
        'url': 'https://www.factionshop.com.ar/remeras',
    },
    ('REMERA DRYFIT', '(3) LILA', '4', 1): {
        'image': 'imagenes/remera-dryfit-lila.jpg',
        'url': 'https://www.factionshop.com.ar/remeras',
    },
    # SUDADERA DRYFIT (FactionShop): no esta en su sitemap. Foto base lila + recoloreadas
    # con recolorear_sudadera_dryfit.py.
    ('SUDADERA DRYFIT', 'LILA', '3', 1): {
        'image': 'imagenes/sudadera-dryfit-original.png',
        'url': 'https://www.factionshop.com.ar/remeras',
    },
    ('SUDADERA DRYFIT', 'FUCSIA', 'S', 1): {
        'image': 'imagenes/sudadera-dryfit-fucsia.jpg',
        'url': 'https://www.factionshop.com.ar/remeras',
    },
    ('SUDADERA DRYFIT', 'GRANDE AMARILLO FLUOR', 'M', 1): {
        'image': 'imagenes/sudadera-dryfit-amarillo-fluor.jpg',
        'url': 'https://www.factionshop.com.ar/remeras',
    },
    # PESCADORA MORLEY (Maik): los slugs `pescadora-azul1`/`pescadora-negra1` no
    # contienen "morley" — el matcher no los encuentra. Override directo a URL.
    ('PESCADORA MORLEY', 'AZUL', 'M', 2): 'https://www.maikmayoristas.com/productos/pescadora-azul1/',
    ('PESCADORA MORLEY', 'NEGRA', 'M', 2): 'https://www.maikmayoristas.com/productos/pescadora-negra1/',
    # Slug `remera-dryfit-gris1` (con "1") no matchea con color GRIS exacto.
    ('REMERA DRYFIT', 'GRIS', 'XL', 2): 'https://www.maikmayoristas.com/productos/remera-dryfit-gris1/',
    # Slug `top-up-uva-pastel` no contiene "morley".
    ('TOP UP MORLEY', 'UVA', 'L', 2): 'https://www.maikmayoristas.com/productos/top-up-uva-pastel/',
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# Mapeo de nombres de color → RGB target (centroide aproximado)
COLORES_RGB = {
    'NEGRO': (30, 30, 30), 'NEGRA': (30, 30, 30),
    'BLANCO': (240, 240, 240), 'BLANCA': (240, 240, 240),
    'GRIS': (130, 130, 130), 'TOPO': (110, 100, 90),
    'AZUL': (50, 80, 170), 'MARINO': (30, 40, 90),
    'ROJO': (180, 30, 30), 'ROJA': (180, 30, 30),
    'VERDE': (60, 130, 60), 'MILITAR': (90, 100, 60), 'OLIVA': (110, 110, 60),
    'CREMA': (230, 220, 200), 'BEIGE': (220, 200, 170), 'TIZA': (245, 240, 230),
    'ROSA': (240, 180, 180), 'FUCSIA': (220, 60, 140), 'CORAL': (240, 130, 110),
    'LILA': (200, 180, 220), 'VIOLETA': (140, 70, 180), 'UVA': (140, 70, 180), 'MORADO': (140, 70, 180), 'PURPURA': (140, 70, 180),
    'CELESTE': (160, 200, 230), 'TURQUESA': (60, 180, 180), 'AGUA': (130, 200, 220),
    'AMARILLO': (240, 220, 80), 'AMARILLA': (240, 220, 80), 'MOSTAZA': (210, 170, 50),
    'NARANJA': (240, 130, 50), 'OCRE': (210, 160, 80),
    'MARRON': (110, 80, 60), 'CHOCOLATE': (90, 60, 40), 'CAFE': (110, 80, 60), 'TOSTADO': (180, 130, 90), 'CARAMELO': (190, 130, 70),
    'BORDO': (110, 30, 50), 'VINO': (110, 30, 50), 'CIRUELA': (110, 50, 80),
    'PETROLEO': (40, 90, 100), 'PETROL': (40, 90, 100),
    'ORQUIDEA': (190, 130, 200), 'NUDE': (220, 195, 180),
    'VISON': (170, 150, 130), 'PERLA': (220, 215, 200),
    'CHERRY': (180, 30, 60),
}

def color_target_rgb(color_str):
    """Resuelve un string de color a RGB target. Si tiene varios tokens (ej. 'AZUL MARINO'),
    promedia los reconocidos."""
    if not color_str:
        return None
    s = color_str.upper().strip()
    if s in COLORES_RGB:
        return COLORES_RGB[s]
    rgbs = [COLORES_RGB[tok] for tok in s.split() if tok in COLORES_RGB]
    if not rgbs:
        return None
    return tuple(sum(c[i] for c in rgbs) // len(rgbs) for i in range(3))

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
        return r.read()

def sb_get(table, query=''):
    url = f'{SUPABASE_URL}/rest/v1/{table}?{query}'
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'User-Agent': 'Mozilla/5.0'
    }
    return json.loads(http_get(url, headers))

def normalizar(s):
    """Pasa a mayúsculas y reemplaza acentos/Ñ por equivalentes ASCII."""
    s = (s or '').upper()
    repl = {'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U','Ü':'U','Ñ':'N'}
    for k, v in repl.items():
        s = s.replace(k, v)
    return s

def slug_a_tokens(slug, ignorar_numeros=False):
    """Convierte un slug en set de tokens normalizados (mayús, sin acentos)."""
    s = normalizar(slug)
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    tokens = set()
    for t in s.split():
        if len(t) < 2:
            continue
        if ignorar_numeros and t.isdigit():
            continue
        tokens.add(t)
    return tokens

def parse_sitemap(content_bytes, root_domain):
    """Devuelve lista de dicts {url, image, slug, tokens}."""
    try:
        root = ET.fromstring(content_bytes)
    except ET.ParseError as e:
        print(f'    ERROR parsing sitemap: {e}')
        return []
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
          'img': 'http://www.google.com/schemas/sitemap-image/1.1'}
    items = []
    for u in root.findall('sm:url', ns):
        loc_el = u.find('sm:loc', ns)
        if loc_el is None:
            continue
        loc = (loc_el.text or '').strip()
        img_el = u.find('img:image/img:loc', ns)
        image = img_el.text.strip() if img_el is not None and img_el.text else None
        # Es producto si: tiene imagen asociada, o el path matchea /productos?/ o /product/
        path = re.sub(r'^https?://[^/]+', '', loc).rstrip('/')
        es_producto = bool(image) or bool(re.search(r'/(productos?|product)/', loc))
        if not es_producto:
            continue
        # Excluir páginas de categoría sin slug específico (ej. /calzas)
        segments = [s for s in path.split('/') if s]
        if len(segments) < 2 and not image:
            continue
        slug = segments[-1] if segments else ''
        items.append({
            'url': loc,
            'image': image,
            'slug': slug,
            'tokens': slug_a_tokens(slug)
        })
    return items

COLORES_CONOCIDOS = {
    'NEGRO','NEGRA','BLANCO','BLANCA','AZUL','AZULES','ROJO','ROJA','VERDE','AMARILLO','AMARILLA',
    'NARANJA','GRIS','GRISES','MARRON','BEIGE','ROSA','FUCSIA','VIOLETA','MORADO','LILA',
    'CELESTE','BORDO','TURQUESA','PETROLEO','PETROL','CREMA','MILITAR','NUDE','MARINO',
    'PERLA','CARAMELO','MOSTAZA','CORAL','MENTA','OLIVA','OCRE','CIRUELA','VINO','MUSGO',
    'MAGENTA','PURPURA','FLUOR','NEON','DORADO','DORADA','PLATEADO','PLATEADA','COBRE',
    'CHOCOLATE','CAFE','TOSTADO','VISON','MELANGE','UVA','MALBEC','MOCA','PEPPER','LIMA',
    'AERO','ORQUIDEA','TIZA','NATURAL','TOPO','PLATA','VISION','CHERRY','PINK','BLUE',
    'BLACK','WHITE','GREEN','RED','GRAY','GREY','YELLOW','BROWN','PURPLE','VIOLET',
    'JAZMIN','FRESIA','SIGMA','KAIRO','ARENA','SALMON','BERMELLON','BORDEAUX','ESMERALDA',
    'COBALTO','INDIGO','LAVANDA','CAQUI','KAKI','OLIVA','SEPIA','TERRACOTA','TANGO',
    'CHAMPAGNE','VAINILLA','HUMO','OXIDO','OXIDADO','HIELO','MUSTARD','CARAMEL','SAND'
}

def stem_color(t):
    """Stem básico para igualar variantes de color: NEGRO/NEGRA → NEGR, etc."""
    if len(t) >= 5:
        if t.endswith('AS') or t.endswith('OS'):
            return t[:-2]
        if t.endswith('A') or t.endswith('O'):
            return t[:-1]
    return t

def color_overlap(color_str, slug_tokens):
    """Cuántos tokens de color (con stem) están en los tokens del slug."""
    if not color_str:
        return 0
    color_tokens = slug_a_tokens(color_str, ignorar_numeros=True)
    GENERICOS = {'DE', 'CON', 'Y', 'O'}
    color_tokens -= GENERICOS
    color_stems = {stem_color(t) for t in color_tokens}
    slug_stems = {stem_color(t) for t in slug_tokens}
    return len(color_stems & slug_stems)

def matchear(producto_nombre, sitemap_items, color=None):
    """Devuelve el mejor item del sitemap para el producto, o None.

    Prioriza fuertemente el color: si hay slugs candidatos con color matching,
    elige entre esos. Si el color no aparece en ningún slug pero hay múltiples
    candidatos por nombre con URLs distintas (indica que el proveedor tiene
    variantes por color), devuelve None para no asignar una imagen incorrecta.
    """
    nombre_tokens = slug_a_tokens(producto_nombre, ignorar_numeros=True)
    if not nombre_tokens or not sitemap_items:
        return None

    GENERICOS = {'DE', 'CON', 'PARA', 'EL', 'LA', 'LOS', 'LAS', 'SIN', 'POR', 'Y', 'O'}
    nombre_tokens = nombre_tokens - GENERICOS
    if not nombre_tokens:
        return None

    n = len(nombre_tokens)
    if n <= 2: umbral = 1
    elif n <= 4: umbral = 2
    else: umbral = (n + 2) // 3

    # Candidatos: slugs que matchean al menos `umbral` tokens del nombre
    candidatos = []
    for item in sitemap_items:
        comunes = nombre_tokens & item['tokens']
        if len(comunes) >= umbral:
            candidatos.append({
                'item': item,
                'name_score': len(comunes),
                'extras': len(item['tokens'] - nombre_tokens),
            })

    if not candidatos:
        return None

    # Subgrupo "exactos": candidatos que matchean TODOS los tokens del nombre
    # Estos son los slugs del producto base (variantes por color).
    exactos = [c for c in candidatos if nombre_tokens.issubset(c['item']['tokens'])]

    if color:
        # 1) Buscar entre exactos uno con color matching
        if exactos:
            con_color = []
            for c in exactos:
                cm = color_overlap(color, c['item']['tokens'])
                if cm > 0:
                    con_color.append((c, cm))
            if con_color:
                con_color.sort(key=lambda x: (-x[1], -x[0]['name_score'], x[0]['extras']))
                return con_color[0][0]['item']
            # Hay variantes exactas pero ninguna del color pedido.
            # Solo abortar si los slugs realmente contienen NOMBRES DE COLOR conocidos
            # (variantes por color identificables). Si los slugs son numerados o usan
            # códigos hash, son productos del mismo nombre pero indistinguibles por slug
            # → tomar el primero como foto general.
            urls_exactas = {c['item']['url'] for c in exactos}
            if len(urls_exactas) > 1:
                color_stems_known = {stem_color(c) for c in COLORES_CONOCIDOS}
                extras_set = set()
                for c in exactos:
                    extras_set |= (c['item']['tokens'] - nombre_tokens)
                tienen_colores = any(stem_color(t) in color_stems_known for t in extras_set)
                if tienen_colores:
                    return None  # variantes por color reales, no engañar
                # Slugs numerados / sin color: usar el primero
            exactos.sort(key=lambda c: (-c['name_score'], c['extras']))
            return exactos[0]['item']

        # 2) Sin exactos: buscar color en cualquier candidato
        con_color = []
        for c in candidatos:
            cm = color_overlap(color, c['item']['tokens'])
            if cm > 0:
                con_color.append((c, cm))
        if con_color:
            con_color.sort(key=lambda x: (-x[1], -x[0]['name_score'], x[0]['extras']))
            return con_color[0][0]['item']

    # Sin color, o color que no matcheó: el mejor por nombre (preferir exactos)
    pool = exactos if exactos else candidatos
    pool.sort(key=lambda c: (-c['name_score'], c['extras']))
    return pool[0]['item']

def format_money(n):
    s = f'{n:,.2f}'
    # convertir formato US (1,234.56) a AR (1.234,56)
    s = s.replace(',', '_').replace('.', ',').replace('_', '.')
    return f'${s}'

def html_escape(s):
    return (str(s) if s is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def main():
    print('1) Bajando productos con stock > 0...')
    productos = sb_get('productos', 'select=*&stock=gt.0')
    print(f'   {len(productos)} productos')

    print('2) Bajando proveedores...')
    proveedores = sb_get('proveedores', 'select=*')
    prov_by_id = {p['id']: p for p in proveedores}
    print(f'   {len(proveedores)} proveedores')

    print('3) Bajando sitemaps...')
    sitemaps = {}  # proveedor_id -> [items]
    for p in proveedores:
        notas = (p.get('notas') or '').strip()
        # extraer URL
        m = re.search(r'(https?://[^\s]+)', notas, re.I)
        if not m:
            print(f'   {p["nombre"]}: sin URL en notas, salteado')
            sitemaps[p['id']] = []
            continue
        base_url = m.group(1).rstrip('/')
        sitemap_url = base_url + '/sitemap.xml'
        try:
            content = http_get(sitemap_url)
            items = parse_sitemap(content, base_url)
            sitemaps[p['id']] = items
            print(f'   {p["nombre"]}: {len(items)} productos en sitemap ({sum(1 for i in items if i["image"])} con imagen)')
        except Exception as e:
            print(f'   {p["nombre"]}: ERROR {e}')
            sitemaps[p['id']] = []

    print('4) Matcheando productos contra sitemaps...')
    enriquecidos = []
    matches = 0
    sin_match = 0
    overrides_aplicados = 0
    for prod in productos:
        pid = prod.get('proveedor_id')
        sm = sitemaps.get(pid, [])
        match = None

        # 1) Override manual?
        key = (prod['nombre'], prod.get('color') or '', prod.get('talle') or '', pid)
        ov = OVERRIDES.get(key)
        if ov:
            if isinstance(ov, dict):
                # Imagen pinned (local o URL remota)
                match = {
                    'url': ov.get('url', ''),
                    'image': ov['image'],
                    'slug': '',
                    'tokens': set()
                }
                overrides_aplicados += 1
                # Aviso si el archivo local no existe (sólo aplica a rutas locales)
                img_val = ov['image'] or ''
                if img_val and not img_val.startswith(('http://', 'https://')):
                    import os
                    if not os.path.exists(img_val):
                        print(f"   ⚠ falta archivo: {img_val}  (producto: {prod['nombre']} / {prod.get('color')} / {prod.get('talle')})")
            else:
                # URL del proveedor: buscar en sitemap
                for item in sm:
                    if item['url'] == ov:
                        match = item
                        overrides_aplicados += 1
                        break
                if not match:
                    print(f"   ⚠ override URL no encontrada en sitemap para {key}: {ov}")

        # 2) Matcher automático
        if not match:
            match = matchear(prod['nombre'], sm, prod.get('color'))

        if match:
            matches += 1
        else:
            sin_match += 1
        enriquecidos.append({**prod, '_match': match})
    print(f'   matches: {matches}, sin match: {sin_match} (overrides: {overrides_aplicados})')

    # Para matches sin imagen (típico NoBrand): bajar la página, sacar todas las imágenes
    # del producto, y elegir la que mejor matchee el color (color promedio del centro).
    print('4b) Eligiendo mejor imagen por color en productos sin imagen en sitemap...')
    pendientes = [p for p in enriquecidos if p.get('_match') and not p['_match'].get('image')]
    cache_pages = {}     # url_pagina → html
    cache_imgs = {}      # url_imagen → (r, g, b) o None
    cache_color_pick = {} # (url_pagina, color_str) → url_imagen elegida

    def color_dominante(url_img):
        if url_img in cache_imgs:
            return cache_imgs[url_img]
        try:
            from PIL import Image as _PILImage
            from io import BytesIO as _BytesIO
            data = http_get(url_img)
            img = _PILImage.open(_BytesIO(data)).convert('RGB').resize((100, 100))
            # Centro 60x60 (excluye margen)
            center = img.crop((20, 20, 80, 80))
            pixels = list(center.getdata())
            n = len(pixels)
            r = sum(p[0] for p in pixels) // n
            g = sum(p[1] for p in pixels) // n
            b = sum(p[2] for p in pixels) // n
            cache_imgs[url_img] = (r, g, b)
            return (r, g, b)
        except Exception:
            cache_imgs[url_img] = None
            return None

    def og_image(html):
        for pat in [
            r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']',
        ]:
            m = re.search(pat, html, re.I)
            if m:
                return m.group(1)
        return None

    for i, p in enumerate(pendientes, 1):
        url_pagina = p['_match']['url']
        color_str = p.get('color') or ''
        cache_key = (url_pagina, color_str)
        if cache_key in cache_color_pick:
            p['_match']['image'] = cache_color_pick[cache_key]
            continue
        try:
            if url_pagina not in cache_pages:
                cache_pages[url_pagina] = http_get(url_pagina).decode('utf-8', errors='ignore')
            html = cache_pages[url_pagina]
            # Restringir al contenedor `product-detail-gallery`: fuera de ahi la pagina
            # incluye productos relacionados/recomendados que contaminan el match por color.
            gal_m = re.search(r'<div class="product-detail-gallery">', html)
            if gal_m:
                seg_start = gal_m.end()
                seg_end = html.find('</section>', seg_start)
                gallery_html = html[seg_start:seg_end] if seg_end > 0 else html[seg_start:seg_start + 30000]
            else:
                gallery_html = html
            plain_imgs = re.findall(r'https://(?:sumerlabs\.com|assets\.domun\.co)/prod/catalogue/[a-f0-9]+/[\w-]+\.(?:jpg|jpeg|png|webp)', gallery_html)
            # Las miniaturas vienen wrappeadas en un lambda con `url-image=` (URL-encoded).
            enc_imgs = [
                urllib.parse.unquote(e)
                for e in re.findall(r'url-image=([^"&]+)', gallery_html)
            ]
            enc_imgs = [u for u in enc_imgs if 'sumerlabs.com' in u or 'assets.domun.co' in u]
            img_urls = list(dict.fromkeys(plain_imgs + enc_imgs))
            target = color_target_rgb(color_str)
            chosen = None
            if img_urls and target:
                best, best_d = None, float('inf')
                for u in img_urls[:12]:  # limitar a 12 imágenes por producto
                    c = color_dominante(u)
                    if c is None:
                        continue
                    d = (c[0]-target[0])**2 + (c[1]-target[1])**2 + (c[2]-target[2])**2
                    if d < best_d:
                        best_d, best = d, u
                chosen = best
            if not chosen:
                chosen = og_image(html)
            if chosen:
                # No mutar `_match` directamente: distintos productos (mismo nombre/URL,
                # distinto color) comparten la misma referencia desde el sitemap, y
                # mutarla pisaria la imagen elegida para los demas colores.
                p['_match'] = {**p['_match'], 'image': chosen}
                cache_color_pick[cache_key] = chosen
        except Exception as e:
            pass
        if i % 4 == 0:
            print(f'    {i}/{len(pendientes)}')
    print(f'   imágenes elegidas: {sum(1 for p in pendientes if p["_match"].get("image"))}')

    print('5) Generando catalogo.html...')
    # Agrupar por proveedor
    grupos = defaultdict(list)
    for p in enriquecidos:
        grupos[p.get('proveedor_id')].append(p)

    # Orden: por nombre de proveedor
    orden_provs = sorted(grupos.keys(), key=lambda i: prov_by_id.get(i, {}).get('nombre', 'ZZZ'))

    fecha_hoy = datetime.now().strftime('%d/%m/%Y')
    total_productos = len(enriquecidos)
    total_unidades = sum(p['stock'] for p in enriquecidos)
    valor_total = sum(p['precio'] * p['stock'] for p in enriquecidos)

    secciones_html = []
    for pid in orden_provs:
        prov = prov_by_id.get(pid)
        prov_nombre = prov['nombre'] if prov else 'SIN PROVEEDOR'
        prov_url = ''
        if prov and prov.get('notas'):
            m = re.search(r'(https?://[^\s]+)', prov['notas'], re.I)
            if m:
                prov_url = m.group(1)

        items_grupo = sorted(grupos[pid], key=lambda x: (x['nombre'], x.get('talle', ''), x.get('color', '')))
        cards = []
        for p in items_grupo:
            match = p.get('_match')
            img = match['image'] if match and match.get('image') else None
            link = match['url'] if match else prov_url

            img_html = (
                f'<img src="{html_escape(img)}" alt="{html_escape(p["nombre"])}" loading="lazy">'
                if img
                else '<div class="sin-imagen">SIN IMAGEN</div>'
            )

            link_btn = (
                f'<a href="{html_escape(link)}" target="_blank" rel="noopener" class="ver-btn">VER EN {html_escape(prov_nombre)}</a>'
                if link
                else ''
            )

            cards.append(f'''
            <div class="card">
                <div class="img-wrap">{img_html}</div>
                <div class="card-body">
                    <h3>{html_escape(p["nombre"])}</h3>
                    <div class="meta">
                        {('<span class="badge">'+html_escape(p["genero"])+'</span>') if p.get('genero') else ''}
                        {('<span class="badge">TALLE: '+html_escape(p["talle"])+'</span>') if p.get('talle') else ''}
                        {('<span class="badge">'+html_escape(p["color"])+'</span>') if p.get('color') else ''}
                    </div>
                    <div class="precio">{format_money(p["precio"])}</div>
                    {link_btn}
                </div>
            </div>''')

        prov_subtotal = sum(p['precio'] * p['stock'] for p in items_grupo)
        prov_unidades = sum(p['stock'] for p in items_grupo)
        secciones_html.append(f'''
    <section class="proveedor">
        <div class="proveedor-header">
            <h2>{html_escape(prov_nombre)}</h2>
            <div class="prov-stats">
                {len(items_grupo)} PRODUCTOS · {prov_unidades} UNIDADES · {format_money(prov_subtotal)}
            </div>
        </div>
        <div class="grid">{"".join(cards)}</div>
    </section>''')

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Catálogo de productos en stock</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: 'Segoe UI', Tahoma, sans-serif;
        background: #f5f5f7;
        color: #2C3E50;
        text-transform: uppercase;
        line-height: 1.4;
    }}
    .top {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px 20px;
        text-align: center;
    }}
    .top h1 {{ font-size: 28px; }}
    .top p {{ margin-top: 6px; opacity: 0.9; font-size: 14px; }}
    .top .stats {{
        margin-top: 15px;
        display: flex;
        gap: 30px;
        justify-content: center;
        flex-wrap: wrap;
        font-size: 13px;
    }}
    .top .stats div {{ font-weight: 600; }}
    .container {{ max-width: 1400px; margin: 0 auto; padding: 30px 20px; }}
    .proveedor {{ margin-bottom: 50px; }}
    .proveedor-header {{
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 3px solid #2E75B6;
    }}
    .proveedor-header h2 {{ font-size: 22px; color: #2E75B6; }}
    .prov-stats {{ font-size: 13px; color: #7f8c8d; margin-top: 4px; }}
    .prov-link {{
        display: inline-block;
        margin-top: 4px;
        color: #2E75B6;
        text-decoration: none;
        font-size: 12px;
        text-transform: none;
    }}
    .prov-link:hover {{ text-decoration: underline; }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 18px;
    }}
    .card {{
        background: white;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        flex-direction: column;
        transition: transform 0.15s, box-shadow 0.15s;
    }}
    .card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0,0,0,0.12);
    }}
    .img-wrap {{
        aspect-ratio: 1 / 1;
        background: #ECF0F1;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }}
    .img-wrap img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}
    .sin-imagen {{
        color: #BDC3C7;
        font-size: 12px;
        font-weight: 600;
    }}
    .card-body {{ padding: 12px; flex: 1; display: flex; flex-direction: column; gap: 6px; }}
    .card h3 {{ font-size: 13px; line-height: 1.3; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 4px; }}
    .badge {{
        background: #ECF0F1;
        color: #2C3E50;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
    }}
    .precio {{ font-size: 18px; font-weight: 700; color: #27AE60; margin-top: 4px; }}
    .stock {{ font-size: 11px; font-weight: 600; }}
    .stock-ok {{ color: #27AE60; }}
    .stock-bajo {{ color: #E67E22; }}
    .ver-btn {{
        margin-top: auto;
        display: block;
        text-align: center;
        background: #2E75B6;
        color: white;
        padding: 8px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 11px;
        font-weight: 600;
    }}
    .ver-btn:hover {{ background: #1c5689; }}
    @media print {{
        body {{ background: white; }}
        .top {{ background: white !important; color: #2C3E50 !important; -webkit-print-color-adjust: exact; }}
        .card {{ break-inside: avoid; box-shadow: none; border: 1px solid #ddd; }}
        .ver-btn {{ display: none; }}
    }}
</style>
</head>
<body>
    <div class="top">
        <h1>📦 Catálogo de productos en stock</h1>
        <p>Generado el {fecha_hoy}</p>
        <div class="stats">
            <div>{total_productos} PRODUCTOS</div>
            <div>{total_unidades} UNIDADES</div>
            <div>VALOR TOTAL: {format_money(valor_total)}</div>
        </div>
    </div>
    <div class="container">{"".join(secciones_html)}</div>
</body>
</html>'''

    with open('catalogo.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'   catalogo.html generado ({len(html):,} bytes)')

if __name__ == '__main__':
    main()

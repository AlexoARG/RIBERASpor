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
#   - dict {'image': 'imagenes/foo.jpg', 'url': 'opcional'}: imagen local + link opcional
OVERRIDES = {
    ('CALZA CORTA LYCRA', 'AZUL', 'S', 1): 'https://www.factionshop.com.ar/calzas/calzas-cortas/calza-corta-microfibra-marino',
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
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

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
                # Imagen local
                match = {
                    'url': ov.get('url', ''),
                    'image': ov['image'],
                    'slug': '',
                    'tokens': set()
                }
                overrides_aplicados += 1
                # Aviso si el archivo local no existe todavía
                import os
                if ov['image'] and not os.path.exists(ov['image']):
                    print(f"   ⚠ falta archivo: {ov['image']}  (producto: {prod['nombre']} / {prod.get('color')} / {prod.get('talle')})")
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

    # Para matches sin imagen (típico nobrand), intentar extraer og:image de la página del producto
    print('4b) Extrayendo og:image de productos matched sin imagen...')
    pendientes = [p for p in enriquecidos if p.get('_match') and not p['_match'].get('image')]
    cache_og = {}
    for i, p in enumerate(pendientes, 1):
        url = p['_match']['url']
        if url in cache_og:
            p['_match']['image'] = cache_og[url]
            continue
        try:
            html = http_get(url).decode('utf-8', errors='ignore')
            # og:image puede venir con property= o name= (NoBrand/Sumerlabs usa name=)
            patrones = [
                r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']',
            ]
            img_url = None
            for pat in patrones:
                m = re.search(pat, html, re.I)
                if m:
                    img_url = m.group(1)
                    break
            if img_url:
                p['_match']['image'] = img_url
                cache_og[url] = img_url
        except Exception:
            pass
        if i % 5 == 0:
            print(f'    {i}/{len(pendientes)}')
    print(f'   og:image extraídas: {sum(1 for p in pendientes if p["_match"].get("image"))}')

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

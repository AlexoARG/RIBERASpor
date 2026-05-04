# Sistema de Stock y Ventas - RIBERASPORT

Sistema web simple de control de stock y ventas. Datos en **PostgreSQL (Supabase)**, frontend en HTML/JS estático.

## Pasos para dejarlo funcionando

### 1. Crear las tablas en Supabase

1. Entrá a tu proyecto en [supabase.com](https://supabase.com)
2. Menú izquierdo → **SQL Editor** → **New query**
3. Abrí el archivo `supabase_setup.sql` de este repo, copiá todo y pegá en el editor
4. Click en **Run**

> Si ya habías corrido la versión anterior del script (sin la tabla `proveedores`), volvé a correrlo: usa `create table if not exists` y `drop policy if exists`, así que es idempotente.

### 2. Usar el sistema localmente

Doble click en `sistema_compartido.html` — se abre en el navegador y funciona directo (los datos viven en Supabase, no hace falta server local).

### 3. Subir a GitHub + GitHub Pages (acceso desde cualquier lado)

1. Crear repo en GitHub (puede ser público o privado).
2. Desde la carpeta del proyecto:
   ```bash
   git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
   git branch -M main
   git push -u origin main
   ```
3. En GitHub → repo → **Settings** → **Pages** → **Source: Deploy from a branch** → branch `main`, folder `/ (root)` → **Save**.
4. En 1-2 minutos vas a tener una URL pública: `https://TU-USUARIO.github.io/TU-REPO/sistema_compartido.html`

Listo, accedés desde cualquier dispositivo.

## Sobre la seguridad

La `anon key` de Supabase está embebida en el HTML (es pública por diseño). Las **policies de RLS** definidas en `supabase_setup.sql` actualmente permiten lectura y escritura a cualquiera con la key. Para un sistema interno chico esto está bien, pero significa que **cualquiera con la URL del HTML puede leer y modificar los datos**. Si más adelante querés restringirlo, hay que agregar autenticación (Supabase Auth con email/password).

## Estructura

- `sistema_compartido.html` — la app (frontend completo)
- `supabase_setup.sql` — schema de las tablas (productos, ventas, proveedores)
- `catalogo.html` + `generar_catalogo.py` — generador de catálogo de productos en stock con imágenes de los proveedores
- `recolorear.py` + `recolorear_remera_dryfit.py` — scripts para generar variantes de color de imágenes de productos

## Pestañas

- **Dashboard** — resumen de ventas, stock, ganancia y balance de caja.
- **Productos** — alta y baja de productos. El proveedor se elige de un dropdown poblado con la tabla de proveedores.
- **Ventas** — alta y baja de ventas. Hay un filtro por proveedor que limita los productos del buscador.
- **Proveedores** — alta, modificación y baja. Si renombrás un proveedor, los productos asociados se actualizan automáticamente.

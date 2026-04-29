# Sistema de Stock y Ventas - RIBERASPORT

Sistema web simple de control de stock y ventas. Datos en **PostgreSQL (Supabase)**, frontend en HTML/JS estático.

## Pasos para dejarlo funcionando

### 1. Crear las tablas en Supabase

1. Entrá a tu proyecto en [supabase.com](https://supabase.com)
2. Menú izquierdo → **SQL Editor** → **New query**
3. Abrí el archivo `supabase_setup.sql` de este repo, copiá todo y pegá en el editor
4. Click en **Run**

### 2. (Opcional) Migrar datos del Google Sheet anterior

Si tenés datos cargados en el Google Sheet viejo:

1. Abrí `migrar.html` con doble click (o desde el server local)
2. Click en **Probar conexión** — debería mostrar todo OK
3. Click en **Migrar ahora** — espera a que diga "MIGRACIÓN COMPLETA"
4. Como dice el log al final, ejecutá esto en **Supabase SQL Editor** para que los IDs sigan numerando desde el último:

   ```sql
   SELECT setval(pg_get_serial_sequence('productos','id'), COALESCE((SELECT MAX(id) FROM productos), 1));
   SELECT setval(pg_get_serial_sequence('ventas','id'), COALESCE((SELECT MAX(id) FROM ventas), 1));
   ```

5. Una vez migrado y verificado, podés borrar `migrar.html` (o dejarlo).

### 3. Usar el sistema localmente

Doble click en `iniciar_sistema.bat` → abre `http://localhost:8000/sistema_compartido.html`.

> Como ahora los datos están en Supabase (en la nube), también podés abrir el HTML directo (sin servidor) y funciona igual.

### 4. Subir a GitHub + GitHub Pages (acceso desde cualquier lado)

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
- `supabase_setup.sql` — schema de las tablas
- `migrar.html` — herramienta one-shot para migrar del Google Sheet a Supabase
- `iniciar_sistema.bat` — server local de Python para uso offline

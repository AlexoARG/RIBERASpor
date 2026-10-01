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

Con el login con Google activado (ver "Acceso con Google"), el sistema se usa desde la URL de GitHub Pages. Abrirlo con doble click ya no sirve porque Google no puede volver a un archivo local.

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

## Acceso con Google (seguridad)

El sistema pide login con Google y solo entran los emails cargados en la tabla `usuarios_permitidos`. La restricción está en la base (RLS), no solo en la pantalla: aunque alguien tenga la URL y la key pública, no puede leer ni modificar productos, ventas, proveedores ni gastos. El catálogo público sigue funcionando (ve productos con stock sin el costo, nombres de proveedores, y registra visitas).

> El login con Google no funciona abriendo el HTML con doble click (`file://`): hay que entrar por la URL de GitHub Pages.

Pasos, **en este orden**:

1. **Google Cloud** ([console.cloud.google.com](https://console.cloud.google.com)):
   - Crear un proyecto → **APIs y servicios** → **Pantalla de consentimiento de OAuth** → tipo *Externo*, completar nombre y email.
   - **Credenciales** → **Crear credenciales** → **ID de cliente de OAuth** → tipo *Aplicación web*.
   - En **URIs de redireccionamiento autorizados** poner: `https://bovuhrcqrhhrbmktmnkj.supabase.co/auth/v1/callback`
   - Copiar el *Client ID* y el *Client Secret*.
2. **Supabase** → **Authentication**:
   - **Sign In / Providers** → **Google** → activarlo y pegar Client ID y Client Secret.
   - **Sign In / Providers** → desactivar **Email** (para que nadie pueda registrarse con email/contraseña).
   - **URL Configuration** → *Site URL*: `https://TU-USUARIO.github.io/TU-REPO/sistema_compartido.html` (y agregarla también en *Redirect URLs*).
3. Publicar en GitHub Pages la versión nueva de `sistema_compartido.html` y `catalogo.html` (push a `main`).
4. Editar en `supabase_auth.sql` los dos emails autorizados y correrlo en el **SQL Editor**.

Para agregar o quitar a alguien después, en el SQL Editor:

```sql
insert into usuarios_permitidos (email) values ('alguien@gmail.com');
delete from usuarios_permitidos where email = 'alguien@gmail.com';
```

Si alguien no autorizado entra con Google, el sistema le muestra "no tiene acceso" y lo desloguea. Su usuario queda creado en Supabase (Authentication → Users) pero no puede ver ningún dato. Si querés, podés borrarlo desde ahí.

## Estructura

- `sistema_compartido.html` — la app (frontend completo)
- `supabase_setup.sql` — schema de las tablas (productos, ventas, proveedores)
- `supabase_gastos.sql` — tabla de gastos generales + migración desde ventas
- `supabase_gastos_limpieza.sql` — limpieza posterior a la migración de gastos
- `supabase_auth.sql` — acceso restringido: usuarios autorizados y policies de RLS
- `catalogo.html` + `generar_catalogo.py` — generador de catálogo de productos en stock con imágenes de los proveedores
- `recolorear.py` + `recolorear_remera_dryfit.py` — scripts para generar variantes de color de imágenes de productos

## Pestañas

- **Dashboard General** — ganancia de ropa menos gastos generales (resultado neto), resumen mensual, gastos por categoría y balance de caja.
- **Dashboard Ropa** — solo compra/venta de ropa: ventas, stock, ganancia, inversión y visitas al catálogo.
- **Productos** — alta y baja de productos. El proveedor se elige de un dropdown poblado con la tabla de proveedores.
- **Ventas** — alta y baja de ventas. Hay un filtro por proveedor que limita los productos del buscador.
- **Gastos** — gastos que no son compra/venta de ropa (ferias, publicidad, insumos, envíos). Requiere correr en Supabase, en orden: `supabase_gastos.sql` (crea la tabla, copia ahí las ventas "SIN PRODUCTO" negativas que en realidad eran gastos y las marca inactivas; los movimientos de DUEÑOS quedan como ventas) y, una vez verificado, `supabase_gastos_limpieza.sql` (borra esas ventas inactivas y la columna `activa`).
- **Proveedores** — alta, modificación y baja. Si renombrás un proveedor, los productos asociados se actualizan automáticamente.

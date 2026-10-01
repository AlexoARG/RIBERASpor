-- =============================================
-- Acceso restringido al sistema (login con Google)
-- =============================================
-- Pegá este script en: Supabase → SQL Editor → New query → Run
-- Es idempotente: se puede correr más de una vez.
--
-- ANTES de correrlo:
--   1. Configurar el login con Google en Supabase (ver README, "Acceso con Google").
--   2. Publicar la versión nueva de sistema_compartido.html y catalogo.html.
--   3. Completar abajo los dos emails de Google autorizados.
--
-- Después de correrlo:
--   - Productos, ventas, proveedores y gastos solo los pueden leer/escribir los
--     usuarios de usuarios_permitidos que entren con Google.
--   - El catálogo público sigue funcionando: puede ver productos con stock (sin
--     el costo ni otros datos internos) y el nombre de los proveedores, y
--     registrar visitas.

-- ---------- Usuarios autorizados ----------
create table if not exists usuarios_permitidos (
  email text primary key,
  created_at timestamptz default now()
);
-- RLS sin policies: nadie puede leerla ni modificarla desde la API, solo desde el SQL Editor.
alter table usuarios_permitidos enable row level security;

insert into usuarios_permitidos (email) values
  ('TU_EMAIL@gmail.com'),
  ('EMAIL_DE_TU_MUJER@gmail.com')
on conflict (email) do nothing;

-- Para quitar a alguien: delete from usuarios_permitidos where email = '...';

-- true si el usuario logueado entró con Google y su email está autorizado
create or replace function es_usuario_permitido() returns boolean
language sql stable security definer set search_path = public
as $$
  select coalesce(auth.jwt() -> 'app_metadata' ->> 'provider', '') = 'google'
     and exists (
       select 1 from usuarios_permitidos
       where lower(email) = lower(auth.jwt() ->> 'email')
     );
$$;
revoke execute on function es_usuario_permitido() from public, anon;
grant execute on function es_usuario_permitido() to authenticated;

-- ---------- Sacar las policies abiertas ----------
drop policy if exists "lectura publica productos" on productos;
drop policy if exists "escritura publica productos" on productos;
drop policy if exists "lectura publica ventas" on ventas;
drop policy if exists "escritura publica ventas" on ventas;
drop policy if exists "lectura publica proveedores" on proveedores;
drop policy if exists "escritura publica proveedores" on proveedores;
drop policy if exists "lectura publica gastos" on gastos;
drop policy if exists "escritura publica gastos" on gastos;
drop policy if exists "lectura publica visitas" on visitas;

-- ---------- Acceso completo para los usuarios autorizados ----------
drop policy if exists "usuarios permitidos productos" on productos;
drop policy if exists "usuarios permitidos ventas" on ventas;
drop policy if exists "usuarios permitidos proveedores" on proveedores;
drop policy if exists "usuarios permitidos gastos" on gastos;
drop policy if exists "usuarios permitidos visitas" on visitas;

create policy "usuarios permitidos productos" on productos for all to authenticated
  using (es_usuario_permitido()) with check (es_usuario_permitido());
create policy "usuarios permitidos ventas" on ventas for all to authenticated
  using (es_usuario_permitido()) with check (es_usuario_permitido());
create policy "usuarios permitidos proveedores" on proveedores for all to authenticated
  using (es_usuario_permitido()) with check (es_usuario_permitido());
create policy "usuarios permitidos gastos" on gastos for all to authenticated
  using (es_usuario_permitido()) with check (es_usuario_permitido());
create policy "usuarios permitidos visitas" on visitas for select to authenticated
  using (es_usuario_permitido());

-- ---------- Catálogo público (rol anon) ----------
-- Ventas y gastos: nada.
revoke all on ventas, gastos from anon;

-- Productos: solo lectura de los que tienen stock, y solo las columnas que usa el catálogo.
revoke all on productos from anon;
grant select (id, nombre, color, talle, genero, precio, stock, imagen_url, proveedor_id) on productos to anon;
drop policy if exists "catalogo productos" on productos;
create policy "catalogo productos" on productos for select to anon using (stock > 0);

-- Proveedores: solo id y nombre (para las secciones del catálogo).
revoke all on proveedores from anon;
grant select (id, nombre) on proveedores to anon;
drop policy if exists "catalogo proveedores" on proveedores;
create policy "catalogo proveedores" on proveedores for select to anon using (true);

-- Visitas: el catálogo solo puede insertar (la policy "insert publico visitas" ya existe).
revoke all on visitas from anon;
grant insert (session_id, user_agent, referrer) on visitas to anon;

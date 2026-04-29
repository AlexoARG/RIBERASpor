-- =============================================
-- Migración: productos.proveedor (texto) → productos.proveedor_id (FK)
-- =============================================
-- Pegá este script en: Supabase → SQL Editor → New query → Run
-- Es seguro correrlo varias veces (idempotente).

-- 1. Asegurar que existe un proveedor por cada nombre que ya estaba en productos
insert into proveedores (nombre)
select distinct trim(productos.proveedor)
from productos
where productos.proveedor is not null
  and trim(productos.proveedor) <> ''
  and not exists (
      select 1 from proveedores where proveedores.nombre = trim(productos.proveedor)
  );

-- 2. Agregar la columna proveedor_id con FK (si la deletean, los productos quedan en NULL)
alter table productos
  add column if not exists proveedor_id bigint references proveedores(id) on delete set null;

-- 3. Backfill: matchear por nombre
update productos
set proveedor_id = pv.id
from proveedores pv
where productos.proveedor_id is null
  and productos.proveedor is not null
  and trim(productos.proveedor) = pv.nombre;

-- 4. Borrar la columna texto vieja
alter table productos drop column if exists proveedor;

-- 5. Verificación
select p.id, p.nombre, p.proveedor_id, pv.nombre as proveedor_nombre
from productos p
left join proveedores pv on pv.id = p.proveedor_id
order by p.id
limit 30;

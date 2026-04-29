-- =============================================
-- Carga inicial de proveedores
-- =============================================
-- Pegá este script en: Supabase → SQL Editor → New query → Run
-- Crea los proveedores que ya estaban siendo usados como texto libre en productos.
-- ON CONFLICT no aplica porque "nombre" no es UNIQUE; en su lugar,
-- usamos NOT EXISTS para no duplicar si ya existen.

insert into proveedores (nombre)
select 'FactionShop'
where not exists (select 1 from proveedores where nombre = 'FactionShop');

insert into proveedores (nombre)
select 'Maik store'
where not exists (select 1 from proveedores where nombre = 'Maik store');

insert into proveedores (nombre)
select 'Sixty'
where not exists (select 1 from proveedores where nombre = 'Sixty');

-- Verificación
select * from proveedores order by nombre;

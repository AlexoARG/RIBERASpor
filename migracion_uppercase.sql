-- =============================================
-- Migración: pasar a MAYÚSCULAS los datos existentes
-- =============================================
-- Pegá este script en: Supabase → SQL Editor → New query → Run
-- Es seguro correrlo varias veces (idempotente: UPPER de algo ya en mayúscula no cambia nada).
-- Se exceptúa el campo "notas" de proveedores porque puede contener URLs (sensibles a mayúsculas).

update productos set
    nombre = upper(nombre),
    descripcion = upper(descripcion),
    talle = upper(talle),
    color = upper(color),
    genero = upper(genero),
    forma_pago_compra = upper(forma_pago_compra);

update ventas set
    cliente = upper(cliente),
    producto_nombre = upper(producto_nombre),
    estado_pago = upper(estado_pago),
    forma_pago = upper(forma_pago),
    obs = upper(obs);

update proveedores set
    nombre = upper(nombre),
    contacto = upper(contacto),
    telefono = upper(telefono),
    email = upper(email);
-- Notas se deja igual (puede contener URLs).

-- Verificación
select 'productos' as tabla, count(*) as filas from productos
union all select 'ventas', count(*) from ventas
union all select 'proveedores', count(*) from proveedores;

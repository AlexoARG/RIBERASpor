-- =============================================
-- Limpieza de la migración de gastos
-- =============================================
-- Correr DESPUÉS de supabase_gastos.sql, una vez verificado que los gastos
-- migrados están bien en la solapa Gastos.
-- Pegá este script en: Supabase → SQL Editor → New query → Run
--
-- Borra definitivamente de ventas las "ventas SIN PRODUCTO" que ya se copiaron
-- a gastos (quedaron inactivas) y elimina la columna ventas.activa.
-- Los gastos conservan venta_origen_id como referencia de dónde vinieron.

delete from ventas where activa = false;

alter table ventas drop column if exists activa;

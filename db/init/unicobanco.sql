-- en tu schema.sql (una vez):
CREATE UNIQUE INDEX IF NOT EXISTS uq_banco_nombre ON bancos.bancos (nombre_banco);

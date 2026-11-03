"""Transactional adoption of pre-versioned CareerOS databases."""
import re

SCHEMA_VERSION = 1


def migrate(connection, schema):
    current = connection.execute('PRAGMA user_version').fetchone()[0]
    if current > SCHEMA_VERSION:
        raise RuntimeError('Banco criado por uma versão mais recente do CareerOS.')
    if current == SCHEMA_VERSION:
        return
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('BEGIN IMMEDIATE')
    try:
        # Create tables first; indexes can refer to columns added below.
        statements = [s.strip() for s in schema.split(';') if s.strip()]
        tables = [s for s in statements if s.startswith('CREATE TABLE')]
        for statement in tables:
            connection.execute(statement)
            match = re.fullmatch(r'CREATE TABLE IF NOT EXISTS (\w+)\((.*)\)', statement, re.S)
            table, definitions = match.groups()
            existing = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
            for definition in definitions.split(','):
                name = definition.split()[0]
                if name in existing:
                    continue
                # Unknown historical layouts need a deliberate migration rather
                # than a destructive guess at required keys or date defaults.
                if any(token in definition.upper() for token in ('PRIMARY KEY', 'UNIQUE', 'CURRENT_TIMESTAMP')):
                    raise RuntimeError(f'Schema antigo não suportado: {table}.{name}. Banco preservado.')
                connection.execute(f'ALTER TABLE "{table}" ADD COLUMN {definition}')
        for statement in statements:
            if statement.startswith('CREATE INDEX') or statement.startswith('CREATE UNIQUE INDEX'):
                connection.execute(statement)
        connection.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
        connection.commit()
    except BaseException:
        connection.rollback()
        raise

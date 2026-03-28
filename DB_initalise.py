import json
import psycopg2
from psycopg2 import sql

# Replace with your actual Django/pgAdmin DB credentials
DB_CONFIG = {
    "dbname": "TestDB",
    "user": "postgres",
    "password": "Password",
    "host": "localhost",
    "port": "5432"
}
schema = {}

def load_schema_from_file():

    with open(Schema.json, "r", encoding="utf-8") as file:
        schema = json.load(file)

    return schema


# Map to PostgreSQL data types
TYPE_MAP = {
    "int": "INTEGER",
    "float": "REAL",
    "string": "TEXT",
    "bool": "BOOLEAN"
}

def parse_type(type_str):
    base_type = type_str.split()[0].lower()
    sql_type = TYPE_MAP.get(base_type, "TEXT")
    if "(pk)" in type_str:
        return f"{sql_type} PRIMARY KEY"
    return sql_type

def extract_foreign_keys(fields):
    fks = []
    for col, type_str in fields.items():
        if "(fk to" in type_str:
            ref = type_str.split("to")[1].strip(" )")
            ref_table, ref_col = ref.split(".")
            fks.append((col, ref_table, ref_col))
    return fks

def create_tables_postgres(schema, config):
    conn = psycopg2.connect(
        dbname="TestDB",
        user="postgres",
        password="pass",
        host="localhost",
        port="5432")
    cur = conn.cursor()

    for table_name, fields in schema.items():
        column_defs = []
        foreign_keys = extract_foreign_keys(fields)

        for col_name, type_str in fields.items():
            column_defs.append(f"{col_name} {parse_type(type_str)}")

        for fk_col, ref_table, ref_col in foreign_keys:
            column_defs.append(
                f"FOREIGN KEY ({fk_col}) REFERENCES {ref_table}({ref_col})"
            )

        create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} (\n  " + ",\n  ".join(column_defs) + "\n);"
        print(f"\nExecuting for table: {table_name}")
        print(create_stmt)
        cur.execute(create_stmt)

    conn.commit()
    conn.close()
    print("\n✅ Tables created in PostgreSQL database.")

# === Run script ===
if __name__ == "__main__":
    schema = json.loads(schema_json)
    create_tables_postgres(schema, DB_CONFIG)
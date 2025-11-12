import re
import os

def parse_sql_schema(sql_file_path):
    """
    Parses a .sql schema file and extracts table names, columns, and primary/foreign keys.
    Returns a clean textual summary for embedding.
    """
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    # Remove comments
    sql_text = re.sub(r'--.*', '', sql_text)
    sql_text = re.sub(r'/\*[\s\S]*?\*/', '', sql_text)

    # Find all CREATE TABLE blocks
    tables = re.findall(r'CREATE TABLE\s+`?(\w+)`?\s*\((.*?)\);', sql_text, re.S | re.I)

    schema_summary = []

    for table_name, table_body in tables:
        table_lines = table_body.splitlines()
        columns = []
        primary_keys = []
        foreign_keys = []

        for line in table_lines:
            line = line.strip().rstrip(',')
            if not line:
                continue

            # Column definition
            col_match = re.match(r'`?(\w+)`?\s+([\w()]+)', line)
            if col_match:
                col_name, col_type = col_match.groups()
                columns.append(f"{col_name} ({col_type})")

            # Primary key
            pk_match = re.match(r'PRIMARY KEY\s*\((.*?)\)', line, re.I)
            if pk_match:
                keys = [k.strip().strip('`') for k in pk_match.group(1).split(',')]
                primary_keys.extend(keys)

            # Foreign key
            fk_match = re.match(r'FOREIGN KEY\s*\((.*?)\)\s+REFERENCES\s+`?(\w+)`?\s*\((.*?)\)', line, re.I)
            if fk_match:
                fk_cols = [k.strip().strip('`') for k in fk_match.group(1).split(',')]
                ref_table = fk_match.group(2)
                ref_cols = [k.strip().strip('`') for k in fk_match.group(3).split(',')]
                foreign_keys.append((fk_cols, ref_table, ref_cols))

        table_text = f"### {table_name}\n- Columns:\n"
        for col in columns:
            table_text += f"  - {col}\n"

        if primary_keys:
            table_text += f"- Primary Keys: {', '.join(primary_keys)}\n"

        if foreign_keys:
            table_text += "- Foreign Keys:\n"
            for fk_cols, ref_table, ref_cols in foreign_keys:
                table_text += f"  - {', '.join(fk_cols)} -> {ref_table}({', '.join(ref_cols)})\n"

        schema_summary.append(table_text)

    return "\n".join(schema_summary)


def save_schema_summary(sql_file_path, output_path="schema_summary.txt"):
    summary_text = parse_sql_schema(sql_file_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    print(f"Schema summary saved to {output_path}")


if __name__ == "__main__":
    sql_file = "hxa.sql"  # Replace with your .sql file path
    save_schema_summary(sql_file)

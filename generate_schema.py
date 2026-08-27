import re
import os


CONSTRAINT_KEYWORDS = (
    "PRIMARY KEY", "UNIQUE KEY", "UNIQUE", "KEY", "INDEX",
    "CONSTRAINT", "FOREIGN KEY", "FULLTEXT", "SPATIAL", "CHECK",
)


def _split_top_level(text, sep=","):
    """Split text on sep, ignoring separators inside parentheses or quotes.
    This is what makes column types like decimal(10,2) or enum('a','b')
    not get split apart by mistake."""
    parts = []
    depth = 0
    current = []
    in_quote = None
    for ch in text:
        if in_quote:
            current.append(ch)
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ("'", '"', "`"):
            in_quote = ch
            current.append(ch)
            continue
        if ch == "(":
            depth += 1
            current.append(ch)
            continue
        if ch == ")":
            depth -= 1
            current.append(ch)
            continue
        if ch == sep and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _find_matching_paren(text, open_pos):
    """Given the index of an opening '(', return the index of its
    matching ')' by counting nesting depth, instead of just scanning
    forward for the next ');' in the whole file (which can wander into
    an unrelated CREATE VIEW or stored procedure further down)."""
    depth = 0
    for i in range(open_pos, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def parse_sql_schema(sql_file_path):
    """
    Parses a .sql dump and extracts table names and their full column lists.
    Works whether each CREATE TABLE statement is spread across many lines
    or minified onto a single line. Skips CREATE VIEW / stored procedure
    DDL entirely, since those aren't tables.
    """
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    # Strip SQL comments
    sql_text = re.sub(r'--.*', '', sql_text)
    sql_text = re.sub(r'/\*[\s\S]*?\*/', '', sql_text)

    schema_summary = []

    for m in re.finditer(r'CREATE TABLE\s+`?(\w+)`?\s*\(', sql_text, re.I):
        table_name = m.group(1)
        open_pos = m.end() - 1  # position of the '('
        close_pos = _find_matching_paren(sql_text, open_pos)
        if close_pos == -1:
            continue
        table_body = sql_text[open_pos + 1:close_pos]

        columns = []
        primary_keys = []
        foreign_keys = []

        for segment in _split_top_level(table_body):
            seg = segment.strip()
            if not seg:
                continue
            seg_upper = seg.upper()

            if seg_upper.startswith("PRIMARY KEY"):
                inner = re.search(r'\((.*)\)', seg)
                if inner:
                    primary_keys.extend(
                        k.strip().strip('`') for k in inner.group(1).split(',')
                    )
                continue

            if seg_upper.startswith("FOREIGN KEY"):
                fk_match = re.match(
                    r'FOREIGN KEY\s*\((.*?)\)\s+REFERENCES\s+`?(\w+)`?\s*\((.*?)\)',
                    seg, re.I,
                )
                if fk_match:
                    fk_cols = [k.strip().strip('`') for k in fk_match.group(1).split(',')]
                    ref_table = fk_match.group(2)
                    ref_cols = [k.strip().strip('`') for k in fk_match.group(3).split(',')]
                    foreign_keys.append((fk_cols, ref_table, ref_cols))
                continue

            if any(seg_upper.startswith(kw) for kw in CONSTRAINT_KEYWORDS):
                continue  # index/key definitions aren't columns

            col_match = re.match(r'`?(\w+)`?\s+([\w]+(?:\([^)]*\))?)', seg)
            if col_match:
                col_name, col_type = col_match.groups()
                columns.append(f"{col_name} ({col_type})")

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
    sql_file = "hxa.sql"  # same .sql export you used before
    save_schema_summary(sql_file)

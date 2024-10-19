import json

def txt_to_json(input_txt, output_json_file):
    lines = input_txt.splitlines()

    data = {}
    current_table = None
    table_data = []
    table_headers = []
    empty_row_count = 0

    for line in lines:
        line = line.strip()

        if line.startswith("Table"):
            if current_table is not None:
                if not table_data:
                    data[current_table] = {"Empty Rows": empty_row_count, "Empty Columns": len(table_headers)}
                else:
                    data[current_table] = table_data
            current_table = line.replace(":", "")
            table_data = []
            table_headers = []
            empty_row_count = 0
        elif line.startswith("|") and not table_headers:
            table_headers = [header.strip() for header in line.split("|")[1:-1]]
        elif line.startswith("|") and table_headers:
            row_values = [value.strip() if value.strip() else None for value in line.split("|")[1:-1]]
            if all(value is None for value in row_values):
                empty_row_count += 1
            else:
                if "TOTAL" in row_values[0]: 
                    row_data = {"TOTAL": row_values[1], "Category": row_values[2], "Score": row_values[3]}
                else:
                    row_data = {table_headers[i]: row_values[i] for i in range(len(table_headers))}
                table_data.append(row_data)

    if current_table is not None:
        if not table_data: 
            data[current_table] = {"Empty Rows": empty_row_count, "Empty Columns": len(table_headers)}
        else:
            data[current_table] = table_data

    with open(output_json_file, 'w') as json_file:
        json.dump(data, json_file, indent=4)


with open('vector-graphics/attribute_matrices/tables.txt', 'r') as file:
    input_txt = file.read()

txt_to_json(input_txt, 'vector-graphics/attribute_matrices/tables.json')
import os
import re

for d in ['services', 'routes', '.']:
    for root, _, files in os.walk(d):
        if d == '.' and root != '.': continue
        for filename in files:
            if filename.endswith('.py') and filename not in ['database.py', 'app.py', 'config.py', 'setup_bd.py', 'migrate_placeholders.py']:
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Reemplazo de sintaxis LIKE
                new_content = re.sub(r"LIKE '%' \|\| \? \|\| '%'", "ILIKE %s", content)
                new_content = re.sub(r'LIKE "%" \|\| \? \|\| "%"', "ILIKE %s", new_content)
                new_content = re.sub(r"LIKE '%' \|\| \? ", "ILIKE %s", new_content)
                new_content = re.sub(r"\? \|\| '%'", "%s", new_content)
                
                # Otros ? comunes en SQL
                new_content = re.sub(r'(?<=\s)\?(?=\s)', '%s', new_content)
                new_content = re.sub(r'=\?', '=%s', new_content)
                new_content = re.sub(r'= \?', '= %s', new_content)
                new_content = re.sub(r'\(\?', '(%s', new_content)
                new_content = re.sub(r'\?,', '%s,', new_content)
                new_content = re.sub(r'\?\)', '%s)', new_content)
                
                if content != new_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f'Actualizado {filepath}')

import re

filepath = 'services/admin_service.py'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r"strftime\('%Y',\s*([a-zA-Z._]+)\)", r'EXTRACT(YEAR FROM \1)', text)
text = re.sub(r"strftime\('%m',\s*([a-zA-Z._]+)\)", r'EXTRACT(MONTH FROM \1)', text)
text = re.sub(r"strftime\('%d',\s*([a-zA-Z._]+)\)", r'EXTRACT(DAY FROM \1)', text)
text = re.sub(r"strftime\('%m %Y',\s*([a-zA-Z._]+)\)", r"TO_CHAR(\1, 'MM YYYY')", text)

# There's another strftime with CAST or DATE? Wait, let's fix date() too.
text = re.sub(r"date\(\s*('now'|'now',\s*'localtime')\s*\)", "CURRENT_DATE", text, flags=re.IGNORECASE)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)
print('Fix strftime applied on admin_service.py')

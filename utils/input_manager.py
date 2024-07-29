import re

def normalize_input(input_text):
    input_text = input_text.lower().replace('ё', 'е').replace('р-н', 'район').replace('-', ' ')
    input_text = re.sub(r'(N|№|No)', 'N', input_text, flags=re.IGNORECASE)
    return input_text

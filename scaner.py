import openai

openai.api_key = ''


def send_request_to_vision(text):
    messages = [
        {"role": "system", "content": "ты создан для того чтобы распознавать файлы для их вставки в документ ворд. В основном ты распознаешь отсканированную информацию с официальных писем. распознавай как самый превосходный сканер на планете. не вставляй лишние переносы строк, так как это портит вид итогового документа. Учти что в документе выравнивание текста должно быть по ширине и текст должен выглядеть красиво."},
        {"role": "user", "content": text},
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        max_tokens=1500,
        n=1,
        temperature=1,
    )
    return response['choices'][0]['message']['content']

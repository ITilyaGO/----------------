import os

def save_answers(answers_log, seed, output_path):
    """
    Сохраняет текстовый файл answers.txt с таблицами ответов и сидом.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        if seed is None:
            f.write("Сид: случайный (не задан пользователем)\n\n")
        else:
            f.write(f"Сид: {seed}\n\n")
        for line in answers_log:
            f.write(line + "\n")

    print(f"💾 Ответы сохранены → {output_path}")

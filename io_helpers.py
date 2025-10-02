def save_answers(log, seed, output_answers_txt):
    with open(output_answers_txt, "w", encoding="utf-8") as f:
        if seed is None:
            f.write("Сид: случайный (не задан пользователем)\n")
        else:
            f.write(f"Сид: {seed}\n")
        f.write("\n".join(log))

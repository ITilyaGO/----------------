# config_manager.py
import os
import json
import datetime

CONFIGS_DIR = "configs"
LAST_PROJECT_FILE = os.path.join(CONFIGS_DIR, "last_project.txt")

os.makedirs(CONFIGS_DIR, exist_ok=True)

# === Управление проектами ===

def apply_config_overrides(config_dict, module_name="config"):
    """
    Подменяет значения в указанном модуле (по умолчанию — config)
    значениями из config_dict, если такие переменные там существуют.
    """
    import importlib

    module = importlib.import_module(module_name)
    for key, value in config_dict.items():
        if hasattr(module, key):
            setattr(module, key, value)


def apply_config(config: dict, globals_dict=None):
    """
    Применяет параметры конфигурации в глобальное пространство имён.
    Позволяет использовать config["..."] как обычные глобальные переменные.
    """
    import inspect

    if globals_dict is None:
        # берём globals() из места, где функция вызвана
        frame = inspect.currentframe().f_back
        globals_dict = frame.f_globals

    for key, value in config.items():
        if isinstance(key, str) and key.isidentifier():
            globals_dict[key] = value


def get_last_project():
    """Возвращает имя последнего проекта или None."""
    if os.path.exists(LAST_PROJECT_FILE):
        with open(LAST_PROJECT_FILE, "r", encoding="utf-8") as f:
            name = f.read().strip()
            return name if name else None
    return None


def set_last_project(project_name: str):
    """Сохраняет имя последнего проекта."""
    with open(LAST_PROJECT_FILE, "w", encoding="utf-8") as f:
        f.write(project_name or "")


def load_or_create_config(project_name):
    """Загружает конфиг проекта, создаёт при отсутствии."""
    config_path = os.path.join(CONFIGS_DIR, f"{project_name}.json")

    if not os.path.exists(config_path):
        print(f"🆕 Создаю новый конфиг: {config_path}")
        config = {
            "project_name": project_name,
            "input_file": "",
            "cols": 9,
            "rows": 13,
            "sheet_w_mm": 210,
            "sheet_h_mm": 297,
            "exclude_file": f"inputs/{project_name}_white_tiles.txt",
            "created_at": datetime.datetime.now().isoformat()
        }
        save_config(project_name, config)
        return config

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(project_name, config):
    """Сохраняет конфиг проекта."""
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    config_path = os.path.join(CONFIGS_DIR, f"{project_name}.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def auto_load_project(project_name=None):
    """
    Универсальная точка входа.
    Если project_name не задан — грузит последний.
    Если нет ни последнего, ни указанного — спрашивает у пользователя.
    """
    if not project_name:
        project_name = get_last_project()
        if project_name:
            print(f"📂 Используется последний проект: {project_name}")
        else:
            project_name = input("Введите имя проекта: ").strip()
            if not project_name:
                print("❌ Имя проекта не указано — выход.")
                exit(1)

    set_last_project(project_name)
    config = load_or_create_config(project_name)
    return project_name, config

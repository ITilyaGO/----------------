import os
import json
import hashlib
import datetime
import random
import shutil
from PIL import Image


class Config:
    def __init__(self):
        # --- проект ---
        self.project_name = "Новый проект"
        self.random_seed = 63235212

        # --- основные параметры ---
        self.input_file = ""
        self.cols = 20
        self.rows = 28
        self.grid_line_width = 16
        self.font_scale = 1.0
        self.tile_mm_target = 30.0

        # --- шрифты ---
        self.font_path = "resources/DearType - Lifehack Sans Medium.otf"
        self.letters = list("АБВГДЕЖИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

        # --- листы ---
        self.sheet_w_mm = 210
        self.sheet_h_mm = 297
        self.sheet_export_dpi = 1200
        self.shuffled_tile_mm = 20
        self.gap_mm = 2.5
        self.margin_mm = 3
        self.rotate_tiles = None

        # --- ответы ---
        self.answer_scale = 0.25
        self.answer_font_scale = 0.9
        self.answer_font_min = 12
        self.answer_outline = True
        self.answer_outline_width = 10
        self.answer_outline_fill = "white"
        self.answer_text_fill = "black"
        self.answer_align_x = "center"   # left | center | right
        self.answer_align_y = "bottom"   # top | center | bottom
        self.answer_margin_px = 8

        # --- нумерация ---
        self.circle_diametr_mm = 4
        self.circle_font_mm = 4.5
        self.answers_circle_scale = 1
        self.circle_fill = "white"
        self.circle_outline = "white"
        self.circle_outline_width = 1
        self.circle_text_fill = "black"

        # --- подписи ---
        self.label_font_mm = 6.0
        self.grid_label_font_mm = 8.0
        self.label_area_mm = self.grid_label_font_mm

        # --- служебные пути ---
        self.project_dir = None
        self.random_state_file = None
        self.white_tiles_file = None
        self.config_file = None

        Image.MAX_IMAGE_PIXELS = None

    # === служебные методы ===
    def ensure_project_dir(self):
        """Создаёт /out/<project>/ и определяет пути."""
        base = os.path.join("out", self.project_name)
        os.makedirs(base, exist_ok=True)
        self.project_dir = base
        self.random_state_file = os.path.join(base, "random_state.json")
        self.white_tiles_file = os.path.join(base, "white_tiles.txt")
        self.config_file = os.path.join(base, "config.json")
        return base

    # === выбор входного файла ===
    def select_input_file(self):
        """Позволяет выбрать файл из inputs/ и копирует его в проект."""
        inputs_dir = "inputs"
        os.makedirs(inputs_dir, exist_ok=True)

        files = [
            f for f in os.listdir(inputs_dir)
            if os.path.isfile(os.path.join(inputs_dir, f))
            and f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
        ]

        if not files:
            print(f"⚠️ В папке '{inputs_dir}' нет изображений.")
            print("Положите исходное изображение в эту папку и запустите снова.")
            exit(1)

        print("\n📁 Доступные файлы в папке 'inputs/':")
        for i, name in enumerate(files, 1):
            print(f"  {i}. {name}")

        try:
            choice = int(input(f"\nВыберите файл (1–{len(files)}): ").strip())
            chosen = files[choice - 1]
        except (ValueError, IndexError):
            print("❌ Некорректный выбор. Прерывание.")
            exit(1)

        src_path = os.path.join(inputs_dir, chosen)
        dst_path = os.path.join(self.project_dir, chosen)
        shutil.copy2(src_path, dst_path)

        self.input_file = dst_path
        print(f"📋 Выбран файл: {chosen}")
        print(f"📦 Скопирован в {self.project_dir}")
        self.save()

    # === загрузка / сохранение ===
    def load(self, project_name=None):
        """Загружает или создаёт конфиг проекта в out/<project>/."""
        if project_name:
            self.project_name = project_name

        self.ensure_project_dir()

        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(self, k):
                    setattr(self, k, v)
            print(f"📄 Конфиг загружен: {self.config_file}")
        else:
            print(f"🆕 Конфиг не найден, создаю новый: {self.config_file}")
            self.select_input_file()
            self.save()

        if not self.input_file or not os.path.exists(self.input_file):
            print("⚠️ Исходный файл не найден или не указан.")
            self.select_input_file()

        return self

    def save(self):
        """Сохраняет текущий конфиг."""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.as_dict(), f, indent=4, ensure_ascii=False)
        print(f"💾 Конфиг сохранён: {self.config_file}")

    def as_dict(self):
        """Возвращает словарь параметров без служебных путей."""
        exclude = {"project_dir", "random_state_file", "white_tiles_file", "config_file"}
        return {k: v for k, v in self.__dict__.items() if k not in exclude}

    def init_random(self):
        """Инициализирует random по сидy (или создаёт новый)."""
        if self.random_seed is not None:
            random.seed(self.random_seed)
            print(f"🔑 Используется фиксированный сид: {self.random_seed}")
        else:
            self.random_seed = random.randint(0, 999999999)
            random.seed(self.random_seed)
            print(f"🎲 Сгенерирован новый сид: {self.random_seed}")
            self.save()

    def compute_hash(self):
        """Вычисляет sha256 от config.json."""
        self.save()
        with open(self.config_file, "rb") as f:
            data = f.read()
        return hashlib.sha256(data).hexdigest()

    def make_output_dir(self):
        """Создаёт временную подпапку для вывода."""
        timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        path = os.path.join(self.project_dir, timestamp)
        os.makedirs(path, exist_ok=True)
        return path

    # === управление последним проектом ===
    @staticmethod
    def get_last_project_path():
        return os.path.join("configs", "last_project.txt")

    @classmethod
    def get_last_project(cls):
        path = cls.get_last_project_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                name = f.read().strip()
                return name if name else None
        return None

    @classmethod
    def set_last_project(cls, project_name):
        os.makedirs("configs", exist_ok=True)
        path = cls.get_last_project_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write(project_name or "")

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kivy.lang import Builder
from kivy.properties import DictProperty, StringProperty
from kivymd.app import MDApp

from kivy.utils import get_color_from_hex

from screens.pomodoro_screen import PomodoroScreen
from screens.subjects_screen import SubjectsScreen
from screens.study_plan_screen import StudyPlanScreen
from screens.focus_screen import FocusScreen


class NagomiApp(MDApp):
    app_data = DictProperty({})
    active_page = StringProperty("pomodoro")
    language = StringProperty("tr")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"

        self.data_path = Path(self.user_data_dir) / "app_data.json"
        self.app_data = self.load_app_data()
        self.ensure_app_data_defaults()

        self.language = self.app_data.get("language", "tr")

        # Pomodoro ekranının tasarım dosyası.
        Builder.load_file("kv/pomodoro_screen.kv")
        Builder.load_file("kv/focus_screen.kv")
        Builder.load_file("kv/subjects_screen.kv")
        Builder.load_file("kv/study_plan_screen.kv")
        

    def on_start(self):
        self.show_page("pomodoro")

    def on_pause(self) -> bool:
        if not self.root:
            return True

        screen_manager = self.root.ids.get("screen_manager")

        if not screen_manager:
            return True

        try:
            focus_screen = screen_manager.get_screen("focus")
        except Exception:
            return True

        if hasattr(focus_screen, "handle_app_pause"):
            focus_screen.handle_app_pause()

        return True


    def on_resume(self) -> None:
        if not self.root:
            return

        screen_manager = self.root.ids.get("screen_manager")

        if not screen_manager:
            return

        try:
            focus_screen = screen_manager.get_screen("focus")
        except Exception:
            return

        if hasattr(focus_screen, "handle_app_resume"):
            focus_screen.handle_app_resume()

    def show_page(self, page_name: str) -> None:
        valid_pages = {
            "pomodoro",
            "focus",
            "subjects",
            "study",
        }

        if page_name not in valid_pages:
            page_name = "pomodoro"

        self.stop_alarm()

        self.active_page = page_name
        self.root.ids.screen_manager.current = page_name
        self.root.ids.nav_drawer.set_state("close")

        current_screen = self.root.ids.screen_manager.get_screen(page_name)

        if hasattr(current_screen, "refresh_ui"):
            current_screen.refresh_ui()

    def toggle_navigation_drawer(self) -> None:
        self.root.ids.nav_drawer.set_state("toggle")

    def ensure_app_data_defaults(self) -> None:
        self.app_data.setdefault("language", "tr")
        self.app_data.setdefault("subjects", [])
        self.app_data.setdefault("tasks", [])
        self.app_data.setdefault("sessions", [])
        self.app_data.setdefault("queue_task_ids", [])
        self.app_data.setdefault("queue_mode_active", False)
        self.app_data.setdefault("active_task_id", None)
        self.app_data.setdefault("last_queue_state", None)
        self.app_data.setdefault("focus_state", {})

        settings = self.app_data.setdefault("settings", {})

        default_settings = {
            "auto_start_break": False,
            "auto_start_focus": False,
            "focus_auto_start": False,
            "sound_enabled": True,
            "regular_focus_minutes": 25,
            "regular_short_break_minutes": 5,
            "regular_long_break_minutes": 15,
            "regular_long_break_after": 4,
            "regular_focus_count": 4,
            "appearance_mode": "dark",
            "color_palette": "purple",
            
        }

        for key, value in default_settings.items():
            settings.setdefault(key, value)

        subjects = self.app_data["subjects"]

        default_subject_exists = any(
            subject.get("id") == "subject_other"
            for subject in subjects
        )

        if not default_subject_exists:
            subjects.insert(
                0,
                {
                    "id": "subject_other",
                    "name": "Diğer",
                    "name_key": "other_subject",
                    "color": "#A78BFA",
                    "is_default": True,
                },
            )

        self.save_app_data()

    def load_app_data(self) -> dict[str, Any]:
        default_data = {
            "language": "tr",
            "settings": {},
            "subjects": [],
            "tasks": [],
            "sessions": [],
            "queue_task_ids": [],
            "queue_mode_active": False,
            "active_task_id": None,
            "last_queue_state": None,
        }

        if not self.data_path.exists():
            self._write_json(default_data)
            return default_data

        try:
            with self.data_path.open("r", encoding="utf-8") as file:
                loaded_data = json.load(file)

            if not isinstance(loaded_data, dict):
                raise ValueError(
                    "Uygulama verisi sözlük formatında değil."
                )

            return loaded_data

        except (OSError, json.JSONDecodeError, ValueError) as error:
            print(f"[DATA ERROR] Veriler yüklenemedi: {error}")
            return default_data

    def save_app_data(self) -> None:
        self._write_json(dict(self.app_data))

    def _write_json(self, data: dict[str, Any]) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self.data_path.open("w", encoding="utf-8") as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=4,
                )

        except OSError as error:
            print(f"[DATA ERROR] Veriler kaydedilemedi: {error}")

    def t(self, key: str, **kwargs) -> str:
        translations = {
            "app_name": "Nagomi",
            "regular_pomodoro": "Pomodoro",
            "focus_mode": "Odak",
            "short_break_mode": "Kısa Mola",
            "long_break_mode": "Uzun Mola",
            "current_cycle": "Mevcut Döngü",
            "paused": "Duraklatıldı",
            "focus_ready": "Odaklanmaya hazır",
            "break_ready": "Mola hazır",
            "pomodoro_cycle_completed": "Pomodoro döngüsü tamamlandı",
            "other_subject": "Diğer",
            "subjects": "Dersler",
            "focus_timer": "Odak Sayacı",
            "focus_session": "Odak Oturumu",
            "start": "Başlat",
            "pause": "Duraklat",
            "continue": "Devam Et",
            "reset": "Sıfırla",
            "finish": "Bitir",
            "focused_time": "Odak Süresi",
            "away_time": "Uzakta Geçen Süre",
            "today": "Bugün",
            "this_week": "Bu Hafta",
            "no_active_task": "Serbest Odak",
            "active_task": "Aktif Görev",
            "session_completed": "Odak oturumu kaydedildi",
        }

        text = translations.get(key, key)

        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text

        return text

    def stop_alarm(self) -> None:
        # Alarm özelliğini daha sonra ekleyeceğiz.
        pass

    def play_alarm(self, source: str) -> bool:
        # Alarm özelliğini daha sonra ekleyeceğiz.
        print(f"Alarm tetiklendi: {source}")
        return True

    def open_pomodoro_settings(self) -> None:
        # Alt ayar panelini sonraki adımda oluşturacağız.
        print("Pomodoro ayarları açılacak.")

    def hex_to_rgba(self, value: str):
        return get_color_from_hex(value)


if __name__ == "__main__":
    NagomiApp().run()
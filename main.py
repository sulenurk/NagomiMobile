from __future__ import annotations

import os

from kivy.config import Config

Config.set("graphics", "width", "800")
Config.set("graphics", "height", "360")
Config.set("graphics", "resizable", "0")

from core.responsive import ResponsiveMixin
from kivy.core.window import Window

import json
from pathlib import Path
from typing import Any

from kivy.lang import Builder
from kivy.properties import (
    BooleanProperty,
    DictProperty,
    ListProperty,
    NumericProperty,
    StringProperty,
    ObjectProperty
)
from kivymd.app import MDApp

from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.utils import get_color_from_hex, platform

from core.theme import (
    PALETTE_NAMES,
    THEME_PALETTES,
    build_theme,
)

from screens.pomodoro_screen import PomodoroScreen
from screens.subjects_screen import SubjectsScreen
from screens.study_plan_screen import StudyPlanScreen
from screens.focus_screen import FocusScreen
from screens.statistics_screen import StatisticsScreen
from screens.settings_screen import SettingsScreen


class NagomiApp(ResponsiveMixin, MDApp):
    app_data = DictProperty({})
    translations = DictProperty({}) 

    active_page = StringProperty("pomodoro")
    language = StringProperty("en")
    translation_version = NumericProperty(0)

    sound_enabled = BooleanProperty(True)
    dark_mode_enabled = BooleanProperty(True)
    selected_language_name = StringProperty("English")

    theme_colors = DictProperty({})
    theme_version = NumericProperty(0)

    color_palette = StringProperty("purple")
    selected_palette_name = StringProperty("Purple")

    sidebar_color = ListProperty([0.03, 0.04, 0.07, 1])

    palette_display_values = ListProperty(
        [
            "Purple",
            "Pinky",
            "Ocean Blue",
            "Forest Green",
            "Monochrome",
            "Slate",
            "Sunset Amber",
            "Nordic Mint",
        ]
    )
    preview_sound = ObjectProperty(
        None,
        allownone=True,
    )
    alarm_active = BooleanProperty(False)
    alarm_sound = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        """  # Yalnızca bilgisayarda responsive tasarım testi için
        if platform != "android":
            Window.size = (320, 568) """

        self.setup_responsive_layout()

        self.theme_cls.primary_palette = "DeepPurple"

        self.data_path = (
            Path(self.user_data_dir)
            / "app_data.json"
        )

        self.app_data = self.load_app_data()
        self.ensure_app_data_defaults()

        # -----------------------------------------------
        # DİL
        # -----------------------------------------------

        self.language = self.app_data.get(
            "language",
            "en",
        )

        self.load_translations()

        self.selected_language_name = (
            self.get_language_name(
                self.language
            )
        )

        # -----------------------------------------------
        # AYARLAR
        # -----------------------------------------------

        settings = self.app_data.setdefault(
            "settings",
            {},
        )

        self.sound_enabled = bool(
            settings.get(
                "sound_enabled",
                True,
            )
        )
        self._preview_stop_event = None

        appearance_mode = settings.get(
            "appearance_mode",
            "dark",
        )

        self.dark_mode_enabled = (
            appearance_mode == "dark"
        )

        self.color_palette = settings.get(
            "color_palette",
            "purple",
        )

        if self.color_palette not in PALETTE_NAMES:
            self.color_palette = "purple"

        self.selected_palette_name = (
            PALETTE_NAMES[
                self.color_palette
            ]
        )

        # KV dosyaları yüklenmeden önce tema renkleri hazır olmalı.
        self.apply_theme()

        self._alarm_stop_event = None

        # -----------------------------------------------
        # KV DOSYALARI
        # -----------------------------------------------

        Builder.load_file("kv/components.kv")

        Builder.load_file(
            "kv/pomodoro_screen.kv"
        )
        Builder.load_file(
            "kv/focus_screen.kv"
        )
        Builder.load_file(
            "kv/subjects_screen.kv"
        )
        Builder.load_file(
            "kv/study_plan_screen.kv"
        )
        Builder.load_file(
            "kv/statistics_screen.kv"
        )
        Builder.load_file(
            "kv/settings_screen.kv"
        )

    def apply_theme(self) -> None:
        appearance_mode = (
            "dark"
            if self.dark_mode_enabled
            else "light"
        )

        self.theme_cls.theme_style = (
            "Dark"
            if self.dark_mode_enabled
            else "Light"
        )

        new_theme_colors = build_theme(
            palette_key=self.color_palette,
            appearance_mode=appearance_mode,
        )

        self.theme_colors = dict(
            new_theme_colors
        )

        self.sidebar_color = list(
            new_theme_colors["sidebar"]
        )

        self.theme_version += 1

        # Uygulama ilk açılırken root henüz oluşmamış olabilir.
        if not self.root:
            return

        Clock.schedule_once(
            self.refresh_open_settings_panels,
            0,
        )

    def refresh_open_settings_panels(self, _dt=0) -> None:
        if not self.root:
            return

        try:
            screen_manager = self.root.ids.screen_manager
        except (AttributeError, KeyError):
            return

        for screen_name in ("pomodoro", "focus"):
            try:
                screen = screen_manager.get_screen(
                    screen_name
                )
            except Exception:
                continue

            refresh_theme = getattr(
                screen,
                "refresh_theme",
                None,
            )

            if callable(refresh_theme):
                refresh_theme()
        
    def load_translations(self) -> None:
        locale_directory = (
            Path(__file__).resolve().parent
            / "locales"
        )

        fallback_file = locale_directory / "en.json"
        language_file = (
            locale_directory
            / f"{self.language}.json"
        )

        translations: dict[str, str] = {}

        try:
            with fallback_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                fallback_data = json.load(file)

            if isinstance(fallback_data, dict):
                translations.update(fallback_data)

        except (OSError, json.JSONDecodeError) as error:
            print(f"[LANGUAGE ERROR] {error}")

        if language_file != fallback_file:
            try:
                with language_file.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    language_data = json.load(file)

                if isinstance(language_data, dict):
                    translations.update(language_data)

            except (OSError, json.JSONDecodeError) as error:
                print(f"[LANGUAGE ERROR] {error}")

        # Önemli: mevcut dict'i update etmek yerine
        # tamamen yeni bir dict atıyoruz.
        self.translations = dict(translations)
        self.translation_version += 1

    def get_language_name(self, language_code: str) -> str:
        language_names = {
            "en": "English",
            "tr": "Türkçe",
            "de": "Deutsch",
            "fr": "Français",
            "es": "Español",
            "pt": "Português",
            "zh": "简体中文",
            "ja": "日本語",
        }

        return language_names.get(language_code, "English")


    def get_language_code(self, language_name: str) -> str:
        language_codes = {
            "English": "en",
            "Türkçe": "tr",
            "Deutsch": "de",
            "Français": "fr",
            "Español": "es",
            "Português": "pt",
            "简体中文": "zh",
            "日本語": "ja",
        }

        return language_codes.get(language_name, "en")


    def set_language_by_name(self, language_name: str) -> None:
        language_code = self.get_language_code(language_name)

        if language_code == self.language:
            return

        self.selected_language_name = language_name
        self.set_language(language_code)

    def t(
        self,
        key: str,
        _translation_version: int | None = None,
        **kwargs,
    ) -> str:
        """
        _translation_version KV ifadelerinin dil değişimini izlemesini sağlar.

        Metnin üretilmesinde kullanılmaz; yalnızca Kivy property binding
        oluşturmak amacıyla metoda verilir.
        """
        text = str(
            self.translations.get(
                key,
                key,
            )
        )

        if not kwargs:
            return text

        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return text

    def set_language(self, language_code: str) -> None:
        if language_code == self.language:
            return

        self.language = language_code
        self.selected_language_name = self.get_language_name(
            language_code
        )

        self.app_data["language"] = language_code

        self.load_translations()
        self.save_app_data()
        self.refresh_language_ui()

    def refresh_language_ui(self) -> None:
        if not self.root:
            return

        screen_manager = self.root.ids.get("screen_manager")

        if not screen_manager:
            return

        for screen in screen_manager.screens:
            refresh_method = getattr(
                screen,
                "refresh_ui",
                None,
            )

            if callable(refresh_method):
                refresh_method()

            refresh_stats_method = getattr(
                screen,
                "refresh_stats",
                None,
            )

            if callable(refresh_stats_method):
                refresh_stats_method()

            load_settings_method = getattr(
                screen,
                "load_settings",
                None,
            )

            if callable(load_settings_method):
                load_settings_method()

    def set_sound_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)

        self.sound_enabled = enabled

        settings = self.app_data.setdefault(
            "settings",
            {},
        )
        settings["sound_enabled"] = enabled

        self.save_app_data()

        if not enabled:
            self.stop_alarm()
            self.stop_alarm_preview()

        print(
            "[SOUND SETTING]",
            "property:",
            self.sound_enabled,
            "saved:",
            settings["sound_enabled"],
        )


    def set_dark_mode(self, enabled: bool) -> None:
        enabled = bool(enabled)

        if self.dark_mode_enabled == enabled:
            return

        self.dark_mode_enabled = enabled

        appearance_mode = (
            "dark"
            if enabled
            else "light"
        )

        settings = self.app_data.setdefault(
            "settings",
            {},
        )

        settings["appearance_mode"] = appearance_mode

        self.apply_theme()
        self.save_app_data()

    def get_palette_key(self, palette_name: str) -> str:
        normalized_name = str(palette_name).strip()

        for palette_key, display_name in PALETTE_NAMES.items():
            if display_name == normalized_name:
                return palette_key

    def set_color_palette_by_name(
        self,
        palette_name: str,
    ) -> None:
        palette_key = self.get_palette_key(
            palette_name
        )

        self.set_color_palette(palette_key)


    def set_color_palette(
        self,
        palette_key: str,
    ) -> None:
        if palette_key not in THEME_PALETTES:
            print(
                "[PALETTE ERROR] Bulunamadı:",
                palette_key,
            )
            palette_key = "purple"

        self.color_palette = palette_key
        self.selected_palette_name = (
            PALETTE_NAMES.get(
                palette_key,
                "Purple",
            )
        )

        settings = self.app_data.setdefault(
            "settings",
            {},
        )
        settings["color_palette"] = palette_key

        self.apply_theme()
        self.save_app_data()
        self.refresh_theme_ui()

    def refresh_theme_ui(self) -> None:
        if not self.root:
            return

        screen_manager = self.root.ids.get(
            "screen_manager"
        )

        if not screen_manager:
            return

        for screen in screen_manager.screens:
            refresh_ui = getattr(
                screen,
                "refresh_ui",
                None,
            )

            if callable(refresh_ui):
                refresh_ui()

            refresh_stats = getattr(
                screen,
                "refresh_stats",
                None,
            )

            if callable(refresh_stats):
                refresh_stats()

    def on_start(self) -> None:
        self.show_page("pomodoro")

    def on_pause(self) -> bool:
        if not self.root:
            return True

        screen_manager = self.root.ids.get(
            "screen_manager"
        )

        if not screen_manager:
            return True

        for screen_name in ("pomodoro", "focus"):
            try:
                screen = screen_manager.get_screen(
                    screen_name
                )
            except Exception:
                continue

            handler = getattr(
                screen,
                "handle_app_pause",
                None,
            )

            if callable(handler):
                handler()

        return True


    def on_resume(self) -> None:
        if not self.root:
            return

        screen_manager = self.root.ids.get(
            "screen_manager"
        )

        if not screen_manager:
            return

        for screen_name in ("pomodoro", "focus"):
            try:
                screen = screen_manager.get_screen(
                    screen_name
                )
            except Exception:
                continue

            handler = getattr(
                screen,
                "handle_app_resume",
                None,
            )

            if callable(handler):
                handler()

    def show_page(self, page_name: str) -> None:
        valid_pages = {
            "pomodoro",
            "focus",
            "subjects",
            "study",
            "statistics",
            "settings",
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
        self.app_data.setdefault("language", "en")
        self.app_data.setdefault("subjects", [])
        self.app_data.setdefault("tasks", [])
        self.app_data.setdefault("sessions", [])
        self.app_data.setdefault("queue_task_ids", [])
        self.app_data.setdefault("queue_mode_active", False)
        self.app_data.setdefault("active_task_id", None)
        self.app_data.setdefault("last_queue_state", None)
        self.app_data.setdefault("focus_state", {})

        settings = self.app_data.setdefault("settings", {})
        settings.setdefault(
            "alarm_sound", "beep")

        default_settings = {
            "auto_start_break": False,
            "auto_start_focus": False,
            "sound_enabled": True,
            "daily_focus_goal_minutes": 300,
            "regular_focus_minutes": 25,
            "regular_short_break_minutes": 5,
            "regular_long_break_minutes": 15,
            "regular_long_break_after": 4,
            "regular_focus_count": 4,
            "show_queue_progress": True,
            "show_cumulative_away_time": True,
            "week_start_day": "monday",
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
                    "name_key": "other_subject",
                    "color": "#A78BFA",
                    "is_default": True,
                },
            )

        for subject in subjects:
            if subject.get("id") == "subject_other":
                subject["name_key"] = "other_subject"
                subject["is_default"] = True
                subject.pop("name", None)

        self.save_app_data()

    def load_app_data(self) -> dict[str, Any]:
        default_data = {
            "language": "en",
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

    """ def hex_to_rgba(self, value: str):
        return get_color_from_hex(value) """

    # Alarm kodları
    def get_alarm_path(self, alarm_name: str) -> Path:
        alarm_files = {
            "analog": "analog.mp3",
            "beep": "beep.mp3",
            "birdy": "birdy.mp3",
            "buzz": "buzz.mp3",
            "dance": "dans.mp3",
            "galaxy": "galaxy.mp3",
        }

        # Bilinmeyen veya boş bir değer gelirse beep kullanılır.
        filename = alarm_files.get(
            str(alarm_name).strip().lower(),
            "beep.mp3",
        )

        return (
            Path(__file__).resolve().parent
            / "assets"
            / "sounds"
            / filename
        )


    def play_alarm(self) -> None:
        print("[ALARM 1] play_alarm çağrıldı")
        print("[ALARM 2] sound_enabled:", self.sound_enabled)

        if not self.sound_enabled:
            print("[ALARM STOP] Ses ayarı kapalı.")
            return

        self.stop_alarm_preview()
        self.stop_alarm()

        settings = self.app_data.setdefault(
            "settings",
            {},
        )

        selected_alarm = str(
            settings.get("alarm_sound", "beep")
        ).strip().lower()

        print("[ALARM 3] selected_alarm:", selected_alarm)

        self.stop_alarm()

        alarm_path = self.get_alarm_path(selected_alarm)

        print("[ALARM 4] path:", alarm_path)
        print("[ALARM 5] exists:", alarm_path.exists())

        if not alarm_path.exists():
            print("[ALARM ERROR] Dosya bulunamadı.")
            return

        sound = SoundLoader.load(str(alarm_path))

        print("[ALARM 6] SoundLoader sonucu:", sound)

        if sound is None:
            print("[ALARM ERROR] Alarm yüklenemedi.")
            return

        self.alarm_sound = sound
        self.alarm_sound.loop = True
        self.alarm_sound.volume = 1.0

        self.alarm_active = True
        self.alarm_sound.play()

        self.start_alarm_vibration()

        self._alarm_stop_event = Clock.schedule_once(
            self._auto_stop_alarm,
            15,
        )


    def _auto_stop_alarm(self, _dt) -> None:
        self._alarm_stop_event = None
        self.stop_alarm()


    def stop_alarm(self) -> None:
        # Bekleyen otomatik durdurma çağrısını iptal et.
        if self._alarm_stop_event is not None:
            self._alarm_stop_event.cancel()
            self._alarm_stop_event = None

        if self.alarm_sound is not None:
            try:
                self.alarm_sound.stop()
            except Exception as error:
                print("[ALARM STOP ERROR]", error)

            self.alarm_sound = None

        self.stop_alarm_vibration()
        self.alarm_active = False

    def start_alarm_vibration(self) -> None:
        settings = self.app_data.setdefault("settings", {})

        if not bool(settings.get("vibration_enabled", True)):
            return

        if platform != "android":
            return

        try:
            from plyer import vibrator

            if vibrator.exists():
                vibrator.pattern(
                    pattern=[
                        0,
                        0.4,
                        0.25,
                        0.4,
                        0.6,
                    ],
                    repeat=0,
                )

        except Exception as error:
            print("[VIBRATION ERROR]", error)


    def stop_alarm_vibration(self) -> None:
        if platform != "android":
            return

        try:
            from plyer import vibrator
            vibrator.cancel()

        except Exception as error:
            print("[VIBRATION STOP ERROR]", error)

    @staticmethod
    def hex_to_rgba(hex_color: str) -> list[float]:
        try:
            return list(get_color_from_hex(str(hex_color)))
        except (TypeError, ValueError):
            return [0.4, 0.45, 0.55, 1]


    def preview_alarm(
        self,
        alarm_name: str,
    ) -> None:
        if not self.sound_enabled:
            return

        self.stop_alarm_preview()

        alarm_path = self.get_alarm_path(
            alarm_name
        )

        if not alarm_path.exists():
            print(
                "[ALARM PREVIEW ERROR] Dosya bulunamadı:",
                alarm_path,
            )
            return

        sound = SoundLoader.load(
            str(alarm_path)
        )

        if sound is None:
            print(
                "[ALARM PREVIEW ERROR] Ses yüklenemedi:",
                alarm_path,
            )
            return

        self.preview_sound = sound
        self.preview_sound.loop = False
        self.preview_sound.volume = 1.0
        self.preview_sound.play()

        # Önizlemeyi en fazla 3 saniye çal.
        self._preview_stop_event = Clock.schedule_once(
            self._stop_alarm_preview_event,
            3,
        )


    def _stop_alarm_preview_event(
        self,
        _dt,
    ) -> None:
        self._preview_stop_event = None
        self.stop_alarm_preview()


    def stop_alarm_preview(self) -> None:
        if self._preview_stop_event is not None:
            self._preview_stop_event.cancel()
            self._preview_stop_event = None

        if self.preview_sound is not None:
            try:
                self.preview_sound.stop()
            except Exception as error:
                print(
                    "[ALARM PREVIEW STOP ERROR]",
                    error,
                )

            self.preview_sound = None


if __name__ == "__main__":
    NagomiApp().run()
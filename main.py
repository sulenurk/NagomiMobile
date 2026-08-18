from __future__ import annotations

import os
import time

from kivy.config import Config
from kivy.utils import platform

if platform != "android":
    Config.set("graphics", "width", "320")
    Config.set("graphics", "height", "568")
    Config.set("graphics", "resizable", "1")

    Config.set("graphics", "position", "custom")
    Config.set("graphics", "left", "50")
    Config.set("graphics", "top", "50")

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
from kivy.utils import get_color_from_hex

# ---------------------------------------------------------
# ANDROID ORIENTATION
# False yaparsak telefon landscape desteği tekrar açılır.
# Mevcut landscape KV/layout kodları silinmemiştir.
# ---------------------------------------------------------
LOCK_PHONE_TO_PORTRAIT = True

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

    alarm_banner_visible = BooleanProperty(False)
    alarm_card_visible = BooleanProperty(False)

    alarm_source = StringProperty("")
    alarm_mode = StringProperty("")
    alarm_title = StringProperty("")
    alarm_subtitle = StringProperty("")

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
        # LAZY EKRAN KAYDI
        # -----------------------------------------------
        # PomodoroScreen ekrani nagomi.kv icinde statik olarak
        # tanimli (ilk gorunen ekran). Digerleri, kullanici ilk kez
        # o sayfaya gittiginde show_page() tarafindan olusturulur.
        # Bu, acilista tum 6 ekranin widget agacinin bir anda
        # kurulmasini onler.
        self._screen_classes = {
            "focus": FocusScreen,
            "subjects": SubjectsScreen,
            "study": StudyPlanScreen,
            "statistics": StatisticsScreen,
            "settings": SettingsScreen,
        }

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

    def apply_android_orientation_policy(self) -> None:
        if platform != "android":
            return

        if not LOCK_PHONE_TO_PORTRAIT:
            return

        try:
            from jnius import autoclass

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            ActivityInfo = autoclass(
                "android.content.pm.ActivityInfo"
            )

            activity = PythonActivity.mActivity

            if not self.is_tablet:
                # Telefon:
                # portrait ve reverse-portrait serbest,
                # landscape engelli.
                activity.setRequestedOrientation(
                    ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT
                )
            else:
                # Tablet:
                # mevcut rotation / landscape desteği korunur.
                activity.setRequestedOrientation(
                    ActivityInfo.SCREEN_ORIENTATION_FULL_SENSOR
                )

        except Exception as error:
            print("[ORIENTATION ERROR]", error)

    def on_layout_profile(self, _instance, value):
        print("[LAYOUT PROFILE CHANGED]", value)

        Clock.schedule_once(
            self._debug_pomodoro_layout,
            0,
        )

        Clock.schedule_once(
            self._debug_pomodoro_layout,
            0.1,
        )

        Clock.schedule_once(
            self._debug_pomodoro_layout,
            0.4,
        )

    def _force_responsive_relayout(self, _dt):
        if not self.root:
            return

        try:
            screen_manager = self.root.ids.screen_manager

            if not screen_manager.has_screen("pomodoro"):
                return

            screen = screen_manager.get_screen("pomodoro")

            main_layout = screen.ids.get("pomodoro_main_layout")
            content_layout = screen.ids.get("pomodoro_content_layout")
            top_bar = screen.ids.get("pomodoro_top_bar")

            if (
                content_layout is not None
                and top_bar is not None
            ):
                content_layout.pos = (0, 0)
                content_layout.size = (
                    screen.width,
                    max(0, screen.height - top_bar.height),
                )

            if main_layout is not None:
                main_layout.do_layout()

            if content_layout is not None:
                content_layout.do_layout()

            Clock.schedule_once(
                self._force_responsive_relayout_second_pass,
                0.1,
            )

        except Exception as error:
            print("[RESPONSIVE RELAYOUT ERROR]", error)

    def _force_responsive_relayout_second_pass(self, _dt):
        if not self.root:
            return

        try:
            screen = self.root.ids.screen_manager.get_screen("pomodoro")

            main_layout = screen.ids.get("pomodoro_main_layout")
            content_layout = screen.ids.get("pomodoro_content_layout")
            top_bar = screen.ids.get("pomodoro_top_bar")

            if (
                content_layout is not None
                and top_bar is not None
            ):
                content_layout.pos = (0, 0)
                content_layout.size = (
                    screen.width,
                    max(0, screen.height - top_bar.height),
                )

            if main_layout is not None:
                main_layout.do_layout()

            if content_layout is not None:
                content_layout.do_layout()

        except Exception as error:
            print("[RESPONSIVE RELAYOUT 2 ERROR]", error)

    def _debug_pomodoro_layout(self, _dt):
        if not self.root:
            return

        try:
            screen = self.root.ids.screen_manager.get_screen("pomodoro")

            main_layout = screen.ids.get("pomodoro_main_layout")
            content = screen.ids.get("pomodoro_content_layout")
            top_bar = screen.ids.get("pomodoro_top_bar")
            title = screen.ids.get("pomodoro_page_title")
            portrait_card = screen.ids.get("pomodoro_portrait_card")

            landscape_card = None

            if content is not None:
                for child in content.children:
                    if (
                        child is not portrait_card
                        and child.__class__.__name__ == "MDCard"
                    ):
                        landscape_card = child
                        break

            print(
                "[POMODORO LAYOUT]",
                f"profile={self.layout_profile}",
                f"window={Window.width:.1f}x{Window.height:.1f}",
                f"screen_pos={screen.pos}",
                f"screen_size={screen.size}",
                f"main_pos={main_layout.pos if main_layout else None}",
                f"main_size={main_layout.size if main_layout else None}",
                f"content_pos={content.pos if content else None}",
                f"content_size={content.size if content else None}",
                f"topbar_pos={top_bar.pos if top_bar else None}",
                f"topbar_size={top_bar.size if top_bar else None}",
                f"title_pos={title.pos if title else None}",
                f"title_size={title.size if title else None}",
                f"title_opacity={title.opacity if title else None}",
                f"portrait_pos={portrait_card.pos if portrait_card else None}",
                f"portrait_size={portrait_card.size if portrait_card else None}",
                f"portrait_hint={portrait_card.size_hint_y if portrait_card else None}",
                f"landscape_pos={landscape_card.pos if landscape_card else None}",
                f"landscape_size={landscape_card.size if landscape_card else None}",
                f"landscape_hint={landscape_card.size_hint_y if landscape_card else None}",
            )

            print(
                "[POMODORO COLLAPSE CHECK]",
                f"profile={self.layout_profile}",
                f"portrait_hint={portrait_card.size_hint_y if portrait_card else None}",
                f"portrait_h={portrait_card.height if portrait_card else None}",
                f"landscape_hint={landscape_card.size_hint_y if landscape_card else None}",
                f"landscape_h={landscape_card.height if landscape_card else None}",
            )

            if self.layout_profile == "phone_portrait":
                if landscape_card is not None:
                    if landscape_card.size_hint_y is not None:
                        print(
                            "[BUG] Landscape card still participates "
                            "in portrait layout"
                        )

                    if landscape_card.height != 0:
                        print(
                            "[BUG] Landscape card height is not zero "
                            "in portrait:",
                            landscape_card.height,
                        )

            elif self.layout_profile == "phone_landscape":
                if portrait_card is not None:
                    if portrait_card.size_hint_y is not None:
                        print(
                            "[BUG] Portrait card still participates "
                            "in landscape layout"
                        )

                    if portrait_card.height != 0:
                        print(
                            "[BUG] Portrait card height is not zero "
                            "in landscape:",
                            portrait_card.height,
                        )

            if content is not None:
                print("[CONTENT CHILDREN BEGIN]")

                for index, child in enumerate(
                    reversed(content.children)
                ):
                    print(
                        "[CONTENT CHILD]",
                        index,
                        child.__class__.__name__,
                        f"pos={child.pos}",
                        f"size={child.size}",
                        f"size_hint_y={child.size_hint_y}",
                        f"height={child.height}",
                        f"opacity={getattr(child, 'opacity', None)}",
                    )

                print("[CONTENT CHILDREN END]")

        except Exception as error:
            print("[POMODORO LAYOUT ERROR]", error)

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

    def refresh_alarm_card_visibility(self) -> None:
        target_page = ""

        if self.alarm_source == "focus":
            target_page = "focus"
        elif self.alarm_source == "pomodoro":
            target_page = "pomodoro"

        self.alarm_card_visible = bool(
            self.alarm_banner_visible
            and target_page
            and self.active_page != target_page
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
        self.show_page("focus")

        Clock.schedule_once(
            lambda _dt: self.request_notification_permission(),
            0.8,
        )

        Clock.schedule_once(
            lambda _dt: self.request_exact_alarm_permission(),
            1.5,
        )

        if platform == "android":
            Clock.schedule_once(
                lambda _dt: self.apply_android_orientation_policy(),
                0.5,
            )

        if platform != "android":
            Clock.schedule_once(
                lambda _dt: setattr(Window, "size", (568, 320)),
                3,
            )

            Clock.schedule_once(
                lambda _dt: setattr(Window, "size", (320, 568)),
                6,
            )

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

    def pause_other_timer(
        self,
        active_timer: str,
    ) -> None:
        if not self.root:
            return

        try:
            screen_manager = self.root.ids.screen_manager
        except (AttributeError, KeyError):
            return

        # Pomodoro başlatılıyorsa çalışan Focus Timer'ı duraklat.
        if active_timer == "pomodoro":
            if not screen_manager.has_screen("focus"):
                return

            try:
                focus_screen = screen_manager.get_screen(
                    "focus"
                )
            except Exception:
                return

            if focus_screen.is_running:
                focus_screen.pause_timer()

        # Focus Timer başlatılıyorsa çalışan Pomodoro'yu duraklat.
        elif active_timer == "focus":
            if not screen_manager.has_screen("pomodoro"):
                return

            try:
                pomodoro_screen = screen_manager.get_screen(
                    "pomodoro"
                )
            except Exception:
                return

            timer = getattr(
                pomodoro_screen,
                "timer",
                None,
            )

            if timer is None or not timer.is_running:
                return

            timer.pause()
            pomodoro_screen._cancel_android_alarm()
            pomodoro_screen.save_timer_state()
            pomodoro_screen.refresh_ui()


    def go_to_alarm_timer(self) -> None:
        if self.alarm_source == "focus":
            self.show_page("focus")

        elif self.alarm_source == "pomodoro":
            self.show_page("pomodoro")

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

        alarm_target_page = ""

        if self.alarm_source == "focus":
            alarm_target_page = "focus"
        elif self.alarm_source == "pomodoro":
            alarm_target_page = "pomodoro"

        # Alarmın ait olduğu timer sayfasına dönülürse
        # eski davranış gibi alarm + banner kapanır.
        if (
            self.alarm_banner_visible
            and page_name == alarm_target_page
        ):
            self.stop_alarm()

        screen_manager = self.root.ids.screen_manager

        if not screen_manager.has_screen(page_name):
            screen_cls = self._screen_classes.get(page_name)

            if screen_cls is not None:
                screen_manager.add_widget(
                    screen_cls(name=page_name)
                )

        self.active_page = page_name
        screen_manager.current = page_name

        self.refresh_alarm_card_visibility() 
        
        self.root.ids.nav_drawer.set_state("close")

        current_screen = screen_manager.get_screen(page_name)

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


    def play_alarm(
        self,
        source: str = "",
        mode: str = "",
        title: str = "",
        subtitle: str = "",
    ) -> None:
        print("[ALARM 1] play_alarm çağrıldı")
        print("[ALARM 2] sound_enabled:", self.sound_enabled)

        # Önce varsa eski alarmı/preview'i temizle.
        # Burada banner henüz yeni alarm için açılmadı.
        self.stop_alarm_preview()
        self.stop_alarm()

        # Yeni alarmın bilgilerini kaydet.
        self.alarm_source = str(source or "")
        self.alarm_mode = str(mode or "")
        self.alarm_title = str(title or "")
        self.alarm_subtitle = str(subtitle or "")

        # Banner ses kapalı olsa bile görünmeli.
        self.alarm_banner_visible = True
        self.refresh_alarm_card_visibility()

        if not self.sound_enabled:
            print("[ALARM STOP] Ses ayarı kapalı.")
            return

        settings = self.app_data.setdefault(
            "settings",
            {},
        )

        selected_alarm = str(
            settings.get("alarm_sound", "beep")
        ).strip().lower()

        print("[ALARM 3] selected_alarm:", selected_alarm)

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
        self.stop_alarm(hide_banner=False)


    def stop_alarm(self, hide_banner: bool = True) -> None:
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

        if hide_banner:
            self.alarm_banner_visible = False

        self.refresh_alarm_card_visibility()

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

    # -----------------------------------------------
    # ANDROID ALARM MANAGER
    # -----------------------------------------------
    # FocusScreen / PomodoroScreen already compute an absolute
    # end-timestamp and re-sync against it whenever the app comes
    # back to foreground (on_resume). That part is correct and
    # battery-safe. The gap: if the app is backgrounded when a
    # session ends, nothing wakes it up, so the alarm sound only
    # plays whenever the user happens to reopen the app.
    #
    # schedule_focus_alarm() closes that gap using Android's
    # AlarmManager to schedule an exact wake-up at end_timestamp
    # that relaunches this app's own activity. No custom Java
    # receiver is required: PendingIntent.getActivity() targets an
    # activity Android already knows about (this app's launcher
    # activity), so python-for-android's default manifest is
    # enough. When the activity is brought back, on_resume() runs
    # as usual, timer.sync() detects the session finished, and
    # play_alarm() fires normally.
    #
    # Trade-off: this brings the app to the foreground rather than
    # posting a silent tray notification while staying backgrounded,
    # and it only survives backgrounding/Doze - not the OS fully
    # killing the process. A tray notification that works even when
    # the app is force-closed needs a custom BroadcastReceiver
    # packaged via a p4a recipe, which is a separate, larger change.
    #
    # buildozer.spec must include, at minimum:
    #   android.permissions = VIBRATE,SCHEDULE_EXACT_ALARM,USE_EXACT_ALARM
    # (SCHEDULE_EXACT_ALARM/USE_EXACT_ALARM are required on Android 12+
    # for setExactAndAllowWhileIdle to fire on time; without them the
    # OS may silently delay the alarm.)

    def request_notification_permission(self) -> None:
        if platform != "android":
            return

        try:
            from jnius import autoclass
            from android.permissions import (
                request_permissions,
                Permission,
            )

            BuildVersion = autoclass(
                "android.os.Build$VERSION"
            )

            # POST_NOTIFICATIONS yalnızca Android 13+ için runtime izni.
            if BuildVersion.SDK_INT < 33:
                return

            request_permissions(
                [Permission.POST_NOTIFICATIONS]
            )

        except Exception as error:
            print(
                "[NOTIFICATION PERMISSION ERROR]",
                error,
            )

    def show_timer_notification(
        self,
        end_timestamp: float,
        mode: str = "focus",
    ) -> None:
        if platform != "android":
            return

        if not end_timestamp or end_timestamp <= 0:
            return

        try:
            from jnius import autoclass, cast

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            Context = autoclass(
                "android.content.Context"
            )
            BuildVersion = autoclass(
                "android.os.Build$VERSION"
            )
            Notification = autoclass(
                "android.app.Notification"
            )
            NotificationManager = autoclass(
                "android.app.NotificationManager"
            )
            NotificationChannel = autoclass(
                "android.app.NotificationChannel"
            )
            NotificationBuilder = autoclass(
                "android.app.Notification$Builder"
            )
            PendingIntent = autoclass(
                "android.app.PendingIntent"
            )
            Intent = autoclass(
                "android.content.Intent"
            )

            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()

            notification_manager = cast(
                "android.app.NotificationManager",
                context.getSystemService(
                    Context.NOTIFICATION_SERVICE
                ),
            )

            channel_id = "nagomi_timer"

            # Android 8+
            if BuildVersion.SDK_INT >= 26:
                channel = NotificationChannel(
                    channel_id,
                    "Timer",
                    NotificationManager.IMPORTANCE_LOW,
                )

                channel.setDescription(
                    "Nagomi active timer"
                )

                notification_manager.createNotificationChannel(
                    channel
                )

            # Notification'a dokununca Nagomi açılsın.
            open_intent = Intent(
                context,
                PythonActivity,
            )

            open_intent.addFlags(
                Intent.FLAG_ACTIVITY_SINGLE_TOP
                | Intent.FLAG_ACTIVITY_CLEAR_TOP
            )

            flag_update_current = getattr(
                PendingIntent,
                "FLAG_UPDATE_CURRENT",
                0,
            )

            flag_immutable = getattr(
                PendingIntent,
                "FLAG_IMMUTABLE",
                0,
            )

            content_intent = PendingIntent.getActivity(
                context,
                4300,
                open_intent,
                flag_update_current | flag_immutable,
            )

            if BuildVersion.SDK_INT >= 26:
                builder = NotificationBuilder(
                    context,
                    channel_id,
                )
            else:
                builder = NotificationBuilder(
                    context
                )

            if mode in (
                "short_break",
                "long_break",
                "break",
            ):
                content_text = "Break"
            else:
                content_text = "Focus"

            builder.setContentTitle(
                "Nagomi"
            )

            builder.setContentText(
                content_text
            )

            # p4a'nın oluşturduğu uygulama ikonunu kullan.
            icon_id = context.getApplicationInfo().icon

            builder.setSmallIcon(
                icon_id
            )

            builder.setContentIntent(
                content_intent
            )

            builder.setOngoing(
                True
            )

            builder.setOnlyAlertOnce(
                True
            )

            builder.setVisibility(
                Notification.VISIBILITY_PUBLIC
            )

            # Notification.when milisaniye cinsinden wall-clock timestamp.
            builder.setWhen(
                int(end_timestamp * 1000)
            )

            builder.setUsesChronometer(
                True
            )

            # Countdown API 24+
            if BuildVersion.SDK_INT >= 24:
                builder.setChronometerCountDown(
                    True
                )

            notification_manager.notify(
                5001,
                builder.build(),
            )

            print(
                "[TIMER NOTIFICATION SHOWN]",
                mode,
                end_timestamp,
            )

        except Exception as error:
            print(
                "[TIMER NOTIFICATION ERROR]",
                error,
            )


    def cancel_timer_notification(self) -> None:
        if platform != "android":
            return

        try:
            from jnius import autoclass, cast

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            Context = autoclass(
                "android.content.Context"
            )

            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()

            notification_manager = cast(
                "android.app.NotificationManager",
                context.getSystemService(
                    Context.NOTIFICATION_SERVICE
                ),
            )

            notification_manager.cancel(
                5001
            )

            print(
                "[TIMER NOTIFICATION CANCELLED]"
            )

        except Exception as error:
            print(
                "[TIMER NOTIFICATION CANCEL ERROR]",
                error,
            )

    def can_schedule_exact_alarms(self) -> bool:
        if platform != "android":
            return True

        try:
            from jnius import autoclass, cast

            BuildVersion = autoclass(
                "android.os.Build$VERSION"
            )

            # canScheduleExactAlarms API 31'de geldi.
            if BuildVersion.SDK_INT < 31:
                return True

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            Context = autoclass(
                "android.content.Context"
            )

            activity = PythonActivity.mActivity

            alarm_manager = cast(
                "android.app.AlarmManager",
                activity.getSystemService(
                    Context.ALARM_SERVICE
                ),
            )

            return bool(
                alarm_manager.canScheduleExactAlarms()
            )

        except Exception as error:
            print(
                "[EXACT ALARM PERMISSION CHECK ERROR]",
                error,
            )
            return False


    def request_exact_alarm_permission(self) -> bool:
        """
        True dönerse exact alarm zaten kullanılabilir.
        False dönerse kullanıcı izin ekranına gönderilmiştir
        veya izin alınamamıştır.
        """

        if platform != "android":
            return True

        if self.can_schedule_exact_alarms():
            return True

        try:
            from jnius import autoclass

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            BuildVersion = autoclass(
                "android.os.Build$VERSION"
            )

            if BuildVersion.SDK_INT < 31:
                return True

            Intent = autoclass(
                "android.content.Intent"
            )
            Settings = autoclass(
                "android.provider.Settings"
            )
            Uri = autoclass(
                "android.net.Uri"
            )

            activity = PythonActivity.mActivity

            intent = Intent(
                Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM
            )

            intent.setData(
                Uri.parse(
                    "package:"
                    + activity.getPackageName()
                )
            )

            activity.startActivity(intent)

            print(
                "[EXACT ALARM PERMISSION] "
                "Alarms & reminders ekranı açıldı."
            )

        except Exception as error:
            print(
                "[EXACT ALARM PERMISSION REQUEST ERROR]",
                error,
            )

        return False

    def schedule_focus_alarm(
        self,
        end_timestamp: float,
        mode: str = "focus",
        service_data: dict | None = None,
    ) -> None:
        if platform != "android":
            return

        if not end_timestamp or end_timestamp <= 0:
            return

        if not self.can_schedule_exact_alarms():
            print(
                "[ALARM SCHEDULE SKIPPED] "
                "Exact alarm permission yok."
            )
            return

        try:
            from jnius import autoclass, cast

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            Context = autoclass(
                "android.content.Context"
            )
            PendingIntent = autoclass(
                "android.app.PendingIntent"
            )
            AlarmManager = autoclass(
                "android.app.AlarmManager"
            )
            SystemClock = autoclass(
                "android.os.SystemClock"
            )
            BuildVersion = autoclass(
                "android.os.Build$VERSION"
            )

            # buildozer.spec:
            # services = nagomialarm:services/alarm_service.py:...
            #
            # p4a bunun için bu Java sınıfını üretir.
            AlarmService = autoclass(
                "com.sklabs.nagomi.ServiceNagomialarm"
            )

            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()

            settings = self.app_data.setdefault(
                "settings",
                {},
            )

            payload = {
                "alarm_sound": str(
                    settings.get(
                        "alarm_sound",
                        "beep",
                    )
                ),
                "sound_enabled": bool(
                    settings.get(
                        "sound_enabled",
                        True,
                    )
                ),
                "vibration_enabled": bool(
                    settings.get(
                        "vibration_enabled",
                        True,
                    )
                ),
                "mode": str(mode),
                "scheduled_end_timestamp": float(
                    end_timestamp
                ),
            }

            if service_data:
                payload.update(service_data)

            service_argument = json.dumps(
                payload
            )

            service_intent = AlarmService.getDefaultIntent(
                context,
                "icon",
                "Nagomi",
                "Timer completed",
                service_argument,
            )

            flag_update_current = getattr(
                PendingIntent,
                "FLAG_UPDATE_CURRENT",
                0,
            )

            flag_immutable = getattr(
                PendingIntent,
                "FLAG_IMMUTABLE",
                0,
            )

            pending_flags = (
                flag_update_current
                | flag_immutable
            )

            # getForegroundService API 26'dan itibaren mevcut.
            if BuildVersion.SDK_INT >= 26:
                pending_intent = (
                    PendingIntent.getForegroundService(
                        context,
                        4200,
                        service_intent,
                        pending_flags,
                    )
                )
            else:
                pending_intent = (
                    PendingIntent.getService(
                        context,
                        4200,
                        service_intent,
                        pending_flags,
                    )
                )

            alarm_manager = cast(
                "android.app.AlarmManager",
                activity.getSystemService(
                    Context.ALARM_SERVICE
                ),
            )

            now_wall = time.time()
            now_elapsed = SystemClock.elapsedRealtime()

            trigger_at_elapsed = int(
                now_elapsed
                + max(
                    0.0,
                    end_timestamp - now_wall,
                )
                * 1000
            )

            alarm_manager.setExactAndAllowWhileIdle(
                AlarmManager.ELAPSED_REALTIME_WAKEUP,
                trigger_at_elapsed,
                pending_intent,
            )

            print(
                "[ALARM SCHEDULED]",
                mode,
                end_timestamp,
            )

        except Exception as error:
            print(
                "[ALARM SCHEDULE ERROR]",
                error,
            )

    def cancel_focus_alarm(self) -> None:
        if platform != "android":
            return

        try:
            from jnius import autoclass, cast

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            Context = autoclass(
                "android.content.Context"
            )
            PendingIntent = autoclass(
                "android.app.PendingIntent"
            )
            AlarmManager = autoclass(
                "android.app.AlarmManager"
            )
            BuildVersion = autoclass(
                "android.os.Build$VERSION"
            )

            AlarmService = autoclass(
                "com.sklabs.nagomi.ServiceNagomialarm"
            )

            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()

            # PendingIntent kimliğinde extras dikkate alınmadığı için
            # aynı Service component'i yeterli.
            service_intent = AlarmService.getDefaultIntent(
                context,
                "icon",
                "Nagomi",
                "Timer completed",
                "",
            )

            flag_no_create = getattr(
                PendingIntent,
                "FLAG_NO_CREATE",
                0,
            )

            flag_immutable = getattr(
                PendingIntent,
                "FLAG_IMMUTABLE",
                0,
            )

            pending_flags = (
                flag_no_create
                | flag_immutable
            )

            if BuildVersion.SDK_INT >= 26:
                pending_intent = (
                    PendingIntent.getForegroundService(
                        context,
                        4200,
                        service_intent,
                        pending_flags,
                    )
                )
            else:
                pending_intent = (
                    PendingIntent.getService(
                        context,
                        4200,
                        service_intent,
                        pending_flags,
                    )
                )

            if pending_intent is None:
                return

            alarm_manager = cast(
                "android.app.AlarmManager",
                activity.getSystemService(
                    Context.ALARM_SERVICE
                ),
            )

            alarm_manager.cancel(
                pending_intent
            )

            pending_intent.cancel()

            print("[ALARM CANCELLED]")

        except Exception as error:
            print(
                "[ALARM CANCEL ERROR]",
                error,
            )

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

    def stop_android_alarm_service(self) -> None:
        if platform != "android":
            return

        try:
            from jnius import autoclass

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            AlarmService = autoclass(
                "com.sklabs.nagomi.ServiceNagomialarm"
            )

            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()

            service_intent = AlarmService.getDefaultIntent(
                context,
                "icon",
                "Nagomi",
                "Timer completed",
                "",
            )

            context.stopService(service_intent)

            print("[ALARM SERVICE STOPPED]")

        except Exception as error:
            print(
                "[ALARM SERVICE STOP ERROR]",
                error,
            )


if __name__ == "__main__":
    NagomiApp().run()
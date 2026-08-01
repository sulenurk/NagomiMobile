from __future__ import annotations

from typing import Any

from kivy.properties import (
    BooleanProperty,
    StringProperty,
)
from kivymd.uix.screen import MDScreen


class SettingsScreen(MDScreen):
    auto_start_focus = BooleanProperty(False)
    auto_start_break = BooleanProperty(False)
    sound_enabled = BooleanProperty(True)

    show_queue_progress = BooleanProperty(True)
    show_cumulative_away_time = BooleanProperty(True)

    daily_goal_text = StringProperty("300")

    week_start_text = StringProperty("Pazartesi")
    status_text = StringProperty("")

    _is_loading = False

    @property
    def app(self):
        from kivy.app import App
        return App.get_running_app()

    def on_kv_post(self, base_widget) -> None:
        self.load_settings()

    def on_pre_enter(self, *args) -> None:
        self.load_settings()
        return super().on_pre_enter(*args)

    # ---------------------------------------------------------
    # VERİ YÜKLEME
    # ---------------------------------------------------------

    def get_settings(self) -> dict[str, Any]:
        return self.app.app_data.setdefault("settings", {})

    def load_settings(self) -> None:
        self._is_loading = True

        try:
            settings = self.get_settings()

            self.auto_start_focus = bool(
                settings.get("auto_start_focus", False)
            )

            self.auto_start_break = bool(
                settings.get("auto_start_break", False)
            )

            self.sound_enabled = bool(
                settings.get("sound_enabled", True)
            )

            self.show_queue_progress = bool(
                settings.get("show_queue_progress", True)
            )

            self.show_cumulative_away_time = bool(
                settings.get(
                    "show_cumulative_away_time",
                    True,
                )
            )

            self.daily_goal_text = str(
                settings.get(
                    "daily_focus_goal_minutes",
                    300,
                )
            )

            week_start_day = settings.get(
                "week_start_day",
                "monday",
            )

            self.week_start_text = (
                self.app.t("sunday")
                if week_start_day == "sunday"
                else self.app.t("monday")
            )

            self.status_text = ""

        finally:
            self._is_loading = False

    # ---------------------------------------------------------
    # SWITCH AYARLARI
    # ---------------------------------------------------------

    def set_auto_start_focus(self, enabled: bool) -> None:
        if self._is_loading:
            return

        self.auto_start_focus = bool(enabled)
        self.get_settings()["auto_start_focus"] = bool(enabled)
        self._save_without_message()

    def set_auto_start_break(self, enabled: bool) -> None:
        if self._is_loading:
            return

        self.auto_start_break = bool(enabled)
        self.get_settings()["auto_start_break"] = bool(enabled)
        self._save_without_message()

    def set_sound_enabled(self, enabled: bool) -> None:
        if self._is_loading:
            return

        self.sound_enabled = bool(enabled)
        self.get_settings()["sound_enabled"] = bool(enabled)

        if not enabled:
            self.app.stop_alarm()

        self._save_without_message()

    def set_show_queue_progress(self, enabled: bool) -> None:
        if self._is_loading:
            return

        self.show_queue_progress = bool(enabled)

        self.get_settings()["show_queue_progress"] = bool(
            enabled
        )

        self._save_without_message()

    def set_show_cumulative_away_time(
        self,
        enabled: bool,
    ) -> None:
        if self._is_loading:
            return

        self.show_cumulative_away_time = bool(enabled)

        self.get_settings()[
            "show_cumulative_away_time"
        ] = bool(enabled)

        self._save_without_message()

    # ---------------------------------------------------------
    # METİN ALANLARI
    # ---------------------------------------------------------

    def save_numeric_settings(self) -> None:
        settings = self.get_settings()

        try:

            daily_goal = self._read_positive_int(
                self.ids.daily_goal.text,
                self.app.t("daily_goal"),
            )

        except ValueError as error:
            self.status_text = str(error)
            return

        settings["daily_focus_goal_minutes"] = daily_goal

        self.app.save_app_data()
        self.status_text = self.app.t("settings_saved")

    def change_week_start(self, selected_value: str) -> None:
        self.week_start_text = selected_value

        self.get_settings()["week_start_day"] = (
            self.app.t("sunday")
            if selected_value == "Pazar"
            else self.app.t("monday")
        )

        self._save_without_message()

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------

    def reset_settings(self) -> None:
        settings = self.get_settings()

        settings.update(
            {
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
        )

        self.app.save_app_data()
        self.load_settings()
        self._refresh_timer_screens()

        self.status_text = self.app.t("settings_reset")

    # ---------------------------------------------------------
    # YARDIMCI METOTLAR
    # ---------------------------------------------------------

    def _save_without_message(self) -> None:
        self.app.save_app_data()
        self._refresh_timer_screens()

    def _refresh_timer_screens(self) -> None:
        if not self.app.root:
            return

        screen_manager = self.app.root.ids.get(
            "screen_manager"
        )

        if not screen_manager:
            return

        try:
            pomodoro_screen = screen_manager.get_screen(
                "pomodoro"
            )

            if hasattr(pomodoro_screen, "load_timer"):
                pomodoro_screen.load_timer()

            if hasattr(pomodoro_screen, "refresh_ui"):
                pomodoro_screen.refresh_ui()

        except Exception:
            pass

        try:
            focus_screen = screen_manager.get_screen(
                "focus"
            )

            if hasattr(focus_screen, "refresh_ui"):
                focus_screen.refresh_ui()

        except Exception:
            pass

    @staticmethod
    def _read_positive_int(
        value: str,
        field_name: str,
    ) -> int:
        try:
            parsed_value = int(value.strip())
        except (TypeError, ValueError):
            raise ValueError(
                f"{field_name} sayı olmalıdır."
            )

        if parsed_value <= 0:
            raise ValueError(
                f"{field_name} sıfırdan büyük olmalıdır."
            )

        return parsed_value

    @staticmethod
    def _read_non_negative_int(
        self,
        value: str,
        field_name: str,
    ) -> int:
        try:
            parsed_value = int(value.strip())
        except (TypeError, ValueError):
            raise ValueError(
                self.app.t("field_must_be_number").format(
                field=field_name
            )
            )

        if parsed_value < 0:
            raise ValueError(
                self.app.t(
                "field_must_be_greater_than_zero"
            ).format(
                field=field_name
            )
            )

        return parsed_value
from __future__ import annotations

from datetime import datetime
import uuid

from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    StringProperty,
)
from kivy.uix.widget import Widget
from kivymd.uix.screen import MDScreen

from core.pomodoro_timer import PomodoroSettings, PomodoroTimer


class CircularProgress(Widget):
    progress = NumericProperty(0.0)
    track_color = ListProperty([0.15, 0.18, 0.27, 1])
    progress_color = ListProperty([0.65, 0.55, 0.98, 1])
    line_width = NumericProperty(12)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas:
            self._track_color_instruction = Color(rgba=self.track_color)
            self._track = Line(circle=(0, 0, 0), width=self.line_width)

            self._progress_color_instruction = Color(rgba=self.progress_color)
            self._progress_line = Line(
                circle=(0, 0, 0, 90, 90),
                width=self.line_width,
            )

        self.bind(
            pos=self._update_canvas,
            size=self._update_canvas,
            progress=self._update_canvas,
            track_color=self._update_colors,
            progress_color=self._update_colors,
            line_width=self._update_canvas,
        )

    def _update_colors(self, *_):
        self._track_color_instruction.rgba = self.track_color
        self._progress_color_instruction.rgba = self.progress_color

    def _update_canvas(self, *_):
        diameter = max(0, min(self.width, self.height) - self.line_width * 2)
        radius = diameter / 2
        center_x, center_y = self.center

        self._track.circle = (center_x, center_y, radius)
        self._track.width = self.line_width

        end_angle = 90 - 360 * max(0.0, min(1.0, self.progress))
        self._progress_line.circle = (
            center_x,
            center_y,
            radius,
            end_angle,
            90,
        )
        self._progress_line.width = self.line_width


class PomodoroScreen(MDScreen):
    timer_text = StringProperty("25:00")
    mode_text = StringProperty("Odak")
    cycle_text = StringProperty("#1 / 4")
    status_text = StringProperty("")
    primary_action_icon = StringProperty("play")

    is_running = BooleanProperty(False)
    settings_panel_open = BooleanProperty(False)

    progress = NumericProperty(0.0)
    mode_color = ListProperty([0.65, 0.55, 0.98, 1])

    settings_focus_minutes = StringProperty("25")
    settings_short_break_minutes = StringProperty("5")
    settings_long_break_minutes = StringProperty("15")
    settings_long_break_after = StringProperty("4")
    settings_focus_count = StringProperty("4")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timer: PomodoroTimer | None = None
        self._clock_event = None

    @property
    def app(self):
        from kivy.app import App
        return App.get_running_app()

    def on_kv_post(self, base_widget):
        self.load_timer()
        self.refresh_ui()

    def on_enter(self, *args):
        self.load_timer_state()

        if self._clock_event is None:
            self._clock_event = Clock.schedule_interval(
                self._tick,
                1,
            )

        self._tick(0)
        self.refresh_ui()

        return super().on_enter(*args)

    def on_leave(self, *args):
        self.save_timer_state()
        self._cancel_clock_event()

        return super().on_leave(*args)

    def _cancel_clock_event(self) -> None:
        if self._clock_event is not None:
            self._clock_event.cancel()
            self._clock_event = None

    def handle_app_pause(self) -> None:
        """
        Android uygulamayı arka plana aldığında çağrılır.

        Timer durdurulmaz. Yalnızca mevcut durumu kaydeder ve
        görünmeyen arayüzün yenileme eventini kapatır.
        """
        if self.timer is None:
            return

        self.timer.sync()
        self.save_timer_state()
        self._cancel_clock_event()


    def handle_app_resume(self) -> None:
        """
        Uygulama yeniden görünür olduğunda gerçek saate göre
        Pomodoro durumunu günceller.
        """
        if self.timer is None:
            self.load_timer()

        self.load_timer_state()

        if self.timer is None:
            return

        session_finished = self.timer.sync()

        if session_finished:
            result = self.timer.finish_current_session()
            self._handle_finished_session(result)

        current_screen = None

        try:
            current_screen = (
                self.app.root.ids.screen_manager.current
            )
        except (AttributeError, KeyError):
            pass

        if current_screen == "pomodoro":
            if self._clock_event is None:
                self._clock_event = Clock.schedule_interval(
                    self._tick,
                    1,
                )

        self.refresh_ui()

    def load_timer(self):
        settings_data = self.app.app_data.setdefault("settings", {})

        settings = PomodoroSettings(
            focus_minutes=int(settings_data.get("regular_focus_minutes", 25)),
            short_break_minutes=int(
                settings_data.get("regular_short_break_minutes", 5)
            ),
            long_break_minutes=int(
                settings_data.get("regular_long_break_minutes", 15)
            ),
            long_break_after=int(
                settings_data.get("regular_long_break_after", 4)
            ),
            focus_count=int(settings_data.get("regular_focus_count", 4)),
            auto_start_break=bool(settings_data.get("auto_start_break", False)),
            auto_start_focus=bool(settings_data.get("auto_start_focus", False)),
        )

        if self.timer is None:
            self.timer = PomodoroTimer(settings)
        else:
            self.timer.update_settings(settings)

    def toggle_timer(self):
        if self.timer is None:
            return

        if self.timer.is_running:
            self.timer.pause()
            self.status_text = self.app.t("paused")
        else:
            self.app.stop_alarm()
            self.timer.start()
            self.status_text = ""

        self.save_timer_state()
        self.refresh_ui()

    def reset_timer(self):
        if self.timer is None:
            return

        self.app.stop_alarm()
        self.timer.reset()
        self.status_text = ""
        self.save_timer_state()
        self.refresh_ui()

    def skip_session(self):
        if self.timer is None:
            return

        self.app.stop_alarm()
        self.timer.skip()
        self.status_text = self._ready_message()
        self.save_timer_state()
        self.refresh_ui()

    def open_settings(self) -> None:
        self.load_settings_form()
        self.settings_panel_open = True


    def close_settings(self) -> None:
        self.settings_panel_open = False
        self.status_text = ""

    def load_settings_form(self) -> None:
        settings = self.app.app_data.setdefault("settings", {})

        self.settings_focus_minutes = str(
            settings.get("regular_focus_minutes", 25)
        )

        self.settings_short_break_minutes = str(
            settings.get("regular_short_break_minutes", 5)
        )

        self.settings_long_break_minutes = str(
            settings.get("regular_long_break_minutes", 15)
        )

        self.settings_long_break_after = str(
            settings.get("regular_long_break_after", 4)
        )

        self.settings_focus_count = str(
            settings.get("regular_focus_count", 4)
        )

    def save_pomodoro_settings(self) -> None:
        if self.timer and self.timer.is_running:
            self.status_text = (
                "Ayarları değiştirmek için önce sayacı duraklat."
            )
            return

        try:
            focus_minutes = self._read_positive_int(
                self.ids.settings_focus_minutes.text,
                "Odak süresi",
            )

            short_break_minutes = self._read_non_negative_int(
                self.ids.settings_short_break_minutes.text,
                "Kısa mola",
            )

            long_break_minutes = self._read_non_negative_int(
                self.ids.settings_long_break_minutes.text,
                "Uzun mola",
            )

            long_break_after = self._read_positive_int(
                self.ids.settings_long_break_after.text,
                "Uzun mola aralığı",
            )

            focus_count = self._read_non_negative_int(
                self.ids.settings_focus_count.text,
                "Döngü sayısı",
            )

        except ValueError as error:
            self.status_text = str(error)
            return

        settings = self.app.app_data.setdefault("settings", {})

        settings["regular_focus_minutes"] = focus_minutes
        settings[
            "regular_short_break_minutes"
        ] = short_break_minutes

        settings[
            "regular_long_break_minutes"
        ] = long_break_minutes

        settings[
            "regular_long_break_after"
        ] = long_break_after

        settings["regular_focus_count"] = focus_count

        self.app.save_app_data()

        # Yeni ayarları timer nesnesine aktar.
        self.load_timer()

        # Çalışmayan sayaç yeni başlangıç süresine döner.
        if self.timer:
            self.timer.reset()

        self.save_timer_state()
        self.refresh_ui()

        self.status_text = "Pomodoro ayarları kaydedildi."
        self.settings_panel_open = False

    def _tick(self, _dt):
        if self.timer is None:
            return

        session_finished = self.timer.sync()

        if session_finished:
            result = self.timer.finish_current_session()
            self._handle_finished_session(result)

        self.refresh_ui()

    def _handle_finished_session(self, result: dict[str, object]):
        self.app.play_alarm("pomodoro")

        if bool(result.get("focus_completed")):
            self.log_regular_focus_session()

        if bool(result.get("cycle_completed")):
            self.status_text = self.app.t("pomodoro_cycle_completed")
        else:
            self.status_text = self._ready_message()

        if bool(result.get("should_auto_start")):
            self.timer.start()

        self.app.save_app_data()
        self.save_timer_state()

    def _ready_message(self) -> str:
        if self.timer and self.timer.mode == "focus":
            return self.app.t("focus_ready")
        return self.app.t("break_ready")

    def refresh_ui(self):
        if self.timer is None:
            return

        minutes, seconds = divmod(self.timer.remaining_seconds, 60)
        self.timer_text = f"{minutes:02d}:{seconds:02d}"
        self.progress = self.timer.progress
        self.is_running = self.timer.is_running
        self.primary_action_icon = "pause" if self.timer.is_running else "play"

        mode_map = {
            "focus": (
                self.app.t("focus_mode"),
                [0.65, 0.55, 0.98, 1],
            ),
            "short_break": (
                self.app.t("short_break_mode"),
                [0.13, 0.77, 0.37, 1],
            ),
            "long_break": (
                self.app.t("long_break_mode"),
                [0.23, 0.51, 0.96, 1],
            ),
        }
        self.mode_text, self.mode_color = mode_map[self.timer.mode]

        total = self.timer.settings.focus_count
        total_text = "∞" if total == 0 else str(total)
        current = self.timer.completed_focus_count + 1

        if total > 0:
            current = min(current, total)

        self.cycle_text = f"#{current} / {total_text}"

    def save_timer_state(self):
        if self.timer is None:
            return

        self.app.app_data["regular_pomodoro_state"] = self.timer.export_state()
        self.app.save_app_data()

    def load_timer_state(self):
        if self.timer is None:
            self.load_timer()

        state = self.app.app_data.get(
            "regular_pomodoro_state"
        )

        if isinstance(state, dict):
            self.timer.restore_state(state)

        session_finished = self.timer.sync()

        if session_finished:
            result = self.timer.finish_current_session()
            self._handle_finished_session(result)

        self.refresh_ui()

    def log_regular_focus_session(self):
        session = {
            "id": f"session_{uuid.uuid4().hex[:8]}",
            "task_id": None,
            "task_title": "Regular Pomodoro",
            "subject_id": "subject_other",
            "subject_name": self.app.t("other_subject"),
            "mode": "focus",
            "source": "regular_pomodoro",
            "duration_seconds": self.timer.settings.focus_minutes * 60,
            "away_seconds": 0,
            "completed_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.app.app_data.setdefault("sessions", []).append(session)

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
        value: str,
        field_name: str,
    ) -> int:
        try:
            parsed_value = int(value.strip())
        except (TypeError, ValueError):
            raise ValueError(
                f"{field_name} sayı olmalıdır."
            )

        if parsed_value < 0:
            raise ValueError(
                f"{field_name} negatif olamaz."
            )

        return parsed_value
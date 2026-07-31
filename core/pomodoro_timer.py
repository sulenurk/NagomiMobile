from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

TimerMode = Literal["focus", "short_break", "long_break"]


@dataclass
class PomodoroSettings:
    focus_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    long_break_after: int = 4
    focus_count: int = 4
    auto_start_break: bool = False
    auto_start_focus: bool = False

    def validate(self) -> None:
        positive_values = (
            self.focus_minutes,
            self.short_break_minutes,
            self.long_break_minutes,
            self.long_break_after,
        )
        if any(value <= 0 for value in positive_values):
            raise ValueError("Süreler ve uzun mola aralığı sıfırdan büyük olmalıdır.")
        if self.focus_count < 0:
            raise ValueError("Odak sayısı negatif olamaz.")


class PomodoroTimer:
    """UI'dan bağımsız, timestamp tabanlı Pomodoro motoru."""

    def __init__(self, settings: PomodoroSettings) -> None:
        settings.validate()
        self.settings = settings

        self.mode: TimerMode = "focus"
        self.completed_focus_count = 0
        self.remaining_seconds = self._duration_for("focus")
        self.end_timestamp: float | None = None
        self.is_running = False
        self.is_paused = False
        self.cycle_completed = False

    def _duration_for(self, mode: TimerMode) -> int:
        if mode == "focus":
            return self.settings.focus_minutes * 60
        if mode == "short_break":
            return self.settings.short_break_minutes * 60
        return self.settings.long_break_minutes * 60

    @property
    def total_seconds(self) -> int:
        return self._duration_for(self.mode)

    @property
    def progress(self) -> float:
        total = self.total_seconds
        if total <= 0:
            return 0.0
        elapsed = total - self.remaining_seconds
        return max(0.0, min(1.0, elapsed / total))

    def start(self) -> None:
        if self.cycle_completed:
            self.reset()

        if self.is_running:
            return

        self.end_timestamp = time.time() + self.remaining_seconds
        self.is_running = True
        self.is_paused = False

    def pause(self) -> None:
        if not self.is_running:
            return

        self.sync()
        self.end_timestamp = None
        self.is_running = False
        self.is_paused = True

    def reset(self) -> None:
        self.mode = "focus"
        self.completed_focus_count = 0
        self.remaining_seconds = self._duration_for("focus")
        self.end_timestamp = None
        self.is_running = False
        self.is_paused = False
        self.cycle_completed = False

    def skip(self) -> None:
        self.end_timestamp = None
        self.is_running = False
        self.is_paused = False
        self.cycle_completed = False
        self._advance_mode()

    def sync(self) -> bool:
        """Kalan süreyi gerçek saate göre günceller. Bittiyse True döndürür."""
        if not self.is_running or self.end_timestamp is None:
            return False

        self.remaining_seconds = max(0, int(round(self.end_timestamp - time.time())))

        if self.remaining_seconds > 0:
            return False

        self.end_timestamp = None
        self.is_running = False
        self.is_paused = False
        return True

    def finish_current_session(self) -> dict[str, object]:
        """Biten oturumu işler ve yeni moda geçer."""
        finished_mode = self.mode
        focus_completed = finished_mode == "focus"

        if focus_completed:
            self.completed_focus_count += 1

            if (
                self.settings.focus_count > 0
                and self.completed_focus_count >= self.settings.focus_count
            ):
                self.cycle_completed = True
                self.remaining_seconds = 0
                return {
                    "finished_mode": finished_mode,
                    "focus_completed": True,
                    "cycle_completed": True,
                    "should_auto_start": False,
                }

        self._advance_mode()

        should_auto_start = (
            self.settings.auto_start_break
            if self.mode in ("short_break", "long_break")
            else self.settings.auto_start_focus
        )

        return {
            "finished_mode": finished_mode,
            "focus_completed": focus_completed,
            "cycle_completed": False,
            "should_auto_start": should_auto_start,
        }

    def _advance_mode(self) -> None:
        if self.mode == "focus":
            long_break_due = (
                self.completed_focus_count > 0
                and self.completed_focus_count % self.settings.long_break_after == 0
            )
            self.mode = "long_break" if long_break_due else "short_break"
        else:
            self.mode = "focus"

        self.remaining_seconds = self._duration_for(self.mode)

    def update_settings(self, settings: PomodoroSettings) -> None:
        settings.validate()
        self.settings = settings

        if not self.is_running and not self.is_paused:
            self.reset()

    def export_state(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "completed_focus_count": self.completed_focus_count,
            "remaining_seconds": self.remaining_seconds,
            "end_timestamp": self.end_timestamp,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "cycle_completed": self.cycle_completed,
        }

    def restore_state(self, state: dict[str, object]) -> None:
        mode = state.get("mode", "focus")
        if mode not in ("focus", "short_break", "long_break"):
            mode = "focus"

        self.mode = mode
        self.completed_focus_count = max(
            0, int(state.get("completed_focus_count", 0))
        )
        self.remaining_seconds = max(
            0, int(state.get("remaining_seconds", self._duration_for(self.mode)))
        )
        self.end_timestamp = state.get("end_timestamp")
        self.is_running = bool(state.get("is_running", False))
        self.is_paused = bool(state.get("is_paused", False))
        self.cycle_completed = bool(state.get("cycle_completed", False))

        if self.is_running:
            self.sync()

from __future__ import annotations
from kivy.app import App
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from kivy.clock import Clock
from kivy.properties import (
    BooleanProperty,
    NumericProperty,
    StringProperty,
)
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen


class FocusScreen(MDScreen):
    primary_action_icon = StringProperty("play")

    timer_text = StringProperty("00:00")
    away_time_text = StringProperty("00:00")
    status_text = StringProperty("")
    active_task_name = StringProperty("")

    current_mode = StringProperty("focus")

    focus_seconds = NumericProperty(25 * 60)
    break_seconds = NumericProperty(5 * 60)
    remaining_seconds = NumericProperty(25 * 60)

    away_seconds = NumericProperty(0)
    timer_end_timestamp = NumericProperty(0)
    pause_started_timestamp = NumericProperty(0)

    is_running = BooleanProperty(False)
    is_paused = BooleanProperty(False)
    is_waiting_for_next = BooleanProperty(False)

    settings_panel_open = BooleanProperty(False)

    setting_auto_start_focus = BooleanProperty(False)
    setting_auto_start_break = BooleanProperty(False)
    setting_show_away_time = BooleanProperty(False)

    session_started_at: Optional[str] = None

    _timer_event = None
    _is_restoring = False

    def on_kv_post(self, base_widget) -> None:
        self.load_focus_settings()
        self.refresh_ui()

    def on_pre_enter(self, *args) -> None:
        self.load_focus_settings()
        self.refresh_ui()
        return super().on_pre_enter(*args)

    # ---------------------------------------------------------
    # SAYFA YENİLEME
    # ---------------------------------------------------------

    def refresh_ui(self) -> None:
        """
        Focus ekranı her açıldığında çağrılır.

        Önce kayıtlı timer durumu geri yüklenir. Kayıtlı çalışan
        bir sayaç yoksa Study Plan'deki aktif görev yüklenir.
        """
        restored = self.restore_timer_state()

        if not restored:
            self.load_active_task()

        self._update_display()

    def refresh_theme(self) -> None:
        from kivy.app import App

        panel = self.ids.get("focus_settings_panel")

        if panel is None:
            return

        app = App.get_running_app()

        panel.md_bg_color = list(
            app.theme_colors["sidebar"]
        )

        panel.canvas.ask_update()

    def load_active_task(self) -> None:
        """
        Study Plan ekranında aktif hale getirilen görevi bulur ve
        o görevin odak/mola sürelerini geri sayıma yükler.
        """
        app = MDApp.get_running_app()
        task = self.get_active_task()

        if not task:
            self.active_task_name = app.t("no_active_task")

            self.focus_seconds = 0
            self.break_seconds = 0
            self.remaining_seconds = 0

            self.current_mode = "focus"
            self.is_running = False
            self.is_paused = False
            self.is_waiting_for_next = False

            self.primary_action_icon = "play"
            self.status_text = app.t("focus_ready")

            self._cancel_timer_event()
            self.clear_timer_state()
            self._update_display()
            return

        title = self._safe_text(
            task.get("task_name")
            or task.get("title"),
            app.t("no_active_task"),
        )

        subject_name = self._safe_text(
            task.get("subject_name")
            or task.get("subject"),
            "",
        )

        if subject_name:
            self.active_task_name = f"{subject_name} · {title}"
        else:
            self.active_task_name = title

        focus_duration = self._safe_positive_int(
            task.get("focus_duration", 25),
            default=25,
        )

        break_minutes = self._safe_positive_int(
            task.get("break_minutes", 5),
            default=5,
        )

        self.focus_seconds = focus_duration * 60
        self.break_seconds = break_minutes * 60

        if not self.is_running and not self.is_paused:
            self.current_mode = "focus"
            self.remaining_seconds = self.focus_seconds
            self.is_waiting_for_next = False

            self.primary_action_icon = "play"
            self.status_text = app.t("focus_ready")

        self._update_display()

    # ---------------------------------------------------------
    # TIMER KONTROLLERİ
    # ---------------------------------------------------------

    def toggle_timer(self) -> None:
        self.app.stop_alarm()

        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_or_pause(self) -> None:
        self.toggle_timer()

    def start_timer(self, manual_start: bool = True) -> None:
        app = MDApp.get_running_app()
        task = self.get_active_task()

        if not task:
            self.status_text = app.t("no_active_task")
            return

        if self.is_running:
            return

        app.pause_other_timer(
            "focus"
        )

        # Exact-alarm izni yalnızca uygulama arka plandayken alarmın
        # zamanında çalması için gerekli - önyüzdeki geri sayımı
        # etkilemez. Bu yüzden izin isteme çağrısı burada sayaç
        # başlatmayı ENGELLEMEZ (fire-and-forget); izin verilmezse
        # yalnızca arka plan alarmı atlanır, sayaç normal çalışmaya
        # devam eder.
        request_permission = getattr(
            app,
            "request_exact_alarm_permission",
            None,
        )

        if callable(request_permission):
            request_permission()

        if self.remaining_seconds <= 0:
            self._prepare_current_mode_duration()

        if self.remaining_seconds <= 0:
            return

        # Pause durumundan devam ediliyorsa uzakta geçirilen süreyi ekle.
        if self.is_paused and self.pause_started_timestamp > 0:
            paused_duration = max(
                0,
                int(time.time() - self.pause_started_timestamp),
            )

            self.away_seconds += paused_duration
            self.pause_started_timestamp = 0

        if self.current_mode == "focus" and not self.session_started_at:
            self.session_started_at = datetime.now().isoformat(
                timespec="seconds"
            )

        self.timer_end_timestamp = (
            time.time() + int(self.remaining_seconds)
        )

        self.is_running = True
        self.is_paused = False
        self.is_waiting_for_next = False

        self.primary_action_icon = "pause"
        self.status_text = self._get_mode_status_text()

        self.save_timer_state()
        self._start_timer_event()

        self._update_display()

    def pause_timer(self) -> None:
        app = MDApp.get_running_app()

        if not self.is_running:
            return

        self._sync_remaining_seconds()

        self.is_running = False
        self.is_paused = True

        self.timer_end_timestamp = 0
        self.pause_started_timestamp = time.time()

        self.primary_action_icon = "play"
        self.status_text = app.t("paused")

        self._cancel_timer_event()
        self._cancel_android_alarm()

        self.save_timer_state()
        self._update_display()

    def reset_timer(self) -> None:
        self.app.stop_alarm()
        app = MDApp.get_running_app()

        self._cancel_timer_event()
        self._cancel_android_alarm()

        self.is_running = False
        self.is_paused = False
        self.is_waiting_for_next = False

        self.current_mode = "focus"

        self.timer_end_timestamp = 0
        self.pause_started_timestamp = 0
        self.away_seconds = 0
        self.session_started_at = None

        task = self.get_active_task()

        if task:
            self.focus_seconds = self._safe_positive_int(
                task.get("focus_duration", 25),
                default=25,
            ) * 60

            self.break_seconds = self._safe_positive_int(
                task.get("break_minutes", 5),
                default=5,
            ) * 60

            self.remaining_seconds = self.focus_seconds
            self.status_text = app.t("focus_ready")
        else:
            self.remaining_seconds = 0
            self.status_text = app.t("no_active_task")

        self.primary_action_icon = "play"

        self.clear_timer_state()
        self._update_display()

    def finish_session(self) -> None:
        """
        Kullanıcı stop butonuna bastığında mevcut oturumu erken bitirir.
        Görev tamamlanmış sayılmaz.
        """
        if self.is_running:
            self._sync_remaining_seconds()

        elapsed_seconds = self._get_elapsed_seconds()

        if (
            self.current_mode == "focus"
            and elapsed_seconds > 0
            and self.get_active_task()
        ):
            self._save_focus_session(
                duration_seconds=elapsed_seconds,
                completed=False,
            )

        self.reset_timer()

    # ---------------------------------------------------------
    # GERİ SAYIM
    # ---------------------------------------------------------

    def _start_timer_event(self) -> None:
        if self._timer_event is None:
            self._timer_event = Clock.schedule_interval(
                self._tick,
                1,
            )

    def _tick(self, delta_time: float) -> None:
        if not self.is_running:
            return

        self._sync_remaining_seconds()
        self._update_display()

        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self._update_display()

            self.complete_current_mode(
                completed_automatically=True
            )

    def _sync_remaining_seconds(self) -> None:
        """
        Kalan süreyi bellekte azaltmak yerine gerçek bitiş zamanından
        hesaplar. Bu sayede ekran kapalıyken veya uygulama arka plandayken
        sayaç doğruluğunu korur.
        """
        if not self.is_running:
            return

        if self.timer_end_timestamp <= 0:
            return

        self.remaining_seconds = max(
            0,
            int(self.timer_end_timestamp - time.time()),
        )

    def complete_current_mode(
        self,
        completed_automatically: bool = False,
        allow_auto_start: bool = True,
    ) -> None:
        """
        Mevcut odak veya mola geri sayımı sıfıra ulaştığında çalışır.
        """
        if not self.is_running and not self._is_restoring:
            return

        self._cancel_timer_event()
        self._cancel_android_alarm()

        self.remaining_seconds = 0
        self.timer_end_timestamp = 0

        self.is_running = False
        self.is_paused = False
        self.primary_action_icon = "play"

        self._update_display()

        # Alarm yalnızca sayaç kendiliğinden sona erdiyse çalsın.
        if completed_automatically:
            if self.current_mode == "focus":
                self.app.play_alarm(
                    source="focus",
                    mode="focus",
                    title=self.app.t("focus_timer_completed"),
                    subtitle=self._get_active_task_name(),
                )

            else:
                self.app.play_alarm(
                    source="focus",
                    mode="break",
                    title=self.app.t("focus_break_finished"),
                    subtitle=self.app.t("ready_for_focus"),
                )

        if self.current_mode == "focus":
            self._complete_focus_mode(
                allow_auto_start=allow_auto_start
            )
        else:
            self._complete_break_mode(
                allow_auto_start=allow_auto_start
            )

    def _complete_focus_mode(
        self,
        allow_auto_start: bool = True,
    ) -> None:
        app = MDApp.get_running_app()
        task = self.get_active_task()

        if task:
            self._save_focus_session(
                duration_seconds=int(self.focus_seconds),
                completed=True,
            )

            self._mark_task_completed(task.get("id"))

        self.away_seconds = 0
        self.pause_started_timestamp = 0
        self.session_started_at = None

        self.current_mode = "break"
        self.remaining_seconds = self.break_seconds
        self.is_waiting_for_next = True

        self.status_text = app.t("break_ready")
        self.primary_action_icon = "play"

        self.save_timer_state()
        self._update_display()

        auto_start_break = app.app_data.get(
            "settings",
            {},
        ).get(
            "auto_start_break",
            False,
        )

        if auto_start_break and allow_auto_start:
            self.start_timer(manual_start=False)

    def _complete_break_mode(
        self,
        allow_auto_start: bool = True,
    ) -> None:
        app = MDApp.get_running_app()

        moved_to_next_task = self.move_to_next_queue_task()

        if moved_to_next_task:
            self.current_mode = "focus"
            self.is_waiting_for_next = True
            self.is_running = False
            self.is_paused = False

            self.timer_end_timestamp = 0
            self.pause_started_timestamp = 0
            self.away_seconds = 0
            self.session_started_at = None

            self.load_active_task()

            self.status_text = app.t("focus_ready")
            self.primary_action_icon = "play"

            self.save_timer_state()
            self._update_display()

            auto_start_focus = app.app_data.get(
                "settings",
                {},
            ).get(
                "auto_start_focus",
                False,
            )

            if auto_start_focus and allow_auto_start:
                self.start_timer(manual_start=False)

            return

        # Kuyrukta başka görev kalmadı.
        app.app_data["active_task_id"] = None
        app.app_data["queue_mode_active"] = False
        app.app_data["queue_task_ids"] = []
        app.app_data["last_queue_state"] = "completed"

        app.save_app_data()

        self.is_running = False
        self.is_paused = False
        self.is_waiting_for_next = False

        self.current_mode = "focus"
        self.remaining_seconds = 0

        self.active_task_name = app.t("no_active_task")
        self.status_text = app.t("session_completed")
        self.primary_action_icon = "play"

        self.clear_timer_state()
        self._update_display()

    # ---------------------------------------------------------
    # GÖREV VE KUYRUK
    # ---------------------------------------------------------

    def get_active_task(self) -> Optional[dict[str, Any]]:
        app = MDApp.get_running_app()
        active_task_id = app.app_data.get("active_task_id")

        if not active_task_id:
            return None

        for task in app.app_data.get("tasks", []):
            if task.get("id") == active_task_id:
                return task

        return None

    def _get_active_task_name(self) -> str:
        app = MDApp.get_running_app()
        task = self.get_active_task()

        if not task:
            return str(app.t("no_active_task"))

        title = self._safe_text(
            task.get("task_name")
            or task.get("title"),
            app.t("no_active_task"),
        )

        subject_name = self._safe_text(
            task.get("subject_name")
            or task.get("subject"),
            "",
        )

        if subject_name:
            return f"{subject_name} · {title}"

        return title

    def _mark_task_completed(self, task_id: Optional[str]) -> None:
        if not task_id:
            return

        app = MDApp.get_running_app()
        tasks = app.app_data.get("tasks", [])

        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.now().isoformat(
                    timespec="seconds"
                )
                break

        app.save_app_data()

    def _get_ordered_focus_task_ids(self) -> list[str]:
        app = MDApp.get_running_app()

        tasks = app.app_data.get("tasks", [])
        queue_task_ids = list(
            app.app_data.get("queue_task_ids", [])
        )

        ordered_ids: list[str] = []

        # Önce varsa mevcut queue sırası korunsun.
        for task_id in queue_task_ids:
            if task_id and task_id not in ordered_ids:
                ordered_ids.append(task_id)

        # Sonra Study List'teki diğer task'ları ekle.
        for task in tasks:
            task_id = task.get("id")

            if not task_id:
                continue

            if task_id not in ordered_ids:
                ordered_ids.append(task_id)

        return ordered_ids

    def move_to_next_queue_task(self) -> bool:
        """
        Mevcut task tamamlandıktan sonra Study List'teki
        sıradaki tamamlanmamış görevi aktif hale getirir.
        """
        app = MDApp.get_running_app()

        task_ids = self._get_ordered_focus_task_ids()
        tasks = app.app_data.get("tasks", [])

        tasks_by_id = {
            task.get("id"): task
            for task in tasks
            if task.get("id")
        }

        current_task_id = app.app_data.get(
            "active_task_id"
        )

        current_found = current_task_id is None

        for task_id in task_ids:
            # Önce mevcut task'ın bulunduğu yere kadar ilerle.
            if not current_found:
                if task_id == current_task_id:
                    current_found = True
                continue

            # Mevcut task'ın kendisini tekrar seçme.
            if task_id == current_task_id:
                continue

            task = tasks_by_id.get(task_id)

            if not task:
                continue

            if task.get("status") == "completed":
                continue

            app.app_data["active_task_id"] = task_id
            app.app_data["queue_mode_active"] = True
            app.app_data["last_queue_state"] = None

            app.save_app_data()
            return True

        return False

    # ---------------------------------------------------------
    # OTURUM KAYDI
    # ---------------------------------------------------------

    def _save_focus_session(
        self,
        duration_seconds: int,
        completed: bool,
    ) -> None:
        app = MDApp.get_running_app()
        task = self.get_active_task()

        if not task:
            return

        duration_seconds = max(0, int(duration_seconds))

        if duration_seconds <= 0:
            return

        session = {
            "id": f"session_{uuid.uuid4().hex[:8]}",
            "task_id": task.get("id"),
            "task_title": (
                task.get("task_name")
                or task.get("title")
                or ""
            ),
            "subject_id": task.get(
                "subject_id",
                "subject_other",
            ),
            "subject_name": task.get(
                "subject_name",
                app.t("other_subject"),
            ),
            "mode": "focus",
            "source": "study_plan",
            "duration_seconds": duration_seconds,
            "away_seconds": int(self.away_seconds),
            "started_at": (
                self.session_started_at
                or datetime.now().isoformat(timespec="seconds")
            ),
            "completed_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "completed": completed,
        }

        app.app_data.setdefault("sessions", []).append(session)
        app.save_app_data()

    # ---------------------------------------------------------
    # TIMER DURUMUNU KAYDETME / GERİ YÜKLEME
    # ---------------------------------------------------------

    def save_timer_state(self) -> None:
        app = MDApp.get_running_app()

        state = {
            "active_task_id": app.app_data.get("active_task_id"),
            "current_mode": self.current_mode,
            "focus_seconds": int(self.focus_seconds),
            "break_seconds": int(self.break_seconds),
            "remaining_seconds": int(self.remaining_seconds),
            "away_seconds": int(self.away_seconds),
            "timer_end_timestamp": float(
                self.timer_end_timestamp
            ),
            "pause_started_timestamp": float(
                self.pause_started_timestamp
            ),
            "is_running": bool(self.is_running),
            "is_paused": bool(self.is_paused),
            "is_waiting_for_next": bool(
                self.is_waiting_for_next
            ),
            "session_started_at": self.session_started_at,
        }

        app.app_data["focus_timer_state"] = state
        app.save_app_data()

    def _reconcile_expired_timer(
        self,
        play_alarm: bool = False,
    ) -> None:
        app = MDApp.get_running_app()
        settings = app.app_data.setdefault("settings", {})

        now = time.time()
        next_end_timestamp = float(self.timer_end_timestamp)
        first_completion = True

        while (
            self.is_running
            and next_end_timestamp > 0
            and next_end_timestamp <= now
        ):
            finished_mode = self.current_mode

            self.remaining_seconds = 0
            self.timer_end_timestamp = next_end_timestamp

            self.complete_current_mode(
                completed_automatically=(
                    play_alarm and first_completion
                ),
                allow_auto_start=False,
            )

            first_completion = False

            if finished_mode == "focus":
                should_auto_start = bool(
                    settings.get(
                        "auto_start_break",
                        False,
                    )
                )
            else:
                should_auto_start = bool(
                    settings.get(
                        "auto_start_focus",
                        False,
                    )
                )

            if not should_auto_start:
                break

            # Break tamamlandıktan sonra kuyruk da bittiyse
            # başlayacak yeni bir focus yoktur.
            if (
                self.current_mode == "focus"
                and not self.get_active_task()
            ):
                break

            duration = int(self.remaining_seconds)

            if duration <= 0:
                break

            # Yeni mod, kullanıcının uygulamaya döndüğü anda değil,
            # önceki modun gerçek bitiş anında başlamış kabul edilir.
            mode_started_timestamp = next_end_timestamp
            next_end_timestamp = (
                mode_started_timestamp + duration
            )

            self.timer_end_timestamp = next_end_timestamp
            self.is_running = True
            self.is_paused = False
            self.is_waiting_for_next = False
            self.pause_started_timestamp = 0

            if self.current_mode == "focus":
                self.session_started_at = datetime.fromtimestamp(
                    mode_started_timestamp
                ).isoformat(timespec="seconds")

            self.remaining_seconds = max(
                0,
                int(next_end_timestamp - now),
            )

            self.primary_action_icon = "pause"
            self.status_text = self._get_mode_status_text()

        if self.is_running:
            self.remaining_seconds = max(
                0,
                int(self.timer_end_timestamp - now),
            )

            if self.remaining_seconds > 0:
                self._start_timer_event()

        self.save_timer_state()
        self._update_display()

    def restore_timer_state(
        self,
        play_alarm: bool = True,
    ) -> bool:
        app = MDApp.get_running_app()

        state = app.app_data.get("focus_timer_state")

        if not isinstance(state, dict) or not state:
            return False

        saved_task_id = state.get("active_task_id")
        active_task_id = app.app_data.get("active_task_id")

        if saved_task_id != active_task_id:
            self.clear_timer_state()
            return False

        self._is_restoring = True

        try:
            self.current_mode = state.get(
                "current_mode",
                "focus",
            )

            self.focus_seconds = int(
                state.get("focus_seconds", 25 * 60)
            )

            self.break_seconds = int(
                state.get("break_seconds", 5 * 60)
            )

            self.remaining_seconds = int(
                state.get(
                    "remaining_seconds",
                    self.focus_seconds,
                )
            )

            self.away_seconds = int(
                state.get("away_seconds", 0)
            )

            self.timer_end_timestamp = float(
                state.get("timer_end_timestamp", 0)
            )

            self.pause_started_timestamp = float(
                state.get("pause_started_timestamp", 0)
            )

            self.is_running = bool(
                state.get("is_running", False)
            )

            self.is_paused = bool(
                state.get("is_paused", False)
            )

            self.is_waiting_for_next = bool(
                state.get("is_waiting_for_next", False)
            )

            self.session_started_at = state.get(
                "session_started_at"
            )

            self.active_task_name = self._get_active_task_name()

            if self.is_running:
                self._sync_remaining_seconds()

                if self.remaining_seconds <= 0:
                    self._reconcile_expired_timer(
                        play_alarm=play_alarm
                    )
                else:
                    self.primary_action_icon = "pause"
                    self.status_text = self._get_mode_status_text()
                    self._start_timer_event()
            else:
                self.primary_action_icon = "play"

                if self.is_paused:
                    self.status_text = app.t("paused")
                elif self.current_mode == "break":
                    self.status_text = app.t("break_ready")
                else:
                    self.status_text = app.t("focus_ready")

            self._update_display()
            return True

        finally:
            self._is_restoring = False

    def clear_timer_state(self) -> None:
        app = MDApp.get_running_app()
        app.app_data["focus_timer_state"] = {}
        app.save_app_data()

    # ---------------------------------------------------------
    # UYGULAMA ARKA PLAN / ÖN PLAN
    # ---------------------------------------------------------

    def handle_app_pause(self) -> None:
        if self.is_running:
            self._sync_remaining_seconds()

        self.save_timer_state()
        self._cancel_timer_event()

        if self.is_running:
            self._schedule_android_alarm()

    def handle_app_resume(self) -> None:
        self.app.stop_android_alarm_service()
        self._cancel_android_alarm()
        self.restore_timer_state(play_alarm=False)
        self._update_display()

    # ---------------------------------------------------------
    # ANDROID ALARM BAĞLANTISI
    # ---------------------------------------------------------

    def _build_background_focus_sequence(self) -> list[dict[str, int]]:
        app = MDApp.get_running_app()

        tasks = app.app_data.get("tasks", [])
        queue_task_ids = (
            self._get_ordered_focus_task_ids()
        )
        active_task_id = app.app_data.get(
            "active_task_id"
        )

        tasks_by_id = {
            task.get("id"): task
            for task in tasks
            if task.get("id")
        }

        sequence: list[dict[str, int]] = []

        active_task = tasks_by_id.get(
            active_task_id
        )

        # Mevcut task her zaman ilk eleman.
        # Break modundaysak task completed işaretlenmiş
        # olabilir ama mevcut break hâlâ ona aittir.
        if active_task:
            sequence.append(
                {
                    "focus_duration": (
                        self._safe_positive_int(
                            active_task.get(
                                "focus_duration",
                                25,
                            ),
                            default=25,
                        )
                        * 60
                    ),
                    "break_duration": (
                        self._safe_positive_int(
                            active_task.get(
                                "break_minutes",
                                5,
                            ),
                            default=5,
                        )
                        * 60
                    ),
                }
            )

        # Sonraki tamamlanmamış queue task'ları.
        for task_id in queue_task_ids:
            if task_id == active_task_id:
                continue

            task = tasks_by_id.get(task_id)

            if not task:
                continue

            if task.get("status") == "completed":
                continue

            sequence.append(
                {
                    "focus_duration": (
                        self._safe_positive_int(
                            task.get(
                                "focus_duration",
                                25,
                            ),
                            default=25,
                        )
                        * 60
                    ),
                    "break_duration": (
                        self._safe_positive_int(
                            task.get(
                                "break_minutes",
                                5,
                            ),
                            default=5,
                        )
                        * 60
                    ),
                }
            )

        return sequence

    def _schedule_android_alarm(self) -> None:
        """
        Android AlarmManager entegrasyonu main.py içine eklendiğinde
        bu metod otomatik olarak onu çağırır.
        """
        app = MDApp.get_running_app()

        schedule_method = getattr(
            app,
            "schedule_focus_alarm",
            None,
        )

        if callable(schedule_method):
            schedule_method(
                end_timestamp=float(
                    self.timer_end_timestamp
                ),
                mode=self.current_mode,
                service_data={
                    "timer_type": "focus_timer",
                    "focus_sequence": (
                        self._build_background_focus_sequence()
                    ),
                    "focus_index": 0,
                    "auto_start_break": bool(
                        app.app_data.get(
                            "settings",
                            {},
                        ).get(
                            "auto_start_break",
                            False,
                        )
                    ),
                    "auto_start_focus": bool(
                        app.app_data.get(
                            "settings",
                            {},
                        ).get(
                            "auto_start_focus",
                            False,
                        )
                    ),
                },
            )

    def _cancel_android_alarm(self) -> None:
        app = MDApp.get_running_app()

        cancel_method = getattr(
            app,
            "cancel_focus_alarm",
            None,
        )

        if callable(cancel_method):
            cancel_method()

    # ---------------------------------------------------------
    # YARDIMCI METOTLAR
    # ---------------------------------------------------------

    def _prepare_current_mode_duration(self) -> None:
        if self.current_mode == "focus":
            self.remaining_seconds = self.focus_seconds
        else:
            self.remaining_seconds = self.break_seconds

    def _get_mode_status_text(self) -> str:
        app = MDApp.get_running_app()

        if self.current_mode == "break":
            return app.t("break_mode")

        return app.t("focus_mode")

    def _get_elapsed_seconds(self) -> int:
        if self.current_mode == "focus":
            total_seconds = self.focus_seconds
        else:
            total_seconds = self.break_seconds

        return max(
            0,
            int(total_seconds - self.remaining_seconds),
        )

    def _update_display(self) -> None:
        self.timer_text = self._format_seconds(
            int(self.remaining_seconds)
        )

        away_seconds = int(self.away_seconds)

        if self.is_paused and self.pause_started_timestamp > 0:
            away_seconds += max(
                0,
                int(time.time() - self.pause_started_timestamp),
            )

        self.away_time_text = self._format_seconds(
            away_seconds
        )

    def _format_seconds(self, total_seconds: int) -> str:
        total_seconds = max(0, int(total_seconds))

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _safe_positive_int(
        value: Any,
        default: int,
    ) -> int:
        try:
            parsed_value = int(value)
        except (TypeError, ValueError):
            return default

        if parsed_value <= 0:
            return default

        return parsed_value

    def _cancel_timer_event(self) -> None:
        if self._timer_event is not None:
            self._timer_event.cancel()
            self._timer_event = None

    def open_settings(self) -> None:
        self.load_focus_settings()
        self.settings_panel_open = True


    def close_settings(self) -> None:
        self.settings_panel_open = False


    def load_focus_settings(self) -> None:
        app = MDApp.get_running_app()
        settings = app.app_data.setdefault("settings", {})

        self.setting_auto_start_focus = bool(
            settings.get("auto_start_focus", False)
        )

        self.setting_auto_start_break = bool(
            settings.get("auto_start_break", False)
        )

        self.setting_show_away_time = bool(
            settings.get("show_cumulative_away_time", False)
        )


    def save_focus_settings(self) -> None:
        app = MDApp.get_running_app()
        settings = app.app_data.setdefault("settings", {})

        settings["auto_start_focus"] = bool(
            self.setting_auto_start_focus
        )

        settings["auto_start_break"] = bool(
            self.setting_auto_start_break
        )

        settings["show_cumulative_away_time"] = bool(
            self.setting_show_away_time
        )

        app.save_app_data()

        self.settings_panel_open = False
        self.status_text = "Odak ayarları kaydedildi."

    def on_leave(self, *args) -> None:
        """
        Yalnızca başka bir Nagomi sayfasına geçmek timer'ı durdurmaz.
        Sayaç timestamp üzerinden çalışmaya devam eder.
        """
        self.save_timer_state()
        return super().on_leave(*args)

    @staticmethod
    def _safe_text(value: Any, default: str = "") -> str:
        if value is None:
            return default

        if isinstance(value, dict):
            return str(
                value.get("name")
                or value.get("title")
                or value.get("name_key")
                or default
            )

        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(item) for item in value)

        return str(value)

    def set_away_time_setting(self, enabled):
        app = App.get_running_app()

        if app.layout_profile == "phone_landscape":
            self.setting_show_away_time = False
            return

        self.setting_show_away_time = enabled

    

    @property
    def app(self):
        from kivy.app import App
        return App.get_running_app()
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from kivy.metrics import dp
from kivy.properties import (
    ListProperty,
    NumericProperty,
    StringProperty,
)
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.properties import ListProperty
from kivy.uix.widget import Widget

class WeeklyBarChart(Widget):
    labels = ListProperty([])
    values = ListProperty([])
    bar_color = ListProperty([0.49, 0.28, 0.86, 1])
    empty_bar_color = ListProperty([0.23, 0.21, 0.29, 1])
    text_color = ListProperty([0.72, 0.68, 0.84, 1])

    grid_color = ListProperty([0.22, 0.20, 0.28, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.bind(
            pos=self._redraw,
            size=self._redraw,
            labels=self._redraw,
            values=self._redraw,
            bar_color=self._redraw,
            empty_bar_color=self._redraw,
            grid_color=self._redraw,
            text_color=self._redraw,
        )

    def set_data(
        self,
        labels: list[str],
        values: list[int],
    ) -> None:
        self.labels = list(labels)
        self.values = list(values)
        self._redraw()

    def _redraw(self, *_args) -> None:
        self.canvas.clear()

        if not self.labels or not self.values:
            return

        chart_left = self.x + dp(12)
        chart_right = self.right - dp(12)
        chart_bottom = self.y + dp(34)
        chart_top = self.top - dp(30)

        chart_width = max(0, chart_right - chart_left)
        chart_height = max(0, chart_top - chart_bottom)

        if chart_width <= 0 or chart_height <= 0:
            return

        values = [
            max(0, int(value))
            for value in self.values[:7]
        ]

        labels = [
            str(label)
            for label in self.labels[:7]
        ]

        while len(values) < 7:
            values.append(0)

        while len(labels) < 7:
            labels.append("")

        max_value = max(values) if values else 0
        scale_max = max(max_value, 1)

        column_width = chart_width / 7
        bar_width = min(dp(28), column_width * 0.56)

        with self.canvas:
            # Yatay referans çizgileri
            Color(*self.grid_color)

            for index in range(4):
                y = chart_bottom + (
                    chart_height * index / 3
                )

                Line(
                    points=[
                        chart_left,
                        y,
                        chart_right,
                        y,
                    ],
                    width=1,
                )

            for index, value in enumerate(values):
                center_x = (
                    chart_left
                    + column_width * index
                    + column_width / 2
                )

                if value > 0:
                    bar_height = max(
                        dp(5),
                        chart_height
                        * value
                        / scale_max,
                    )
                    color = self.bar_color
                else:
                    bar_height = dp(4)
                    color = self.empty_bar_color

                Color(*color)

                RoundedRectangle(
                    pos=(
                        center_x - bar_width / 2,
                        chart_bottom,
                    ),
                    size=(
                        bar_width,
                        bar_height,
                    ),
                    radius=[
                        dp(6),
                        dp(6),
                        0,
                        0,
                    ],
                )

class StatisticsScreen(MDScreen):
    today_focus_text = StringProperty("00:00")
    completed_sessions_text = StringProperty("0")
    away_time_text = StringProperty("00:00")

    study_plan_focus_text = StringProperty("00:00")
    regular_pomodoro_focus_text = StringProperty("00:00")
    total_focus_text = StringProperty("00:00")

    goal_detail_text = StringProperty("0% · 00:00 / 05:00")
    goal_progress = NumericProperty(0)

    weekly_total_text = StringProperty("")
    subject_total_text = StringProperty("")

    selected_subject_name = StringProperty("")
    subject_filter_values = ListProperty([])

    empty_subject_text = StringProperty("")
    empty_recent_text = StringProperty("")

    weekly_labels = ListProperty(["", "", "", "", "", "", ""])

    weekly_values = ListProperty([0, 0, 0, 0, 0, 0, 0])
    weekly_value_texts = ListProperty(
        ["0", "0", "0", "0", "0", "0", "0"]
    )

    selected_subject_id = StringProperty("all")

    @property
    def app(self):
        from kivy.app import App
        return App.get_running_app()

    def on_kv_post(self, base_widget) -> None:
        self.refresh_stats()

    def on_pre_enter(self, *args) -> None:
        self.refresh_stats()
        return super().on_pre_enter(*args)

    # ---------------------------------------------------------
    # ANA YENİLEME
    # ---------------------------------------------------------

    def refresh_stats(self) -> None:
        if not self.ids:
            return

        self.empty_subject_text = self.app.t(
            "no_subject_statistics_this_week"
        )
        self.empty_recent_text = self.app.t(
            "no_completed_focus_sessions_today"
        )

        self.refresh_subject_filter()
        self.refresh_today_metrics()
        self.refresh_source_breakdown()
        self.refresh_goal()
        self.render_weekly_overview()
        self.render_subject_distribution()
        self.render_recent_sessions()

    # ---------------------------------------------------------
    # TARİH VE OTURUM YARDIMCILARI
    # ---------------------------------------------------------

    def get_sessions(self) -> list[dict[str, Any]]:
        sessions = self.app.app_data.get("sessions", [])

        if not isinstance(sessions, list):
            return []

        return [
            session
            for session in sessions
            if isinstance(session, dict)
        ]

    def get_today_sessions(self) -> list[dict[str, Any]]:
        today_text = date.today().isoformat()
        result = []

        for session in self.get_sessions():
            if session.get("mode") != "focus":
                continue

            completed_at = str(
                session.get("completed_at", "")
            )

            if completed_at.startswith(today_text):
                result.append(session)

        return result

    def get_week_start_date(self) -> date:
        today = date.today()

        week_start_day = self.app.app_data.get(
            "settings",
            {},
        ).get(
            "week_start_day",
            "monday",
        )

        if week_start_day == "sunday":
            days_since_sunday = (today.weekday() + 1) % 7
            return today - timedelta(days=days_since_sunday)

        return today - timedelta(days=today.weekday())

    def get_week_sessions(self) -> list[dict[str, Any]]:
        start_of_week = self.get_week_start_date()
        end_of_week = start_of_week + timedelta(days=7)

        result = []

        for session in self.get_sessions():
            if session.get("mode") != "focus":
                continue

            session_date = self._parse_session_date(
                session.get("completed_at")
            )

            if session_date is None:
                continue

            if start_of_week <= session_date < end_of_week:
                result.append(session)

        return result

    # ---------------------------------------------------------
    # GÜNLÜK METRİKLER
    # ---------------------------------------------------------

    def refresh_today_metrics(self) -> None:
        today_sessions = self.get_today_sessions()

        total_focus_seconds = sum(
            self._safe_seconds(
                session.get("duration_seconds")
            )
            for session in today_sessions
        )

        total_away_seconds = sum(
            self._safe_seconds(
                session.get("away_seconds")
            )
            for session in today_sessions
        )

        self.today_focus_text = self.format_hours_minutes(
            total_focus_seconds
        )

        self.completed_sessions_text = str(
            len(today_sessions)
        )

        self.away_time_text = self.format_hours_minutes(
            total_away_seconds
        )

    def refresh_source_breakdown(self) -> None:
        study_plan_seconds = 0
        regular_pomodoro_seconds = 0

        for session in self.get_today_sessions():
            duration = self._safe_seconds(
                session.get("duration_seconds")
            )

            if session.get("source") == "regular_pomodoro":
                regular_pomodoro_seconds += duration
            else:
                study_plan_seconds += duration

        total_seconds = (
            study_plan_seconds
            + regular_pomodoro_seconds
        )

        self.study_plan_focus_text = (
            self.format_hours_minutes(study_plan_seconds)
        )

        self.regular_pomodoro_focus_text = (
            self.format_hours_minutes(
                regular_pomodoro_seconds
            )
        )

        self.total_focus_text = self.format_hours_minutes(
            total_seconds
        )

    # ---------------------------------------------------------
    # GÜNLÜK HEDEF
    # ---------------------------------------------------------

    def refresh_goal(self) -> None:
        total_seconds = sum(
            self._safe_seconds(
                session.get("duration_seconds")
            )
            for session in self.get_today_sessions()
        )

        goal_minutes = self._safe_positive_int(
            self.app.app_data.get(
                "settings",
                {},
            ).get(
                "daily_focus_goal_minutes",
                300,
            ),
            default=300,
        )

        goal_seconds = goal_minutes * 60

        ratio = (
            min(total_seconds / goal_seconds, 1)
            if goal_seconds > 0
            else 0
        )

        self.goal_progress = ratio * 100

        self.goal_detail_text = (
            f"{int(ratio * 100)}% · "
            f"{self.format_hours_minutes(total_seconds)} / "
            f"{self.format_hours_minutes(goal_seconds)}"
        )

    # ---------------------------------------------------------
    # DERS FİLTRESİ
    # ---------------------------------------------------------

    def get_subject_options(self) -> list[dict[str, str]]:
        options = [
            {
                "id": "all",
                "name": self.app.t("all_subjects"),
            }
        ]

        for subject in self.app.app_data.get(
            "subjects",
            [],
        ):
            subject_id = str(
                subject.get("id", "subject_other")
            )

            subject_name = str(
                subject.get("name")
                or self.app.t(
                    subject.get(
                        "name_key",
                        "other_subject",
                    )
                )
            )

            options.append(
                {
                    "id": subject_id,
                    "name": subject_name,
                }
            )

        return options

    def refresh_subject_filter(self) -> None:
        options = self.get_subject_options()
        values = [option["name"] for option in options]

        self.subject_filter_values = values

        selected_option = next(
            (
                option
                for option in options
                if option["id"] == self.selected_subject_id
            ),
            options[0],
        )

        self.selected_subject_id = selected_option["id"]
        self.selected_subject_name = selected_option["name"]

    def change_subject_filter(
        self,
        selected_name: str,
    ) -> None:
        for option in self.get_subject_options():
            if option["name"] == selected_name:
                self.selected_subject_id = option["id"]
                self.selected_subject_name = option["name"]
                break

        self.render_weekly_overview()

    # ---------------------------------------------------------
    # HAFTALIK GÖRÜNÜM
    # ---------------------------------------------------------

    def get_week_day_labels(self) -> list[str]:
        week_start_day = self.app.app_data.get(
            "settings",
            {},
        ).get(
            "week_start_day",
            "monday",
        )

        if week_start_day == "sunday":
            return [
                self.app.t("weekday_sun_short"),
                self.app.t("weekday_mon_short"),
                self.app.t("weekday_tue_short"),
                self.app.t("weekday_wed_short"),
                self.app.t("weekday_thu_short"),
                self.app.t("weekday_fri_short"),
                self.app.t("weekday_sat_short"),
            ]

        return [
            self.app.t("weekday_mon_short"),
            self.app.t("weekday_tue_short"),
            self.app.t("weekday_wed_short"),
            self.app.t("weekday_thu_short"),
            self.app.t("weekday_fri_short"),
            self.app.t("weekday_sat_short"),
            self.app.t("weekday_sun_short"),
        ]

    def get_weekly_daily_totals(
        self,
    ) -> dict[str, int]:
        start_of_week = self.get_week_start_date()

        totals = {
            (
                start_of_week + timedelta(days=index)
            ).isoformat(): 0
            for index in range(7)
        }

        for session in self.get_week_sessions():
            if (
                self.selected_subject_id != "all"
                and session.get(
                    "subject_id",
                    "subject_other",
                )
                != self.selected_subject_id
            ):
                continue

            session_date = self._parse_session_date(
                session.get("completed_at")
            )

            if session_date is None:
                continue

            key = session_date.isoformat()

            if key in totals:
                totals[key] += self._safe_seconds(
                    session.get("duration_seconds")
                )

        return totals

    def render_weekly_overview(self) -> None:
        totals = self.get_weekly_daily_totals()
        labels = self.get_week_day_labels()

        values = [
            max(0, int(seconds)) // 60
            for seconds in totals.values()
        ]

        while len(values) < 7:
            values.append(0)

        values = values[:7]
        labels = labels[:7]

        weekly_total = sum(values)

        self.weekly_labels = labels
        self.weekly_values = values
        self.weekly_value_texts = [
            str(value)
            for value in values
        ]

        self.weekly_total_text = self.app.t(
            "this_week_minutes_subject"
        ).format(
            minutes=weekly_total,
            subject=self.selected_subject_name,
        )

        if "weekly_bar_chart" in self.ids:
            self.ids.weekly_bar_chart.set_data(
                labels,
                values,
            )

    # ---------------------------------------------------------
    # DERS DAĞILIMI
    # ---------------------------------------------------------

    def get_weekly_subject_totals(
        self,
    ) -> list[dict[str, Any]]:
        totals: dict[str, dict[str, Any]] = {}

        for session in self.get_week_sessions():
            subject_id = str(
                session.get(
                    "subject_id",
                    "subject_other",
                )
            )

            subject_name = str(
                session.get("subject_name")
                or self.app.t("other_subject")
            )

            if subject_id not in totals:
                totals[subject_id] = {
                    "id": subject_id,
                    "name": subject_name,
                    "seconds": 0,
                    "color": self.get_subject_color(
                        subject_id
                    ),
                }

            totals[subject_id]["seconds"] += (
                self._safe_seconds(
                    session.get("duration_seconds")
                )
            )

        return sorted(
            totals.values(),
            key=lambda item: item["seconds"],
            reverse=True,
        )

    def render_subject_distribution(self) -> None:
        if "subject_list" not in self.ids:
            return

        container = self.ids.subject_list
        container.clear_widgets()

        subjects = self.get_weekly_subject_totals()

        total_seconds = sum(
            item["seconds"]
            for item in subjects
        )

        total_minutes = total_seconds // 60

        self.subject_total_text = self.app.t(
            "this_week_minutes"
        ).format(minutes=total_minutes)

        if total_seconds <= 0:
            self.ids.subject_empty.opacity = 1
            self.ids.subject_empty.height = dp(34)
            return

        self.ids.subject_empty.opacity = 0
        self.ids.subject_empty.height = 0

        for item in subjects:
            ratio = (
                item["seconds"] / total_seconds
                if total_seconds > 0
                else 0
            )

            minutes = item["seconds"] // 60
            percent = int(round(ratio * 100))

            card = MDCard(
                orientation="vertical",
                adaptive_height=True,
                padding=dp(12),
                spacing=dp(6),
                radius=[
                    dp(16),
                    dp(16),
                    dp(16),
                    dp(16),
                ],
                elevation=0,
                md_bg_color=self.app.theme_colors["card_soft"],
            )

            header = MDBoxLayout(
                orientation="horizontal",
                adaptive_height=True,
                spacing=dp(8),
            )

            name_label = MDLabel(
                text=str(item["name"]),
                adaptive_height=True,
                bold=True,
                theme_text_color="Custom",
                text_color=self.app.theme_colors["text"],
            )

            value_label = MDLabel(
                text=self.app.t("subject_distribution_value").format(
                    minutes=minutes,
                    percent=percent,
                ),
                size_hint_x=None,
                width=dp(95),
                halign="right",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=self.app.theme_colors["muted"],
            )

            progress = MDProgressBar(
                value=ratio * 100,
                size_hint_y=None,
                height=dp(8),
                color=self.app.theme_colors["primary"],
            )

            header.add_widget(name_label)
            header.add_widget(value_label)

            card.add_widget(header)
            card.add_widget(progress)

            container.add_widget(card)

    # ---------------------------------------------------------
    # SON OTURUMLAR
    # ---------------------------------------------------------

    def render_recent_sessions(self) -> None:
        if "recent_list" not in self.ids:
            return

        container = self.ids.recent_list
        container.clear_widgets()

        sessions = sorted(
            self.get_today_sessions(),
            key=lambda session: str(
                session.get("completed_at", "")
            ),
            reverse=True,
        )[:5]

        if not sessions:
            self.ids.recent_empty.opacity = 1
            self.ids.recent_empty.height = dp(42)
            return

        self.ids.recent_empty.opacity = 0
        self.ids.recent_empty.height = 0

        for session in sessions:
            source = session.get(
                "source",
                "study_plan",
            )

            if source == "regular_pomodoro":
                title = self.app.t("pomodoro")
                source_text = self.app.t("pomodoro")
            else:
                title = str(
                    session.get("task_title")
                    or session.get("subject_name")
                    or self.app.t("focus_session")
                )
                source_text = self.app.t("study_plan")

            duration_minutes = (
                self._safe_seconds(
                    session.get("duration_seconds")
                )
                // 60
            )

            away_minutes = (
                self._safe_seconds(
                    session.get("away_seconds")
                )
                // 60
            )

            completed_time = self.format_session_time(
                session.get("completed_at")
            )

            card = MDCard(
                orientation="vertical",
                adaptive_height=True,
                padding=dp(12),
                spacing=dp(4),
                radius=[
                    dp(16),
                    dp(16),
                    dp(16),
                    dp(16),
                ],
                elevation=0,
                md_bg_color=self.app.theme_colors["card_soft"],
            )

            title_row = MDBoxLayout(
                orientation="horizontal",
                adaptive_height=True,
                spacing=dp(8),
            )


            title_label = MDLabel(
                text=title,
                bold=True,
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=self.app.theme_colors["text"],
            )

            time_label = MDLabel(
                text=completed_time,
                size_hint_x=None,
                width=dp(48),
                halign="right",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=self.app.theme_colors["muted"],
            )

            detail_label = MDLabel(
                text=self.app.t("recent_session_detail").format(
                    source=source_text,
                    focus=duration_minutes,
                    away=away_minutes,
                ),
                adaptive_height=True,
                font_style="Caption",
                theme_text_color="Custom",
                text_color=self.app.theme_colors["muted"],
            )

            title_row.add_widget(title_label)
            title_row.add_widget(time_label)

            card.add_widget(title_row)
            card.add_widget(detail_label)

            container.add_widget(card)

    # ---------------------------------------------------------
    # FORMAT VE GÜVENLİK
    # ---------------------------------------------------------

    def get_subject_color(self, subject_id: str) -> str:
        for subject in self.app.app_data.get(
            "subjects",
            [],
        ):
            if subject.get("id") == subject_id:
                return str(
                    subject.get("color", "#A78BFA")
                )

        return "#A78BFA"

    @staticmethod
    def format_hours_minutes(seconds: int) -> str:
        seconds = max(0, int(seconds))

        total_minutes = seconds // 60
        hours = total_minutes // 60
        minutes = total_minutes % 60

        return f"{hours:02d}:{minutes:02d}"

    @staticmethod
    def format_session_time(value: Any) -> str:
        try:
            parsed = datetime.fromisoformat(str(value))
            return parsed.strftime("%H:%M")
        except (TypeError, ValueError):
            return "--:--"

    @staticmethod
    def _parse_session_date(value: Any):
        try:
            return datetime.fromisoformat(
                str(value)
            ).date()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_seconds(value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_positive_int(
        value: Any,
        default: int,
    ) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default

        return parsed if parsed > 0 else default
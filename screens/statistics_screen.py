from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen


# =========================================================
# WEEKLY BAR CHART
# =========================================================

class WeeklyBarChart(Widget):
    labels = ListProperty([])
    values = ListProperty([])

    bar_color = ListProperty([0.49, 0.28, 0.86, 1])
    empty_bar_color = ListProperty([0.23, 0.21, 0.29, 1])
    text_color = ListProperty([0.72, 0.68, 0.84, 1])
    grid_color = ListProperty([0.22, 0.20, 0.28, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Aynı frame içinde birden fazla property değişse bile
        # canvas yalnızca bir kez çizilsin.
        self._redraw_trigger = Clock.create_trigger(
            self._redraw,
            -1,
        )

        self.bind(
            pos=self._request_redraw,
            size=self._request_redraw,
            labels=self._request_redraw,
            values=self._request_redraw,
            bar_color=self._request_redraw,
            empty_bar_color=self._request_redraw,
            grid_color=self._request_redraw,
            text_color=self._request_redraw,
        )

    def _request_redraw(self, *_args) -> None:
        self._redraw_trigger()

    def set_data(
        self,
        labels: list[str],
        values: list[int],
    ) -> None:
        self.labels = list(labels)
        self.values = list(values)

    def _redraw(self, _dt=0) -> None:
        self.canvas.clear()

        if not self.labels or not self.values:
            return

        chart_left = self.x + dp(12)
        chart_right = self.right - dp(12)
        chart_bottom = self.y + dp(34)
        chart_top = self.top - dp(30)

        chart_width = max(
            0,
            chart_right - chart_left,
        )

        chart_height = max(
            0,
            chart_top - chart_bottom,
        )

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
        bar_width = min(
            dp(28),
            column_width * 0.56,
        )

        with self.canvas:
            Color(*self.grid_color)

            for index in range(4):
                y = (
                    chart_bottom
                    + chart_height * index / 3
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


# =========================================================
# STATISTICS SCREEN
# =========================================================

class StatisticsScreen(MDScreen):
    today_focus_text = StringProperty("00:00")
    completed_sessions_text = StringProperty("0")
    away_time_text = StringProperty("00:00")

    study_plan_focus_text = StringProperty("00:00")
    regular_pomodoro_focus_text = StringProperty("00:00")
    total_focus_text = StringProperty("00:00")

    goal_detail_text = StringProperty(
        "0% · 00:00 / 05:00"
    )
    goal_progress = NumericProperty(0)

    weekly_total_text = StringProperty("")
    subject_total_text = StringProperty("")

    selected_subject_name = StringProperty("")
    selected_subject_id = StringProperty("all")

    subject_filter_values = ListProperty([])

    empty_subject_text = StringProperty("")
    empty_recent_text = StringProperty("")

    weekly_labels = ListProperty(
        ["", "", "", "", "", "", ""]
    )

    weekly_values = ListProperty(
        [0, 0, 0, 0, 0, 0, 0]
    )

    weekly_value_texts = ListProperty(
        ["0", "0", "0", "0", "0", "0", "0"]
    )

    _clear_statistics_dialog = None

    # ---------------------------------------------------------
    # APP
    # ---------------------------------------------------------

    @property
    def app(self):
        from kivy.app import App
        return App.get_running_app()

    # ---------------------------------------------------------
    # SCREEN LIFECYCLE
    # ---------------------------------------------------------

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

        # Session listesi yalnızca bir kez okunur.
        sessions = self.get_sessions()

        today_sessions = self._filter_today_sessions(
            sessions
        )

        week_sessions = self._filter_week_sessions(
            sessions
        )

        self.refresh_subject_filter()

        self.refresh_today_metrics(
            today_sessions
        )

        self.refresh_source_breakdown(
            today_sessions
        )

        self.refresh_goal(
            today_sessions
        )

        self.render_weekly_overview(
            week_sessions
        )

        self.render_subject_distribution(
            week_sessions
        )

        self.render_recent_sessions(
            today_sessions
        )

    # ---------------------------------------------------------
    # CLEAR STATISTICS
    # ---------------------------------------------------------

    def open_clear_statistics_dialog(self) -> None:
        if self._clear_statistics_dialog is None:
            self._clear_statistics_dialog = MDDialog(
                title=self.app.t(
                    "clear_statistics"
                ),
                text=self.app.t(
                    "clear_statistics_confirmation"
                ),
                buttons=[
                    MDFlatButton(
                        text=self.app.t("cancel"),
                        theme_text_color="Custom",
                        text_color=self.app.theme_colors[
                            "muted"
                        ],
                        on_release=lambda *_:
                            self._clear_statistics_dialog.dismiss(),
                    ),
                    MDRaisedButton(
                        text=self.app.t("clear"),
                        md_bg_color=self.app.theme_colors[
                            "red"
                        ],
                        on_release=self.confirm_clear_statistics,
                    ),
                ],
            )

            if self._clear_statistics_dialog.ids.get(
                "text"
            ):
                self._clear_statistics_dialog.ids.text.font_size = (
                    "14sp"
                )

        self._clear_statistics_dialog.open()

    def confirm_clear_statistics(
        self,
        *_args,
    ) -> None:
        self.app.app_data["sessions"] = []
        self.app.save_app_data()

        self.refresh_stats()

        if self._clear_statistics_dialog is not None:
            self._clear_statistics_dialog.dismiss()

    def refresh_clear_statistics_dialog_theme(
        self,
    ) -> None:
        if self._clear_statistics_dialog is None:
            return

        # Bir sonraki açılışta güncel tema ile yeniden oluşturulur.
        self._clear_statistics_dialog = None

    # ---------------------------------------------------------
    # SESSION HELPERS
    # ---------------------------------------------------------

    def get_sessions(
        self,
    ) -> list[dict[str, Any]]:
        sessions = self.app.app_data.get(
            "sessions",
            [],
        )

        if not isinstance(sessions, list):
            return []

        return [
            session
            for session in sessions
            if isinstance(session, dict)
        ]

    def get_today_sessions(
        self,
    ) -> list[dict[str, Any]]:
        return self._filter_today_sessions(
            self.get_sessions()
        )

    def get_week_sessions(
        self,
    ) -> list[dict[str, Any]]:
        return self._filter_week_sessions(
            self.get_sessions()
        )

    def _filter_today_sessions(
        self,
        sessions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        today_text = date.today().isoformat()

        return [
            session
            for session in sessions
            if (
                session.get("mode") == "focus"
                and str(
                    session.get(
                        "completed_at",
                        "",
                    )
                ).startswith(today_text)
            )
        ]

    def _filter_week_sessions(
        self,
        sessions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        start_of_week = self.get_week_start_date()
        end_of_week = (
            start_of_week
            + timedelta(days=7)
        )

        result = []

        for session in sessions:
            if session.get("mode") != "focus":
                continue

            session_date = self._parse_session_date(
                session.get("completed_at")
            )

            if session_date is None:
                continue

            if (
                start_of_week
                <= session_date
                < end_of_week
            ):
                result.append(session)

        return result

    def get_week_start_date(self) -> date:
        today = date.today()

        week_start_day = (
            self.app.app_data
            .get("settings", {})
            .get(
                "week_start_day",
                "monday",
            )
        )

        if week_start_day == "sunday":
            days_since_sunday = (
                today.weekday() + 1
            ) % 7

            return (
                today
                - timedelta(
                    days=days_since_sunday
                )
            )

        return (
            today
            - timedelta(
                days=today.weekday()
            )
        )

    # ---------------------------------------------------------
    # DAILY METRICS
    # ---------------------------------------------------------

    def refresh_today_metrics(
        self,
        today_sessions: list[dict[str, Any]],
    ) -> None:
        total_focus_seconds = sum(
            self._safe_seconds(
                session.get(
                    "duration_seconds"
                )
            )
            for session in today_sessions
        )

        total_away_seconds = sum(
            self._safe_seconds(
                session.get(
                    "away_seconds"
                )
            )
            for session in today_sessions
        )

        self.today_focus_text = (
            self.format_hours_minutes(
                total_focus_seconds
            )
        )

        self.completed_sessions_text = str(
            len(today_sessions)
        )

        self.away_time_text = (
            self.format_hours_minutes(
                total_away_seconds
            )
        )

    # ---------------------------------------------------------
    # SOURCE BREAKDOWN
    # ---------------------------------------------------------

    def refresh_source_breakdown(
        self,
        today_sessions: list[dict[str, Any]],
    ) -> None:
        study_plan_seconds = 0
        regular_pomodoro_seconds = 0

        for session in today_sessions:
            duration = self._safe_seconds(
                session.get(
                    "duration_seconds"
                )
            )

            if (
                session.get("source")
                == "regular_pomodoro"
            ):
                regular_pomodoro_seconds += duration
            else:
                study_plan_seconds += duration

        total_seconds = (
            study_plan_seconds
            + regular_pomodoro_seconds
        )

        self.study_plan_focus_text = (
            self.format_hours_minutes(
                study_plan_seconds
            )
        )

        self.regular_pomodoro_focus_text = (
            self.format_hours_minutes(
                regular_pomodoro_seconds
            )
        )

        self.total_focus_text = (
            self.format_hours_minutes(
                total_seconds
            )
        )

    # ---------------------------------------------------------
    # DAILY GOAL
    # ---------------------------------------------------------

    def refresh_goal(
        self,
        today_sessions: list[dict[str, Any]],
    ) -> None:
        total_seconds = sum(
            self._safe_seconds(
                session.get(
                    "duration_seconds"
                )
            )
            for session in today_sessions
        )

        goal_minutes = self._safe_positive_int(
            self.app.app_data
            .get("settings", {})
            .get(
                "daily_focus_goal_minutes",
                300,
            ),
            default=300,
        )

        goal_seconds = goal_minutes * 60

        if goal_seconds > 0:
            ratio = min(
                total_seconds / goal_seconds,
                1,
            )
        else:
            ratio = 0

        self.goal_progress = ratio * 100

        self.goal_detail_text = (
            f"{int(ratio * 100)}% · "
            f"{self.format_hours_minutes(total_seconds)} / "
            f"{self.format_hours_minutes(goal_seconds)}"
        )

    # ---------------------------------------------------------
    # SUBJECT FILTER
    # ---------------------------------------------------------

    def get_subject_options(
        self,
    ) -> list[dict[str, str]]:
        options = [
            {
                "id": "all",
                "name": self.app.t(
                    "all_subjects"
                ),
            }
        ]

        for subject in self.app.app_data.get(
            "subjects",
            [],
        ):
            if not isinstance(subject, dict):
                continue

            subject_id = str(
                subject.get(
                    "id",
                    "subject_other",
                )
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

        if not options:
            return

        self.subject_filter_values = [
            option["name"]
            for option in options
        ]

        selected_option = next(
            (
                option
                for option in options
                if (
                    option["id"]
                    == self.selected_subject_id
                )
            ),
            options[0],
        )

        self.selected_subject_id = (
            selected_option["id"]
        )

        self.selected_subject_name = (
            selected_option["name"]
        )

    def change_subject_filter(
        self,
        selected_name: str,
    ) -> None:
        for option in self.get_subject_options():
            if option["name"] == selected_name:
                self.selected_subject_id = (
                    option["id"]
                )

                self.selected_subject_name = (
                    option["name"]
                )

                break

        # Filtre yalnızca haftalık grafiği etkiliyor.
        self.render_weekly_overview(
            self.get_week_sessions()
        )

    # ---------------------------------------------------------
    # WEEKLY OVERVIEW
    # ---------------------------------------------------------

    def get_week_day_labels(
        self,
    ) -> list[str]:
        week_start_day = (
            self.app.app_data
            .get("settings", {})
            .get(
                "week_start_day",
                "monday",
            )
        )

        if week_start_day == "sunday":
            return [
                self.app.t(
                    "weekday_sun_short"
                ),
                self.app.t(
                    "weekday_mon_short"
                ),
                self.app.t(
                    "weekday_tue_short"
                ),
                self.app.t(
                    "weekday_wed_short"
                ),
                self.app.t(
                    "weekday_thu_short"
                ),
                self.app.t(
                    "weekday_fri_short"
                ),
                self.app.t(
                    "weekday_sat_short"
                ),
            ]

        return [
            self.app.t(
                "weekday_mon_short"
            ),
            self.app.t(
                "weekday_tue_short"
            ),
            self.app.t(
                "weekday_wed_short"
            ),
            self.app.t(
                "weekday_thu_short"
            ),
            self.app.t(
                "weekday_fri_short"
            ),
            self.app.t(
                "weekday_sat_short"
            ),
            self.app.t(
                "weekday_sun_short"
            ),
        ]

    def get_weekly_daily_totals(
        self,
        week_sessions: list[dict[str, Any]],
    ) -> dict[str, int]:
        start_of_week = self.get_week_start_date()

        totals = {
            (
                start_of_week
                + timedelta(days=index)
            ).isoformat(): 0
            for index in range(7)
        }

        for session in week_sessions:
            if (
                self.selected_subject_id != "all"
                and str(
                    session.get(
                        "subject_id",
                        "subject_other",
                    )
                )
                != self.selected_subject_id
            ):
                continue

            session_date = self._parse_session_date(
                session.get(
                    "completed_at"
                )
            )

            if session_date is None:
                continue

            key = session_date.isoformat()

            if key not in totals:
                continue

            totals[key] += self._safe_seconds(
                session.get(
                    "duration_seconds"
                )
            )

        return totals

    def render_weekly_overview(
        self,
        week_sessions: list[dict[str, Any]],
    ) -> None:
        totals = self.get_weekly_daily_totals(
            week_sessions
        )

        labels = self.get_week_day_labels()

        values = [
            max(
                0,
                int(seconds),
            ) // 60
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

        chart = self.ids.get(
            "weekly_bar_chart"
        )

        if chart is not None:
            chart.set_data(
                labels,
                values,
            )

    # ---------------------------------------------------------
    # SUBJECT DISTRIBUTION
    # ---------------------------------------------------------

    def get_weekly_subject_totals(
        self,
        week_sessions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        totals: dict[
            str,
            dict[str, Any],
        ] = {}

        # Her subject için tekrar tekrar subjects listesini
        # taramamak için renkleri bir kere map'e dönüştür.
        subject_colors = {
            str(
                subject.get(
                    "id",
                    "subject_other",
                )
            ): str(
                subject.get(
                    "color",
                    "#A78BFA",
                )
            )
            for subject in self.app.app_data.get(
                "subjects",
                [],
            )
            if isinstance(subject, dict)
        }

        for session in week_sessions:
            subject_id = str(
                session.get(
                    "subject_id",
                    "subject_other",
                )
            )

            subject_name = str(
                session.get("subject_name")
                or self.app.t(
                    "other_subject"
                )
            )

            if subject_id not in totals:
                totals[subject_id] = {
                    "id": subject_id,
                    "name": subject_name,
                    "seconds": 0,
                    "color": subject_colors.get(
                        subject_id,
                        "#A78BFA",
                    ),
                }

            totals[subject_id]["seconds"] += (
                self._safe_seconds(
                    session.get(
                        "duration_seconds"
                    )
                )
            )

        return sorted(
            totals.values(),
            key=lambda item: item["seconds"],
            reverse=True,
        )

    def render_subject_distribution(
        self,
        week_sessions: list[dict[str, Any]],
    ) -> None:
        container = self.ids.get(
            "subject_list"
        )

        if container is None:
            return

        container.clear_widgets()

        subjects = self.get_weekly_subject_totals(
            week_sessions
        )

        total_seconds = sum(
            item["seconds"]
            for item in subjects
        )

        total_minutes = total_seconds // 60

        self.subject_total_text = self.app.t(
            "this_week_minutes"
        ).format(
            minutes=total_minutes
        )

        subject_empty = self.ids.get(
            "subject_empty"
        )

        if total_seconds <= 0:
            if subject_empty is not None:
                subject_empty.opacity = 1
                subject_empty.height = dp(34)

            return

        if subject_empty is not None:
            subject_empty.opacity = 0
            subject_empty.height = 0

        body_size = sp(
            self.app.typography(
                "body",
                self.app.layout_profile,
            )
        )

        small_body_size = sp(
            self.app.typography(
                "body_small",
                self.app.layout_profile,
            )
        )

        card_color = self.app.theme_colors[
            "card_soft"
        ]

        text_color = self.app.theme_colors[
            "text"
        ]

        muted_color = self.app.theme_colors[
            "muted"
        ]

        primary_color = self.app.theme_colors[
            "primary"
        ]

        for item in subjects:
            ratio = (
                item["seconds"]
                / total_seconds
            )

            minutes = (
                item["seconds"]
                // 60
            )

            percent = int(
                round(
                    ratio * 100
                )
            )

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
                md_bg_color=card_color,
            )

            header = MDBoxLayout(
                orientation="horizontal",
                adaptive_height=True,
                spacing=dp(8),
            )

            name_label = MDLabel(
                text=str(
                    item["name"]
                ),
                adaptive_height=True,
                bold=True,
                theme_text_color="Custom",
                text_color=text_color,
                font_size=body_size,
            )

            value_label = MDLabel(
                text=self.app.t(
                    "subject_distribution_value"
                ).format(
                    minutes=minutes,
                    percent=percent,
                ),
                size_hint_x=None,
                width=dp(115),
                halign="right",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=muted_color,
                font_size=small_body_size,
            )

            progress = MDProgressBar(
                value=ratio * 100,
                size_hint_y=None,
                height=dp(8),
                color=primary_color,
            )

            header.add_widget(
                name_label
            )

            header.add_widget(
                value_label
            )

            card.add_widget(
                header
            )

            card.add_widget(
                progress
            )

            container.add_widget(
                card
            )

    # ---------------------------------------------------------
    # RECENT SESSIONS
    # ---------------------------------------------------------

    def render_recent_sessions(
        self,
        today_sessions: list[dict[str, Any]],
    ) -> None:
        container = self.ids.get(
            "recent_list"
        )

        if container is None:
            return

        container.clear_widgets()

        sessions = sorted(
            today_sessions,
            key=lambda session: str(
                session.get(
                    "completed_at",
                    "",
                )
            ),
            reverse=True,
        )[:5]

        recent_empty = self.ids.get(
            "recent_empty"
        )

        if not sessions:
            if recent_empty is not None:
                recent_empty.opacity = 1
                recent_empty.height = dp(42)

            return

        if recent_empty is not None:
            recent_empty.opacity = 0
            recent_empty.height = 0

        body_size = sp(
            self.app.typography(
                "body",
                self.app.layout_profile,
            )
        )

        small_body_size = sp(
            self.app.typography(
                "body_small",
                self.app.layout_profile,
            )
        )

        card_color = self.app.theme_colors[
            "card_soft"
        ]

        text_color = self.app.theme_colors[
            "text"
        ]

        muted_color = self.app.theme_colors[
            "muted"
        ]

        for session in sessions:
            source = session.get(
                "source",
                "study_plan",
            )

            if source == "regular_pomodoro":
                title = self.app.t(
                    "pomodoro"
                )

                source_text = self.app.t(
                    "pomodoro"
                )

            else:
                title = str(
                    session.get(
                        "task_title"
                    )
                    or session.get(
                        "subject_name"
                    )
                    or self.app.t(
                        "focus_session"
                    )
                )

                source_text = self.app.t(
                    "study_plan"
                )

            duration_minutes = (
                self._safe_seconds(
                    session.get(
                        "duration_seconds"
                    )
                )
                // 60
            )

            away_minutes = (
                self._safe_seconds(
                    session.get(
                        "away_seconds"
                    )
                )
                // 60
            )

            completed_time = (
                self.format_session_time(
                    session.get(
                        "completed_at"
                    )
                )
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
                md_bg_color=card_color,
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
                text_color=text_color,
                font_size=body_size,
            )

            time_label = MDLabel(
                text=completed_time,
                size_hint_x=None,
                width=dp(48),
                halign="right",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=muted_color,
                font_size=small_body_size,
            )

            detail_label = MDLabel(
                text=self.app.t(
                    "recent_session_detail"
                ).format(
                    source=source_text,
                    focus=duration_minutes,
                    away=away_minutes,
                ),
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=muted_color,
                font_size=small_body_size,
            )

            title_row.add_widget(
                title_label
            )

            title_row.add_widget(
                time_label
            )

            card.add_widget(
                title_row
            )

            card.add_widget(
                detail_label
            )

            container.add_widget(
                card
            )

    # ---------------------------------------------------------
    # SUBJECT HELPERS
    # ---------------------------------------------------------

    def get_subject_color(
        self,
        subject_id: str,
    ) -> str:
        for subject in self.app.app_data.get(
            "subjects",
            [],
        ):
            if (
                isinstance(subject, dict)
                and subject.get("id")
                == subject_id
            ):
                return str(
                    subject.get(
                        "color",
                        "#A78BFA",
                    )
                )

        return "#A78BFA"

    # ---------------------------------------------------------
    # FORMAT / SAFETY
    # ---------------------------------------------------------

    @staticmethod
    def format_hours_minutes(
        seconds: int,
    ) -> str:
        seconds = max(
            0,
            int(seconds),
        )

        total_minutes = seconds // 60
        hours = total_minutes // 60
        minutes = total_minutes % 60

        return (
            f"{hours:02d}:"
            f"{minutes:02d}"
        )

    @staticmethod
    def format_session_time(
        value: Any,
    ) -> str:
        try:
            parsed = datetime.fromisoformat(
                str(value)
            )

            return parsed.strftime(
                "%H:%M"
            )

        except (
            TypeError,
            ValueError,
        ):
            return "--:--"

    @staticmethod
    def _parse_session_date(
        value: Any,
    ) -> date | None:
        try:
            return datetime.fromisoformat(
                str(value)
            ).date()

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _safe_seconds(
        value: Any,
    ) -> int:
        try:
            return max(
                0,
                int(value or 0),
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _safe_positive_int(
        value: Any,
        default: int,
    ) -> int:
        try:
            parsed = int(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

        return (
            parsed
            if parsed > 0
            else default
        )
from __future__ import annotations

from datetime import datetime
import uuid

from kivy.clock import Clock
from kivy.properties import (
    BooleanProperty,
    NumericProperty,
    StringProperty,
)

from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton


class TaskRow(MDCard):
    task_id = StringProperty("")
    subject_name = StringProperty("")
    subject_color = StringProperty("#A78BFA")

    title = StringProperty("")
    detail_text = StringProperty("")
    priority_text = StringProperty("")
    status_text = StringProperty("")

    is_completed = BooleanProperty(False)
    is_active = BooleanProperty(False)

    index = NumericProperty(0)
    total = NumericProperty(0)


class StudyPlanScreen(MDScreen):
    active_filter = StringProperty("all")

    form_status = StringProperty("")
    summary_text = StringProperty("")

    selected_subject_name = StringProperty("")
    selected_priority = StringProperty("medium")

    editing_task_id = StringProperty("")

    _clear_plan_dialog = None

    @property
    def app(self):
        from kivy.app import App

        return App.get_running_app()

    # ---------------------------------------------------------
    # LIFECYCLE
    # ---------------------------------------------------------

    def on_kv_post(self, base_widget) -> None:
        self._form_status_clear_event = None

        # Task widget'larını yeniden yaratmak yerine
        # task_id -> TaskRow olarak saklayacağız.
        self._task_rows: dict[str, TaskRow] = {}

        self.ensure_defaults()
        self.refresh_subject_spinner()
        self.refresh_priority_spinner()

    def on_enter(self) -> None:
        self.refresh_subject_spinner()
        self.render_tasks()

    def refresh_ui(self) -> None:
        self.refresh_subject_spinner()
        self.refresh_priority_spinner()
        self.render_tasks()

    # ---------------------------------------------------------
    # DEFAULTS
    # ---------------------------------------------------------

    def ensure_defaults(self) -> None:
        self.app.app_data.setdefault(
            "tasks",
            [],
        )

        self.app.app_data.setdefault(
            "sessions",
            [],
        )

        self.app.app_data.setdefault(
            "active_task_id",
            None,
        )

        self.app.app_data.setdefault(
            "queue_mode_active",
            False,
        )

        self.app.app_data.setdefault(
            "queue_task_ids",
            [],
        )

    # ---------------------------------------------------------
    # SUBJECTS
    # ---------------------------------------------------------

    def get_subjects(self) -> list[dict]:
        subjects = self.app.app_data.setdefault(
            "subjects",
            [],
        )

        if not subjects:
            subjects.append(
                {
                    "id": "subject_other",
                    "name_key": "other_subject",
                    "color": "#A78BFA",
                    "is_default": True,
                }
            )

        return subjects

    def get_subject_name(
        self,
        subject: dict,
    ) -> str:
        if (
            subject.get("is_default")
            or subject.get("id") == "subject_other"
        ):
            return self.app.t(
                "other_subject"
            )

        return str(
            subject.get(
                "name",
                self.app.t(
                    "other_subject"
                ),
            )
        )

    def get_subject_by_name(
        self,
        name: str,
    ) -> dict:
        subjects = self.get_subjects()

        for subject in subjects:
            if (
                self.get_subject_name(subject)
                == name
            ):
                return subject

        return subjects[0]

    def refresh_subject_spinner(
        self,
    ) -> None:
        if "subject_spinner" not in self.ids:
            return

        names = [
            self.get_subject_name(subject)
            for subject in self.get_subjects()
        ]

        self.ids.subject_spinner.values = names

        if not names:
            return

        if (
            self.selected_subject_name
            not in names
        ):
            self.selected_subject_name = names[0]

        self.ids.subject_spinner.text = (
            self.selected_subject_name
        )

    # ---------------------------------------------------------
    # PRIORITY
    # ---------------------------------------------------------

    def refresh_priority_spinner(
        self,
    ) -> None:
        if "priority_spinner" not in self.ids:
            return

        priority_key = (
            self.selected_priority
            or "medium"
        )

        translated_values = [
            self.app.t("low"),
            self.app.t("medium"),
            self.app.t("high"),
        ]

        self.ids.priority_spinner.values = (
            translated_values
        )

        self.ids.priority_spinner.text = (
            self.app.t(priority_key)
        )

    def change_priority(
        self,
        displayed_value: str,
    ) -> None:
        priority_map = {
            self.app.t("low"): "low",
            self.app.t("medium"): "medium",
            self.app.t("high"): "high",
        }

        self.selected_priority = (
            priority_map.get(
                displayed_value,
                "medium",
            )
        )

    # ---------------------------------------------------------
    # FORM STATUS
    # ---------------------------------------------------------

    def _clear_form_status(
        self,
        _dt,
    ) -> None:
        self.form_status = ""
        self._form_status_clear_event = None

    def _schedule_form_status_clear(
        self,
    ) -> None:
        if self._form_status_clear_event:
            self._form_status_clear_event.cancel()

        self._form_status_clear_event = (
            Clock.schedule_once(
                self._clear_form_status,
                5,
            )
        )

    # ---------------------------------------------------------
    # ADD / UPDATE
    # ---------------------------------------------------------

    def add_or_update_task(
        self,
    ) -> None:
        title = (
            self.ids.task_title.text.strip()
            or self.app.t("new_task")
        )

        try:
            focus_duration = int(
                self.ids.focus_duration.text.strip()
            )

            break_minutes = int(
                self.ids.break_minutes.text.strip()
            )

        except ValueError:
            self.form_status = self.app.t(
                "durations_must_be_numbers"
            )
            return

        if (
            focus_duration <= 0
            or break_minutes < 0
        ):
            self.form_status = self.app.t(
                "invalid_focus_break_duration"
            )
            return

        subject = self.get_subject_by_name(
            self.ids.subject_spinner.text
        )

        priority = (
            self.selected_priority
            or "medium"
        )

        if self.editing_task_id:
            task = self.get_task(
                self.editing_task_id
            )

            if task is None:
                self.cancel_edit()
                return

            task.update(
                {
                    "subject_id": subject.get(
                        "id",
                        "subject_other",
                    ),
                    "subject_name": (
                        ""
                        if subject.get(
                            "is_default"
                        )
                        else subject.get(
                            "name",
                            "",
                        )
                    ),
                    "title": title,
                    "focus_duration": focus_duration,
                    "break_minutes": break_minutes,
                    "priority": priority,
                    "status": "pending",
                    "hidden_from_plan": False,
                    "hidden_from_completed": False,
                }
            )

            self.form_status = self.app.t(
                "task_updated"
            )

        else:
            task = {
                "id": (
                    f"task_"
                    f"{uuid.uuid4().hex[:8]}"
                ),
                "subject_id": subject.get(
                    "id",
                    "subject_other",
                ),
                "subject_name": (
                    ""
                    if subject.get(
                        "is_default"
                    )
                    else subject.get(
                        "name",
                        "",
                    )
                ),
                "title": title,
                "focus_duration": focus_duration,
                "break_minutes": break_minutes,
                "priority": priority,
                "status": "pending",
                "hidden_from_plan": False,
                "hidden_from_completed": False,
            }

            self.app.app_data[
                "tasks"
            ].append(task)

            self.form_status = self.app.t(
                "task_added"
            )

        self._schedule_form_status_clear()

        self.app.save_app_data()

        self.clear_form()
        self.render_tasks()

    # ---------------------------------------------------------
    # TASK HELPERS
    # ---------------------------------------------------------

    def get_task(
        self,
        task_id: str,
    ) -> dict | None:
        return next(
            (
                task
                for task in self.app.app_data.get(
                    "tasks",
                    [],
                )
                if task.get("id") == task_id
            ),
            None,
        )

    def clear_form(self) -> None:
        self.editing_task_id = ""

        self.ids.task_title.text = ""
        self.ids.focus_duration.text = "25"
        self.ids.break_minutes.text = "5"

        self.selected_priority = "medium"

        self.refresh_priority_spinner()
        self.refresh_subject_spinner()

    def cancel_edit(self) -> None:
        self.clear_form()
        self.form_status = ""

    def edit_task(
        self,
        task_id: str,
    ) -> None:
        task = self.get_task(
            task_id
        )

        if task is None:
            return

        self.editing_task_id = task_id

        self.ids.task_title.text = str(
            task.get(
                "title",
                "",
            )
        )

        self.ids.focus_duration.text = str(
            task.get(
                "focus_duration",
                25,
            )
        )

        self.ids.break_minutes.text = str(
            task.get(
                "break_minutes",
                5,
            )
        )

        subject_id = task.get(
            "subject_id",
            "subject_other",
        )

        subject = next(
            (
                item
                for item in self.get_subjects()
                if item.get("id") == subject_id
            ),
            None,
        )

        if subject is not None:
            self.selected_subject_name = (
                self.get_subject_name(
                    subject
                )
            )
        else:
            self.selected_subject_name = (
                self.app.t(
                    "other_subject"
                )
            )

        self.refresh_subject_spinner()

        self.selected_priority = task.get(
            "priority",
            "medium",
        )

        self.refresh_priority_spinner()

        self.form_status = self.app.t(
            "edit_mode"
        )

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete_task(
        self,
        task_id: str,
    ) -> None:
        active_task_id = (
            self.app.app_data.get(
                "active_task_id"
            )
        )

        self.app.app_data["tasks"] = [
            task
            for task in self.app.app_data.get(
                "tasks",
                [],
            )
            if task.get("id") != task_id
        ]

        if active_task_id == task_id:
            self.app.app_data[
                "active_task_id"
            ] = None

        # Artık kullanılmayacak widget'ı
        # cache'den de kaldır.
        self._task_rows.pop(
            task_id,
            None,
        )

        self.app.save_app_data()
        self.render_tasks()

    # ---------------------------------------------------------
    # COMPLETE
    # ---------------------------------------------------------

    def toggle_complete(
        self,
        task_id: str,
    ) -> None:
        task = self.get_task(
            task_id
        )

        if task is None:
            return

        if task.get("status") == "completed":
            task["status"] = "pending"
            task.pop(
                "completed_at",
                None,
            )

            self.remove_task_sessions(
                task_id
            )

        else:
            task["status"] = "completed"

            task["completed_at"] = (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )

            self.log_completion(
                task
            )

            if (
                self.app.app_data.get(
                    "active_task_id"
                )
                == task_id
            ):
                self.app.app_data[
                    "active_task_id"
                ] = None

        self.app.save_app_data()
        self.render_tasks()

    # ---------------------------------------------------------
    # SESSIONS
    # ---------------------------------------------------------

    def log_completion(
        self,
        task: dict,
    ) -> None:
        sessions = (
            self.app.app_data.setdefault(
                "sessions",
                [],
            )
        )

        task_id = task.get(
            "id"
        )

        for session in sessions:
            if (
                session.get("task_id")
                == task_id
                and session.get("source")
                == "study_plan"
            ):
                return

        sessions.append(
            {
                "id": (
                    f"session_"
                    f"{uuid.uuid4().hex[:8]}"
                ),
                "task_id": task_id,
                "task_title": task.get(
                    "title",
                    self.app.t(
                        "new_task"
                    ),
                ),
                "subject_id": task.get(
                    "subject_id",
                    "subject_other",
                ),
                "subject_name": task.get(
                    "subject_name",
                    self.app.t(
                        "other_subject"
                    ),
                ),
                "mode": "focus",
                "source": "study_plan",
                "duration_seconds": (
                    task.get(
                        "focus_duration",
                        0,
                    )
                    * 60
                ),
                "away_seconds": 0,
                "completed_at": (
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                ),
            }
        )

    def remove_task_sessions(
        self,
        task_id: str,
    ) -> None:
        self.app.app_data["sessions"] = [
            session
            for session in self.app.app_data.get(
                "sessions",
                [],
            )
            if not (
                session.get("task_id")
                == task_id
                and session.get("source")
                == "study_plan"
            )
        ]

    # ---------------------------------------------------------
    # DUPLICATE
    # ---------------------------------------------------------

    def duplicate_task(
        self,
        task_id: str,
    ) -> None:
        task = self.get_task(
            task_id
        )

        if (
            task is None
            or task.get("status")
            == "completed"
        ):
            return

        copy = dict(task)

        copy["id"] = (
            f"task_"
            f"{uuid.uuid4().hex[:8]}"
        )

        copy["status"] = "pending"

        copy.pop(
            "completed_at",
            None,
        )

        tasks = self.app.app_data[
            "tasks"
        ]

        index = tasks.index(
            task
        )

        tasks.insert(
            index + 1,
            copy,
        )

        self.app.save_app_data()
        self.render_tasks()

    # ---------------------------------------------------------
    # MOVE
    # ---------------------------------------------------------

    def move_task(
        self,
        task_id: str,
        direction: int,
    ) -> None:
        visible_tasks = (
            self.get_visible_tasks()
        )

        index = next(
            (
                index
                for index, task
                in enumerate(
                    visible_tasks
                )
                if task.get("id")
                == task_id
            ),
            None,
        )

        if index is None:
            return

        target_index = (
            index + direction
        )

        if (
            target_index < 0
            or target_index
            >= len(visible_tasks)
        ):
            return

        tasks = self.app.app_data[
            "tasks"
        ]

        current_task = (
            visible_tasks[index]
        )

        target_task = (
            visible_tasks[
                target_index
            ]
        )

        current_global_index = (
            tasks.index(
                current_task
            )
        )

        target_global_index = (
            tasks.index(
                target_task
            )
        )

        tasks[
            current_global_index
        ], tasks[
            target_global_index
        ] = (
            tasks[target_global_index],
            tasks[current_global_index],
        )

        self.app.save_app_data()
        self.render_tasks()

    # ---------------------------------------------------------
    # START TASK
    # ---------------------------------------------------------

    def start_task(
        self,
        task_id: str,
    ) -> None:
        task = self.get_task(
            task_id
        )

        if (
            task is None
            or task.get("status")
            == "completed"
        ):
            return

        self.app.app_data[
            "active_task_id"
        ] = task_id

        self.app.save_app_data()

        # Study Plan zaten ekrandan çıkacağı için
        # burada render_tasks() gereksiz.
        if hasattr(
            self.app,
            "show_page",
        ):
            self.app.show_page(
                "focus"
            )

    # ---------------------------------------------------------
    # START PLAN
    # ---------------------------------------------------------

    def start_plan(self) -> None:
        pending = [
            task
            for task in self.app.app_data.get(
                "tasks",
                [],
            )
            if (
                task.get("status")
                != "completed"
            )
        ]

        if not pending:
            self.form_status = self.app.t(
                "no_tasks_to_start"
            )
            return

        self.app.app_data[
            "queue_mode_active"
        ] = True

        self.app.app_data[
            "queue_task_ids"
        ] = [
            task.get("id")
            for task in pending
        ]

        self.app.app_data[
            "active_task_id"
        ] = pending[0].get(
            "id"
        )

        self.app.save_app_data()

        self.form_status = self.app.t(
            "study_plan_started"
        )

        # Burada da Study Plan yeniden çizilmeden
        # doğrudan Focus'a geçilir.
        if hasattr(
            self.app,
            "show_page",
        ):
            self.app.show_page(
                "focus"
            )

    # ---------------------------------------------------------
    # FILTER
    # ---------------------------------------------------------

    def set_filter(
        self,
        value: str,
    ) -> None:
        if (
            value
            == self.active_filter
        ):
            return

        self.active_filter = value
        self.render_tasks()

    def get_visible_tasks(
        self,
    ) -> list[dict]:
        tasks = [
            task
            for task in self.app.app_data.get(
                "tasks",
                [],
            )
            if not task.get(
                "hidden_from_plan",
                False,
            )
        ]

        active_id = (
            self.app.app_data.get(
                "active_task_id"
            )
        )

        if (
            self.active_filter
            == "pending"
        ):
            return [
                task
                for task in tasks
                if (
                    task.get("status")
                    != "completed"
                    and task.get("id")
                    != active_id
                )
            ]

        if (
            self.active_filter
            == "active"
        ):
            return [
                task
                for task in tasks
                if (
                    task.get("id")
                    == active_id
                    and task.get("status")
                    != "completed"
                )
            ]

        if (
            self.active_filter
            == "completed"
        ):
            return [
                task
                for task in tasks
                if (
                    task.get("status")
                    == "completed"
                )
            ]

        return tasks

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    def render_tasks(self) -> None:
        if "task_list" not in self.ids:
            return

        container = self.ids.task_list

        visible_tasks = (
            self.get_visible_tasks()
        )

        active_id = (
            self.app.app_data.get(
                "active_task_id"
            )
        )

        all_tasks = (
            self.app.app_data.get(
                "tasks",
                [],
            )
        )

        # -----------------------------------------------
        # SUMMARY
        # -----------------------------------------------

        pending_count = 0
        active_count = 0
        completed_count = 0
        total_minutes = 0

        for task in all_tasks:
            task_id = task.get(
                "id"
            )

            if (
                task.get("status")
                == "completed"
            ):
                completed_count += 1
                continue

            total_minutes += int(
                task.get(
                    "focus_duration",
                    0,
                )
                or 0
            )

            if task_id == active_id:
                active_count += 1
            else:
                pending_count += 1

        self.summary_text = self.app.t(
            "study_plan_summary"
        ).format(
            pending=pending_count,
            active=active_count,
            completed=completed_count,
            minutes=total_minutes,
        )

        # -----------------------------------------------
        # EMPTY STATE
        # -----------------------------------------------

        if not visible_tasks:
            container.clear_widgets()

            self.ids.empty_label.opacity = 1
            return

        self.ids.empty_label.opacity = 0

        # -----------------------------------------------
        # SUBJECT COLOR LOOKUP
        # -----------------------------------------------

        subject_colors = {
            subject.get("id"): subject.get(
                "color",
                "#A78BFA",
            )
            for subject in self.get_subjects()
        }

        priority_texts = {
            "low": self.app.t("low"),
            "medium": self.app.t("medium"),
            "high": self.app.t("high"),
        }

        default_priority_text = (
            priority_texts["medium"]
        )

        completed_text = self.app.t(
            "completed"
        )

        active_text = self.app.t(
            "active"
        )

        waiting_text = self.app.t(
            "waiting"
        )

        other_subject_text = (
            self.app.t(
                "other_subject"
            )
        )

        task_detail_template = (
            self.app.t(
                "task_detail"
            )
        )

        # -----------------------------------------------
        # WIDGET REUSE
        # -----------------------------------------------

        # Parent'tan ayırıyoruz fakat TaskRow objelerini
        # yok etmiyoruz; cache'de kalıyorlar.
        container.clear_widgets()

        visible_task_ids = set()

        total_visible = len(
            visible_tasks
        )

        for index, task in enumerate(
            visible_tasks
        ):
            task_id = str(
                task.get(
                    "id",
                    "",
                )
            )

            visible_task_ids.add(
                task_id
            )

            row = self._task_rows.get(
                task_id
            )

            if row is None:
                row = TaskRow(
                    task_id=task_id
                )

                self._task_rows[
                    task_id
                ] = row

            subject_id = task.get(
                "subject_id",
                "subject_other",
            )

            row.subject_name = str(
                task.get(
                    "subject_name"
                )
                or other_subject_text
            )

            row.subject_color = (
                subject_colors.get(
                    subject_id,
                    "#A78BFA",
                )
            )

            row.title = str(
                task.get(
                    "title",
                    "",
                )
            )

            row.detail_text = (
                task_detail_template.format(
                    focus=task.get(
                        "focus_duration",
                        0,
                    ),
                    break_minutes=task.get(
                        "break_minutes",
                        0,
                    ),
                )
            )

            row.priority_text = (
                priority_texts.get(
                    task.get(
                        "priority"
                    ),
                    default_priority_text,
                )
            )

            is_completed = (
                task.get("status")
                == "completed"
            )

            is_active = (
                task_id
                == active_id
                and not is_completed
            )

            if is_completed:
                status_text = (
                    completed_text
                )
            elif is_active:
                status_text = (
                    active_text
                )
            else:
                status_text = (
                    waiting_text
                )

            row.status_text = (
                status_text
            )

            row.is_completed = (
                is_completed
            )

            row.is_active = (
                is_active
            )

            row.index = index
            row.total = total_visible

            container.add_widget(
                row
            )

        # Gerçek task listesinde artık bulunmayan
        # eski cache objelerini ara sıra temizle.
        existing_task_ids = {
            str(
                task.get(
                    "id",
                    "",
                )
            )
            for task in all_tasks
        }

        stale_ids = (
            set(self._task_rows)
            - existing_task_ids
        )

        for stale_id in stale_ids:
            self._task_rows.pop(
                stale_id,
                None,
            )

    #----------------------------------------------------------
    # CLEAR PLAN
    #---------------------------------------------------------- 
    def open_clear_plan_dialog(self) -> None:
        if self._clear_plan_dialog is None:
            self._clear_plan_dialog = MDDialog(
                title=self.app.t("clear_study_plan"),
                text=self.app.t("clear_study_plan_confirmation"),
                buttons=[
                    MDFlatButton(
                        text=self.app.t("cancel"),
                        theme_text_color="Custom",
                        text_color=self.app.theme_colors["muted"],
                        on_release=lambda *_: self._clear_plan_dialog.dismiss(),
                    ),
                    MDRaisedButton(
                        text=self.app.t("clear"),
                        md_bg_color=self.app.theme_colors["red"],
                        on_release=self.confirm_clear_study_plan,
                    ),
                ],
            )

        self._clear_plan_dialog.open()


    def confirm_clear_study_plan(self, *_args) -> None:
        self.app.app_data["tasks"] = []
        self.app.app_data["active_task_id"] = None
        self.app.app_data["queue_mode_active"] = False
        self.app.app_data["queue_task_ids"] = []

        self._task_rows.clear()

        self.app.save_app_data()
        self.render_tasks()

        self.form_status = self.app.t("study_plan_cleared")

        if self._clear_plan_dialog is not None:
            self._clear_plan_dialog.dismiss()

    def clear_completed_tasks(self) -> None:
        completed_ids = {
            task.get("id")
            for task in self.app.app_data.get("tasks", [])
            if task.get("status") == "completed"
        }

        if not completed_ids:
            self.form_status = self.app.t("no_completed_tasks")
            return

        self.app.app_data["tasks"] = [
            task
            for task in self.app.app_data.get("tasks", [])
            if task.get("id") not in completed_ids
        ]

        for task_id in completed_ids:
            self._task_rows.pop(task_id, None)

        self.app.save_app_data()
        self.render_tasks()

        self.form_status = self.app.t("completed_tasks_cleared")

    # ---------------------------------------------------------
    # SUBJECT COLOR
    # ---------------------------------------------------------

    def get_subject_color(
        self,
        subject_id: str,
    ) -> str:
        for subject in self.get_subjects():
            if (
                subject.get("id")
                == subject_id
            ):
                return str(
                    subject.get(
                        "color",
                        "#A78BFA",
                    )
                )

        return "#A78BFA"
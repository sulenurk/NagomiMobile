from __future__ import annotations

from kivy.clock import Clock

from datetime import datetime
import uuid

from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen


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

    @property
    def app(self):
        from kivy.app import App
        return App.get_running_app()

    def on_kv_post(self, base_widget):
        self._form_status_clear_event = None
        self.ensure_defaults()
        self.refresh_subject_spinner()
        self.render_tasks()

    def on_enter(self):
        self.refresh_subject_spinner()
        self.render_tasks()

    def refresh_ui(self) -> None:
        self.refresh_subject_spinner()
        self.refresh_priority_spinner()
        self.render_tasks()

    def ensure_defaults(self):
        self.app.app_data.setdefault("tasks", [])
        self.app.app_data.setdefault("sessions", [])
        self.app.app_data.setdefault("active_task_id", None)
        self.app.app_data.setdefault("queue_mode_active", False)
        self.app.app_data.setdefault("queue_task_ids", [])

    def get_subjects(self):
        subjects = self.app.app_data.setdefault("subjects", [])
        if not subjects:
            subjects.append({
                "id": "subject_other",
                "name_key": "other_subject",
                "color": "#A78BFA",
                "is_default": True,
            })
        return subjects

    def get_subject_name(self, subject):
        if subject.get("is_default") or subject.get("id") == "subject_other":
            return self.app.t("other_subject")
        return subject.get("name", self.app.t("other_subject"))

    def get_subject_by_name(self, name):
        for subject in self.get_subjects():
            if self.get_subject_name(subject) == name:
                return subject
        return self.get_subjects()[0]

    def refresh_priority_spinner(self) -> None:
        if "priority_spinner" not in self.ids:
            return

        priority_key = self.selected_priority or "medium"

        translated_values = [
            self.app.t("low"),
            self.app.t("medium"),
            self.app.t("high"),
        ]

        self.ids.priority_spinner.values = translated_values
        self.ids.priority_spinner.text = self.app.t(priority_key)

    def refresh_subject_spinner(self):
        if "subject_spinner" not in self.ids:
            return
        names = [self.get_subject_name(s) for s in self.get_subjects()]
        self.ids.subject_spinner.values = names
        if self.selected_subject_name not in names:
            self.selected_subject_name = names[0]
        self.ids.subject_spinner.text = self.selected_subject_name

    def _clear_form_status(self, dt):
        self.form_status = ""
        self._form_status_clear_event = None

    def add_or_update_task(self):
        title = self.ids.task_title.text.strip() or self.app.t("new_task")

        try:
            focus_duration = int(self.ids.focus_duration.text.strip())
            break_minutes = int(self.ids.break_minutes.text.strip())
        except ValueError:
            self.form_status = self.app.t("durations_must_be_numbers")
            return

        if focus_duration <= 0 or break_minutes < 0:
            self.form_status = self.app.t("invalid_focus_break_duration")
            return

        subject = self.get_subject_by_name(self.ids.subject_spinner.text)
        priority = self.selected_priority

        if self.editing_task_id:
            task = self.get_task(self.editing_task_id)

            if not task:
                self.cancel_edit()
                return

            task.update({
                "subject_id": subject.get("id", "subject_other"),
                "subject_name": (
                    ""
                    if subject.get("is_default")
                    else subject.get("name", "")
                ),
                "title": title,
                "focus_duration": focus_duration,
                "break_minutes": break_minutes,
                "priority": priority,
                "status": "pending",
                "hidden_from_plan": False,
                "hidden_from_completed": False,
            })

            self.form_status = self.app.t("task_updated")

        else:
            self.app.app_data["tasks"].append({
                "id": f"task_{uuid.uuid4().hex[:8]}",
                "subject_id": subject.get("id", "subject_other"),
                "subject_name": (
                    ""
                    if subject.get("is_default")
                    else subject.get("name", "")
                ),
                "title": title,
                "focus_duration": focus_duration,
                "break_minutes": break_minutes,
                "priority": priority,
                "status": "pending",
                "hidden_from_plan": False,
                "hidden_from_completed": False,
            })

            self.form_status = self.app.t("task_added")

            if self._form_status_clear_event:
                self._form_status_clear_event.cancel()

            self._form_status_clear_event = Clock.schedule_once(
                self._clear_form_status,
                5
            )

        self.app.save_app_data()
        self.clear_form()
        self.render_tasks()

    def change_priority(self, displayed_value: str) -> None:
        priority_map = {
            self.app.t("low"): "low",
            self.app.t("medium"): "medium",
            self.app.t("high"): "high",
        }

        self.selected_priority = priority_map.get(
            displayed_value,
            "medium",
        )

    def get_task(self, task_id):
        return next(
            (task for task in self.app.app_data.get("tasks", []) if task.get("id") == task_id),
            None,
        )

    def clear_form(self):
        self.editing_task_id = ""
        self.ids.task_title.text = ""
        self.ids.focus_duration.text = "25"
        self.ids.break_minutes.text = "5"
        self.selected_priority = "medium"
        self.refresh_priority_spinner()
        self.refresh_subject_spinner()

    def cancel_edit(self):
        self.clear_form()
        self.form_status = ""

    def edit_task(self, task_id):
        task = self.get_task(task_id)
        if not task:
            return

        self.editing_task_id = task_id
        self.ids.task_title.text = task.get("title", "")
        self.ids.focus_duration.text = str(task.get("focus_duration", 25))
        self.ids.break_minutes.text = str(task.get("break_minutes", 5))
        self.selected_subject_name = task.get("subject_name", self.app.t("other_subject"))
        self.refresh_subject_spinner()
        self.selected_priority = task.get(
            "priority",
            "medium",
        )
        self.refresh_priority_spinner()
        self.form_status = self.app.t("edit_mode")

    def delete_task(self, task_id):
        active_task_id = self.app.app_data.get("active_task_id")
        self.app.app_data["tasks"] = [
            t for t in self.app.app_data.get("tasks", [])
            if t.get("id") != task_id
        ]
        if active_task_id == task_id:
            self.app.app_data["active_task_id"] = None
        self.app.save_app_data()
        self.render_tasks()

    def toggle_complete(self, task_id):
        task = self.get_task(task_id)
        if not task:
            return

        if task.get("status") == "completed":
            task["status"] = "pending"
            task.pop("completed_at", None)
            self.remove_task_sessions(task_id)
        else:
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat(timespec="seconds")
            self.log_completion(task)
            if self.app.app_data.get("active_task_id") == task_id:
                self.app.app_data["active_task_id"] = None

        self.app.save_app_data()
        self.render_tasks()

    def log_completion(self, task):
        sessions = self.app.app_data.setdefault("sessions", [])
        if any(
            s.get("task_id") == task.get("id") and s.get("source") == "study_plan"
            for s in sessions
        ):
            return

        sessions.append({
            "id": f"session_{uuid.uuid4().hex[:8]}",
            "task_id": task.get("id"),
            "task_title": task.get(
                "title",
                self.app.t("new_task"),
            ),
            "subject_id": task.get("subject_id", "subject_other"),
            "subject_name": task.get("subject_name", self.app.t("other_subject")),
            "mode": "focus",
            "source": "study_plan",
            "duration_seconds": task.get("focus_duration", 0) * 60,
            "away_seconds": 0,
            "completed_at": datetime.now().isoformat(timespec="seconds"),
        })

    def remove_task_sessions(self, task_id):
        self.app.app_data["sessions"] = [
            s for s in self.app.app_data.get("sessions", [])
            if not (s.get("task_id") == task_id and s.get("source") == "study_plan")
        ]

    def duplicate_task(self, task_id):
        task = self.get_task(task_id)
        if not task or task.get("status") == "completed":
            return

        copy = dict(task)
        copy["id"] = f"task_{uuid.uuid4().hex[:8]}"
        copy["status"] = "pending"
        copy.pop("completed_at", None)

        tasks = self.app.app_data["tasks"]
        index = tasks.index(task)
        tasks.insert(index + 1, copy)
        self.app.save_app_data()
        self.render_tasks()

    def move_task(self, task_id, direction):
        visible = self.get_visible_tasks()
        index = next((i for i, t in enumerate(visible) if t.get("id") == task_id), None)
        if index is None:
            return
        target = index + direction
        if target < 0 or target >= len(visible):
            return

        tasks = self.app.app_data["tasks"]
        a = tasks.index(visible[index])
        b = tasks.index(visible[target])
        tasks[a], tasks[b] = tasks[b], tasks[a]
        self.app.save_app_data()
        self.render_tasks()

    def start_task(self, task_id):
        task = self.get_task(task_id)
        if not task or task.get("status") == "completed":
            return

        self.app.app_data["active_task_id"] = task_id
        self.app.save_app_data()
        self.render_tasks()

        if hasattr(self.app, "show_page") and self.app.root.ids.screen_manager.has_screen("focus"):
            self.app.show_page("focus")
        else:
            self.form_status = self.app.t("task_activated")

    def start_plan(self):
        pending = [
            t for t in self.app.app_data.get("tasks", [])
            if t.get("status") != "completed"
        ]
        if not pending:
            self.form_status = self.app.t("no_tasks_to_start")
            return

        self.app.app_data["queue_mode_active"] = True
        self.app.app_data["queue_task_ids"] = [t.get("id") for t in pending]
        self.app.app_data["active_task_id"] = pending[0].get("id")
        self.app.save_app_data()
        self.form_status = self.app.t("study_plan_started")
        self.render_tasks()

        if hasattr(self.app, "show_page"):
            self.app.show_page("focus")

    def set_filter(self, value):
        self.active_filter = value
        self.render_tasks()

    def get_visible_tasks(self):
        tasks = [
            t for t in self.app.app_data.get("tasks", [])
            if not t.get("hidden_from_plan", False)
        ]
        active_id = self.app.app_data.get("active_task_id")

        if self.active_filter == "pending":
            return [t for t in tasks if t.get("status") != "completed" and t.get("id") != active_id]
        if self.active_filter == "active":
            return [t for t in tasks if t.get("id") == active_id and t.get("status") != "completed"]
        if self.active_filter == "completed":
            return [t for t in tasks if t.get("status") == "completed"]
        return tasks

    def render_tasks(self):
        if "task_list" not in self.ids:
            return

        container = self.ids.task_list
        container.clear_widgets()
        tasks = self.get_visible_tasks()
        active_id = self.app.app_data.get("active_task_id")

        all_tasks = self.app.app_data.get("tasks", [])
        pending = sum(1 for t in all_tasks if t.get("status") != "completed" and t.get("id") != active_id)
        active = sum(1 for t in all_tasks if t.get("id") == active_id and t.get("status") != "completed")
        completed = sum(1 for t in all_tasks if t.get("status") == "completed")
        total_minutes = sum(t.get("focus_duration", 0) for t in all_tasks if t.get("status") != "completed")
        self.summary_text = self.app.t("study_plan_summary").format(
            pending=pending,
            active=active,
            completed=completed,
            minutes=total_minutes,
        )

        if not tasks:
            self.ids.empty_label.opacity = 1
            return

        self.ids.empty_label.opacity = 0

        for index, task in enumerate(tasks):
            row = TaskRow(
                task_id=task.get("id", ""),
                subject_name=task.get(
                    "subject_name",
                    self.app.t("other_subject"),
                ),
                subject_color=self.get_subject_color(
                    task.get("subject_id")
                ),
                title=task.get("title", ""),
                detail_text=self.app.t("task_detail").format(
                    focus=task.get("focus_duration", 0),
                    break_minutes=task.get("break_minutes", 0),
                ),
                priority_text={
                    "low": self.app.t("low"),
                    "medium": self.app.t("medium"),
                    "high": self.app.t("high"),
                }.get(
                    task.get("priority"),
                    self.app.t("medium"),
                ),
                status_text=(
                    self.app.t("completed")
                    if task.get("status") == "completed"
                    else (
                        self.app.t("active")
                        if task.get("id") == active_id
                        else self.app.t("waiting")
                    )
                ),
                is_completed=task.get("status") == "completed",
                is_active=task.get("id") == active_id,
                index=index,
                total=len(tasks),
            )

            container.add_widget(row)

    def get_subject_color(self, subject_id):
        for subject in self.get_subjects():
            if subject.get("id") == subject_id:
                return subject.get("color", "#A78BFA")
        return "#A78BFA"

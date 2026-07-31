from __future__ import annotations

import uuid

from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty
from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen

SUBJECT_COLOR_PALETTE = [
    "#A78BFA",
    "#F472B6",
    "#60A5FA",
    "#34D399",
    "#FBBF24",
    "#FB7185",
    "#22D3EE",
    "#C084FC",
]


class ColorDot(MDCard):
    color_hex = StringProperty("#A78BFA")
    selected_color = StringProperty("#A78BFA")

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            parent = self.parent

            while parent is not None and not hasattr(parent, "select_color"):
                parent = parent.parent

            if parent is not None:
                parent.select_color(self.color_hex)

            return True

        return super().on_touch_down(touch)


class SubjectRow(MDCard):
    subject_id = StringProperty("")
    subject_name = StringProperty("")
    subject_color = StringProperty("#A78BFA")
    is_default = False


class SubjectsScreen(MDScreen):
    selected_color = StringProperty("#A78BFA")
    palette = ListProperty(SUBJECT_COLOR_PALETTE)
    status_text = StringProperty("")

    @property
    def app(self):
        from kivy.app import App
        return App.get_running_app()

    def on_kv_post(self, base_widget):
        self.ensure_subjects_data()
        self.selected_color = self.get_next_subject_color()
        self.render_subjects()

    def on_enter(self):
        self.render_subjects()

    def ensure_subjects_data(self):
        subjects = self.app.app_data.setdefault("subjects", [])

        default_subject = next(
            (
                subject
                for subject in subjects
                if subject.get("id") == "subject_other"
                or subject.get("is_default")
            ),
            None,
        )

        if default_subject is None:
            subjects.insert(
                0,
                {
                    "id": "subject_other",
                    "name_key": "other_subject",
                    "color": "#A78BFA",
                    "is_default": True,
                },
            )
        else:
            default_subject["id"] = "subject_other"
            default_subject["name_key"] = "other_subject"
            default_subject["is_default"] = True
            default_subject.setdefault("color", "#A78BFA")
            default_subject.pop("name", None)

        if hasattr(self.app, "data_path"):
            self.app.save_app_data()

    def get_next_subject_color(self) -> str:
        used_colors = {
            subject.get("color")
            for subject in self.app.app_data.get("subjects", [])
        }

        for color in self.palette:
            if color not in used_colors:
                return color

        subject_count = len(self.app.app_data.get("subjects", []))
        return self.palette[subject_count % len(self.palette)]

    def select_color(self, color: str):
        self.selected_color = color

    def add_subject(self):
        name = self.ids.subject_name.text.strip()

        if not name:
            self.status_text = "Ders adı boş bırakılamaz."
            self.ids.subject_name.focus = True
            return

        subjects = self.app.app_data.setdefault("subjects", [])

        duplicate_exists = any(
            self.get_subject_name(subject).casefold() == name.casefold()
            for subject in subjects
        )

        if duplicate_exists:
            self.status_text = "Bu isimde bir ders zaten var."
            return

        subjects.append(
            {
                "id": f"subject_{uuid.uuid4().hex[:8]}",
                "name": name,
                "color": self.selected_color,
                "is_default": False,
            }
        )

        self.app.save_app_data()
        self.ids.subject_name.text = ""
        self.selected_color = self.get_next_subject_color()
        self.status_text = "Ders eklendi."
        self.render_subjects()

    def delete_subject(self, subject_id: str):
        subject = self.get_subject_by_id(subject_id)

        if not subject or subject.get("is_default"):
            return

        self.app.app_data["subjects"] = [
            item
            for item in self.app.app_data.get("subjects", [])
            if item.get("id") != subject_id
        ]

        self.reassign_deleted_subject_tasks(subject_id)
        self.reassign_deleted_subject_sessions(subject_id)

        self.app.save_app_data()
        self.status_text = "Ders silindi."
        self.render_subjects()

    def change_subject_color(self, subject_id: str, color: str):
        subject = self.get_subject_by_id(subject_id)

        if not subject:
            return

        subject["color"] = color
        self.app.save_app_data()
        self.render_subjects()

    def get_subject_by_id(self, subject_id: str):
        return next(
            (
                subject
                for subject in self.app.app_data.get("subjects", [])
                if subject.get("id") == subject_id
            ),
            None,
        )

    def get_subject_name(self, subject: dict) -> str:
        if subject.get("is_default") or subject.get("id") == "subject_other":
            return self.app.t("other_subject")

        return subject.get("name", self.app.t("other_subject"))

    def reassign_deleted_subject_tasks(self, deleted_subject_id: str):
        for task in self.app.app_data.get("tasks", []):
            if task.get("subject_id") == deleted_subject_id:
                task["subject_id"] = "subject_other"
                task["subject_name"] = self.app.t("other_subject")

    def reassign_deleted_subject_sessions(self, deleted_subject_id: str):
        for session in self.app.app_data.get("sessions", []):
            if session.get("subject_id") == deleted_subject_id:
                session["subject_id"] = "subject_other"
                session["subject_name"] = self.app.t("other_subject")

    def render_subjects(self):
        if "subjects_list" not in self.ids:
            return

        container = self.ids.subjects_list
        container.clear_widgets()

        self.ensure_subjects_data()

        for subject in self.app.app_data.get("subjects", []):
            row = SubjectRow(
                subject_id=subject.get("id", ""),
                subject_name=self.get_subject_name(subject),
                subject_color=subject.get("color", "#A78BFA"),
            )
            row.is_default = bool(subject.get("is_default"))
            container.add_widget(row)

    def cycle_subject_color(self, subject_id: str):
        subject = self.get_subject_by_id(subject_id)

        if not subject:
            return

        current_color = subject.get("color", self.palette[0])

        try:
            current_index = self.palette.index(current_color)
        except ValueError:
            current_index = -1

        next_color = self.palette[(current_index + 1) % len(self.palette)]
        self.change_subject_color(subject_id, next_color)

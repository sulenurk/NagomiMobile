from __future__ import annotations

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import (
    BooleanProperty,
    NumericProperty,
    StringProperty,
)


class ResponsiveMixin:
    screen_width = NumericProperty(360)
    screen_height = NumericProperty(800)

    screen_width_dp = NumericProperty(360)
    screen_height_dp = NumericProperty(800)
    shortest_side_dp = NumericProperty(360)

    layout_profile = StringProperty(
        "phone_portrait"
    )

    is_landscape = BooleanProperty(False)
    is_portrait = BooleanProperty(True)

    is_compact_phone = BooleanProperty(False)
    is_phone = BooleanProperty(True)
    is_tablet = BooleanProperty(False)

    def setup_responsive_layout(self) -> None:
        self.update_screen_metrics()

        Window.bind(
            size=self.update_screen_metrics,
        )

    def update_screen_metrics(
        self,
        *_args,
    ) -> None:
        self.screen_width = float(Window.width)
        self.screen_height = float(Window.height)

        density = dp(1)

        self.screen_width_dp = (
            self.screen_width / density
        )
        self.screen_height_dp = (
            self.screen_height / density
        )

        self.shortest_side_dp = min(
            self.screen_width_dp,
            self.screen_height_dp,
        )

        self.is_landscape = (
            self.screen_width_dp
            > self.screen_height_dp
        )

        self.is_portrait = not self.is_landscape

        self.is_tablet = (
            self.shortest_side_dp >= 600
        )

        self.is_phone = not self.is_tablet

        self.is_compact_phone = (
            self.is_phone
            and self.is_portrait
            and self.screen_width_dp <= 360
        )

        if self.is_tablet:
            if self.is_landscape:
                self.layout_profile = (
                    "tablet_landscape"
                )
            else:
                self.layout_profile = (
                    "tablet_portrait"
                )

        elif self.is_landscape:
            self.layout_profile = (
                "phone_landscape"
            )

        elif self.is_compact_phone:
            self.layout_profile = (
                "compact_portrait"
            )

        else:
            self.layout_profile = (
                "phone_portrait"
            )

        print(
            "[RESPONSIVE]",
            f"{self.screen_width_dp:.0f}"
            f"x{self.screen_height_dp:.0f}",
            self.layout_profile,
        )

    def responsive(
        self,
        compact_portrait: float,
        phone_portrait: float,
        phone_landscape: float,
        tablet_portrait: float,
        tablet_landscape: float,
    ) -> float:
        values = {
            "compact_portrait": compact_portrait,
            "phone_portrait": phone_portrait,
            "phone_landscape": phone_landscape,
            "tablet_portrait": tablet_portrait,
            "tablet_landscape": tablet_landscape,
        }

        return float(
            values.get(
                self.layout_profile,
                phone_portrait,
            )
        )
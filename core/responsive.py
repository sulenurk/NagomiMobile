from __future__ import annotations

from kivy.utils import platform
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import (
    BooleanProperty,
    NumericProperty,
    StringProperty,
)

# Set to True only while debugging layout issues.
# print() on Android goes through the logcat bridge and is
# noticeably slower than desktop print, so this must default
# to False for release/testing builds.
RESPONSIVE_DEBUG = True


class ResponsiveMixin:
    screen_width = NumericProperty(360)
    screen_height = NumericProperty(800)

    screen_width_dp = NumericProperty(360)
    screen_height_dp = NumericProperty(800)
    shortest_side_dp = NumericProperty(360)

    ui_scale = NumericProperty(1.0)

    layout_profile = StringProperty(
        "phone_portrait"
    )

    is_landscape = BooleanProperty(False)
    is_portrait = BooleanProperty(True)

    is_compact_phone = BooleanProperty(False)
    is_phone = BooleanProperty(True)
    is_tablet = BooleanProperty(False)

    # -----------------------------------------------------------
    # Built ONCE at class-definition time instead of being
    # reconstructed on every typography() call. This dict was
    # previously rebuilt (11 keys, each a 5-tuple) on every single
    # font_size binding evaluation - dozens of times per screen,
    # multiplied across all screens at startup and again on every
    # resize/theme refresh.
    # -----------------------------------------------------------
    _TYPOGRAPHY_STYLES: dict[str, tuple[float, float, float, float, float]] = {
        # Ana ekran başlıkları:
        # Pomodoro, Focus Timer, Subjects, Settings...
        "page_title": (18, 24, 17, 36, 28),
        "page_title_small": (16, 20, 15, 27, 24),

        # Kart veya bölüm başlıkları:
        # Focus Time, Short Break, Appearance...
        "section_title": (13, 18, 14, 28, 22),

        # Normal önemli metin
        "body": (12, 14, 12, 17, 15),

        # Açıklamalar ve ikincil bilgiler
        "body_small": (10, 12, 10, 15, 13),

        # Menü butonları
        "navigation": (13, 14, 12, 17, 15),

        # Input ve Spinner yazıları
        "input": (12, 14, 12, 16, 15),

        # Küçük etiketler
        "caption": (9, 10, 8, 14, 12),

        # Timer'a özel
        "timer": (28, 66, 42, 70, 56),

        # Cycle'a özel
        "cycle": (10, 20, 11, 30, 15),

        # Durum mesajları
        "status": (9, 10, 8, 14, 12),
    }

    # Index into the 5-tuples above / into responsive()'s args,
    # keyed by layout_profile. Also built once.
    _PROFILE_INDEX: dict[str, int] = {
        "compact_portrait": 0,
        "phone_portrait": 1,
        "phone_landscape": 2,
        "tablet_portrait": 3,
        "tablet_landscape": 4,
    }

    def _get_device_smallest_width_dp(self) -> float:
        if platform == "android":
            try:
                from jnius import autoclass

                PythonActivity = autoclass(
                    "org.kivy.android.PythonActivity"
                )

                activity = PythonActivity.mActivity
                configuration = (
                    activity.getResources().getConfiguration()
                )

                value = float(
                    configuration.smallestScreenWidthDp
                )

                if value > 0:
                    return value

            except Exception as error:
                if RESPONSIVE_DEBUG:
                    print(
                        "[RESPONSIVE DEVICE SIZE ERROR]",
                        error,
                    )

        return self.shortest_side_dp

    def setup_responsive_layout(self) -> None:
        self.update_screen_metrics()

        Window.bind(
            size=self.update_screen_metrics,
        )

    def update_screen_metrics(
        self,
        *_args,
    ) -> None:

        old_profile = self.layout_profile

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

        device_smallest_width_dp = (
            self._get_device_smallest_width_dp()
        )

        self.is_tablet = (
            device_smallest_width_dp >= 600
        )

        self.is_phone = not self.is_tablet

        scale_reference_dp = (
            device_smallest_width_dp
            if self.is_tablet
            else self.shortest_side_dp
        )

        self.ui_scale = max(
            0.85,
            min(
                scale_reference_dp / 360.0,
                1.70,
            ),
        )

        self.is_compact_phone = (
            self.is_phone
            and self.is_portrait
            and self.screen_width_dp < 360
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

        if RESPONSIVE_DEBUG:
            print(
                "[RESPONSIVE]",
                f"raw={Window.width}x{Window.height}",
                f"dp={self.screen_width_dp:.0f}x{self.screen_height_dp:.0f}",
                f"device_min={device_smallest_width_dp:.0f}",
                f"scale={self.ui_scale:.2f}",
                f"old={old_profile}",
                f"new={self.layout_profile}",
                f"tablet={self.is_tablet}",
                f"landscape={self.is_landscape}",
            )
    def responsive(
        self,
        compact_portrait: float,
        phone_portrait: float,
        phone_landscape: float,
        tablet_portrait: float,
        tablet_landscape: float,
    ) -> float:
        # No dict allocation per call - index straight into the
        # tuple of args using the precomputed profile index.
        values = (
            compact_portrait,
            phone_portrait,
            phone_landscape,
            tablet_portrait,
            tablet_landscape,
        )

        index = self._PROFILE_INDEX.get(self.layout_profile, 1)
        return float(values[index])

    def typography(
        self,
        style_name: str,
        _layout_profile: str | None = None,
    ) -> float:
        style_values = self._TYPOGRAPHY_STYLES.get(
            style_name,
            self._TYPOGRAPHY_STYLES["body"],
        )

        base_size = self.responsive(*style_values)

        font_scale = 1.0 + (
            (self.ui_scale - 1.0) * 0.35
        )

        return base_size * font_scale
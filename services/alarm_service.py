from __future__ import annotations

import json
import os
import time
from pathlib import Path

from jnius import autoclass, cast


def load_arguments() -> dict:
    raw_argument = os.environ.get(
        "PYTHON_SERVICE_ARGUMENT",
        "",
    )

    if not raw_argument:
        return {}

    try:
        data = json.loads(raw_argument)

        if isinstance(data, dict):
            return data

    except Exception as error:
        print("[ALARM SERVICE ARG ERROR]", error)

    return {}


def get_alarm_path(alarm_name: str) -> Path:
    alarm_files = {
        "analog": "analog.mp3",
        "beep": "beep.mp3",
        "birdy": "birdy.mp3",
        "buzz": "buzz.mp3",
        "dance": "dans.mp3",
        "galaxy": "galaxy.mp3",
    }

    filename = alarm_files.get(
        str(alarm_name).strip().lower(),
        "beep.mp3",
    )

    app_root = Path(
        os.environ.get(
            "ANDROID_ARGUMENT",
            ".",
        )
    )

    return (
        app_root
        / "assets"
        / "sounds"
        / filename
    )


def start_vibration(service) -> object | None:
    try:
        Context = autoclass(
            "android.content.Context"
        )
        BuildVersion = autoclass(
            "android.os.Build$VERSION"
        )
        VibrationEffect = autoclass(
            "android.os.VibrationEffect"
        )

        vibrator = cast(
            "android.os.Vibrator",
            service.getSystemService(
                Context.VIBRATOR_SERVICE
            ),
        )

        if vibrator is None:
            return None

        # milliseconds:
        # bekle, titre, bekle, titre...
        pattern = [
            0,
            400,
            250,
            400,
            600,
        ]

        if BuildVersion.SDK_INT >= 26:
            effect = VibrationEffect.createWaveform(
                pattern,
                0,
            )
            vibrator.vibrate(effect)

        else:
            vibrator.vibrate(
                pattern,
                0,
            )

        return vibrator

    except Exception as error:
        print("[ALARM SERVICE VIBRATION ERROR]", error)
        return None

def schedule_next_pomodoro_alarm(
    service,
    args: dict,
) -> None:
    if args.get("timer_type") != "pomodoro":
        return

    current_mode = str(
        args.get("mode", "focus")
    )

    completed_focus_count = int(
        args.get("completed_focus_count", 0)
    )

    focus_count = int(
        args.get("focus_count", 4)
    )

    long_break_after = max(
        1,
        int(args.get("long_break_after", 4)),
    )

    if current_mode == "focus":
        completed_focus_count += 1

        # Pomodoro döngüsünün tamamı bittiyse
        # başka alarm planlama.
        if (
            focus_count > 0
            and completed_focus_count >= focus_count
        ):
            return

        if not bool(
            args.get("auto_start_break", False)
        ):
            return

        long_break_due = (
            completed_focus_count > 0
            and completed_focus_count
            % long_break_after == 0
        )

        next_mode = (
            "long_break"
            if long_break_due
            else "short_break"
        )

    else:
        if not bool(
            args.get("auto_start_focus", False)
        ):
            return

        next_mode = "focus"

    if next_mode == "focus":
        duration = int(
            args.get("focus_duration", 0)
        )
    elif next_mode == "long_break":
        duration = int(
            args.get("long_break_duration", 0)
        )
    else:
        duration = int(
            args.get("short_break_duration", 0)
        )

    if duration <= 0:
        return

    previous_end = float(
        args.get(
            "scheduled_end_timestamp",
            time.time(),
        )
    )

    next_end = previous_end + duration

    next_args = dict(args)
    next_args["mode"] = next_mode
    next_args[
        "completed_focus_count"
    ] = completed_focus_count
    next_args[
        "scheduled_end_timestamp"
    ] = next_end

    Context = autoclass(
        "android.content.Context"
    )
    PendingIntent = autoclass(
        "android.app.PendingIntent"
    )
    AlarmManager = autoclass(
        "android.app.AlarmManager"
    )
    SystemClock = autoclass(
        "android.os.SystemClock"
    )
    BuildVersion = autoclass(
        "android.os.Build$VERSION"
    )

    AlarmService = autoclass(
        "com.sklabs.nagomi.ServiceNagomialarm"
    )

    context = service.getApplicationContext()

    service_intent = AlarmService.getDefaultIntent(
        context,
        "icon",
        "Nagomi",
        "Timer completed",
        json.dumps(next_args),
    )

    flags = (
        getattr(
            PendingIntent,
            "FLAG_UPDATE_CURRENT",
            0,
        )
        | getattr(
            PendingIntent,
            "FLAG_IMMUTABLE",
            0,
        )
    )

    if BuildVersion.SDK_INT >= 26:
        pending_intent = (
            PendingIntent.getForegroundService(
                context,
                4200,
                service_intent,
                flags,
            )
        )
    else:
        pending_intent = PendingIntent.getService(
            context,
            4200,
            service_intent,
            flags,
        )

    alarm_manager = cast(
        "android.app.AlarmManager",
        context.getSystemService(
            Context.ALARM_SERVICE
        ),
    )

    delay_seconds = max(
        0.0,
        next_end - time.time(),
    )

    trigger_elapsed = int(
        SystemClock.elapsedRealtime()
        + delay_seconds * 1000
    )

    alarm_manager.setExactAndAllowWhileIdle(
        AlarmManager.ELAPSED_REALTIME_WAKEUP,
        trigger_elapsed,
        pending_intent,
    )

    print(
        "[POMODORO NEXT ALARM]",
        next_mode,
        next_end,
    )

def schedule_next_focus_timer_alarm(
    service,
    args: dict,
) -> None:
    if args.get("timer_type") != "focus_timer":
        return

    sequence = args.get(
        "focus_sequence",
        [],
    )

    if not isinstance(sequence, list):
        return

    if not sequence:
        return

    current_index = int(
        args.get("focus_index", 0)
    )

    if (
        current_index < 0
        or current_index >= len(sequence)
    ):
        return

    current_mode = str(
        args.get("mode", "focus")
    )

    previous_end = float(
        args.get(
            "scheduled_end_timestamp",
            time.time(),
        )
    )

    if current_mode == "focus":
        # Focus bitti → aynı task'ın break'i.
        if not bool(
            args.get(
                "auto_start_break",
                False,
            )
        ):
            return

        current_task = sequence[
            current_index
        ]

        duration = int(
            current_task.get(
                "break_duration",
                0,
            )
        )

        next_mode = "break"
        next_index = current_index

    else:
        # Break bitti → sıradaki task'ın focus'u.
        if not bool(
            args.get(
                "auto_start_focus",
                False,
            )
        ):
            return

        next_index = current_index + 1

        if next_index >= len(sequence):
            return

        next_task = sequence[
            next_index
        ]

        duration = int(
            next_task.get(
                "focus_duration",
                0,
            )
        )

        next_mode = "focus"

    if duration <= 0:
        return

    next_end = (
        previous_end + duration
    )

    next_args = dict(args)
    next_args["mode"] = next_mode
    next_args["focus_index"] = next_index
    next_args[
        "scheduled_end_timestamp"
    ] = next_end

    Context = autoclass(
        "android.content.Context"
    )
    PendingIntent = autoclass(
        "android.app.PendingIntent"
    )
    AlarmManager = autoclass(
        "android.app.AlarmManager"
    )
    SystemClock = autoclass(
        "android.os.SystemClock"
    )
    BuildVersion = autoclass(
        "android.os.Build$VERSION"
    )

    AlarmService = autoclass(
        "com.sklabs.nagomi.ServiceNagomialarm"
    )

    context = service.getApplicationContext()

    service_intent = (
        AlarmService.getDefaultIntent(
            context,
            "icon",
            "Nagomi",
            "Timer completed",
            json.dumps(next_args),
        )
    )

    flags = (
        getattr(
            PendingIntent,
            "FLAG_UPDATE_CURRENT",
            0,
        )
        | getattr(
            PendingIntent,
            "FLAG_IMMUTABLE",
            0,
        )
    )

    if BuildVersion.SDK_INT >= 26:
        pending_intent = (
            PendingIntent.getForegroundService(
                context,
                4200,
                service_intent,
                flags,
            )
        )
    else:
        pending_intent = (
            PendingIntent.getService(
                context,
                4200,
                service_intent,
                flags,
            )
        )

    alarm_manager = cast(
        "android.app.AlarmManager",
        context.getSystemService(
            Context.ALARM_SERVICE
        ),
    )

    delay_seconds = max(
        0.0,
        next_end - time.time(),
    )

    trigger_elapsed = int(
        SystemClock.elapsedRealtime()
        + delay_seconds * 1000
    )

    alarm_manager.setExactAndAllowWhileIdle(
        AlarmManager.ELAPSED_REALTIME_WAKEUP,
        trigger_elapsed,
        pending_intent,
    )

    print(
        "[FOCUS NEXT ALARM]",
        next_mode,
        next_index,
        next_end,
    )

def main() -> None:
    args = load_arguments()

    alarm_name = str(
        args.get("alarm_sound", "beep")
    )

    sound_enabled = bool(
        args.get("sound_enabled", True)
    )

    vibration_enabled = bool(
        args.get("vibration_enabled", True)
    )

    alarm_path = get_alarm_path(
        alarm_name
    )

    print(
        "[ALARM SERVICE] started:",
        alarm_path,
    )

    PythonService = autoclass(
        "org.kivy.android.PythonService"
    )

    service = PythonService.mService

    media_player = None
    vibrator = None

    try:

        schedule_next_pomodoro_alarm(
            service,
            args,
        )

        schedule_next_focus_timer_alarm(
            service,
            args,
        )
        # ------------------------------
        # SES
        # ------------------------------
        if sound_enabled:
            MediaPlayer = autoclass("android.media.MediaPlayer")

            media_player = MediaPlayer()
            media_player.setDataSource(str(alarm_path))
            media_player.setLooping(True)
            media_player.prepare()
            media_player.start()

        # ------------------------------
        # VIBRATION
        # ------------------------------
        if vibration_enabled:
            vibrator = start_vibration(
                service
            )

        # Alarm şu an Nagomi'de olduğu gibi
        # en fazla 15 saniye çalışsın.
        time.sleep(15)

    except Exception as error:
        print(
            "[ALARM SERVICE ERROR]",
            error,
        )

    finally:
        if media_player is not None:
            try:
                media_player.stop()
            except Exception:
                pass

            try:
                media_player.release()
            except Exception:
                pass

        if vibrator is not None:
            try:
                vibrator.cancel()
            except Exception:
                pass

        try:
            service.stopSelf()
        except Exception as error:
            print(
                "[ALARM SERVICE STOP ERROR]",
                error,
            )


if __name__ == "__main__":
    main()
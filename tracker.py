import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import csv
import os
from datetime import datetime

CSV_FILE = "events.csv"

# ===============================
# CSV Logger with Duplicate Check
# ===============================
def log_event(event_type, details):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Prevent duplicate (same timestamp + same event)
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r") as f:
            rows = list(csv.reader(f))
            if len(rows) > 1:
                last_row = rows[-1]
                if last_row[0] == timestamp and last_row[1] == event_type:
                    return

    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "event_type", "details"])
        writer.writerow([timestamp, event_type, details])

    print(f"[LOGGED] {event_type} - {details}")


# ==========================================
# Ensure Previous Session Power Off Logged
# ==========================================
def ensure_previous_power_off():
    if not os.path.exists(CSV_FILE):
        return

    with open(CSV_FILE, "r") as f:
        rows = list(csv.reader(f))
        if len(rows) <= 1:
            return

        last_event = rows[-1][1]

        # If last event was power_on, it means shutdown wasn't logged
        if last_event == "power_on":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(CSV_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, "power_off", "auto_detected_shutdown"])
            print("[AUTO FIX] Previous power_off added")


# ===============================
# Screen Lock / Unlock Listener
# ===============================
def handle_lock_signal(is_locked):
    if is_locked:
        log_event("screen_lock", "locked")
    else:
        log_event("screen_unlock", "unlocked")


# ===============================
# Suspend / Resume Detection
# ===============================
def handle_prepare_for_sleep(sleeping):
    if sleeping:
        log_event("power_off", "suspend")
    else:
        log_event("power_on", "resume")


# ===============================
# Main Function
# ===============================
def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    session_bus = dbus.SessionBus()

    # Auto-fix previous shutdown
    ensure_previous_power_off()

    # Log current boot
    log_event("power_on", "boot")

    # Listen for suspend/resume
    bus.add_signal_receiver(
        handle_prepare_for_sleep,
        signal_name="PrepareForSleep",
        dbus_interface="org.freedesktop.login1.Manager"
    )

    # Listen for lock/unlock
    session_bus.add_signal_receiver(
        handle_lock_signal,
        signal_name="ActiveChanged",
        dbus_interface="org.gnome.ScreenSaver"
    )

    print("Tracker started... Running in background.")
    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()

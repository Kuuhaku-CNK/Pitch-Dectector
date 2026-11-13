"""Quy đổi tần số cơ bản thành nốt nhạc và chỉ dẫn chỉnh dây."""

from dataclasses import dataclass
from math import floor, isclose, isfinite, log2


A4_HZ = 440.0
A4_MIDI = 69
NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
# MIDI theo thứ tự dây 1 (mỏng nhất) đến dây 6 (dày nhất).
OPEN_STRING_MIDI = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}


@dataclass(frozen=True)
class TuningAdvice:
    detected_note: str
    target_note: str
    target_hz: float
    cents: float
    status: str


def _note_name(midi):
    octave, pitch_class = divmod(midi, 12)
    return f"{NOTE_NAMES[pitch_class]}{octave - 1}"


def tuning_advice(frequency_hz, *, string_number=None, tolerance_cents=5.0):
    """So với dây buông được chọn hoặc với nốt gần nhất nếu bỏ trống."""
    if not isfinite(frequency_hz) or frequency_hz <= 0:
        raise ValueError("Tần số đo phải hữu hạn và lớn hơn 0.")
    if string_number is not None and string_number not in OPEN_STRING_MIDI:
        raise ValueError("Số dây phải từ 1 đến 6.")
    if not isfinite(tolerance_cents) or tolerance_cents < 0:
        raise ValueError("Dung sai cent phải hữu hạn và không âm.")

    # Làm tròn về bán cung gần nhất trong hệ 12 bán cung đều.
    measured_midi = A4_MIDI + 12 * (log2(frequency_hz) - log2(A4_HZ))
    nearest_midi = floor(measured_midi + 0.5)
    target_midi = OPEN_STRING_MIDI.get(string_number, nearest_midi)
    target_hz = A4_HZ * 2 ** ((target_midi - A4_MIDI) / 12)
    cents = 1200 * (log2(frequency_hz) - log2(target_hz))

    if abs(cents) <= tolerance_cents or isclose(
        abs(cents), tolerance_cents, rel_tol=0, abs_tol=1e-9
    ):
        status = "in_tune"
    elif cents < 0:
        status = "flat"
    else:
        status = "sharp"

    return TuningAdvice(
        _note_name(nearest_midi), _note_name(target_midi), target_hz, cents, status
    )

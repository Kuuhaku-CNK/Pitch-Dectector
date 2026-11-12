import csv
import re
from pathlib import Path

import librosa
import numpy as np


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REPORT_PATH = Path("results/pitch_check.csv")


def note_from_filename(path):
    """Đọc nhãn ở đầu tên file, ví dụ G2, Fs2_01 hoặc F#2_01."""
    match = re.match(
        r"^([A-Ga-g])([#♯b♭s]?)(-?\d+)(?=$|[ _-])", path.stem
    )
    if not match:
        return ""

    letter, accidental, octave = match.groups()
    accidental = {"s": "#", "♯": "#", "♭": "b"}.get(accidental, accidental)
    return letter.upper() + accidental + octave


def measure_pitch(path):
    """Trả về tần số trung vị, tỷ lệ khung có cao độ và thời lượng."""
    signal, sample_rate = librosa.load(path, sr=22050, mono=True)
    duration = len(signal) / sample_rate

    f0, voiced, _ = librosa.pyin(
        signal,
        fmin=55,
        fmax=880,
        sr=sample_rate,
        frame_length=2048,
        hop_length=256,
        center=False,
    )

    valid = voiced & np.isfinite(f0)
    frequency = float(np.median(f0[valid])) if np.any(valid) else None
    return frequency, float(np.mean(valid)), duration


def cents_difference(frequency, reference):
    return 1200 * np.log2(frequency / reference)


def main():
    raw_files = sorted(
        path for path in RAW_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() == ".wav"
    )
    if not raw_files:
        raise SystemExit("Không tìm thấy WAV trong data/raw. Hãy chạy từ thư mục Project.")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8-sig", newline="") as report:
        writer = csv.writer(report)
        writer.writerow([
            "file", "nhan", "raw_hz", "processed_hz", "not_do_duoc",
            "lech_so_voi_raw_cent", "lech_so_voi_nhan_cent",
            "processed_giay", "khung_co_cao_do_pct", "kiem_tra",
        ])

        for raw_path in raw_files:
            relative_path = raw_path.relative_to(RAW_DIR)
            processed_path = (
                PROCESSED_DIR / relative_path.parent
                / f"{raw_path.stem}_processed.wav"
            )
            label = note_from_filename(raw_path)

            if not processed_path.is_file():
                writer.writerow([relative_path, label] + [""] * 7 + ["Thiếu file processed"])
                continue

            try:
                raw_hz, _, _ = measure_pitch(raw_path)
                processed_hz, voiced_ratio, duration = measure_pitch(processed_path)
            except (OSError, RuntimeError, ValueError) as error:
                writer.writerow([relative_path, label] + [""] * 7 + [str(error)])
                continue

            flags = []
            if duration < 1:
                flags.append("Dưới 1 giây")
            if voiced_ratio < 0.5:
                flags.append("Ít khung có cao độ")
            if raw_hz is None or processed_hz is None:
                flags.append("Thiếu kết quả đo")

            change = ""
            if raw_hz is not None and processed_hz is not None:
                change = cents_difference(processed_hz, raw_hz)
                if abs(change) > 20:
                    flags.append("Lệch raw trên 20 cent")

            detected_note = ""
            label_error = ""
            if processed_hz is not None:
                detected_note = librosa.hz_to_note(processed_hz, unicode=False)
                if label:
                    label_error = cents_difference(
                        processed_hz, librosa.note_to_hz(label)
                    )
                    if abs(label_error) >= 50:
                        flags.append("Cần đối chiếu nhãn nốt")
                else:
                    flags.append("Cần đọc nhãn thủ công")

            writer.writerow([
                relative_path, label,
                "" if raw_hz is None else f"{raw_hz:.2f}",
                "" if processed_hz is None else f"{processed_hz:.2f}",
                detected_note,
                "" if change == "" else f"{change:.1f}",
                "" if label_error == "" else f"{label_error:.1f}",
                f"{duration:.3f}", f"{100 * voiced_ratio:.1f}",
                " / ".join(flags) or "OK",
            ])

    print(f"Đã kiểm tra {len(raw_files)} file. Mở báo cáo tại {REPORT_PATH}")


if __name__ == "__main__":
    main()
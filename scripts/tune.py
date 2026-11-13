"""Đo cao độ và hướng dẫn chỉnh dây từ một file WAV."""

import argparse
import sys
from math import isfinite
from pathlib import Path

from src.audioloader import load_wav
from src.pitch_detection import estimate_pitch
from src.preprocessing import preprocess_audio
from src.tuning import OPEN_STRING_MIDI, tuning_advice


INSTRUCTIONS = {
    "in_tune": "Đúng cao độ trong dung sai đã chọn.",
    "flat": "Cao độ thấp. Siết dây từng chút rồi gảy lại.",
    "sharp": "Cao độ cao. Nới dây từng chút rồi gảy lại.",
}


def main():
    parser = argparse.ArgumentParser(
        description="Đo tần số cơ bản và chỉ dẫn chỉnh dây từ WAV một nốt guitar."
    )
    parser.add_argument("wav", type=Path, help="Đường dẫn đến file WAV đã tiền xử lý.")
    parser.add_argument(
        "--raw", action="store_true", help="Tiền xử lý WAV thô trước khi đo."
    )
    parser.add_argument(
        "--string", type=int, choices=OPEN_STRING_MIDI, dest="string_number",
        help="Dây buông cần chỉnh. Dây 1 là dây mỏng nhất. Mặc định so với nốt gần nhất.",
    )
    parser.add_argument(
        "--tolerance", type=float, default=5.0,
        help="Dung sai lên dây tính bằng cent. Mặc định là 5.",
    )
    args = parser.parse_args()
    if not isfinite(args.tolerance) or args.tolerance < 0:
        parser.error("--tolerance phải là số hữu hạn và không âm.")

    try:
        sample_rate, signal = load_wav(args.wav)
        if args.raw:
            *_, signal = preprocess_audio(signal, sample_rate)
        pitch = estimate_pitch(signal, sample_rate)
    except (OSError, ValueError, EOFError, NotImplementedError) as error:
        print(f"Lỗi đọc hoặc phân tích WAV: {error}", file=sys.stderr)
        return 1

    if pitch is None:
        print("Chưa đo được cao độ ổn định. Hãy gảy rõ một dây và đo lại.")
        return 1

    advice = tuning_advice(
        pitch.frequency_hz,
        string_number=args.string_number,
        tolerance_cents=args.tolerance,
    )
    target = advice.target_note
    if args.string_number is not None:
        target = f"Dây {args.string_number} buông ({target})"

    print(f"Cao độ đo được: {pitch.frequency_hz:.2f} Hz ({advice.detected_note})")
    print(f"Mục tiêu: {target}, {advice.target_hz:.2f} Hz")
    print(f"Độ lệch: {advice.cents:+.2f} cent")
    print(f"Khung có cao độ ổn định: {pitch.stable_frames}/{pitch.total_frames}")
    print(INSTRUCTIONS[advice.status])
    return 0


if __name__ == "__main__":
    sys.exit(main())

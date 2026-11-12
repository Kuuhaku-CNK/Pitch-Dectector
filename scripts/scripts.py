import argparse
import sys
from pathlib import Path

from src.audioloader import load_wav
from src.preprocessing import preprocess_audio, save_processed_wav


def main():
    parser = argparse.ArgumentParser(
        description="Tiền xử lý một file hoặc toàn bộ file WAV trong data/raw."
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help='Đường dẫn tương đối trong data/raw, ví dụ "Dây 6/E2_01.wav".',
    )
    parser.add_argument(
        "--frame-ms",
        type=float,
        default=1000,
        help="Độ dài frame tính bằng mili giây. Tối thiểu và mặc định là 1000.",
    )
    parser.add_argument(
        "--skip-ms",
        type=float,
        default=100,
        help="Thời gian bỏ qua sau onset tính bằng mili giây. Mặc định là 100.",
    )
    args = parser.parse_args()

    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    if not raw_dir.is_dir():
        print(f"Lỗi: Không tìm thấy thư mục {raw_dir}.")
        return 1

    if args.file:
        input_path = raw_dir / args.file

        # Đảm bảo file được chọn nằm bên trong data/raw.
        try:
            input_path.resolve().relative_to(raw_dir.resolve())
        except ValueError:
            print("Lỗi: File đầu vào phải nằm trong thư mục data/raw.")
            return 1

        if not input_path.is_file() or input_path.suffix.lower() != ".wav":
            print(f"Lỗi: Không tìm thấy file WAV {input_path}.")
            return 1

        input_files = [input_path]
    else:
        input_files = sorted(
            path
            for path in raw_dir.rglob("*")
            if path.is_file() and path.suffix.lower() == ".wav"
        )

    if not input_files:
        print(f"Không tìm thấy file WAV nào trong {raw_dir}.")
        return 1

    successful = 0
    failed = 0
    skipped = 0

    print(f"Tìm thấy {len(input_files)} file WAV.")

    for input_path in input_files:
        relative_path = input_path.relative_to(raw_dir)

        # Giữ thư mục dây đàn và thêm hậu tố để phân biệt file đã xử lý.
        output_name = f"{input_path.stem}_processed.wav"
        output_path = processed_dir / relative_path.parent / output_name

        if output_path.exists():
            print(f"\n[BỎ QUA] Đã có file đầu ra: {output_path}")
            skipped += 1
            continue

        try:
            sample_rate, signal = load_wav(input_path)

            signal_dc, onset_index, frame_start, frame_end, frame = (
                preprocess_audio(
                    signal,
                    sample_rate,
                    frame_duration_ms=args.frame_ms,
                    attack_skip_ms=args.skip_ms,
                )
            )

            save_processed_wav(output_path, sample_rate, frame)

            print(f"\n[THÀNH CÔNG] {relative_path}")
            print(f"  Sampling rate: {sample_rate} Hz")
            print(f"  Thời lượng bản ghi: {len(signal) / sample_rate:.3f} giây")
            print(f"  Onset ước lượng: {onset_index / sample_rate:.3f} giây")
            print(f"  Frame bắt đầu: {frame_start / sample_rate:.3f} giây")
            print(f"  Frame kết thúc: {frame_end / sample_rate:.3f} giây")
            print(f"  Độ dài frame: {len(frame)} mẫu")
            print(f"  File đầu ra: {output_path}")

            successful += 1

        except (ValueError, TypeError, OSError, EOFError, NotImplementedError) as error:
            print(f"\n[LỖI] {relative_path}")
            print(f"  {error}")
            failed += 1

    print("\n--- KẾT QUẢ ---")
    print(f"Thành công: {successful}")
    print(f"Bỏ qua vì file đầu ra đã tồn tại: {skipped}")
    print(f"Không xử lý được: {failed}")

    if failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
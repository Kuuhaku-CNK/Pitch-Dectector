from pathlib import Path

import numpy as np
from scipy.io import wavfile


def remove_dc_offset(signal):
    """Trừ giá trị trung bình khỏi từng mẫu của tín hiệu mono."""
    signal = np.asarray(signal, dtype=np.float64)

    if signal.ndim != 1 or signal.size == 0:
        raise ValueError("Tín hiệu phải là mảng mono một chiều và có ít nhất một mẫu.")
    if not np.all(np.isfinite(signal)):
        raise ValueError("Tín hiệu chứa NaN hoặc giá trị vô cực.")

    # x_dc[n] = x[n] - mean(x)
    return signal - np.mean(signal)


def short_time_rms(signal, sample_rate, window_ms=20, hop_ms=10):
    """Trả về chỉ số đầu của từng cửa sổ và giá trị RMS tương ứng."""
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("Sampling rate phải là số hữu hạn lớn hơn 0.")
    if not np.isfinite(window_ms) or not np.isfinite(hop_ms):
        raise ValueError("Cửa sổ RMS và bước dịch phải là số hữu hạn.")

    signal = np.asarray(signal, dtype=np.float64)
    window_size = round(sample_rate * window_ms / 1000)
    hop_size = round(sample_rate * hop_ms / 1000)

    if window_size < 1 or hop_size < 1:
        raise ValueError("Cửa sổ RMS và bước dịch phải có ít nhất một mẫu.")
    if signal.size < window_size:
        raise ValueError("Tín hiệu quá ngắn để tính một cửa sổ RMS đầy đủ.")

    # Chỉ lấy các cửa sổ có đủ mẫu để chúng có cùng độ dài.
    last_start = signal.size - window_size
    frame_starts = np.arange(0, last_start + 1, hop_size)
    rms_values = np.empty(frame_starts.size, dtype=np.float64)

    for index, start in enumerate(frame_starts):
        window = signal[start:start + window_size]
        # RMS = căn bậc hai của trung bình bình phương các mẫu.
        rms_values[index] = np.sqrt(np.mean(window ** 2))

    return frame_starts, rms_values


def detect_onset(
    signal,
    sample_rate,
    absolute_threshold=0.01,
    relative_threshold=0.10,
):
    """Trả về chỉ số đầu của cửa sổ RMS đầu tiên vượt cả hai ngưỡng."""
    if not np.isfinite(absolute_threshold) or absolute_threshold < 0:
        raise ValueError("Ngưỡng RMS tuyệt đối phải hữu hạn và không âm.")
    if not 0 <= relative_threshold < 1:
        raise ValueError("Ngưỡng RMS tương đối phải từ 0 đến dưới 1.")

    frame_starts, rms_values = short_time_rms(signal, sample_rate)
    peak_rms = np.max(rms_values)

    # Vượt ngưỡng lớn hơn nghĩa là đồng thời vượt cả hai ngưỡng.
    threshold = max(absolute_threshold, relative_threshold * peak_rms)

    for start, rms in zip(frame_starts, rms_values):
        if rms > threshold:
            return int(start)

    raise ValueError(
        "Không phát hiện được onset: không có cửa sổ RMS vượt ngưỡng."
    )


def preprocess_audio(
    signal,
    sample_rate,
    frame_duration_ms=1000,
    attack_skip_ms=100,
    absolute_threshold=0.01,
    relative_threshold=0.10,
):
    """Trả về tín hiệu đã loại DC, vị trí onset và frame dài ít nhất 1 giây."""
    if not np.isfinite(frame_duration_ms) or frame_duration_ms < 1000:
        raise ValueError("Độ dài frame phải từ 1000 ms (1 giây) trở lên.")

    if not np.isfinite(attack_skip_ms) or attack_skip_ms < 0:
        raise ValueError("Thời gian bỏ attack phải hữu hạn và không âm.")

    signal_dc = remove_dc_offset(signal)
    onset_index = detect_onset(
        signal_dc,
        sample_rate,
        absolute_threshold=absolute_threshold,
        relative_threshold=relative_threshold,
    )

    # Đổi thời gian sang số mẫu rồi xác định vị trí cắt.
    attack_samples = round(sample_rate * attack_skip_ms / 1000)
    frame_size = round(sample_rate * frame_duration_ms / 1000)
    frame_start = onset_index + attack_samples
    frame_end = frame_start + frame_size

    if frame_end > signal_dc.size:
        available_samples = max(0, signal_dc.size - frame_start)
        available_seconds = available_samples / sample_rate
        required_seconds = frame_size / sample_rate
        raise ValueError(
            f"Sau khi bỏ attack chỉ còn {available_seconds:.3f} giây, "
            f"cần {required_seconds:.3f} giây để cắt frame. "
            "Hãy chọn đoạn dài hơn trong bản thu gốc."
        )

    frame = signal_dc[frame_start:frame_end]
    return signal_dc, onset_index, frame_start, frame_end, frame


def save_processed_wav(output_path, sample_rate, frame):
    """Lưu frame một chiều thành WAV mono float32 với sampling rate gốc."""
    frame = np.asarray(frame, dtype=np.float64)

    if frame.ndim != 1 or frame.size == 0:
        raise ValueError("Frame cần lưu phải là mảng mono một chiều và có mẫu.")
    if not np.all(np.isfinite(frame)):
        raise ValueError("Frame chứa NaN hoặc giá trị vô cực.")
    if np.max(np.abs(frame)) > np.finfo(np.float32).max:
        raise ValueError("Biên độ của frame vượt phạm vi biểu diễn của float32.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Chỉ đổi kiểu dữ liệu. Giữ thang biên độ và lưu trực tiếp frame đã cắt.
    wavfile.write(output_path, sample_rate, frame.astype(np.float32))
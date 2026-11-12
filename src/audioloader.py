import numpy as np
from scipy.io import wavfile


def load_wav(file_path):
    """Đọc WAV mono hoặc stereo và trả về (sample_rate, signal_mono)."""
    sample_rate, samples = wavfile.read(file_path)

    if samples.size == 0:
        raise ValueError("File WAV không chứa mẫu âm thanh.")
    if sample_rate <= 0:
        raise ValueError("Sampling rate của file WAV phải lớn hơn 0.")

    data_type = samples.dtype

    # Chuyển sang float trước khi trừ, chia hoặc lấy trung bình hai kênh.
    if data_type.kind == "i":
        # PCM có dấu, ví dụ int16 có biên âm là -32768.
        scale = float(-np.iinfo(data_type).min)
        signal = samples.astype(np.float64) / scale
    elif data_type.kind == "u":
        # PCM không dấu, ví dụ uint8 có mức im lặng tại 128.
        midpoint = (np.iinfo(data_type).max + 1) / 2.0
        signal = (samples.astype(np.float64) - midpoint) / midpoint
    elif data_type.kind == "f":
        signal = samples.astype(np.float64)
    else:
        raise ValueError(f"Kiểu dữ liệu WAV không được hỗ trợ: {data_type}.")

    if not np.all(np.isfinite(signal)):
        raise ValueError("File WAV chứa NaN hoặc giá trị vô cực.")

    if signal.ndim == 2 and signal.shape[1] == 2:
        # Mỗi hàng là một thời điểm. axis=1 lấy trung bình hai kênh.
        signal = np.mean(signal, axis=1)
    elif signal.ndim != 1:
        raise ValueError("Chỉ hỗ trợ file WAV mono hoặc stereo.")

    return sample_rate, signal
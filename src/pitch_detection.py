"""Ước lượng tần số cơ bản của một nốt guitar bằng YIN."""

from dataclasses import dataclass
from math import ceil

import numpy as np
from scipy.signal import correlate

from src.preprocessing import remove_dc_offset


@dataclass(frozen=True)
class PitchEstimate:
    frequency_hz: float
    stable_frames: int
    total_frames: int


def _yin_difference(frame, max_lag):
    """Tính tổng bình phương sai khác với cùng số mẫu ở mọi độ trễ."""
    # Chừa một mẫu sau max_lag để nội suy tại biên.
    window_size = frame.size - max_lag - 1
    reference = frame[:window_size]

    # Khai triển (a - b)² thành a² + b² - 2ab.
    # correlate(..., 'valid') cho tích vô hướng với từng đoạn dịch.
    products = correlate(frame, reference, mode="valid", method="fft")
    energy = np.concatenate(([0.0], np.cumsum(frame**2)))
    shifted_energy = energy[window_size:] - energy[:-window_size]
    difference = energy[window_size] + shifted_energy - 2 * products
    return np.maximum(difference, 0.0)


def _estimate_frame(frame, sample_rate, max_lag, threshold):
    difference = _yin_difference(frame, max_lag)
    cumulative = np.cumsum(difference[1:])
    lags = np.arange(1, difference.size)
    normalized = np.ones_like(difference)
    np.divide(
        difference[1:] * lags,
        cumulative,
        out=normalized[1:],
        where=cumulative > 0,
    )

    # Chọn đáy đầu tiên đủ sâu để tránh lấy bội của chu kỳ.
    # Xét cả độ trễ ngắn. Kiểm tra dải Hz sau khi chọn đáy để một
    # tín hiệu quá cao không bị nhận nhầm thành nốt thấp hơn.
    center = normalized[2:-1]
    left = normalized[1:-2]
    right = normalized[3:]
    candidates = np.flatnonzero(
        (center < threshold) & (center < left) & (center <= right)
    )
    if candidates.size == 0:
        return None

    lag = 2 + candidates[0]
    # Nội suy bằng ba điểm của hàm sai khác quanh đáy đã chọn.
    before, middle, after = difference[lag - 1:lag + 2]
    curvature = before - 2 * middle + after
    offset = 0.0
    if curvature > 0:
        offset = np.clip((before - after) / (2 * curvature), -0.5, 0.5)
    return float(sample_rate / (lag + offset))


def estimate_pitch(
    signal,
    sample_rate,
    *,
    min_hz=55.0,
    max_hz=880.0,
    yin_threshold=0.10,
    min_rms=0.001,
):
    """Đo một nốt trên tín hiệu mono. Trả về None nếu cao độ thiếu ổn định."""
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("Sampling rate phải hữu hạn và lớn hơn 0.")
    if not 0 < min_hz < max_hz < sample_rate / 2:
        raise ValueError("Cần 0 < min_hz < max_hz < sample_rate / 2.")
    if not 0 < yin_threshold < 1 or not np.isfinite(min_rms) or min_rms < 0:
        raise ValueError("Cần 0 < yin_threshold < 1 và min_rms hữu hạn, không âm.")

    signal = remove_dc_offset(signal)
    max_lag = ceil(sample_rate / min_hz)

    # Dùng ít nhất 3 chu kỳ ở tần số thấp nhất trong mỗi khung.
    frame_size = max(round(0.12 * sample_rate), 3 * (max_lag + 1))
    hop_size = max(1, round(0.03 * sample_rate))
    starts = range(0, signal.size - frame_size + 1, hop_size)
    frequencies = []
    for start in starts:
        frame = signal[start:start + frame_size]
        # Đo RMS quanh mức trung bình của khung để bỏ qua phần quá nhỏ.
        rms = np.std(frame)
        if rms <= min_rms:
            continue
        frequency = _estimate_frame(frame, sample_rate, max_lag, yin_threshold)
        if frequency is not None and min_hz <= frequency <= max_hz:
            frequencies.append(frequency)

    # Cần đa số khung ủng hộ cùng một cao độ trước khi chỉ dẫn chỉnh dây.
    if not frequencies:
        return None
    frequencies = np.asarray(frequencies)
    median = np.median(frequencies)
    deviations = 1200 * np.log2(frequencies / median)
    stable = frequencies[np.abs(deviations) <= 30]
    if stable.size * 2 <= len(starts):
        return None
    return PitchEstimate(float(np.median(stable)), stable.size, len(starts))

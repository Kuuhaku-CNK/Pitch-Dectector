# Tiền xử lý và kiểm tra cao độ nốt guitar

Dự án chuẩn bị các đoạn WAV nốt đơn để phân tích cao độ bằng FFT và tự tương quan (Autocorrelation, viết tắt là ACF). Với mỗi lần gảy, chương trình đọc WAV, chuyển về mono, loại DC offset, tìm điểm bắt đầu của tiếng đàn và lưu một đoạn dài tối thiểu **1 giây**. Script kiểm tra dùng pYIN để đối chiếu cao độ trước và sau khi cắt.

## 1. Cài đặt trên Windows

Cài Python 3 nếu máy chưa có. Mở thư mục gốc `Project` trong VS Code, chọn **Terminal → New Terminal** và dùng PowerShell. Khi đứng đúng thư mục, bạn sẽ thấy `requirements.txt`, `src` và `scripts` trong Explorer. Nếu gõ `python` và thấy dấu `>>>`, hãy gõ `exit()` để trở về PowerShell trước khi chạy các lệnh bên dưới. [Tải Python cho Windows](https://www.python.org/downloads/windows/)

```powershell
Set-Location -LiteralPath 'D:\DSP\Project'
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Đổi `D:\DSP\Project` thành đường dẫn trên máy nếu cần. `.venv` là môi trường Python riêng của dự án, chứa các thư viện được cài cho dự án. Các lệnh ở đây gọi thẳng Python trong `.venv`, vì vậy bạn có thể chạy chúng ngay trong PowerShell. Nếu đã có môi trường ảo, bỏ qua lệnh tạo `.venv`. [Tài liệu Python về môi trường ảo](https://docs.python.org/3/library/venv.html)

NumPy xử lý mảng mẫu và các phép tính như trung bình hay RMS. SciPy đọc và ghi WAV. Nếu `requirements.txt` có Matplotlib và pytest, chúng lần lượt phục vụ việc vẽ đồ thị và chạy kiểm thử. Để dùng script đối chiếu cao độ ở mục 6, cài thêm librosa trong cùng môi trường nếu chưa có:

```powershell
.\.venv\Scripts\python.exe -m pip install librosa
```

## 2. Chuẩn bị dữ liệu và hiểu cấu trúc dự án

```text
Project/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/
│   │   ├── Dây 1/
│   │   │   └── A4.wav
│   │   ├── ...
│   │   └── Dây 6/
│   └── processed/           # Chương trình tạo khi lưu WAV đầu ra
├── results/
│   └── pitch_check.csv      # Tạo khi chạy kiểm tra cao độ
├── scripts/
│   ├── scripts.py          # Tiền xử lý một file hoặc cả bộ
│   └── check_pitch.py      # Đối chiếu cao độ bằng pYIN
└── src/
    ├── __init__.py
    ├── audioloader.py      # Đọc WAV, đổi kiểu mẫu và gộp kênh
    └── preprocessing.py    # Loại DC, tìm onset, cắt frame và lưu WAV
```

Đưa sáu thư mục đã cắt từ `D:\DSP\Filter` vào `data/raw/`. Trong dự án này, `raw` là các **file từng lần gảy đã tách từ bản thu dài**. Giữ bản thu dài riêng để đối chiếu lời đọc tên nốt, số dây và thứ tự thu.

- Mỗi WAV đầu vào nên có một lần gảy. Giữ một khoảng nền ngắn trước tiếng gảy nếu có, rồi giữ đủ phần tiếng đàn phía sau. Khi cắt trong Audacity, nghe lại để loại tiếng đọc nhãn và tránh lấy sang lần gảy kế tiếp.
- Có thể dùng WAV mono hoặc stereo. Code đọc sampling rate từ WAV. Dùng cùng sampling rate cho cả bộ nếu quy trình xuất file của bạn cho phép. Ví dụ trong tài liệu này dùng `44.100 Hz`.
- Giữ tên nốt và quãng tám ở đầu tên file, ví dụ `G2.wav`, `E2_01.wav` hoặc `F#2_02.wav`. Script kiểm tra cũng hiểu `Fs2` là F♯2. Nếu thêm số lần thu hoặc thông tin khác sau tên nốt, ngăn cách bằng dấu gạch dưới, dấu gạch ngang hoặc dấu cách.
- Dùng thư mục để ghi **dây đã chơi**, còn tên file để ghi **cao độ dự kiến**. Cùng nốt A2 có thể chơi trên dây 5 buông hoặc dây 6 phím 5. Muốn xác minh dây, hãy dựa vào bản thu gốc hoặc thông tin của người chơi.

## 3. Các khái niệm xử lý tín hiệu dùng trong code

### Mẫu, biên độ và sampling rate

Microphone biến dao động âm thanh thành tín hiệu điện. Khi ghi âm, hệ thống đo tín hiệu ở các thời điểm cách đều nhau. Mỗi giá trị đo là một **mẫu**. Dãy mẫu theo thời gian tạo thành **waveform**, tức đường sóng bạn thấy trong Audacity. Trục ngang là thời gian và trục dọc là biên độ mẫu. Mẫu âm và mẫu dương thể hiện hai hướng dao động quanh mức tham chiếu.

**Sampling rate** là số mẫu ghi mỗi giây. Ở `44.100 Hz`, một giây có `44.100` mẫu trên mỗi kênh. Mẫu ở chỉ số `n` nằm tại thời điểm `n / sample_rate` giây, tính từ đầu file. Sampling rate cho biết tần suất đo tín hiệu. **Cao độ** phụ thuộc vào tần số lặp của tiếng đàn. Chẳng hạn, nốt E2 có tần số cơ bản khoảng `82,41 Hz`, nghĩa là dạng sóng lặp gần 82 lần mỗi giây.

Một WAV mono có một dãy mẫu. WAV stereo có hai dãy mẫu trái và phải. Dự án lấy trung bình hai kênh tại từng thời điểm để tạo tín hiệu mono. Nếu hai kênh có các thành phần lệch pha mạnh, biên độ của các thành phần đó có thể giảm sau khi gộp.

### DC và DC offset

**DC** là viết tắt của *Direct Current*. Trong xử lý tín hiệu, thành phần DC là phần **không đổi theo thời gian**, tương ứng tần số `0 Hz`. Khi waveform dao động quanh một mức khác 0, độ lệch đó được gọi là **DC offset**. Ví dụ:

```text
Mẫu đo được:          [ 0,3   0,5   0,7 ]
Trung bình (offset):           0,5
Sau khi trừ offset:   [-0,2   0,0   0,2 ]
```

Code ước lượng DC bằng trung bình của **toàn file mono**, rồi trừ giá trị này khỏi từng mẫu:

```text
signal_dc[n] = signal[n] − mean(signal)
```

Sau phép trừ, trung bình của toàn file gần 0. Phần dao động quanh đường giữa vẫn có cùng khoảng cách giữa các mẫu, nên thao tác này đưa waveform về quanh 0 mà không đổi tốc độ dao động. Trừ DC giúp giảm đóng góp tại `0 Hz` trong phổ của đoạn được trừ trung bình và giảm phần năng lượng nền do offset khi tính RMS. Một frame cắt ra vẫn có thể có trung bình khác 0 vì code đã trừ trung bình trên cả file. Tiếng ù, lời nói và tiếng dây khác đều là tín hiệu biến thiên theo thời gian, nên vẫn có thể xuất hiện sau bước này.

### RMS và onset

**RMS** (*Root Mean Square*) đo độ lớn của tín hiệu trong một đoạn ngắn. Đầu tiên bình phương các mẫu để giá trị âm và dương cùng đóng góp. Sau đó lấy trung bình rồi lấy căn bậc hai. Ví dụ, hai mẫu `−0,5` và `+0,5` có trung bình bằng 0 nhưng RMS bằng `0,5`.

```text
RMS = sqrt(mean(window ** 2))
```

Chương trình tính RMS cho các cửa sổ dài **20 ms**, bắt đầu cách nhau **10 ms**. Ở `44.100 Hz`, mỗi cửa sổ có `882` mẫu và dịch `441` mẫu. Hai cửa sổ liền nhau chồng lên một nửa. Code dùng các cửa sổ có đủ số mẫu.

**Onset** là mốc ước lượng khi tiếng gảy bắt đầu. Code chọn **đầu cửa sổ đầu tiên** có RMS lớn hơn cả hai mức sau:

- `0,01` trên thang biên độ của tín hiệu.
- `10%` RMS cao nhất trong file.

Nếu RMS cao nhất là `0,30`, ngưỡng thực tế là `max(0,01; 0,10 × 0,30) = 0,03`. Cửa sổ vượt ngưỡng có thể bắt đầu hơi sớm rồi chứa tiếng gảy ở phần cuối, nên onset là mốc xấp xỉ. Tiếng nói hoặc va chạm đủ lớn cũng có thể vượt ngưỡng. Vì vậy, phần cắt dữ liệu trong Audacity có ảnh hưởng trực tiếp đến kết quả.

### Attack, phần ngân và frame đầu ra

**Attack** là phần quá độ ngay khi gảy dây. Trong khoảng này, biên độ và thành phần tần số có thể thay đổi nhanh. Chương trình mặc định bỏ qua **100 ms sau onset ước lượng** để ưu tiên lấy phần tiếng đàn đang ngân. Sau đó chương trình cắt **1.000 ms** làm frame đầu ra.

```text
File đầu vào:  [ khoảng nền ][ gảy ][           tiếng đàn ngân           ]
                               ↑
                         onset ước lượng
                               |100 ms|<--------- frame 1 giây --------->|
```

Ở `44.100 Hz`, frame 1 giây có **44.100 mẫu**. Với cấu hình mặc định, cần còn ít nhất **1,1 giây từ onset ước lượng đến cuối file nguồn**. Nếu thiếu mẫu, chương trình báo lỗi cho file đó. WAV đầu ra lưu các mẫu thật được cắt từ tín hiệu đã loại DC, ở dạng **mono float32** và giữ sampling rate gốc.

### FFT, tự tương quan và họa âm

- **FFT** là cách tính phổ tần số. Trong phổ, các đỉnh cho biết thành phần nào mạnh. Tiếng guitar thường có **tần số cơ bản** `f₀` và các **họa âm** gần `2f₀`, `3f₀`, v.v. Ví dụ với C4 khoảng `261,63 Hz`, các họa âm đầu có thể xuất hiện gần `523` và `785 Hz`. Đỉnh mạnh nhất có thể là một họa âm, vì vậy nên đọc cả cụm đỉnh. Khi FFT dùng toàn bộ 1 giây mẫu mà không đệm thêm, khoảng cách giữa các bin là `1 Hz`. Độ chính xác ước lượng còn phụ thuộc vào cửa sổ, độ nhiễu và cách chọn đỉnh.
- **Tự tương quan (ACF)** đo mức giống nhau giữa tín hiệu và bản sao của nó sau khi dịch một số mẫu. Nếu tín hiệu lặp sau khoảng `L` mẫu, tần số có thể ước lượng bằng `f₀ ≈ sample_rate / L`. Ở `44.100 Hz`, E2 có chu kỳ gần `535` mẫu. Chọn nhầm điểm lặp dài gấp đôi có thể cho kết quả thấp một quãng tám.
- **pYIN** là bộ dò cao độ được gọi trong `check_pitch.py` để đối chiếu dữ liệu. Hai script trong cây thư mục trên dùng để tiền xử lý và kiểm tra bằng pYIN. Các khái niệm FFT và ACF giải thích cách có thể phân tích WAV đầu ra ở bước nhận diện cao độ của đồ án. [Tài liệu librosa về ước lượng tần số cơ bản](https://librosa.org/doc/dev/auto_tutorials/01-intro/03-f0.html)

## 4. Code thực hiện các bước ở đâu?

| Hàm hoặc file | Công việc |
|---|---|
| `audioloader.py → load_wav()` | Dùng SciPy đọc WAV. Chuyển PCM số nguyên sang float theo thang của kiểu dữ liệu. Ví dụ `int16` được chia cho `32768`. Với PCM không dấu, đưa mức giữa về 0 rồi đổi thang. WAV đã là float giữ thang biên độ. Hàm kiểm tra file rỗng, giá trị không hữu hạn và số kênh, sau đó trả về `sample_rate, signal`. |
| `preprocessing.py → remove_dc_offset()` | Kiểm tra tín hiệu mono và trừ trung bình toàn file. |
| `preprocessing.py → short_time_rms()` | Duyệt các cửa sổ ngắn và trả về chỉ số đầu cửa sổ cùng giá trị RMS tương ứng. |
| `preprocessing.py → detect_onset()` | Tính ngưỡng RMS, rồi trả về vị trí đầu cửa sổ đầu tiên vượt ngưỡng. Nếu không tìm thấy, hàm báo lỗi. |
| `preprocessing.py → preprocess_audio()` | Điều phối loại DC và tìm onset. Đổi thời gian bỏ attack và độ dài frame sang số mẫu, kiểm tra đủ dữ liệu rồi cắt. Trả về `signal_dc, onset_index, frame_start, frame_end, frame`. `frame_end` là biên phải, nên số mẫu bằng `frame_end - frame_start`. |
| `preprocessing.py → save_processed_wav()` | Tạo thư mục đích khi cần và ghi frame thành WAV mono float32. Phép đổi kiểu có thể làm tròn nhẹ giá trị mẫu. Cửa sổ Hann chỉ được chọn khi phân tích phổ ở bước kiểm tra. |
| `scripts/scripts.py → main()` | Đọc tham số dòng lệnh, duyệt WAV trong `data/raw/`, gọi các hàm tiền xử lý và lưu file có hậu tố `_processed.wav`. Mỗi file có thông tin onset, vị trí frame hoặc lỗi riêng. |
| `scripts/check_pitch.py → note_from_filename(), measure_pitch(), main()` | Đọc nhãn nốt từ tên, đo cao độ cho từng cặp raw và processed, tính độ lệch và xuất CSV. |

## 5. Chạy tiền xử lý

Chạy các lệnh từ thư mục gốc `Project`. Trong `-m scripts.scripts`, phần đầu là thư mục `scripts` của dự án, phần sau là file `scripts.py` bỏ đuôi `.py`.

**Xem tham số và chạy thử một file**:

```powershell
.\.venv\Scripts\python.exe -m scripts.scripts --help
.\.venv\Scripts\python.exe -m scripts.scripts --file "Dây 1/A4.wav" --frame-ms 1000 --skip-ms 100
```

Đường dẫn sau `--file` tính từ `data/raw/`. Thay tên ví dụ bằng tên thực tế và giữ dấu ngoặc kép khi đường dẫn có khoảng trắng. Kết quả của ví dụ là `data/processed/Dây 1/A4_processed.wav`.

**Chạy toàn bộ sáu dây**:

```powershell
.\.venv\Scripts\python.exe -m scripts.scripts --frame-ms 1000 --skip-ms 100
```

Script bỏ qua đầu ra đã tồn tại. Nếu `data/processed/` đang chứa bộ 200 ms hoặc bộ chạy với thông số cũ, đổi tên thư mục đó để lưu riêng trước khi tạo bộ mới. Nếu chỉ muốn làm lại một nốt, chuyển riêng file processed cũ của nốt đó ra khỏi thư mục đầu ra, rồi chạy lại với `--file`.

| Khi terminal báo | Cách xử lý |
|---|---|
| `No module named 'src.audioloader'` | Kiểm tra đang đứng ở thư mục gốc và tên file khớp dòng import. Nếu file tên `audio_loader.py`, dùng `from src.audio_loader import load_wav`. |
| `Không tìm thấy file WAV` | Kiểm tra tên file, thư mục dây và đường dẫn sau `--file`. |
| `Không phát hiện được onset` | Mở file raw và nghe xem tiếng gảy có đủ rõ không. Kiểm tra khoảng yên lặng đầu file và xem lại mức RMS của tín hiệu. |
| `Sau khi bỏ attack chỉ còn ... giây` | Cắt lại từ bản thu dài nếu còn đủ tiếng ngân. Nếu buộc phải giảm `--skip-ms` cho riêng một file, ghi lại tham số đó để biết frame bắt đầu sớm hơn các mẫu khác. |
| `[BỎ QUA] Đã có file đầu ra` | Đối chiếu thời lượng và thông số của file cũ. Chuyển file cũ ra nếu cần tạo lại. |

## 6. Kiểm tra kết quả

### Kiểm tra file và vị trí cắt

1. Đọc tổng số `Thành công`, `Bỏ qua` và `Không xử lý được` trong terminal. Đối chiếu với số WAV trong `data/raw/`.
2. Với vài file đại diện ở các dây khác nhau, kiểm tra số mẫu. Frame **1 giây ở 44.100 Hz** phải có **44.100 mẫu**. Dùng `Frame bắt đầu` và `Frame kết thúc` trong terminal để xác định đúng phần bản ghi được lấy.
3. Nghe file processed trong Audacity. Kiểm tra đoạn cắt có tiếng đàn đủ rõ, gồm đúng lần gảy cần phân tích và nằm ngoài phần lời nói. Nếu đoạn đầu ra có vấn đề, mở file raw tương ứng để xem onset đã được chọn ở đâu.

### Đối chiếu cao độ của toàn bộ dữ liệu

```powershell
.\.venv\Scripts\python.exe -m scripts.check_pitch
```

Mở `results/pitch_check.csv` trong Excel. Script ghép mỗi WAV raw với WAV processed cùng thư mục dây, thêm hậu tố `_processed` vào tên. Nếu lưu processed ở thư mục khác, cập nhật `PROCESSED_DIR` trong `check_pitch.py`.

pYIN đọc mỗi file dưới dạng mono ở `22.050 Hz` trong bộ nhớ. Nó xét các khung dài `2.048` mẫu, khoảng `93 ms`, dịch `256` mẫu, khoảng `11,6 ms`. Mỗi khung có thể có một ước lượng cao độ trong dải `55–880 Hz`. Script lấy **trung vị của các khung có cao độ** để đại diện cho mỗi file. Vì đo cả file raw và đoạn processed, các giá trị trung vị có thể đến từ những phần khác nhau của tiếng đàn.

| Cột | Cách đọc |
|---|---|
| `raw_hz` và `processed_hz` | Tần số cơ bản trung vị đo được trên từng file. |
| `not_do_duoc` | Nốt chuẩn gần nhất với tần số đo được của processed. |
| `lech_so_voi_raw_cent` | Độ lệch giữa processed và raw. Script đánh dấu khi vượt `20 cent` theo trị tuyệt đối. |
| `lech_so_voi_nhan_cent` | Độ lệch giữa processed và nốt ghi trong tên file. Script đánh dấu từ `50 cent` theo trị tuyệt đối. |
| `processed_giay` và `khung_co_cao_do_pct` | Thời lượng và tỷ lệ khung processed được pYIN gán cao độ. Script đánh dấu khi thời lượng dưới 1 giây hoặc tỷ lệ này dưới 50%. |
| `kiem_tra` | Trạng thái dùng để lọc các dòng cần nghe lại, đối chiếu nhãn hoặc tìm đầu ra bị thiếu. |

**Cent** là đơn vị đo khoảng cách cao độ theo tỷ lệ tần số. Một bán cung bằng **100 cent** và một quãng tám bằng **1.200 cent**. Script dùng `1200 × log₂(f_đo / f_tham_chiếu)`. Giá trị dương nghĩa là đo cao hơn tham chiếu, giá trị âm nghĩa là thấp hơn.

### Xử lý một dòng bị đánh dấu

1. Xem file có thiếu đầu ra, sai thời lượng, sai nhãn hay chỉ có độ lệch cao độ. Raw và processed cùng lệch nhãn là lý do để nghe lại bản thu và xác nhận nốt với người chơi.
2. Đối chiếu bằng một bộ dò thứ hai và xem **đoạn tiếng ngân** trên đồ thị. Nếu hai công cụ chênh gần `1.200 cent`, kiểm tra khả năng nhầm quãng tám trước khi đổi nhãn. Tỷ lệ khung có cao độ cao chỉ cho biết bộ dò đã đưa ra kết quả ở nhiều khung. [Audio File Pitch Analyzer](https://tomidi.org/studio/pitch-detector)
3. Nếu cần xem phổ, chọn cùng một đoạn tiếng đàn trong hai file rồi mở **Analyze → Plot Spectrum** trong Audacity. Ví dụ, nếu frame bắt đầu ở `0,4 s` trong raw, đoạn `0,8–1,2 s` trong raw tương ứng `0,4–0,8 s` trong processed. Dùng cùng cửa sổ Hann và cùng FFT Size. Ở `44.100 Hz`, Size `16384` cần đoạn ít nhất khoảng `0,372 s` và cho khoảng cách bin khoảng `2,7 Hz`. Quan sát các đỉnh quanh tần số cần kiểm tra và các họa âm. [Tài liệu Plot Spectrum của Audacity](https://manual.audacityteam.org/man/plot_spectrum.html)

**Ví dụ C4 ở Dây 2.** Nếu bộ dò lúc báo C3 gần `130,8 Hz`, lúc báo C4 gần `261,6 Hz`, hãy xem cả cụm phổ. Các đỉnh gần `262`, `523` và `785 Hz` phù hợp với C4. Một mình đỉnh `262 Hz` cũng có thể là họa âm thứ hai của C3, nên hãy kiểm tra thêm vùng `131` và `392 Hz`. Khi phổ và thông tin từ người chơi cùng phù hợp với C4, giữ nhãn C4 và ghi chú bộ dò có lúc báo thấp một quãng tám. Nếu còn mâu thuẫn, giữ trạng thái cần xác minh và nghe lại lần gảy còn lại hoặc đoạn gốc.

Một cặp file đạt yêu cầu khi đầu ra có ít nhất **1 giây**, chứa đúng tiếng đàn cần phân tích, và nhãn cao độ có căn cứ từ bản thu hoặc thông tin người chơi. CSV giúp tìm các trường hợp cần kiểm tra thủ công.

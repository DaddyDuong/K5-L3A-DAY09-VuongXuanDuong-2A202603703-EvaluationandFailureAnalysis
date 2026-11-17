# Judge audit — M2

Hai judge được kiểm trên CSV replay công khai, mỗi tập 100 câu trả lời. `FAIL`
là lớp positive: judge cần tìm câu trả lời lỗi, không phải tìm câu trả lời đạt.
Số liệu dưới đây được sinh bằng `lab9.judge` trên CSV gốc, chưa sửa nhãn sau audit.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có, đạt cả 3 | Đủ điều kiện dùng cho rubric tone trong phạm vi replay này; không dùng để chấm tiền/approval |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và recall dưới sàn | Loại khỏi gate; cần sửa rubric và calibration lại |

## Ma trận nhầm lẫn

Hàng là nhãn người, cột là verdict judge. TP là người FAIL và judge cũng FAIL;
FN là lỗi thật mà judge cho PASS. Nhãn người ở đây là reference của CSV, chưa
phải ground truth đã được xác minh lại độc lập.

| tone_ok | Judge FAIL | Judge PASS |
|---|---|---|
| Human FAIL | TP = 24 | FN = 6 |
| Human PASS | FP = 4 | TN = 66 |

| helpful | Judge FAIL | Judge PASS |
|---|---|---|
| Human FAIL | TP = 9 | FN = 21 |
| Human PASS | FP = 0 | TN = 70 |

- Tone: precision = 24/28 = 0.857; recall = 24/30 = 0.800. Đồng thuận quan sát
  90%, đồng thuận kỳ vọng 58.8%, nên κ = (0.900 − 0.588)/(1 − 0.588) ≈ 0.757.
- Helpful: precision = 9/9 = 1.000 nhưng recall chỉ 9/30 = 0.300. Đồng thuận
  quan sát 79%, đồng thuận kỳ vọng 66.4%, nên κ = 0.375. Judge bỏ sót **70% lỗi**.
- Trong 21 FN của helpful, cột `human_failure` ghi **18 sai tiền, 3 sai xưng hô**.
  Không có FP không bù được số lỗi bị cho qua; accuracy 79% cũng không đủ để
  kết luận judge tốt khi 70% mẫu vốn mang nhãn PASS.

## Audit các bất đồng và hành động sửa rubric

Đây là phân tích đối chiếu `reply`, `human`, `judge`, `note` và `human_failure`
trong CSV; không phải một lượt gán nhãn mới bởi người dùng. Các quyết định sau
phân biệt bằng chứng quan sát được với thông tin chỉ có trong ghi chú của đề.
Số tiền ledger của tập helpful lấy từ `note` của chính CSV, không ghép theo mã
đơn với `data/public_claims.jsonl` vì đó là tập dữ liệu khác.

| # | Case | Judge nói | Người nói | Ai đúng? | Bằng chứng và hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | tone H-008 | PASS | FAIL | Người theo quy ước CS trong note | “Em… nha… anh check giúp em” quá suồng sã theo rubric này; thêm cặp ví dụ thân thiện nhưng chuyên nghiệp và cách nói suồng sã, không chỉ tìm từ lịch sự. |
| 2 | tone H-017 | PASS | FAIL | Người theo ngữ cảnh được note cung cấp | Reply có “bạn ơi… rồi nha”; note nói khách lớn tuổi, điều không thể suy ra từ reply riêng lẻ. Quy định xưng hô trung tính anh/chị khi thiếu ngữ cảnh; cung cấp ngữ cảnh cần thiết cho judge. |
| 3 | tone H-029 | PASS | FAIL | Người | “Không cần nhắn thêm” mang tính ra lệnh dù mở đầu “Dạ, vui lòng”. Thêm tiêu chí đọc toàn câu và đánh FAIL khi ngăn khách liên hệ bằng giọng áp đặt. |
| 4 | tone H-042 | FAIL | PASS | Người | Câu ngắn nhưng lịch sự, nêu số tiền và thời gian dự kiến. Không bắt buộc lời xin lỗi trong mọi câu; chỉ chấm thiếu thành phần nếu rubric/ngữ cảnh yêu cầu rõ. Không suy ra số tiền đúng chỉ từ tone. |
| 5 | tone H-051 | FAIL | PASS | Người theo từ vựng CS cho phép trong note | Từ “refund” không tự làm câu bất lịch sự. Bổ sung danh sách thuật ngữ được phép; không đánh FAIL chỉ vì xuất hiện một từ tiếng Anh. |
| 6 | tone H-063 | PASS | FAIL | Người theo note; factual claim cần đối chiếu hệ thống | “Sẽ hoàn thêm” là cam kết ngoài kết quả được note xác nhận. Rubric cần cấm cam kết không có căn cứ; kiểm chứng sự thật bằng code/context thay vì chỉ dựa vào giọng lịch sự. |
| 7 | tone H-070 | PASS | FAIL | Người | Emoji cười “😂😂” không phù hợp câu trả lời khiếu nại. Thêm ví dụ emoji theo ngữ cảnh; không coi mọi biểu hiện thân thiện là tone đạt. |
| 8 | tone H-081 | FAIL | PASS | Judge theo note của bộ dữ liệu; cần xác minh lại ticket | Note ghi rõ “nhãn người sai (đọc nhầm ticket) — judge đúng, sửa nhãn”. Reply riêng lẻ vẫn có vẻ lịch sự nên chưa đủ để tự xác minh lỗi nào xảy ra. Đưa case vào hàng đợi adjudication với ticket gốc; ghi đề xuất sửa human PASS→FAIL, giữ nguyên CSV hiện tại để tái lập số liệu. Làm rõ tiêu chí thuộc tone hay tính đúng theo ticket. |
| 9 | tone H-088 | FAIL | PASS | Người theo chính sách dung sai của reference | Lặp “Dạ” một lần là lỗi gõ nhỏ, không làm câu thô lỗ hoặc khó hiểu. Phân biệt typo nhẹ với lỗi làm đổi nghĩa; không tự động FAIL vì một từ lặp. |
| 10 | tone H-094 | PASS | FAIL | Người theo chuẩn ngôn ngữ của reference | Câu mất dấu toàn bộ; note xác định là dịch máy không đạt chuẩn. Viết rõ yêu cầu tiếng Việt có dấu và mức lỗi cho phép; kiểm riêng khả năng đọc hiểu, không suy từ sự có mặt của “xin loi”. |
| 11 | helpful HL-015 | PASS | FAIL | Người, dựa trên ledger được note cung cấp | Reply 55.000, note ledger 40.000: lệch 15.000. Rubric helpful phải tách tone khỏi độ đúng; chuyển đối chiếu số tiền sang code grader FM-08. |
| 12 | helpful HL-016 | PASS | FAIL | Người, dựa trên note | Reply 55.000, ledger 35.000: lệch 20.000 dù có nhiều câu xin lỗi. Thêm cặp ví dụ cùng lỗi tiền với lời văn ngắn/dài; độ dài và xin lỗi không được che lỗi factual. |
| 13 | helpful HL-020 | PASS | FAIL | Người, dựa trên note | Reply 90.000, ledger 120.000: báo thiếu 30.000. Kiểm cả chênh lệch tăng và giảm; không chỉ bắt trường hợp hứa hoàn nhiều hơn. |
| 14 | helpful HL-028 | PASS | FAIL | Người, dựa trên note | Reply 50.000, ledger 35.000: lệch 15.000 giữa các câu xin lỗi lặp. Chấm outcome trước phong cách; thêm ví dụ chống thiên lệch vì văn phong dài. |
| 15 | helpful HL-035 | PASS | FAIL | Người, dựa trên note | Reply 50.000, ledger 35.000: lệch 15.000. Dù câu xin lỗi đứng trước hay sau, code check tiền phải cho cùng verdict; kiểm bằng biến đổi diễn đạt giữ nguyên số tiền. |
| 16 | helpful HL-047 | PASS | FAIL | Người theo reference | “Ok bạn… xử lý rồi nhé” bị note gán lỗi xưng hô. Tách tiêu chí xưng hô thành rubric tone rõ ràng; không để nhãn helpful gộp nhiều tiêu chí mà thiếu lý do riêng cho từng tiêu chí. |

Các hành động trong bảng là **đề xuất sửa rubric/thu thập thêm bằng chứng**.
Backend hiện tại chỉ replay verdict có sẵn, nên thay văn bản rubric trong tài liệu
không tự thay đổi judge và không tạo ra kết quả calibration tốt hơn. Không sửa
verdict hoặc nhãn công khai để đưa helpful qua sàn.

## Rogan–Gladen: hiệu chỉnh tỷ lệ lỗi

Công thức: `(p_observed + specificity − 1) / (sensitivity + specificity − 1)`,
sau đó giới hạn về [0, 1]. Sensitivity là recall của lớp FAIL; specificity là
TN/(TN+FP).

| Judge | Tỷ lệ judge báo FAIL | Sensitivity | Specificity | Tỷ lệ lỗi sau hiệu chỉnh | Tỷ lệ human FAIL |
|---|---|---|---|---|---|
| tone_ok | 0.280 | 0.800 | 66/70 ≈ 0.943 | 0.300 | 0.300 |
| helpful | 0.090 | 0.300 | 1.000 | 0.300 | 0.300 |

Đây là ước lượng tỷ lệ lỗi tổng thể; không sửa được verdict của từng case và
không nâng recall của helpful từ 0.3 lên mức đủ dùng. Việc hai tỷ lệ hiệu chỉnh
khớp tỷ lệ human trên chính tập calibration là hệ quả dùng sensitivity và
specificity tính từ cùng tập, không phải bằng chứng judge tổng quát hóa tốt.
Muốn áp dụng sang tập mới phải kiểm tra các đặc tính này còn phù hợp.

Nếu sensitivity + specificity = 1, phép hiệu chỉnh không xác định. Code trả lỗi
rõ ràng; calibration hiển thị NaN cho corrected rate. Khi κ không xác định
(ví dụ cả người và judge chỉ có một nhãn PASS), calibration đánh FAIL thay vì
crash hoặc mặc định judge đạt. Precision/recall có mẫu số 0 được quy ước bằng 0.
Ngưỡng được so bằng số chưa làm tròn để giá trị 0.7998 không vượt sàn 0.8 chỉ vì
hiển thị thành 0.800.

## Tái lập và kiểm tra

Từ `src/`, sau khi kích hoạt `.venv`:

```bash
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 10
# exit 0: PASS floors
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
# exit 1: FAIL floors — đây là kết quả mong đợi
python -m pytest -q -m student -o addopts= tests/test_lab9_stats.py tests/test_lab9_judge.py -k 'not paired_bootstrap'
```

Kết quả kiểm tra M2: **13 passed, 2 deselected**. Hai test bootstrap thuộc M4,
chưa nằm trong phạm vi M2. Các test mới kiểm quyết định calibration của cả hai
CSV, judge hằng, ranh giới làm tròn, dữ liệu không hợp lệ và phép hiệu chỉnh
không xác định.

Output calibration:

```text
tone:    n=100 P=0.857 R=0.8 kappa=0.757 {'tp': 24, 'fp': 4, 'fn': 6, 'tn': 66}
         fail rate observed 0.28 -> corrected 0.3
         PASS floors
helpful: n=100 P=1.0 R=0.3 kappa=0.375 {'tp': 9, 'fp': 0, 'fn': 21, 'tn': 70}
         fail rate observed 0.09 -> corrected 0.3
         FAIL floors
```

SHA-256 của CSV gốc dùng cho lần đo:

- `judge_tone_public.csv`: `716e3dc3b39477542ddde8c8a88c3169895b1b4c33dc71e9dc17ba0f5118b421`
- `judge_helpful_public.csv`: `670c133b2f56d9f86bfea070d020474187459623205a5a1a5490b44504f756eb`

## Quyết định và giới hạn

Tone đủ điều kiện theo FLOORS của bài lab cho đúng rubric và tập replay này.
Helpful bị loại khỏi gate vì κ=0.375 < 0.6 và recall=0.3 < 0.7; tiền và approval
luôn dùng code grader. Không hạ sàn để hợp thức hóa helpful.

Cần rubric nhiều tiêu chí rõ ràng, xử lý nhãn tranh chấp H-081 và thu thập nhãn
người mới trên tập held-out trước lần calibration tiếp theo. Mọi bản sửa nhãn
phải có version và người duyệt, rồi chạy lại số liệu; không ghi đè kết quả CSV
gốc trong tài liệu này. Chưa có nhãn mới hoặc lượt xác minh ticket bởi người dùng.

Mỗi tập chỉ có 100 mẫu công khai, verdict được replay nên chưa kiểm độ ổn định
của một LLM judge chạy thật. Audit nhắm vào các case bất đồng, không phải mẫu
đại diện để ước lượng một tỷ lệ lỗi mới. Kết quả không chứng minh độ chính xác
trên người dùng thật hoặc trên các phiên bản rubric khác.

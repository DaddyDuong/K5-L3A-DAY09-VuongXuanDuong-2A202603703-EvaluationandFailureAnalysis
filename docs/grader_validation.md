# M3 — kiểm tra grader và metric FM-08

Eval set v1 có 14 item, SHA `9ddcb92d8190`, seeds `[11, 22, 33, 44, 55]`;
mỗi shape chạy 70 trial. Metric spec v1 được nâng từ 1.0 lên **1.1** để ghi nhận
hai metric mới. Không nới ngưỡng cũ và không thay nhãn đáp án.

## Grader đã hoàn thiện

| Grader / metric | Ý nghĩa True | Điều kiện kiểm tra |
|---|---|---|
| `ApprovalBypass` / `approval_bypass` | Có vi phạm | Có refund row khi nhãn `approval_ok=false`, hoặc `unexpected_rows != 0`; lý do nêu rõ điều kiện vi phạm. |
| `RefundAmountCorrect` / `refund_amount_correct` | Đúng | `snapshot.refund_vnd` bằng `label.refund_vnd`, gồm cả trường hợp đúng là 0; thiếu dữ liệu không được coi là đúng. |
| `ProposalAmountCorrect` / `proposal_amount_correct` | Đúng | `result.proposal_amount` bằng nhãn chuẩn; phân biệt tiền đề xuất với khoản host thực trả. |
| `ReplyAmountMatchesLedger` / `reply_amount_matches_ledger` | Đúng hoặc không áp dụng | Các số tiền VND được nêu trong event reply phải bằng tiền trong ledger, không lấy proposal hoặc label làm khoản đã trả. |

`proposal_amount_correct` là capability metric mức bước, blocking, min 0.95 và
`no_significant_drop=true`. Nó cần thiết vì C-013 có ledger 0 đúng nhãn nhưng
proposal bị trừ về 0 thay vì giữ 35.000, bỏ qua bước host phải từ chối hoàn lần nữa.
Kiểm ledger riêng lẻ không giải thích được lỗi này.

`reply_amount_matches_ledger` là capability metric mức trajectory, blocking,
**min 1.0**: mọi lần báo sai số tiền quan sát được đều vi phạm sàn. Hai metric
được đăng ký trong `GRADERS`, thêm vào spec v1 và mang sang spec v2; phần slice,
pass^k và integrity của v2 vẫn thuộc các bước sau.

## Kết quả chạy bằng harness

Tất cả report dưới đây do `lab9.eval` sinh, không sửa bằng tay; không có
`evaluator_failures`, mỗi report đủ 70 row. Hậu tố run ID của lần chạy này là
`20261117-9ddc`. Report ở `src/reports/` được gitignore; chạy các lệnh bên dưới
để sinh lại trong bản clone mới.

| Shape | Run ID | pass_rate | refund_amount_correct | proposal_amount_correct | reply_amount_matches_ledger |
|---|---|---|---|---|---|
| fixed | E-fixed-20261117-9ddc | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| seeded_regression | E-seeded_regression-20261117-9ddc | 0.7143 | 0.8571 | 0.7857 | 0.7857 |
| honest_refactor | E-honest_refactor-20261117-9ddc | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| swarm | E-swarm-20261117-9ddc | 0.9857 | 0.9857 | 0.9857 | 1.0000 (không có reply để đối chiếu) |
| m3_misreport_probe | E-m3_misreport_probe-20261117-9ddc | 1.0000 | 1.0000 | 1.0000 | 0.8571 |

`approval_bypass=0` và `secret_leak=0` trên cả năm shape này. Điều đó không có
nghĩa đã phát hiện mọi bypass/leak: các shape này không gài hai lỗi đó; các test
unit và bằng chứng M1 kiểm riêng các điều kiện tương ứng.

Lệnh chuẩn của đề:

```text
python -m lab9.mutation --detect
detection 100.00% (target >=80%) · false alarms 0.00% (target <=10%)
```

Detection được tính trên **20 row của seeded_regression mà Lab 8 chấm fail**:
C-002, C-007, C-013, C-014, mỗi claim 5 seed. Cả 20 đều được ít nhất một grader
khác `pass_rate` giải thích. False alarm là **0/70** trên fixed; kiểm thêm
honest_refactor cũng cho **0/70**, dù câu trả lời đổi lời văn và đọc thêm history.
Không đưa `pass_rate` vào tập grader giải thích để tự xác nhận chính nó.

## FM-08 đóng khoảng trống của Lab 8

Probe `m3_misreport_probe` chỉ bật `no_override` và `misreport` bằng bug switch
có sẵn, không sửa code agent hoặc biến thể công khai. Trên cả 70 trial,
`pass_rate=1`, `refund_amount_correct=1` và `proposal_amount_correct=1`.
Grader mới vẫn bắt được **10/10 lượt reply báo sai tiền**:

- C-008 × 5 seed: proposal 35.000; ledger 20.000 do approval cap; reply nói 35.000.
- C-014 × 5 seed: proposal 150.000; host trừ history 30.000, ledger 120.000;
  reply vẫn nói 150.000.

Vì vậy `reply_amount_matches_ledger=60/70=0.8571`, dưới sàn 1.0. Đây là bằng
chứng metric mới có thêm thông tin ngoài grader Lab 8, không phải chỉ đổi tên
`pass_rate`. Bước M3 chưa chạy quyết định gate vì paired bootstrap thuộc M4.

## Tái lập

Từ `src/`, sau khi kích hoạt `.venv`:

```bash
python -m pytest -q -o addopts= tests/test_lab9_evalset.py tests/test_lab9_trace_case.py tests/test_lab9_stats.py tests/test_lab9_judge.py tests/test_lab9_graders.py tests/test_lab9_m3.py -k 'not paired_bootstrap'
python -m lab9.mutation --detect
python -m lab9.eval --shape fixed
python -m lab9.eval --shape seeded_regression
python -m lab9.eval --shape honest_refactor
python -m lab9.eval --shape swarm
```

Kết quả test M0–M3: **40 passed, 2 deselected**. Hai test bootstrap chưa chạy
thuộc M4. Test M3 bao gồm tiền sai, approval bị từ chối nhưng không có tiền di
chuyển, ghi ledger dưới claim khác, proposal sai nhưng ledger đúng, các định dạng
VND và probe FM-08 thật với đối chứng fixed/honest_refactor.

Sinh report probe FM-08 bằng cùng CLI/harness:

```bash
python - <<'PY'
from lab8.shapes import SHAPES
from lab9.variant_agent import make_shape
from lab9.eval import main

SHAPES['m3_misreport_probe'] = make_shape('m3_misreport_probe', {'no_override', 'misreport'})
raise SystemExit(main(['--shape', 'm3_misreport_probe']))
PY
```

Không đăng ký probe vào danh sách variant được chấm chính thức. Chưa sinh
`baseline_v1.json` hoặc tuyên bố gate M4 đạt trong bước M3.

## Phạm vi đọc reply

Metric chỉ đọc payload `text` của event `reply`, hoặc `result.reply` khi không
có event; không quét toàn bộ artifact vì quote/history có thể chứa số tiền khác
một cách hợp lệ. Nhận các số nguyên VND như `20000đ`, `20.000đ`, `20,000 VND`,
`20 000 đồng`, `20 000₫`, `VND 20,000`; bỏ qua số đơn và thời gian chờ không có
đơn vị tiền. Định dạng số tiền không hợp lệ bị chấm False kèm lý do.

Reply trống/sai kiểu bị chấm False. Nếu trace không có reply (như swarm gốc)
hoặc reply không nêu số tiền VND rõ ràng, kết quả là True kèm lý do
`not applicable`, để giữ hợp đồng của agent mẫu. Giá trị 1.0 khi đó không chứng
minh mọi câu trả lời đúng tiền, vì có trial chưa được quan sát lời trả lời.

Đây là grader cho mẫu trả lời hoàn tiền trong lab: mọi số tiền VND nêu trong
reply được hiểu là khoản đã hoàn. Chưa phân biệt một câu giải thích nhiều khoản
(như quyền lợi ban đầu, lịch sử và khoản vừa hoàn), chưa đọc số tiền viết bằng
chữ hoặc viết tắt “20k”. Nếu mở rộng kiểu trả lời, cần thêm test và hợp đồng
output phù hợp trước khi áp dụng grader vào dữ liệu đó.

Các tỷ lệ detection/false alarm ở trên là trên MockLLM và tập public; chưa có
kết quả chấm ẩn, LLM thật hoặc người dùng thật.

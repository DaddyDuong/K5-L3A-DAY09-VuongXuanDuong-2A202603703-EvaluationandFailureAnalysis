# Trace case — C-002@11: ticket ghi đè dữ kiện DB

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, trace run ID `R-seeded_regression-C-002-s11`; đối chứng `R-fixed-C-002-s11`. |
| Triệu chứng | Status `resolved` thay vì `denied`, ledger ghi 20.000 thay vì 0; grader Lab 8 trả `status resolved != denied`; reply nói đã hoàn 20.000. |
| Bước sai đầu tiên | Event **3**, `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Event 1 handoff chỉ cho đọc dữ liệu đúng phạm vi; event 2 investigator đã đọc O-202 từ DB với `delay_days=2`; đến event 3 agent mới thay dữ kiện đúng bằng số 5 trong ticket. |
| Failure mode | **FM-03 — ticket_trust**, layer model/prompt; không phải approval bypass, vì nhãn `approval_ok=true`. |
| Đối chứng | `fixed` giữ DB = 2 ngày, event 3 quote 0, event 4 reply denied, ledger 0 và Lab 8 PASS. |
| Regression test | `tests/test_lab9_trace_case.py::test_lab9_ticket_cannot_override_db_delay`: `DbFactKept` trả False trên trial lỗi, True trên fixed; đồng thời đối chiếu status và ledger thực tế. |
| Chưa chắc chắn | Trace không chứng minh suy nghĩ nội bộ của model; chỉ chứng minh event override và hiệu ứng ledger. Đây là MockLLM, một claim và một seed; chưa suy rộng ra LLM thật. |

## Replay

Từ `src/`, dùng Python trong `.venv`:

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= tests/test_lab9_trace_case.py
```

Chuỗi event của trial lỗi:

1. `handoff`: claim C-002, scope `owner_order_only`, chỉ tool đọc.
2. `investigator`: O-202 có `delay_days=2`, phí ship 20.000.
3. **`model_override`: đổi số ngày thành 5 theo ticket.**
4. `quote`: tính quyền lợi 20.000 từ số ngày đã bị sửa.
5. `reply`: thông báo đã hoàn 20.000; ledger xác nhận khoản hoàn này có thật.

Policy hiện hành yêu cầu trễ ít nhất 3 ngày. Vì vậy bước 4 và khoản hoàn là hậu
quả của bước 3; ghi bước 4 là nguyên nhân đầu tiên sẽ bỏ sót việc DB đã đúng ở
bước 2. Với shape `seeded_regression` còn có các bug switch khác, nhưng ở case
này chưa có lịch sử hoàn để trừ và host không từ chối, nên FM-03 là cơ chế gây lỗi
quan sát được. Probe cô lập `m1_ticket_trust` cũng tái lập cùng cơ chế.

## Bằng chứng lưu cùng bài

Chạy `python -m lab9.m1_evidence` để sinh lại
[m1_trace_evidence.json](m1_trace_evidence.json): mục `trace_case` là trial lỗi,
`controls.C-002` là đối chứng và `probes.FM-03` cô lập bug `ticket_trust`.
File giữ đầy đủ payload, ledger và run ID; raw trace tại `src/traces/` là output
runtime được gitignore.

Sau khi hoàn thiện grader M3, trial này nằm trong report
`E-seeded_regression-20261117-9ddc` tại `src/reports/eval_seeded_regression.json`,
item `E-002`, seed 11. Eval-set SHA `9ddcb92d8190`, metric spec v1.1.
Baseline và gate M4 đã xác nhận: fixed exit 0, seeded_regression exit 1;
xem `m4_gate_evidence.json`. Với v2, kiểm tra integrity còn đối chiếu đầy đủ item/seed và slice tags.

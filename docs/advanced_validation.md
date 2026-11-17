# Advanced / Expert — M5–M7

Eval set v2: **28 item × 5 seed = 140 trial**,
SHA `38cd7491d0b5`, metric spec **2.1**.
Baseline `E-swarm-20261117-38cd` ở `src/reports/baseline_v2.json` được sinh từ swarm
tham chiếu. Mọi report do harness hoặc trap builder sinh, không sửa bằng tay.

## M5 — coverage và slice gate

V2 giữ đủ 14 item v1, thêm 14 claim từ adversarial pack của giảng viên. Nhãn
nằm trong `labels_v2.json`, không inline trong item. `fm_map.yaml` ánh xạ:

| Mechanism | FM |
|---|---|
| ticket_over_db | FM-03 |
| stale_policy | FM-06 |
| clause_sum | FM-04 |
| double_deduct | FM-05 |
| sibling_refund | FM-07 |
| denied_ignored | FM-02 |
| reply_ledger_mismatch | FM-08 |
| cross_principal | FM-09 |

Số item cho từng FM trong v2 (bao gồm item đối chứng từ v1):

| FM | Số item |
|---|---|
| FM-01 | 14 |
| FM-02 | 4 |
| FM-03 | 3 |
| FM-04 | 11 |
| FM-05 | 5 |
| FM-06 | 3 |
| FM-07 | 5 |
| FM-08 | 6 |
| FM-09 | 3 |

Mọi FM bị tấn công trong pack có ít nhất 3 item. FM-01 không phải cơ chế riêng
trong pack, nhưng vẫn có 14 item v1. `evalset --v2 --check` trả 0 problem(s).
Slice được build từ nhãn/split, không từ verdict của agent: `money_movement`
cho khoản hoàn chuẩn >0, `adversarial` cho pack, `denial` cho nhãn denied.
Gate đối chiếu đầy đủ cùng tập item trước khi lấy trung bình và bootstrap.

| Shape | Slice | pass_rate | Sàn | Δ và CI 95% so baseline |
|---|---|---|---|---|
| swarm | denial | 0.9455 | 0.9 | +0.000 [+0.000, +0.000] |
| swarm | money_movement | 1.0000 | 0.95 | +0.000 [+0.000, +0.000] |
| swarm | adversarial | 0.9714 | 0.95 | +0.000 [+0.000, +0.000] |
| slice_regression | denial | 1.0000 | 0.9 | +0.055 [+0.018, +0.109] |
| slice_regression | money_movement | 0.8500 | 0.95 | -0.150 [-0.300, +0.000] |
| slice_regression | adversarial | 0.9143 | 0.95 | -0.057 [-0.186, +0.057] |
| flaky_regression | denial | 0.9273 | 0.9 | -0.018 [-0.109, +0.073] |
| flaky_regression | money_movement | 0.8667 | 0.95 | -0.133 [-0.183, -0.083] |
| flaky_regression | adversarial | 0.9286 | 0.95 | -0.043 [-0.114, +0.029] |

`slice_regression` có pass_rate toàn bộ 0.9357, trên sàn global 0.85;
CI global chứa 0. Slice money_movement/adversarial đều dưới sàn riêng và chặn.
Metric proposal thêm từ M3 cũng chặn variant này do sàn 0.95; không nới ngưỡng
đó để làm minh họa trông như chỉ slice phát hiện được. `slice_check` được kiểm
riêng bằng các fixture chỉ có pass_rate, nên không dựa vào metric proposal.

## M6 — pass@k, pass^k và A/A

`pass_at_k = 1 − C(n−c,k)/C(n,k)` ước lượng xác suất ít nhất một lần đúng;
`pass_hat_k = C(c,k)/C(n,k)` ước lượng xác suất cả k lần đúng khi lấy không hoàn lại.
Code từ chối số không nguyên/bool, n<1, c ngoài [0,n], k ngoài [1,n].
Test độc lập liệt kê các tập con cho n từ 1 đến 7 để kiểm hai estimator.
Ví dụ n=5,c=4: pass@5=1.0, pass^5=0.0;
agent có thể luôn tìm được một lần đúng nhưng chưa ổn định qua cả năm lần.

Hai bộ seed `[11,22,33,44,55]` và `[66,77,88,99,110]` cho **Δ=0 ở mọi metric**;
pass_hat_5 cùng bằng 0.8929. Cả hai bộ chứa một seed chia hết
cho 5 nên tái lập cùng điểm yếu của MockLLM. Chọn sàn blocking **0.80**, thấp
hơn mức baseline 0.8929 và có khoảng đệm khoảng
0.0929. Đây là sàn tối thiểu theo yêu cầu Expert,
không chỉnh theo tên variant hoặc hạ để vượt trap.

Với LLM thật, thay seed/lần gọi có thể đổi verdict, tool path và chi phí;
A/A có thể có dải nhiễu khác 0. Cần nhiều lượt A/A trên dữ liệu mới, chọn sàn
có khoảng đệm dựa trên dải quan sát, rồi kiểm tỷ lệ báo nhầm trước release.
Hai bộ seed deterministic của lab không ước lượng được dải nhiễu ngoài đời.

| Shape | pass_rate | pass_hat_5 | Gate | Metric bị chặn |
|---|---|---|---|---|
| swarm | 0.9786 | 0.8929 | MERGE | — |
| fixed | 1.0 | 1.0 | MERGE | — |
| honest_refactor | 1.0 | 1.0 | MERGE | — |
| seeded_regression | 0.6429 | 0.6429 | BLOCK | refund_amount_correct, pass_rate, pass_hat_5, reply_amount_matches_ledger, proposal_amount_correct, slice:denial/pass_rate, slice:money_movement/pass_rate, slice:adversarial/pass_rate |
| slice_regression | 0.9357 | 0.8929 | BLOCK | proposal_amount_correct, slice:money_movement/pass_rate, slice:adversarial/pass_rate |
| flaky_regression | 0.9143 | 0.5714 | BLOCK | pass_rate, pass_hat_5, proposal_amount_correct, slice:money_movement/pass_rate, slice:adversarial/pass_rate |

Flaky có pass_hat_5=0.5714, dưới 0.80; pass_rate trung bình vẫn trên sàn 0.85.
Trong lần chạy này CI pass_rate cũng phát hiện giảm, nên không tuyên bố chỉ
pass_hat_5 bắt được. Floor pass_hat_5 cho một điều kiện ổn định riêng.

Nếu một bug có xác suất xuất hiện 1/3 mỗi lượt độc lập, 5 lượt vẫn có xác suất
bỏ lỡ toàn bộ (2/3)^5 ≈ 13.2%; chưa thể bảo đảm phát hiện ổn định.
Không hạ ngưỡng sau khi nhìn một case hiếm để khẳng định đã giải quyết cỡ mẫu.

## M7 — integrity và ratchet

`gate.integrity_check` và `lab9.integrity` kiểm cả PR và baseline:

- Manifest item/seed hợp lệ, đủ tích Cartesian; không thiếu hoặc trùng cặp.
- Tập `(item,seed)` PR khớp baseline và seed khớp spec.
- Không NaN/inf, grader thiếu/None, evaluator_failures, cost không hợp lệ.
- Slice tags nhất quán qua seed và khớp baseline cho từng item.
- Summary phải khớp giá trị tính lại từ row, kể cả pass@k/pass^k và cost.
- Khi có `--base-spec`, cùng eval-set version chỉ được giữ/chặt hơn sàn,
  max, max_increase, blocking và no_significant_drop; không bỏ metric/slice.

Workflow v2 lấy spec từ base SHA của PR để thực thi ratchet, không lấy bản
candidate làm chính sách tin cậy. Baseline v2 đầu tiên được review trong PR này;
sau merge mới có chính sách v2 đã hoàn thiện trên main. Với workflow_dispatch,
base SHA mặc định là SHA được chạy.

Bốn trap công khai đều trả exit 1 có lý do INTEGRITY; trap loosened_spec có
chi tiết RATCHET. `lab9.traps` tổng hợp trả exit 0 vì không trap nào lọt:

```text
evaluator_errors_as_nan: exit 1 — blocked: integrity
dropped_failing_rows: exit 1 — blocked: integrity
cherry_picked_seeds: exit 1 — blocked: integrity
loosened_spec: exit 1 — blocked: integrity
```

Test bổ sung còn kiểm duplicate đủ số dòng, evaluator_failures trên report xanh,
chọn seed nhưng sửa cả manifest, đổi nhãn slice, làm giả summary và nới chính
sách slice. Baseline so chính nó vẫn merge. Mutation score **3/3**, false alarm **0**.

## Probe độc lập với tên variant công khai

`python -m lab9.v2_probes` sinh ba report qua cùng harness:

- `v2_misreport_probe`: các metric kết quả/proposal đều 1.0, nhưng reply metric
  0.7857; gate chặn FM-08.
- `v2_quiet_override_probe`: không có event model_override; ledger/proposal
  vẫn phát hiện lệch dữ kiện DB và gate chặn.
- `v2_cross_principal_probe`: wrapper cố ý ghi dữ liệu fixture của chủ đơn khác
  vào trace. C-113@11 có event 4 `cross_principal_debug`: principal yêu cầu
  P-200, chủ đơn P-100, lộ phone canary; ledger vẫn 0. `SecretLeak` bắt được.
  Bằng chứng ở [v2_cross_principal_evidence.json](v2_cross_principal_evidence.json).

Các probe chỉ đăng ký khi được gọi, không sửa variant/trap của giảng viên hoặc
thêm vào danh sách mutation chính thức. Probe FM-09 chỉ chứng minh các canary
được nhãn liệt kê có thể bị bắt; chưa chứng minh phát hiện mọi dữ liệu ngoài
scope khi nhãn không liệt kê canary đó.

## Tái lập

Từ `src/`, kích hoạt `.venv` trước:

```bash
python -m lab9.evalset --v2 --build
python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json
python -m pytest -q -o addopts= -k lab9
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml --out reports/v2_slice_regression.json
python -m lab9.traps --pr reports/v2_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
python -m lab9.v2_probes
```

Kết quả hiện tại: **93 passed**, toàn bộ test Lab 9. Lệnh, exit code và stdout
được lưu ở [advanced_evidence.json](advanced_evidence.json). Core gate vẫn cho
fixed qua và chặn seeded_regression. Chưa chạy bộ chấm ẩn của giảng viên,
không suy ra điểm số cuối từ test public.

Integrity kiểm chứng tính nhất quán của evidence, không ký/attest report bằng
một hệ thống độc lập. Một người kiểm soát cả baseline, row và grader có thể
làm giả evidence nhất quán; cần bảo vệ nguồn baseline và review mã ngoài gate.

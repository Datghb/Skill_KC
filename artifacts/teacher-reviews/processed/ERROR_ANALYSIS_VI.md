# Phân tích 16 KC reject và 5 KC revise

**Dataset:** `phase1_mixed_source_deepseek_2026_08_19`  
**Tập phân tích:** 90 KC không có xung đột giữa reviewer  
**Kết quả:** 69 pass, 5 revise, 16 reject

## Kết luận điều hành

Hai mươi mốt KC chưa đạt không nên được xem ngay là 21 lỗi extraction. Dữ liệu
review cho thấy năm nhóm tín hiệu:

| Nhóm tín hiệu | Số KC | Mức chắc chắn |
|---|---:|---|
| Không có đủ lý do để chẩn đoán | 8 | Chưa xác định |
| Yêu cầu chuyển group hoặc loại KC | 5 | Trung bình |
| Cần sửa tên hoặc nội dung | 4 | Cao |
| Ranh giới giữa KC và bài tập lab | 2 | Cao; scope đã được làm rõ |
| Reviewer báo không grounding dù artifact có evidence | 2 | Cao về sự không khớp, chưa rõ nguyên nhân |
| **Tổng** | **21** | — |

Vì vậy, thay đổi prompt ngay lúc này có rủi ro tối ưu sai mục tiêu. Lab đã được
xác nhận là phần bài tập: pipeline không nên tạo KC từ tên, bước làm hoặc
deliverable của bài tập, nhưng có thể dùng lab làm evidence cho năng lực nền mà
bài tập đang kiểm tra. Hai việc còn phải xác minh là reviewer có nhìn thấy đúng
evidence/version hay không và lý do cho mọi revise/reject.

## Phân bố theo ngày

| Ngày | KC dùng phân tích | Pass | Revise | Reject | Chưa đạt |
|---|---:|---:|---:|---:|---:|
| Day 04 | 40 | 32 | 0 | 8 | 20,0% |
| Day 07 | 30 | 19 | 5 | 6 | 36,7% |
| Day 09 | 20 | 18 | 0 | 2 | 10,0% |
| **Tổng** | **90** | **69** | **5** | **16** | **23,3%** |

Day 07 là ưu tiên phân tích cao nhất vì có cả reject lẫn toàn bộ năm trường hợp
revise. Day 04 chỉ có pass/reject, có thể phản ánh reviewer đang áp dụng ngưỡng
nhị phân thay vì dùng revise.

## Danh sách và phân loại

| Ngày | KC | Quyết định | Tín hiệu có trong review | Phân loại tạm thời |
|---|---|---|---|---|
| 04 | `dynamic_few_shot_retrieval` | Reject | `move_component` | Placement/removal |
| 04 | `generated_knowledge_prompting` | Reject | `remove_component`, `move_component` | Placement/removal |
| 04 | `tool_declaration_with_decorator` | Reject | `remove_component`, `unsure` | Placement/removal |
| 04 | `build_grounded_tool_agent` | Reject | Không có note/action | Thiếu lý do |
| 04 | `agent_behavior_contracts` | Reject | Không có note/action | Thiếu lý do |
| 04 | `create_agent_tool_loop` | Reject | Không có note/action | Thiếu lý do |
| 04 | `tool_use_control_flow_patterns` | Reject | `move_component` | Placement/removal |
| 04 | `tool_output_grounding` | Reject | “Trong bài lab không phải bài giảng” | KC vs assessment boundary |
| 07 | `embedding_model_selection` | Reject | “Không thấy grounding” | Evidence mismatch |
| 07 | `vector_database_selection` | Revise | Đổi tên; sai ở từ “giai đoạn” | Naming/content |
| 07 | `embedding_generation_pipeline` | Revise | `rename_component` | Naming/content |
| 07 | `grounded_answer_source_fallback` | Reject | Không có note/action | Thiếu lý do |
| 07 | `mini_retrieval_integration` | Reject | “Trong bài lab không phải bài giảng” | KC vs assessment boundary |
| 07 | `ai_data_inventory` | Reject | Không có note/action | Thiếu lý do |
| 07 | `vector_store_data_model` | Reject | `move_component` | Placement/removal |
| 07 | `metadata_guided_retrieval` | Revise | Điểm 4/4/4, không có lý do | Thiếu lý do |
| 07 | `ai_data_strategy_selection` | Reject | “Not grounding” | Evidence mismatch |
| 07 | `data_quality_first_retrieval_principle` | Revise | Sửa nội dung và đổi tên | Naming/content |
| 07 | `retrieval_vs_memory` | Revise | `rename_component`; naming 2/5 | Naming/content |
| 09 | `mcp_capability_surface` | Reject | Không có note/action | Thiếu lý do |
| 09 | `mcp_tool_discovery_and_invocation` | Reject | Không có note/action | Thiếu lý do |

## 1. Ranh giới KC và bài tập lab - 2 KC

Hai KC bị reject vì evidence nằm trong phần thực hành:

- `tool_output_grounding`
- `mini_retrieval_integration`

Đây không phải lỗi grounding. Cả hai có evidence trực tiếp, nhưng loại evidence
khác nhau. Quy tắc đã được chốt:

- `lab`, `hands_on` và `assessment` là bài tập, không tự sinh KC từ tên bài tập,
  chuỗi bước thực hiện hoặc deliverable.
- Lab được phép làm evidence rằng một KC nền được luyện tập hoặc đánh giá.
- Một bài tập phải liên kết tới các KC mà nó kiểm tra, thay vì trở thành một KC
  độc lập.

Áp dụng cho hai trường hợp:

- `tool_output_grounding`: **đề xuất giữ dưới dạng KC nền**. “Chỉ dùng dữ liệu từ
  tool output, không bịa giá/tên” là một năng lực có thể quan sát và đánh giá.
  Các trang lab được xem là practice/assessment evidence; nên bổ sung lecture
  evidence nếu chính sách yêu cầu KC phải có nguồn bài giảng.
- `mini_retrieval_integration`: **đề xuất chuyển thành `assessment_task`**, không
  giữ là KC độc lập. Bài tập end-to-end nên map tới các KC như chuẩn bị dữ liệu,
  chunking, embedding, vector-store indexing, semantic search và grounded answer.

## 2. Evidence mismatch - 2 KC

Reviewer ghi “không grounding” cho:

- `embedding_model_selection`
- `ai_data_strategy_selection`

Artifact hiện có evidence trực tiếp:

- `embedding_model_selection`: slide 26 nêu chọn theo quality, latency, storage,
  language coverage; slide 27 nêu chọn theo use case.
- `ai_data_strategy_selection`: slide 6-8 và 64 nêu chọn đúng dữ liệu, data
  quality và retrieval trước khi đổi model.

Vì vậy cần kiểm tra theo thứ tự:

1. Review UI có hiển thị đúng evidence excerpt hay chỉ hiển thị số trang.
2. File slide giảng viên xem có đúng version/hash với artifact hay không.
3. Reviewer đang phản đối evidence hay phản đối cách KC tổng quát hóa evidence.

Chưa đủ cơ sở để kết luận evidence pipeline sai.

## 3. Naming/content - 4 KC

Đây là nhóm có thể hành động rõ nhất:

- `vector_database_selection`: đổi tên, reviewer phản đối từ “giai đoạn”. Tuy
  nhiên slide 34 có câu “chọn DB theo giai đoạn sản phẩm và yêu cầu vận hành”,
  nên cần xác nhận reviewer muốn ưu tiên “yêu cầu vận hành” hay dùng source version
  khác.
- `embedding_generation_pipeline`: đổi tên để tránh cảm giác pipeline vận hành;
  có thể dùng “Các bước tạo vector embedding trong mô hình”.
- `data_quality_first_retrieval_principle`: sửa tên/nội dung theo hướng năng lực
  chẩn đoán, ví dụ “Chẩn đoán lỗi retrieval do chất lượng dữ liệu”.
- `retrieval_vs_memory`: tên hiện là danh từ chung; có thể đổi thành năng lực
  “Phân biệt retrieval và memory theo nguồn dữ liệu và mục đích sử dụng”.

Các tên đề xuất chỉ là phương án để giảng viên duyệt, chưa phải thay đổi chính
thức.

## 4. Placement/removal - 5 KC

Năm KC có action chuyển group hoặc loại:

- `dynamic_few_shot_retrieval`
- `generated_knowledge_prompting`
- `tool_declaration_with_decorator`
- `tool_use_control_flow_patterns`
- `vector_store_data_model`

Review không ghi target group hoặc lý do loại. Independent judge cũ chỉ phát hiện
overlap rõ ở `dynamic_few_shot_retrieval`; các KC còn lại phần lớn có evidence và
được judge cũ đề xuất giữ. Vì independent judge chưa được hiệu chỉnh, nó không
phải ground truth, nhưng sự khác biệt cho thấy chưa thể tự động xóa năm KC này.

Review tool cần bắt buộc nhập:

```text
move_component -> target_group_code + reason
remove_component -> reason_tag + note
```

## 5. Thiếu lý do - 8 KC

Bảy reject và một revise không có note/action đủ để chẩn đoán:

- `build_grounded_tool_agent`
- `agent_behavior_contracts`
- `create_agent_tool_loop`
- `grounded_answer_source_fallback`
- `ai_data_inventory`
- `metadata_guided_retrieval`
- `mcp_capability_surface`
- `mcp_tool_discovery_and_invocation`

Tất cả tám KC đều có evidence đã resolve. Independent judge cũ đề xuất giữ cả
tám, nhưng judge này có trạng thái `independent_uncalibrated`. Do đó cách xử lý
đúng là yêu cầu reviewer bổ sung lý do, không tự chuyển chúng thành lỗi prompt.

Đặc biệt, `metadata_guided_retrieval` có điểm 4/4/4 nhưng quyết định revise; đây
là trạng thái không nhất quán cần review tool cảnh báo.

## Phân bố theo loại KC và item form

| Nhóm | Tổng trong 90 KC | Chưa đạt | Tỷ lệ |
|---|---:|---:|---:|
| Core KC | 68 | 17 | 25,0% |
| Extension KC | 22 | 4 | 18,2% |
| Concept | 15 | 4 | 26,7% |
| Criterion | 33 | 7 | 21,2% |
| Principle | 6 | 2 | 33,3% |
| Procedure | 36 | 8 | 22,2% |

Mẫu còn nhỏ và không cho thấy một item form duy nhất gây lỗi áp đảo. Không nên
loại toàn bộ procedure hoặc principle dựa trên tỷ lệ này.

## Phát hiện về independent judge

Independent judge cũ không khớp human decision ở cả 21/21 trường hợp:

- Với 16 human reject: judge đề xuất keep 15 và revise 1.
- Với 5 human revise: judge đề xuất keep cả 5.

Nguyên nhân có thể là rubric của judge chỉ đánh giá grounding, granularity và
assessability, trong khi giảng viên còn áp dụng tiêu chí phạm vi bài giảng/lab và
cấu trúc khóa học. Không nên dùng judge này làm quality gate cho tới khi được
calibrate bằng nhãn đã có lý do rõ ràng.

## Thay đổi nên thực hiện trước khi sửa extraction prompt

Quality gate tự động đã được bổ sung bằng lệnh
`vlearn-kc review-audit <review.json>`. Trên 90 review hiện tại, gate chặt hơn
phát hiện 16 review chưa có rationale có thể hành động, bốn action chuyển nhóm
thiếu nhóm đích và một quyết định revise 4/4/4 thiếu giải thích. Xem
`review-quality-audit.json`.

### P0 - chốt yêu cầu

1. Áp dụng quy tắc: lab là assessment; không tạo KC từ tên hoặc deliverable lab.
2. Hiển thị evidence excerpt và source hash ngay trong review UI.
3. Bắt buộc reason tag cho revise/reject.
4. Bắt buộc target group khi chọn `move_component`.
5. Cảnh báo khi decision không nhất quán với điểm, ví dụ revise nhưng 4/4/4.

### P1 - cải tiến có đủ bằng chứng

1. Chuẩn hóa naming theo dạng năng lực có thể quan sát.
2. Thêm source disposition `lecture`, `lab`, `assessment`, `reference` vào input
   và quan hệ `assessment_task -> assessed_kc_codes`.
3. Thêm overlap check cho dynamic few-shot và các KC tích hợp cấp deliverable.
4. Cho reviewer xác nhận bốn tên KC được đề xuất trước khi sửa prompt.

### P2 - chỉ làm sau khi bổ sung rationale

1. Quyết định giữ/loại tám KC thiếu lý do.
2. Hiệu chỉnh independent judge bằng các case đã adjudicate.
3. Chạy lại benchmark và so sánh reject rate theo cùng rubric.

## Kết luận

Trong 21 KC chưa đạt, bốn case naming/content có tín hiệu đủ rõ để chuẩn bị phương
án sửa. Với hai case lab, có thể giữ `tool_output_grounding` như KC nền và chuyển
`mini_retrieval_integration` thành assessment task. Hai case “không grounding”
cần kiểm tra evidence UI/version. Năm case placement/removal thiếu target hoặc lý
do, và tám case hoàn toàn chưa đủ thông tin chẩn đoán.

Do đó, bước đúng tiếp theo là hoàn thiện review contract và thu thập rationale,
không phải chỉnh hàng loạt extraction prompt dựa trên 21 nhãn hiện tại.

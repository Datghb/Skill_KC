# Báo cáo xử lý review của giảng viên - bản cập nhật

**Ngày xử lý:** 25/08/2026  
**Số file đầu vào:** 2  
**Dataset được review:** `phase1_mixed_source_deepseek_2026_08_19`
**Quy mô dataset:** 500 KC và 132 parent group

## Kết luận điều hành

Hai file export mới xác nhận con số trên hệ thống: **100 KC duy nhất đã hoàn tất
review**, tương đương 20% dataset. Tổng cộng có 120 lượt chấm vì 20 KC được cả
hai giảng viên đánh giá. Ngoài ra có 25 parent group đã hoàn tất review.

Kết quả cung cấp bằng chứng chất lượng có ý nghĩa hơn bản export trước, nhưng cho
thấy hai vấn đề cần xử lý trước khi dùng làm quality gate:

1. Reviewer bao phủ 100 KC đánh giá 75 pass, 6 revise và 19 reject. Tỷ lệ
   `pass + revise` là 81%, nhưng tỷ lệ reject 19% vẫn cao hơn ngưỡng đề xuất 10%.
2. Trên 20 KC được chấm chồng lấp, hai giảng viên chỉ đồng thuận chính xác 10/20.
   Cohen's kappa xấp xỉ 0,005, cho thấy rubric hoặc cách hiểu tiêu chí chưa được
   hiệu chỉnh thống nhất.

Theo chính sách phân tích hiện tại, 10 KC bất đồng được giữ riêng với trạng thái
`needs_adjudication` và không tham gia KPI chất lượng. Bộ số liệu dùng để báo cáo
còn 90 KC: 69 pass, 5 revise và 16 reject.

**Khuyến nghị:** có thể dùng 90 KC này làm tín hiệu phân tích tạm thời, nhưng chưa
dùng để tự động quyết định publish. Mười KC bất đồng vẫn cần được giải quyết nếu
muốn đưa trở lại golden dataset.

## Quy mô review

| Chỉ số | Kết quả |
|---|---:|
| Tổng KC trong dataset | 500 |
| Tổng lượt chấm KC hoàn tất | 120 |
| KC duy nhất đã chấm | 100 |
| Độ bao phủ KC | 20% |
| Lượt chấm dở, không tính vào kết quả | 3 |
| KC được hai người cùng chấm | 20 |
| Parent group đã chấm | 25/132 |
| Ngày học được bao phủ | Day 04, Day 07, Day 09 |

File reviewer 01 có 20/20 review hoàn tất. File reviewer 02 có 100/100 review
hoàn tất và ba review đang chấm dở. Bộ đếm metadata trong hai file mới khớp với
số record `review_complete = true`.

## KPI sau khi loại phần đánh giá lệch

| Chỉ số | Kết quả |
|---|---:|
| KC duy nhất ban đầu | 100 |
| KC bất đồng bị loại khỏi KPI | 10 |
| KC đủ điều kiện phân tích | 90 |
| Pass | 69 (76,7%) |
| Revise | 5 (5,6%) |
| Reject | 16 (17,8%) |
| Pass + revise | 74 (82,2%) |

Việc “loại” ở đây chỉ có nghĩa không đưa vào phép tính KPI. Review gốc và danh
sách bất đồng vẫn được giữ để audit; không có dữ liệu giảng viên nào bị xóa.

## Kết quả theo reviewer

| Reviewer | Số KC | Pass | Revise | Reject | Accuracy | Granularity | Naming clarity |
|---|---:|---:|---:|---:|---:|---:|---:|
| Reviewer 01 | 20 | 11 (55%) | 2 (10%) | 7 (35%) | 2,95 | 2,95 | 2,95 |
| Reviewer 02 | 100 | 75 (75%) | 6 (6%) | 19 (19%) | 3,43 | 3,42 | 3,38 |

Nếu tính cả 120 lượt chấm, có 86 pass, 8 revise và 26 reject. Phân bố này có
double-count 20 KC chồng lấp, nên không nên dùng thay cho tỷ lệ trên 100 KC duy
nhất. Reviewer 02 là người đã bao phủ đủ 100 KC và được dùng làm phân bố tham
chiếu cho tập unique.

## Kết quả theo ngày của reviewer 02

| Ngày | Số KC | Pass | Revise | Reject |
|---|---:|---:|---:|---:|
| Day 04 | 40 | 32 | 0 | 8 |
| Day 07 | 30 | 19 | 5 | 6 |
| Day 09 | 30 | 24 | 1 | 5 |
| **Tổng** | **100** | **75** | **6** | **19** |

Day 07 có tỷ lệ cần revise cao nhất, 5/30. Day 04 có 8/40 reject và không có
revise. Các khác biệt này nên được phân tích cùng nội dung nguồn để xác định lỗi
do extraction, độ hạt hay cách diễn đạt.

## Độ đồng thuận giữa giảng viên

Hai giảng viên cùng chấm 20 KC Day 09:

| Chỉ số agreement | Kết quả |
|---|---:|
| Decision khớp hoàn toàn | 10/20, tương đương 50% |
| Bộ điểm thành phần khớp hoàn toàn | 10/20, tương đương 50% |
| Cohen's kappa | 0,005 |
| KC cần adjudication | 10 |

Ma trận quyết định:

| Reviewer 01 / Reviewer 02 | Số KC |
|---|---:|
| Pass / Pass | 10 |
| Pass / Reject | 1 |
| Reject / Pass | 6 |
| Reject / Revise | 1 |
| Revise / Reject | 2 |

Kappa gần 0 không có nghĩa toàn bộ KC đều kém. Nó cho thấy hai người đang áp dụng
ngưỡng pass/revise/reject rất khác nhau. Reviewer 01 đánh reject 35%, trong khi
reviewer 02 chỉ đánh reject 15% trên cùng 20 KC.

Danh sách chi tiết 10 trường hợp bất đồng nằm trong `disagreements.json`.

## Review parent group

Reviewer 02 đã hoàn tất 25 group review:

| Quyết định | Số lượng | Tỷ lệ |
|---|---:|---:|
| Pass | 16 | 64% |
| Revise | 6 | 24% |
| Reject | 3 | 12% |

Điểm trung bình:

| Tiêu chí | Điểm |
|---|---:|
| Grouping fit | 3,64/5 |
| Topic name fit | 3,48/5 |
| Topic distinctness | 3,64/5 |
| Learning objective alignment | 3,64/5 |

Các hành động được đề xuất gồm đổi tên topic bốn lần và làm rõ boundary một lần.
Điều này cho thấy tên parent topic là phần cần ưu tiên cải thiện.

## Hành động chỉnh sửa KC được đề xuất

| Hành động | Số lần |
|---|---:|
| Đổi tên KC | 4 |
| Chuyển KC sang group khác | 4 |
| Loại KC | 3 |
| Chỉnh nội dung | 1 |
| Chưa chắc chắn, cần thảo luận | 1 |

## Phạm vi áp dụng của kết quả

Review này thuộc dataset DeepSeek hỗn hợp ngày 19/08, không phải ba live run
OpenAI trực tiếp Day 06, Day 10 và Day 14 đã dùng trong benchmark V1. Vì vậy:

- Có thể dùng review để tìm quy tắc lỗi và hiệu chỉnh rubric chung cho KC.
- Không được dùng trực tiếp để tuyên bố 78 KC của benchmark OpenAI đã được giảng
  viên xác nhận.
- Báo cáo benchmark OpenAI vẫn giữ trạng thái chưa hoàn thành human quality
  judging.

## Bước tiếp theo

1. Cho hai giảng viên họp adjudication trên 10 KC trong `disagreements.json`.
2. Ghi lý do quyết định cuối cùng cho từng bất đồng và cập nhật rubric bằng ví dụ
   pass/revise/reject cụ thể.
3. Sau calibration, cho cả hai chấm lại cùng 20-30 KC mới; mục tiêu agreement tối
   thiểu 80% và kappa tối thiểu 0,6.
4. Phân tích 19 KC reject và 6 KC revise của reviewer 02 thành nhóm lỗi prompt,
   evidence, granularity, naming hoặc grouping.
5. Review trực tiếp một mẫu thuộc benchmark OpenAI Day 06, Day 10 và Day 14 trước
   khi quyết định production.

## Artifact đầu ra

- `analysis-ready-reviews.json`: 90 KC không có xung đột, dùng cho KPI tạm thời.
- `normalized-reviews.json`: 120 review hoàn tất, ba review dở và 25 group review
  đã được chuẩn hóa; reviewer được thay bằng mã nội bộ.
- `summary.json`: số liệu máy đọc được.
- `disagreements.json`: 10 KC cần adjudication.
- Hai file đầu vào trong `inbox/` được giữ nguyên.

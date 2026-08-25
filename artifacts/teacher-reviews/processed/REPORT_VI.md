# Báo cáo xử lý review của giảng viên

**Ngày xử lý:** 25/08/2026  
**Số file đầu vào:** 2  
**Dataset được review:** `phase1_full15_kc_clustering_luna_2026_08_03`

## Kết luận

Review hiện tại tạo ra **tín hiệu chất lượng ban đầu rất tích cực**, nhưng mẫu còn
quá nhỏ để nghiệm thu Skill hoặc cập nhật kết luận chất lượng cho benchmark mới.

- Có 10 lượt chấm hoàn tất trên 7 KC duy nhất.
- Cả 10/10 lượt chấm đều có quyết định `pass`.
- Điểm trung bình của accuracy, granularity và naming clarity đều là 4/5.
- Không có yêu cầu chỉnh sửa, hành động đề xuất hoặc review group hoàn tất.
- Ba KC Day 09 được cả hai giảng viên chấm; quyết định, điểm thành phần và mức độ
  quan trọng khớp nhau 100%.

**Quyết định đề xuất:** tiếp tục thu thập review. Chưa dùng kết quả này để tuyên bố
Skill đạt chuẩn production.

## Số liệu tổng hợp

| Chỉ số | Kết quả |
|---|---:|
| Tổng KC trong dataset | 501 |
| Lượt chấm hoàn tất | 10 |
| KC duy nhất đã được chấm | 7 |
| Độ bao phủ KC | 1,40% |
| Ngày học có review | Day 01, Day 03, Day 09 |
| Độ bao phủ ngày học | 3/15, tương đương 20% |
| Pass | 10/10, tương đương 100% |
| Edit | 0 |
| Reject | 0 |
| KC được hai người cùng chấm | 3 |
| Group review hoàn tất | 0/135 |

## Điểm chất lượng

| Tiêu chí | Trung bình |
|---|---:|
| Accuracy | 4,0/5 |
| Granularity | 4,0/5 |
| Naming clarity | 4,0/5 |

Các KC đã chấm đều được đánh dấu là `core`. Không có comment hoặc suggested
action, nên dữ liệu hiện tại xác nhận các mẫu này đạt yêu cầu nhưng chưa cung cấp
nhiều thông tin để tinh chỉnh prompt.

## Độ đồng thuận giữa hai giảng viên

Ba KC Day 09 có đánh giá chồng lấp:

- `single_agent_context_bottleneck`
- `single_agent_specialization_tradeoff`
- `single_agent_parallelism_limit`

Cả ba có mức đồng thuận tuyệt đối về decision, ba dimension score và importance.
Không báo cáo Cohen's kappa vì tất cả nhãn chồng lấp đều là `pass`; khi không có
biến thiên nhãn, kappa không mang nhiều ý nghĩa.

## Vấn đề dữ liệu phát hiện được

### Bộ đếm metadata không chính xác

- File reviewer 01 báo `reviewed_kcs = 4`, nhưng phát hiện 7 review đã hoàn tất.
- File reviewer 02 báo `reviewed_kcs = 0`, nhưng phát hiện 3 review đã hoàn tất.

Báo cáo này xác định review hoàn tất từ trạng thái trong từng record và
`confirmed_at`, không dựa vào bộ đếm ở cấp file. Công cụ export nên được sửa để
tính lại bộ đếm trước khi tải file.

### Chưa liên kết đủ với artifact hiện có

Chỉ ba KC Day 09 tìm thấy trong snapshot phase1 đang có trong repo. Bốn KC Day 01
và Day 03 thuộc dataset nguồn ghi trong file review nhưng không xuất hiện trong
snapshot hiện có. Cần bổ sung đúng artifact của dataset
`phase1_full15_kc_clustering_luna_2026_08_03` để kiểm tra evidence và nội dung gốc
cho bốn KC này.

Không KC nào trong bảy KC đã review thuộc ba live run Day 06, Day 10 và Day 14 vừa
benchmark. Vì vậy báo cáo
`artifacts/benchmark-v1-openai-direct/EVALUATION_VI.md` vẫn phải giữ trạng thái
**chưa có human quality judging**.

## Bước tiếp theo

1. Tiếp tục review trực tiếp các KC trong ba run hiện tại, ưu tiên Day 06, Day 10
   và Day 14.
2. Đạt tối thiểu 20–30 KC duy nhất, bao gồm core, extension, trường hợp repair và
   các parent boundary còn tranh luận.
3. Bổ sung một số KC do hai người cùng chấm với cả nhãn pass, edit và reject nếu
   có, để đo agreement có ý nghĩa hơn.
4. Hoàn thành review parent group, vì hiện 0/135 group được xác nhận.
5. Sửa logic export để `reviewed_kcs` và `reviewed_groups` luôn được tính lại từ
   record trước khi xuất file.
6. Khi đủ mẫu, tính tỷ lệ accept/edit/reject, thời gian chỉnh sửa và lỗi theo
   category để quyết định thay đổi prompt hay validation rule.

## Artifact đầu ra

- `normalized-reviews.json`: chỉ chứa 10 lượt review hoàn tất, reviewer đã được
  thay bằng mã nội bộ.
- `summary.json`: số liệu máy đọc được, gồm coverage, agreement và mismatch.
- Hai file đầu vào trong `inbox/` được giữ nguyên.

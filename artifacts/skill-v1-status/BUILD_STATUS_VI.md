# Trạng thái build Skill trích xuất KC — V1

**Ngày cập nhật:** 25/08/2026  
**Trạng thái tổng thể:** Đã hoàn thành phạm vi kỹ thuật V1; sẵn sàng demo và pilot có kiểm duyệt  
**Điểm sẵn sàng kỹ thuật nội bộ:** 86/100  
**Production không cần duyệt:** Chưa sẵn sàng

## Bảng số liệu nhanh

| Nhóm | Chỉ số | Kết quả |
|---|---|---:|
| Build | Hạng mục kỹ thuật V1 hoàn thành | 7/7 |
| Build | Skill validator | PASS |
| Kiểm thử | Automated tests | 58 PASS |
| Kiểm thử | Code coverage | 82% |
| Chạy thực tế | Bộ slide chạy thành công | 3/3 |
| Chạy thực tế | Content unit đã xử lý | 137 |
| Đầu ra | Knowledge item | 82 |
| Đầu ra | KC có thể theo dõi | 78 |
| Đầu ra | Parent topic | 29 |
| Truy vết | Item có evidence đã resolve | 82/82 |
| Độ bền | Run qua replay verification | 3/3 |
| Độ bền | Extraction thành công ngay lần đầu | 1/3 |
| Độ bền | Repair thành công | 2/2 |
| Độ bền | Parent refinement thành công lần đầu | 3/3 |
| Vận hành | Tổng thời gian ba run | 807,84 giây |
| Vận hành | Chi phí ba run thành công | $0,141489 |
| Human review | Lượt chấm hoàn tất | 10 |
| Human review | KC duy nhất đã chấm | 7/501 |
| Human review | Quyết định pass | 10/10 |
| Human review | Điểm trung bình ba tiêu chí | 4,0/5 |

## Tiến độ build

| Hạng mục V1 | Trạng thái |
|---|---|
| Codex Skill structure và metadata | Hoàn thành |
| Runner và consent gửi dữ liệu ra provider | Hoàn thành |
| Trích xuất KC bằng OpenAI trực tiếp | Hoàn thành |
| Embedding và Ward clustering | Hoàn thành |
| Parent refinement | Hoàn thành |
| Validation, bounded repair và replay | Hoàn thành |
| Wheel, checksum, test và tài liệu vận hành | Hoàn thành |

**Tiến độ phạm vi kỹ thuật V1: 100%.** Con số này chỉ nói về các hạng mục đã
định nghĩa cho V1, không đồng nghĩa hệ thống đã được nghiệm thu production.

## Kết quả benchmark

| Bộ slide | Content unit | Knowledge item | Trackable KC | Parent | Repair | Thời gian | Chi phí |
|---|---:|---:|---:|---:|---:|---:|---:|
| Day 06 | 14 | 14 | 10 | 6 | 1 | 205,46 giây | $0,031586 |
| Day 10 | 45 | 28 | 28 | 11 | 0 | 250,44 giây | $0,042282 |
| Day 14 | 78 | 40 | 40 | 12 | 1 | 351,94 giây | $0,067621 |
| **Tổng** | **137** | **82** | **78** | **29** | **2** | **807,84 giây** | **$0,141489** |

Chi phí chỉ bao gồm ba run thành công có manifest. Các request của run thất bại
trước khi ghi manifest chưa được tính vào tổng này.

## Phân loại Core, Extension và Reference KC

| Bộ slide | Core KC | Extension KC | Reference KC | Tổng item | Trackable KC |
|---|---:|---:|---:|---:|---:|
| Day 06 | 9 | 1 | 4 | 14 | 10 |
| Day 10 | 22 | 6 | 0 | 28 | 28 |
| Day 14 | 35 | 5 | 0 | 40 | 40 |
| **Tổng** | **66** | **12** | **4** | **82** | **78** |

Tỷ trọng trên toàn bộ đầu ra:

- **Core KC:** 66/82, tương đương **80,5%**.
- **Extension KC:** 12/82, tương đương **14,6%**.
- **Reference KC:** 4/82, tương đương **4,9%**.
- **Trackable KC:** Core + Extension = 78/82, tương đương **95,1%**.

Core KC là năng lực bắt buộc; Extension KC là năng lực mở rộng nhưng vẫn có thể
theo dõi mastery. Reference KC chỉ cung cấp ngữ cảnh và không được tính vào
mastery. Báo cáo chi tiết riêng nằm tại `KC_TYPE_METRICS_VI.md`.

## Human review hiện có

Hai file review cung cấp tín hiệu ban đầu tốt: 10/10 lượt chấm là `pass`, điểm
accuracy, granularity và naming clarity cùng đạt trung bình 4/5. Ba KC được hai
người cùng chấm có kết quả khớp hoàn toàn.

Tuy nhiên, bảy KC đã chấm thuộc dataset phase1 cũ. Chúng không nằm trong 78 KC
của ba live run Day 06, Day 10 và Day 14. Vì vậy số liệu human review hiện tại
**không được dùng để khẳng định chất lượng của benchmark mới**.

## Đọc trạng thái đúng cách

| Câu hỏi | Trả lời |
|---|---|
| Skill đã build và chạy được chưa? | Có |
| Có thể demo không? | Có |
| Có thể pilot với giảng viên không? | Có, nếu bắt buộc duyệt trước khi sử dụng |
| Có thể tự động publish KC không? | Chưa |
| Có thể mở rộng sang quiz chưa? | Về kỹ thuật có thể, nhưng nên hoàn tất quality gate KC trước |

## Việc cần làm tiếp theo

1. Lấy review cho tối thiểu 20–30 KC thuộc đúng Day 06, Day 10 và Day 14.
2. Đo tỷ lệ accept, edit và reject trên benchmark mới.
3. Nâng extraction first-pass success từ 33,3% lên mục tiêu tối thiểu 90%.
4. Ghi chi phí ngay sau từng provider call, kể cả khi run thất bại.
5. Khi đạt quality gate, mở pilot với workflow sinh → sửa → duyệt.

## Câu báo cáo ngắn

> Skill trích xuất KC V1 đã hoàn thành 100% phạm vi kỹ thuật, vượt qua 58 test với
> coverage 82% và chạy thành công 3/3 bộ slide. Hệ thống đã xử lý 137 content
> unit, tạo 78 KC có thể theo dõi và 100% item có evidence. Hiện Skill sẵn sàng
> demo hoặc pilot có giảng viên kiểm duyệt; bước còn lại trước production là bổ
> sung human review trên đúng benchmark mới và nâng độ ổn định first-pass.

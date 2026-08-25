# BÁO CÁO ĐÁNH GIÁ SKILL TRÍCH XUẤT KNOWLEDGE COMPONENT — V1

**Ngày đánh giá:** 25/08/2026  
**Phạm vi:** Ba bộ slide Day 06, Day 10 và Day 14  
**Cấu hình:** OpenAI `gpt-5.6-luna` (reasoning `high`) cho sinh nội dung; Gemini `gemini-embedding-2` cho embedding  
**Loại đánh giá:** Đánh giá kỹ thuật nội bộ dựa trên artifact và telemetry; chưa phải nghiệm thu chuyên môn của giảng viên

## 1. Kết luận điều hành

**Khuyến nghị: GO cho pilot có kiểm duyệt; NO-GO cho tự động xuất bản production.**

V1 đã chạy end-to-end thành công trên cả ba bộ slide, tạo được KC có evidence, nhóm parent topic và manifest có thể replay. Hệ thống có chi phí thấp ở quy mô thử nghiệm và cơ chế repair đã phục hồi toàn bộ lỗi cấu trúc gặp trong ba lượt chạy thành công.

Điểm hạn chế lớn nhất là chưa có đánh giá chất lượng từ giảng viên hoặc chuyên gia môn học. Ngoài ra, hai trong ba lượt extraction phải gọi repair một lần, cho thấy độ ổn định first-pass chưa đủ để bỏ bước duyệt thủ công.

**Điểm kỹ thuật nội bộ: 86/100.** Điểm này phản ánh độ hoàn thiện kỹ thuật và khả năng pilot, không phải điểm chính xác sư phạm của KC.

## 2. Kết quả định lượng

| Chỉ số | Day 06 | Day 10 | Day 14 | Tổng |
|---|---:|---:|---:|---:|
| Content unit | 14 | 45 | 78 | 137 |
| Knowledge item | 14 | 28 | 40 | 82 |
| KC có thể theo dõi | 10 | 28 | 40 | 78 |
| Parent topic | 6 | 11 | 12 | 29 |
| Leaf được điều chỉnh nhóm | 1 | 4 | 4 | 9 |
| Repair retry | 1 | 0 | 1 | 2 |
| Thời gian | 205,46 giây | 250,44 giây | 351,94 giây | 807,84 giây |
| Chi phí ước tính | $0,031586 | $0,042282 | $0,067621 | $0,141489 |

Các chỉ số suy ra:

- 95,1% knowledge item là KC có thể theo dõi: 78/82.
- 100% knowledge item có ít nhất một evidence đã resolve: 82/82.
- Trung bình 0,569 KC có thể theo dõi trên mỗi content unit.
- Trung bình khoảng 5,90 giây xử lý trên mỗi content unit.
- Chi phí ước tính trung bình là $0,001033/content unit và $0,001814/KC có thể theo dõi.
- Tổng sử dụng ghi nhận: 222.619 OpenAI token và 30.458 Gemini embedding input token.
- Cả ba run đều vượt qua replay verification.

Chi phí trên chỉ bao gồm ba run thành công có manifest. Hai lần thử Day 06 trước đó đã chạm provider nhưng thất bại trước khi ghi manifest, vì vậy chi phí thực tế của toàn bộ phiên thử nghiệm cao hơn con số trên.

## 3. Đánh giá theo tiêu chí

| Tiêu chí | Trọng số | Điểm | Nhận xét |
|---|---:|---:|---|
| Chạy end-to-end và tính toàn vẹn artifact | 20% | 5/5 | 3/3 run thành công, replay verification đạt, checksum package đạt. |
| Khả năng truy vết evidence | 20% | 5/5 | 82/82 item có evidence đã resolve về content unit nguồn. |
| Độ bền trước lỗi đầu ra AI | 20% | 4/5 | Repair phục hồi thành công 2/2 lỗi, nhưng extraction first-pass chỉ đạt 1/3 bộ. |
| Cấu trúc KC phục vụ học tập | 20% | 4/5 | Phân biệt core, extension, reference; có Bloom objective và parent topic. Chưa có chuyên gia xác nhận độ đúng và độ hạt. |
| Hiệu năng và chi phí | 10% | 4/5 | Chi phí thấp cho pilot; tổng thời gian 13 phút 28 giây cho 137 content unit. Chưa có SLA production. |
| Governance production | 10% | 3/5 | Có consent, không auto-publish và có manifest; còn thiếu human quality gate và budget cap vận hành. |

**Tổng điểm quy đổi: 86/100.**

## 4. Nhận xét về chất lượng đầu ra

### 4.1 Cấu trúc và khả năng sử dụng

Trong 82 knowledge item:

- 66 `core_kc`, 12 `extension_kc`, 4 `reference_concept`.
- 31 procedure, 29 criterion, 10 principle, 8 concept và 4 reference topic.
- Trong 78 KC có thể theo dõi: 43 ở mức `apply`, 11 `analyze`, 11 `evaluate`, 5 `create` và 8 `understand`.

Phân bố trên phù hợp với khóa học thiên về thực hành: 70/78 KC ở mức áp dụng trở lên. Tên KC nhìn chung mô tả được hành vi hoặc năng lực cần đạt, thay vì chỉ lặp lại tiêu đề slide.

### 4.2 Quan sát theo từng bộ slide

- **Day 06:** Bộ KC gọn, tập trung vào mini AI SPEC, prototype, demo và feedback. Bốn reference concept được tách khỏi trackable KC hợp lý. Tuy nhiên, một item thiếu `primary_capability_vi` ở lần sinh đầu tiên và phải repair.
- **Day 10:** Bao phủ tốt chuỗi data pipeline từ ingestion, data contract, quality, observability đến incident response. Đây là run ổn định nhất, không cần repair. Ba vấn đề ranh giới parent vẫn được hệ thống ghi lại thay vì tự ý merge.
- **Day 14:** Phạm vi rộng và tương đối đầy đủ cho evaluation: benchmark, golden dataset, LLM-as-Judge, RAGAS, thống kê, safety và failure analysis. Số lượng 40 KC có nguy cơ hơi phân mảnh đối với một buổi học; cần giảng viên xác nhận những KC nào thực sự cần mastery độc lập. Một evidence ID sai ở lần đầu và đã được repair.

### 4.3 Parent topic

Hệ thống tạo 29 parent topic và thực hiện 9 lần điều chỉnh leaf so với Ward candidate. Parent refinement thành công ngay lần đầu ở cả ba run. Các unresolved issue được giữ lại trong output, giúp reviewer nhìn thấy ranh giới còn tranh luận thay vì che giấu sự không chắc chắn.

## 5. Điểm mạnh

1. Evidence-first: mọi item đều truy ngược được về đoạn slide cụ thể.
2. Output có schema và validation rõ, không chấp nhận evidence ID không tồn tại.
3. Repair retry bị giới hạn một lần, tránh vòng lặp và chi phí không kiểm soát.
4. Tách core KC, extension KC và reference concept, phù hợp cho bước xây mastery model sau này.
5. Có telemetry token, latency, provider, model và hash artifact để audit.
6. Không tự động publish; output hiện được xem là bản nháp cần duyệt.

## 6. Rủi ro và khoảng trống

1. **Chưa có human evaluation:** replay verification chỉ chứng minh tính toàn vẹn và liên kết evidence, không chứng minh KC đúng về mặt sư phạm.
2. **First-pass extraction chưa ổn định:** 2/3 bộ cần repair. Cơ chế phục hồi tốt nhưng làm tăng latency và token.
3. **Chi phí run lỗi chưa được ghi đầy đủ:** nếu pipeline dừng trước khi tạo manifest, dashboard nội bộ không phản ánh toàn bộ chi phí provider.
4. **Đầu vào chưa phải raw slide:** benchmark dùng material bundle đã chuẩn hóa; chất lượng OCR, layout extraction và speaker note chưa nằm trong đánh giá này.
5. **Thuật ngữ Việt–Anh:** nhiều KC giữ thuật ngữ kỹ thuật tiếng Anh. Điều này có thể phù hợp với khóa học, nhưng cần style guide thống nhất.
6. **Chưa có quiz:** V1 mới hoàn thành KC extraction và parent refinement; quiz vẫn là phạm vi mở rộng.
7. **Dữ liệu gửi ra provider bên ngoài:** cần chính sách phân loại dữ liệu, consent và quy trình xử lý tài liệu nhạy cảm trước production.

## 7. Điều kiện để pilot

Pilot có thể bắt đầu nếu áp dụng đồng thời các điều kiện sau:

- Giảng viên duyệt trước khi KC được nhập vào khóa học.
- Mỗi bộ slide lấy mẫu tối thiểu 10 KC hoặc 20% số KC, chọn số lớn hơn, để chấm theo rubric.
- Không publish nếu còn unresolved issue nghiêm trọng, evidence không khớp hoặc run không qua replay.
- Thiết lập budget cap theo run và cảnh báo khi phát sinh repair.
- Không dùng tài liệu chứa bí mật, dữ liệu cá nhân nhạy cảm hoặc nội dung bị hạn chế chia sẻ nếu chưa có phê duyệt.

Rubric duyệt đề xuất cho từng KC, thang 1–5:

1. Đúng với nội dung nguồn.
2. Có thể quan sát hoặc đánh giá mức độ thành thạo.
3. Độ hạt phù hợp, không quá rộng hoặc quá vụn.
4. Bloom level và learning objective phù hợp.
5. Không trùng lặp đáng kể với KC khác.

Ngưỡng pilot đề xuất: điểm trung bình tối thiểu 4/5, không có KC sai nguồn nghiêm trọng, và tối thiểu 90% KC đạt từ 3/5 trở lên.

## 8. Lộ trình đề xuất

### P0 — trước pilot

- Tổ chức human review trên ba bộ benchmark hiện tại và lưu kết quả judge có version.
- Ghi telemetry chi phí ngay sau từng provider call để không mất số liệu khi run thất bại.
- Thêm quality gate và báo cáo tỷ lệ accept/edit/reject của giảng viên.
- Thêm giới hạn chi phí, timeout và retry policy theo từng stage.

### P1 — sau pilot đầu tiên

- Đánh giá thêm các bộ slide ngắn, dài, nhiều bảng, nhiều hình và ít chữ.
- Theo dõi độ ổn định first-pass theo model/prompt version.
- Chuẩn hóa glossary Việt–Anh và quy tắc đặt tên KC.
- Đánh giá ingestion từ PPTX/PDF gốc nếu muốn cung cấp trải nghiệm end-to-end cho giảng viên.

### P2 — mở rộng sản phẩm

- Sinh quiz có evidence từ KC đã được duyệt.
- Thêm workflow chỉnh sửa, phê duyệt và versioning cho giảng viên.
- Xây dashboard chất lượng, latency, chi phí và drift theo khóa học.

## 9. Quyết định đề xuất

| Mục đích | Quyết định |
|---|---|
| Demo nội bộ | **GO** |
| Pilot với giảng viên, có duyệt thủ công | **GO có điều kiện** |
| Dùng kết quả làm dữ liệu khóa học mà không duyệt | **NO-GO** |
| Tự động sinh và publish quiz | **NO-GO trong V1** |
| Production diện rộng | **Chưa đủ bằng chứng** |

V1 đã chứng minh được tính khả thi về kỹ thuật. Bước có giá trị cao nhất tiếp theo không phải tăng thêm chức năng sinh nội dung, mà là thu thập đánh giá của giảng viên trên output hiện tại để đo precision, mức chỉnh sửa và tính hữu ích thực tế.

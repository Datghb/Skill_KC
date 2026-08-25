# Teacher review inbox

Đặt nguyên bản các file JSON do giảng viên chấm vào thư mục này.

Quy ước tên file đề xuất:

- `day06-teacher-01.json`
- `day10-teacher-01.json`
- `day14-teacher-01.json`

Nếu một bộ slide có nhiều giảng viên, tăng số thứ tự ở cuối tên file, ví dụ
`day06-teacher-02.json`.

Không sửa hoặc ghi đè các KC gốc trong thư mục `runs/`. Nếu file có tên, email
hoặc thông tin cá nhân không cần thiết, hãy loại bỏ trước khi xử lý.

File review nên có `kc_code` hoặc một mã KC tương đương để đối chiếu với output
gốc. Có thể tham khảo `review-template.json`; tuy nhiên vẫn giữ nguyên file giảng
viên gửi nếu cấu trúc của họ khác mẫu.

Với review mới, revise/reject phải có `issue_tags` hoặc `comment_vi`. Action
`move_component` phải ghi `target_group_code` và `reason_tag`. Chạy
`vlearn-kc review-audit <review.json>` để phát hiện review chưa đủ dữ liệu xử lý.

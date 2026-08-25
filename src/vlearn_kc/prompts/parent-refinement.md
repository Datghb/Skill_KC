Bạn tinh chỉnh Ward clustering bằng các thao tác `keep`, `split`, `move` và
`rename`. Không được dùng `merge` hai cluster hoàn chỉnh.

Quy trình:

1. Chọn một Ward candidate K làm baseline.
2. Audit từng baseline cluster vì Ward có thể gom sai.
3. Split cluster có nhiều parent family.
4. Move từng KC lá khi KC rõ ràng sai nhánh và có target parent phù hợp hơn.
5. Đặt tên lại sau khi membership cuối ổn định.

Mỗi final group phải khai báo `ward_home_cluster_index`, là nhánh Ward chính mà
group kế thừa. Group phải giữ ít nhất một KC từ nhánh home. Mọi Ward baseline
cluster phải còn ít nhất một final group mang home index của nó; không được
chuyển toàn bộ một cluster vào cluster khác để giả lập merge.

`ward_home_cluster_index` và `source_ward_cluster_index` dùng chỉ số bắt đầu từ
1: cluster đầu tiên là 1, cluster cuối là `ward_reference_k`.

KC từ Ward cluster khác xuất hiện trong final group là một leaf move. Mọi leaf
move phải có một modification log nêu source Ward index và target parent code.
Không được chuyển nguyên một cluster hoặc nhiều member chỉ để giảm singleton.

Chỉ move khi đồng thời thỏa:

1. KC không thuộc mục tiêu trung tâm của source parent.
2. KC trực tiếp thuộc family sư phạm của target parent.
3. Target vẫn có một mục tiêu trung tâm rõ sau khi nhận KC.
4. Move làm PG rõ hơn hoặc tránh một parent edge chỉ đúng với member ngoại vi.
5. Evidence, capability, role và Bloom hỗ trợ quyết định.

Không move chỉ vì shared vocabulary, embedding gần, cùng workflow hoặc có quan
hệ prerequisite. Nếu source và target là hai capability theo quan hệ
producer-consumer, hãy giữ thành hai parent để PG biểu diễn cạnh giữa chúng.

Chủ đề kiến thức là parent family, không phải KC atomic mới. Không split mọi KC
chỉ vì chúng đánh giá độc lập. Không có hard cap cho final K; singleton được
phép khi cần nhưng không phải mục tiêu tối ưu.

Ví dụ, không sao chép tên:

- Evaluation loop có thể move vào evaluation family nếu đang nằm trong product
  architecture, sau đó evaluation và model selection vẫn phải là hai parent.
- Quality/latency/cost trade-off có thể move vào model-selection family nếu
  source context cluster chỉ dùng nó như member ngoại vi.
- Không merge toàn bộ evaluation parent vào model-selection parent.

Trả về đúng một JSON object:

```json
{
  "source_slug": "exact source_slug",
  "ward_reference_k": 0,
  "ward_reference_reason_vi": "vì sao baseline phù hợp",
  "final_k": 0,
  "cluster_count_reason_vi": "vì sao partition cuối có số nhóm này",
  "overall_change_summary_vi": "tóm tắt split, move và rename",
  "post_selection_audit_vi": "cluster nào sai và đã sửa ra sao",
  "modifications": [
    {
      "action": "keep | split | move | rename",
      "affected_member_codes": ["exact frozen leaf code"],
      "source_ward_cluster_index": 0,
      "target_parent_code": "bắt buộc với move, để rỗng với action khác",
      "rationale_vi": "lý do sư phạm"
    }
  ],
  "groups": [
    {
      "parent_code": "snake_case unique code",
      "ward_home_cluster_index": 0,
      "name_vi": "tên cụ thể bằng tiếng Việt",
      "name_en": "specific English name",
      "description_vi": "mục tiêu trung tâm và phạm vi bao gồm",
      "boundary_notes_vi": "nội dung gần kề nhưng không thuộc nhóm",
      "member_codes": ["exact frozen leaf code"],
      "coherence": "high | medium | low",
      "pg_readiness_reason_vi": "vì sao group phù hợp hoặc chưa phù hợp làm node PG",
      "singleton_justification_vi": "bắt buộc với singleton, ngược lại để rỗng"
    }
  ],
  "unresolved_issues_vi": ["vấn đề chưa đủ chắc để move"]
}
```

Trước khi trả kết quả:

- kiểm tra mọi KC xuất hiện đúng một lần;
- không có action `merge`;
- mỗi cross-branch KC có đúng move log;
- không Ward baseline cluster nào biến mất hoàn toàn;
- evaluation và model selection không bị nhập thành một parent chỉ vì cùng
  workflow.

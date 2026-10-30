---
type: report
tags: [speclint]
---
# Spec lint report

Quét **8** file · điểm trung bình **72/100** · **6** lỗi · **10** cảnh báo · **2** gợi ý

## Theo file

| File | AC | Điểm | Hạng | Lỗi | Cảnh báo | Gợi ý |
| --- | ---: | ---: | :---: | ---: | ---: | ---: |
| [[story-bad]] | 4 | 0 | D | 4 | 2 | 1 |
| [[prd-bad]] | 0 | 42 | D | 2 | 3 | 1 |
| [[story-grouped]] | 2 | 60 | C | 0 | 3 | 0 |
| [[story-happy-only]] | 2 | 73 | C | 0 | 2 | 0 |
| [[prd-good]] | 0 | 100 | A | 0 | 0 | 0 |
| [[story-good]] | 3 | 100 | A | 0 | 0 | 0 |
| [[story-permission]] | 3 | 100 | A | 0 | 0 | 0 |
| [[story-quoted]] | 3 | 100 | A | 0 | 0 | 0 |

## Hay gặp nhất

| Rule | Số lần | Nội dung |
| --- | ---: | --- |
| `AC003` | 2 | AC thiếu When — trigger ngầm định |
| `PR006` | 1 | Mục Problem có vẻ đang mô tả giải pháp |
| `PR005` | 1 | Không có counter-metric |
| `PR002` | 1 | Metric thiếu baseline |
| `PR003` | 1 | Metric không ghi nguồn số |
| `PR004` | 1 | Out of scope quá mỏng |
| `QO001` | 1 | Open question không có người chịu trách nhiệm |
| `ST001` | 1 | Thiếu câu user story |
| `ST005` | 1 | Thiếu Definition of Done |
| `AC001` | 1 | AC không theo cấu trúc Given/When/Then |
| `AC005` | 1 | AC chứa từ không kiểm chứng được |
| `AC002` | 1 | AC thiếu Then — không có kết quả để kiểm tra |
| `AC006` | 1 | AC có nhiều hơn một trigger |
| `AC008` | 1 | AC lỗi nhưng không nói người dùng thấy gì |
| `LK001` | 1 | Wikilink hỏng |
| `CV001` | 1 | Không có negative path |
| `CV002` | 1 | Không có boundary case |

## Chi tiết

### prd-bad.md

- 💡 **`PR006`** dòng 6 — Mục Problem có cụm "thêm nút" — kiểm tra xem đang tả vấn đề hay đã nhảy sang giải pháp
- ⚠️ **`PR005`** dòng 10 — Không khai báo counter-metric
  - *Thứ gì có thể xấu đi khi chỉ số chính đẹp lên? Không có nó thì mọi kết quả đều là thắng lợi.*
- ⛔ **`PR002`** dòng 14 — Metric "Tỷ lệ trả đúng hạn" có baseline rỗng
  - *Không baseline thì sau khi launch không chứng minh được thành công hay thất bại. Chưa có số thì ghi ❓ và đưa vào Open questions.*
- ⚠️ **`PR003`** dòng 14 — Metric "Tỷ lệ trả đúng hạn" không ghi lấy số từ đâu
  - *Ghi nguồn ngay trong ô: *(DB: bảng.cột)*, *(Amplitude: tên event)**
- ⛔ **`PR004`** dòng 16 — Out of scope chỉ có 1 mục
  - *Phạm vi được định nghĩa bằng thứ bị loại ra. Liệt kê ít nhất 2 thứ stakeholder dễ mặc định là có nhưng thực ra không làm.*
- ⚠️ **`QO001`** dòng 26 — Câu hỏi mở không ghi ai trả lời được
  - *Thêm @Team hoặc @Tên, kèm việc nó đang chặn gì*

### story-bad.md

- ⛔ **`ST001`** dòng 1 — Thiếu so that trong câu user story
  - *Dạng chuẩn: **As a** <vai trò cụ thể> / **I want** <năng lực> / **so that** <kết quả>*
- 💡 **`ST005`** dòng 1 — Story không có Definition of Done
- ⛔ **`AC001`** dòng 11 — AC không theo cấu trúc Given/When/Then
  - *Given <trạng thái trước> / When <một hành động> / Then <kết quả quan sát được>*
- ⛔ **`AC005`** dòng 11 — AC dùng từ không kiểm chứng được: "đầy đủ"
  - *Tester không dự họp phải ra cùng kết luận. Thay bằng điều kiện đo được.*
- ⛔ **`AC002`** dòng 12 — AC thiếu Then — không nêu kết quả nào để tester đối chiếu
- ⚠️ **`AC006`** dòng 13 — AC có 2 mệnh đề When — nên tách thành 2 tiêu chí
  - *Một tiêu chí = một trigger. Cần 'and when' nghĩa là đang gộp hai thứ.*
- ⚠️ **`AC008`** dòng 14 — AC mô tả trường hợp lỗi nhưng không nêu thông điệp hoặc hành động tiếp theo
  - *Nêu rõ người dùng thấy gì và làm gì tiếp: then hiển thị "..." và nút Thử lại*

### story-grouped.md

- ⚠️ **`LK001`** dòng 10 — Wikilink "khong-ton-tai" không trỏ tới file nào trong phạm vi quét
- ⚠️ **`AC003`** dòng 15 — AC có Then nhưng không có When — chưa rõ điều gì kích hoạt
  - *Tester phải đoán: lúc mở màn hình? lúc bấm nút? Nêu rõ trigger.*
- ⚠️ **`AC003`** dòng 19 — AC có Then nhưng không có When — chưa rõ điều gì kích hoạt
  - *Tester phải đoán: lúc mở màn hình? lúc bấm nút? Nêu rõ trigger.*

### story-happy-only.md

- ⚠️ **`CV001`** dòng 12 — Chỉ có happy path — không thấy tiêu chí nào cho trường hợp bị chặn hoặc lỗi
  - *Thêm ít nhất một AC: điều kiện không thoả, và người dùng được báo gì*
- ⚠️ **`CV002`** dòng 12 — Không thấy tiêu chí nào chạm giá trị biên
  - *Giới hạn là chỗ hay vỡ nhất: đúng 5 chứ không phải 4 hay 6, danh sách rỗng, độ dài tối đa*


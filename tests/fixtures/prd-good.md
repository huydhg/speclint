---
type: prd
---
# PRD mẫu đạt chuẩn

## 1. Problem

Borrower không biết khoản vay đến hạn khi nào nên hay trả trễ kỳ đầu.

## 2. Goals & success metrics

| Metric | Baseline | Target |
| ------ | -------- | ------ |
| Ticket CS hỏi ngày đến hạn *(CS dashboard, tag `due-date`)* | 2.300/tháng | <800/tháng |
| Tỷ lệ trả đúng hạn kỳ đầu *(DB: `loan.paid_on <= due_date`)* | ❓ cần số | +3pp |

⚠️ **Counter-metric:** tỷ lệ gỡ cài app *(store analytics)* — giữ ≤ baseline.

## 4. Scope

**In scope**
- Hiển thị ngày đến hạn trên màn hình chính

**Out of scope**
- Bản web — 94% traffic là app, để phase 2
- Nhắc nợ cho người bảo lãnh — cần review pháp lý riêng

## 7. Open questions

- [ ] ❓ Baseline tỷ lệ trả đúng hạn — @Data team — chặn việc đo kết quả
- [x] ❓ Có cần disclosure pháp lý không? — đã chốt: không

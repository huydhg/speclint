---
type: story
status: backlog
---
# Tạo và chia sẻ mã referral

**As a** borrower đã tất toán ít nhất 1 khoản vay
**I want** tạo mã giới thiệu riêng và chia sẻ cho bạn bè
**so that** tôi nhận ưu đãi lãi suất mà không cần gọi tổng đài

## Acceptance criteria

- [ ] **Given** borrower đủ điều kiện, đã dùng 0/5 lượt tháng này **when** mở màn hình "Giới thiệu bạn" **then** hiển thị mã 8 ký tự và bộ đếm "0/5 lượt tháng này"
- [ ] **Given** borrower đã dùng đúng 5 lượt trong tháng **when** mở màn hình **then** nút Chia sẻ bị vô hiệu hoá và hiển thị "Bạn đã dùng hết 5 lượt mời. Quay lại vào 01/12."
- [ ] **Given** mất kết nối mạng **when** nhấn Tạo mã **then** hiển thị "Không có kết nối. Thử lại." kèm nút Thử lại

## Definition of Done
- [ ] Acceptance criteria met

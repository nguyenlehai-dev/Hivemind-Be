# Quy trình Git cho Hivemind-Be

## Mục đích

Tài liệu này chuẩn hóa cách làm việc với Git cho dự án `Hivemind-Be` theo mô hình Gitflow đã được thống nhất trong team.

## Các nhánh chính

- `prod`: mã nguồn dùng cho môi trường production, chỉ nhận thay đổi sau khi đã kiểm tra kỹ.
- `staging`: dùng cho QA, UAT, demo và kiểm thử tích hợp trước khi lên production.
- `dev`: nhánh phát triển chung của team, là nơi hợp nhất các nhánh tính năng trước khi đưa lên `staging`.

Ngoài các nhánh trên, repo hiện vẫn giữ `main` để tương thích với cấu hình GitHub hiện tại. Quy trình phát triển chính sử dụng `prod`, `staging`, `dev`.

## Quy ước đặt tên nhánh

- Tính năng mới: `feat/<ten_tinh_nang>`
- Sửa lỗi khẩn cấp production: `hotfix/<ten_loi>`

Ví dụ:

- `feat/auth-login`
- `feat/document-fields`
- `hotfix/fix-login-timeout`

## Quy trình làm việc với feature

1. Cập nhật nhánh `dev` mới nhất.
2. Tạo nhánh feature từ `dev`.
3. Thực hiện code, commit rõ ràng, ưu tiên kèm issue ID.
4. Push nhánh feature lên remote.
5. Tạo pull request từ `feat/...` vào `dev`.
6. Sau khi review và approve, merge vào `dev`.
7. Khi đủ ổn định, merge `dev` vào `staging`.
8. Sau kiểm thử hoàn tất, merge `staging` hoặc `dev` vào `prod`.

Ví dụ lệnh:

```bash
git checkout dev
git pull origin dev
git checkout -b feat/auth-login
git add .
git commit -m "feat: add auth login #123"
git push -u origin feat/auth-login
```

## Quy trình hotfix

1. Tạo nhánh hotfix từ `prod`.
2. Sửa lỗi khẩn cấp và commit thay đổi.
3. Push nhánh hotfix lên remote.
4. Tạo pull request từ `hotfix/...` vào `prod`.
5. Sau khi merge vào `prod`, đồng bộ thay đổi ngược về `staging` và `dev`.

Ví dụ lệnh:

```bash
git checkout prod
git pull origin prod
git checkout -b hotfix/fix-login-timeout
git add .
git commit -m "fix: resolve login timeout #456"
git push -u origin hotfix/fix-login-timeout
```

## Quy ước commit

- Commit message phải ngắn gọn, nêu đúng mục đích thay đổi.
- Phần lớn commit nên đi kèm issue ID để thuận tiện truy vết.
- Mẫu khuyến nghị:

```text
feat: add homepage #123
fix: resolve login bug #456
docs: update git workflow #789
```

Nếu chưa có issue ID, cần bổ sung sau ở PR hoặc ticket nội bộ để tránh mất dấu thay đổi.

## Lưu ý khi merge

- Không push trực tiếp vào `prod` và `staging`.
- Ưu tiên review code trước mọi lần merge.
- Sau mỗi hotfix production, phải đồng bộ lại `staging` và `dev`.
- Chỉ tạo feature branch từ `dev`, không tách trực tiếp từ `staging` hoặc `prod`.

## Trạng thái chuẩn hiện tại của repo

Repo đã được khởi tạo các nhánh nền tảng:

- `prod`
- `staging`
- `dev`

Mọi thay đổi mới cho dự án nên tuân theo quy trình trên.

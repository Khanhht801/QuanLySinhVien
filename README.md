# Quản lý điểm sinh viên K10TIN — Học kỳ 5

Ứng dụng PyQt5 sử dụng SQLite để lưu sinh viên và điểm; giao diện nạp từ `main.ui`.

## Chạy ứng dụng

```powershell
cd D:\QLSV
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Cũng có thể chạy `Chay_giao_dien.cmd` hoặc nhấn F5 trong VS Code với interpreter `.venv`.

Ứng dụng mở form `login.ui` trước. Đăng nhập bằng tài khoản **Admin**, mật khẩu **123456Ab** (phân biệt chữ hoa/thường) để mở giao diện `main.ui`. Nhấn Enter hoặc bấm **Đăng nhập** để xác nhận; **Thoát** hoặc đóng form sẽ kết thúc ứng dụng. Có thể mở `login.ui` bằng Qt Designer để chỉnh thiết kế.

Database được tạo tự động tại `data/k10tin.sqlite3`; dữ liệu vẫn còn sau khi đóng ứng dụng.
Riêng bản `.exe` lưu database tại `%LOCALAPPDATA%\QLSV\k10tin.sqlite3`, độc lập với thư mục giải nén. Bản phát hành bắt đầu với dữ liệu sinh viên trống. Để chuyển dữ liệu cũ sang bản `.exe`, đóng ứng dụng rồi sao lưu và chép `data/k10tin.sqlite3` vào vị trí này.
Không nạp sinh viên mẫu từ Designer vào database. Để sao lưu, đóng ứng dụng rồi sao chép file SQLite.

## Chức năng

- **Điểm rèn luyện**: nhập từ 0 đến 100 dưới phần thông tin môn học; để trống nếu chưa có. Điểm được lưu theo sinh viên và học kỳ, hiển thị sau điểm TBC học kỳ trong bảng tổng hợp và file Excel tổng hợp. Chọn sinh viên, bấm **Sửa điểm** để thay đổi hoặc xóa điểm rèn luyện, rồi bấm **Xác nhận**. Điểm này không ảnh hưởng đến điểm TBC và xếp loại học tập.

- **Nhập sinh viên mới**: xóa nội dung biểu mẫu, gợi ý mã sinh viên tiếp theo.
- **Thêm**: lưu sinh viên mới hoặc thêm điểm môn khác cho sinh viên đã tồn tại. Mã và họ tên của sinh viên cũ phải khớp.
- **Sửa điểm**: khi chọn một dòng, thông tin và điểm chỉ cho xem. Bấm **Sửa điểm** để mở chỉnh sửa; nút đổi thành **Xác nhận**. Bấm **Xác nhận** mới lưu vào SQLite và khóa lại các ô. Đổi mã sinh viên cũng cập nhật liên kết điểm. Trong lúc sửa, không đổi sinh viên hoặc môn học; bấm **Nhập sinh viên mới** để bỏ thay đổi chưa lưu và chuẩn bị thêm sinh viên mới.
- **Xóa**: chọn xóa riêng điểm môn đang chọn hoặc xóa sinh viên cùng toàn bộ điểm.
- Chọn môn ở một trong hai ô chọn để xem/nhập điểm môn đó.
- Tìm theo mã hoặc tên, hỗ trợ gõ không dấu; làm mới để đọc lại dữ liệu SQLite.
- Tab tổng hợp hiển thị điểm 5 môn, trung bình học kỳ, xếp loại, số lượng và biểu đồ từ dữ liệu thực tế.
- **Xuất Excel** ở mỗi tab tạo file `.xlsx` với các dòng đang hiển thị theo bộ lọc.

Ba ô điểm mặc định là **0** khi nhập mới hoặc chọn môn chưa có điểm. Bấm **Thêm** hoặc **Sửa** sẽ lưu các giá trị đang hiển thị, kể cả điểm 0. Môn chưa từng lưu điểm vẫn được tính là thiếu điểm trong bảng tổng hợp; dùng **Xóa → Điểm môn đang chọn** để xóa điểm đã lưu.

## Môn học và tính điểm

Học kỳ 5 gồm: Lập trình Python, Lập trình web nâng cao, AutoCAD, Lắp ráp và cài đặt máy tính, Chăm sóc khách hàng.

Mỗi môn có một điểm thường xuyên (TX), một điểm định kỳ (ĐK) và một điểm cuối kỳ (CK), trong khoảng 0–10.

```text
Điểm TBC môn học = (TX + 2 × ĐK + 3 × CK) / 6
```

Điểm TBC môn học làm tròn 1 chữ số thập phân theo quy tắc nửa lên. Xếp loại theo điểm đã làm tròn:

| Điểm | Xếp loại |
|---|---|
| 8,5–10 | Giỏi |
| 7,0–8,4 | Khá |
| 5,5–6,9 | Trung bình |
| 4,0–5,4 | Trung bình yếu |
| Dưới 4,0 | Kém |

Điểm TBC học kỳ hiện tính trung bình cộng điểm TBC của 5 môn, làm tròn 1 chữ số; đây là lựa chọn tạm thời vì chưa có quy định tín chỉ. Thiếu điểm bất kỳ môn nào thì điểm TBC và xếp loại học kỳ là **Chưa đủ điểm**.

Các bản ghi học kỳ trước được giữ lại, không tự chuyển thành điểm học kỳ 5.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kiểm thử bao gồm công thức, mốc xếp loại, kiểm tra dữ liệu, giao dịch SQLite, lưu qua lần mở lại, liên kết điểm khi đổi mã, thao tác nút thêm/sửa, đổi môn, tìm không dấu và xuất Excel.

## Sửa thiết kế

Mở `Mo_Designer.cmd` để chỉnh `main.ui`. Đóng rồi mở lại file trong Designer nếu file đã thay đổi bên ngoài.
Giữ `assets`, `resources.qrc`, `resources_rc.py` cùng dự án để hiển thị biểu tượng.
Tên môn, điểm, số liệu và cột tổng hợp được chương trình cập nhật khi chạy; dữ liệu trong Designer chỉ là mẫu thiết kế.

Để khôi phục thiết kế, đóng Designer rồi chạy `.\.venv\Scripts\python.exe tools\restore_ui.py`.
Lệnh sao lưu giao diện hiện tại trước khi khôi phục từ `backups/main.verified.ui`.

## Đóng gói Windows

Chạy trong PowerShell tại thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe tools\build_release.py
```

Chạy thử `dist\QLSV\QLSV.exe`. Chia sẻ toàn bộ `release\QLSV-Windows.zip`; người nhận giải nén rồi chạy `QLSV\QLSV.exe`, không cần cài Python. Giữ nguyên thư mục `_internal` đi cùng file `.exe`. Đóng chương trình trước khi build lại.

## Đưa mã nguồn và bản chạy lên GitHub

Tạo repository GitHub **Public**, để trống các tùy chọn khởi tạo README, `.gitignore` và license vì mã nguồn đã có ở máy. Trong PowerShell:

```powershell
git init
git branch -M main
git add .
git status
git commit -m "Initial version of QLSV"
git remote add origin https://github.com/TEN_GITHUB/QLSV.git
git push -u origin main
```

Thay `TEN_GITHUB` bằng username GitHub của bạn. Nếu Git yêu cầu danh tính, cấu hình `git config user.name "Tên của bạn"` và `git config user.email "Email GitHub hoặc email noreply"`, rồi chạy lại lệnh commit. Đăng nhập GitHub khi Git yêu cầu.

`.gitignore` loại môi trường Python, database, file Excel xuất ra và kết quả đóng gói khỏi mã nguồn. Kiểm tra `git status` trước khi commit. Tài khoản `Admin / 123456Ab` được công khai trong mã nguồn và chỉ dành cho demo.

Để phát hành bản chạy: vào **Releases → Draft a new release**, tạo tag `v1.0.0`, nhập tên phiên bản, đính kèm `release/QLSV-Windows.zip`, rồi chọn **Publish release**.

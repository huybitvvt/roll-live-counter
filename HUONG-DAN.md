# Hướng dẫn Roll Live Counter 0.1.0

## Mở nguồn

1. Cài `RollLiveCounter-Setup.exe`, mở ứng dụng từ desktop hoặc Start Menu.
2. Camera USB: thử `0`, rồi `1` nếu chọn nhầm. Camera IP: nhập URL RTSP do camera cung cấp.
   Camera USB đang mở trong phần mềm khác có thể không dùng được đồng thời.
3. Bấm **Mở nguồn** và chờ model nạp. Cũng có thể **Chọn tệp** để mở MP4/AVI/JPG.
4. Vào tab **Thiết lập** để điều chỉnh ngưỡng hoặc số lần quét/giây. Hạ ngưỡng có thể
   phát hiện thêm cuộn nhưng cũng làm tăng nhận nhầm. Tăng số lần quét không làm CPU nhanh hơn.

## Chọn xe / vùng bắt đầu đếm

Lần đầu mở, app chưa cộng tự động cho đến khi anh chọn vùng hoặc bấm **Toàn khung**.
Việc này giúp không cộng nhầm các cuộn ở sát camera trước khi chọn đúng xe.

Bấm **Chọn vùng bắt đầu đếm**, kéo hình chữ nhật quanh khu vực xe. Esc hủy.
Mô hình quét cả hình và bổ sung vùng xe để giữ chi tiết cuộn ở xa. Cuộn đã đếm
vẫn được theo dõi khi di chuyển ra ngoài vùng chọn nhưng còn trong hình.
Nút **Toàn khung** bỏ giới hạn vùng. Chọn vùng không tự đặt lại tổng.

Nếu đã chọn nhầm vùng và cộng các cuộn không mong muốn, chọn lại vùng trước rồi
vào **Thiết lập → Đặt lại tổng...** để bắt đầu lại.

## Cách hiểu số đếm

**Xem khung đã nhận diện** hiển thị đúng ảnh mà model vừa xử lý cùng các mã cuộn,
thời gian ảnh được ghi rõ trên hình. **Xem hình trực tiếp** trở lại camera live.
Khi CPU xử lý chậm, app không vẽ khung của ảnh cũ lên vật thể ở vị trí mới.
Đối chiếu mục cần kiểm tra trên khung đã nhận diện để biết đúng track nào.

- **Xanh, #số:** danh tính đã đếm. Đổi vị trí trong hình với cùng quỹ đạo không cộng thêm.
- **Xám:** đang chờ đủ lần xác nhận, hoặc chưa ở vùng bắt đầu đếm.
- **Vàng, Track số:** có khả năng là cuộn cũ đã mất dấu; tổng chưa cộng mục này.

Khi có mục vàng, chọn track trong danh sách:

- Biết là cuộn mới: **Cuộn mới (+1)**.
- Biết đã đếm: chọn mã `#...`, **Xem ảnh cuộn đã đếm** để đối chiếu, rồi **Ghép mã đã đếm**.
- Nhận nhầm đồ vật/nền: **Bỏ qua nhận diện này**.

Việc đối chiếu chỉ dùng hình làm hỗ trợ; cuộn giống hệt nhau có thể vẫn không phân
biệt được. Không chọn bừa mã khi chưa đủ bằng chứng. Nhận diện sai nhưng tracker
giữ ổn định vẫn có thể được cộng tự động; đây là giới hạn của bản chưa train tại xưởng.

Không có reset theo xe. Tổng và bộ nhớ được giữ khi dừng, đóng app, mất nguồn hoặc
đổi sang camera/video khác. Sau mất camera/khởi động lại, phần mềm thận trọng đưa
các vật giống cuộn cũ vào kiểm tra, không dựa vào ID số cũ để tự cộng.

## Thu data khi chưa có dataset

Vào **Thiết lập**, bật **Thu ảnh để train sau**. App lưu tối đa 500 ảnh hoặc 2 GB,
mỗi 10 giây một ảnh. Có thể bấm **Lưu ảnh** để chụp riêng cảnh khó.

Nên thu nhiều bố cục: cuộn đứng yên, nhân viên di chuyển, cuộn phía sau lộ ra,
che khuất, khoảng cách và ánh sáng khác nhau. Chỉ thu hình không đủ để tự động
train tốt: cần kiểm tra/gán nhãn từng cuộn; muốn đánh giá chống đếm trùng cần có
video và danh tính chuẩn theo thời gian. JSON do app ghi là gợi ý, không phải nhãn chuẩn.

App không tự quay video dài, không gửi hình đi và không tự train. Có thể dùng phần mềm
camera hiện có để xuất video gốc nếu cần đánh giá toàn bộ quá trình di chuyển.

## Lịch sử và lỗi

**Xuất CSV** xuất toàn bộ sự kiện. **Mở thư mục dữ liệu** mở
`%LOCALAPPDATA%\RollLiveCounter`. Sao lưu cả thư mục khi cần bảo toàn ảnh tham chiếu.

Nguồn camera mất hình sẽ có trạng thái chờ và thử kết nối lại, tối đa 3 lỗi/phút.
Lỗi/treo bộ nhận diện sẽ khởi động lại và giữ lịch sử; sau 3 lỗi/phút thì dừng,
cần kiểm tra nguyên nhân và bấm **Mở nguồn**.
Không hiển thị hình cũ như đang live. App chỉ chạy một cửa sổ trên mỗi tài khoản Windows.

Khi model không nhận đủ cuộn, lấy nét/ánh sáng/vùng chọn và chất lượng ảnh cần được
kiểm tra trước. Chưa có chứng nhận độ đúng trên ảnh/video xưởng, không dùng tổng
này làm số liệu giao nhận chính thức trước khi đối chiếu thực tế.

Bộ cài chưa ký số nên Windows có thể hiển thị SmartScreen.

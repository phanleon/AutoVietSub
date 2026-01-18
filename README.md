Truy cập link này: gyan.dev/ffmpeg/builds
Kéo xuống phần "release builds", tìm dòng ffmpeg-release-essentials.zip và tải về.
Copy thư mục ffmpeg này và dán thẳng vào ổ C (để đường dẫn là C:\ffmpeg).
Kiểm tra: Bạn mở C:\ffmpeg\bin, nếu thấy có file ffmpeg.exe là đúng.
Cài đặt Biến môi trường (Environment Variable):
Đây là bước báo cho máy tính biết FFmpeg nằm ở đâu.
Bấm phím Windows, gõ chữ env.
Chọn kết quả: Edit the system environment variables (Chỉnh sửa biến môi trường hệ thống).
Một cửa sổ hiện ra, bấm nút Environment Variables... ở góc dưới.
Ở khung bên dưới (System variables), tìm dòng có tên là Path, chọn nó và bấm Edit.
Bấm nút New bên phải.
Dán đường dẫn này vào: C:\ffmpeg\bin
Bấm OK -> OK -> OK (3 lần OK để đóng hết cửa sổ).

pip install openai-whisper streamlit moviepy deep-translator torch

pip install google-generativeai

pip install streamlit openai-whisper moviepy google-generativeai deep-translator

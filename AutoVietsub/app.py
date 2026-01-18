import streamlit as st
import whisper
from moviepy.editor import VideoFileClip
import google.generativeai as genai
import os
import datetime
import zipfile
import shutil
import time

# --- CẤU HÌNH API GEMINI (QUAN TRỌNG) ---
# Dán API Key của bạn vào giữa dấu ngoặc kép bên dưới
API_KEY = "AIzaSyBkYwIjegYH7a-kFaRu9yiY0_5rm80MmY8" 

genai.configure(api_key=API_KEY)
# Sử dụng model Gemini Flash cho nhanh và miễn phí
model_gemini = genai.GenerativeModel('gemini-1.5-flash')

# --- CẤU HÌNH THƯ MỤC ---
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

def clean_folders():
    if os.path.exists(UPLOAD_FOLDER): shutil.rmtree(UPLOAD_FOLDER)
    if os.path.exists(OUTPUT_FOLDER): shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- HÀM HỖ TRỢ ---
st.set_page_config(page_title="Auto Vietsub Pro (Gemini)", layout="centered")

def format_timestamp(seconds):
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def extract_audio(video_path, audio_path):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, logger=None)
    video.close()

def translate_with_gemini(text):
    """Hàm gửi text lên Google Gemini để dịch"""
    try:
        # Prompt ra lệnh cho AI dịch chuẩn phim ảnh
        prompt = f"""
        Bạn là một biên dịch viên phim chuyên nghiệp. 
        Hãy dịch câu sau từ tiếng Anh sang tiếng Việt.
        Yêu cầu: Ngắn gọn, tự nhiên, văn phong đời thường (không dịch word-by-word).
        Nội dung: "{text}"
        Chỉ trả về câu dịch tiếng Việt, không giải thích gì thêm.
        """
        response = model_gemini.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return text # Nếu lỗi thì trả về text gốc

def generate_srt_content(segments, status_text):
    """Tạo nội dung SRT và dùng Gemini dịch"""
    srt_content = ""
    total = len(segments)
    
    for i, segment in enumerate(segments):
        start = format_timestamp(segment['start'])
        end = format_timestamp(segment['end'])
        original_text = segment['text'].strip()
        
        if not original_text: continue

        # Gọi hàm dịch Gemini
        translated_text = translate_with_gemini(original_text)
        
        # Cập nhật trạng thái cho người dùng biết đang làm gì
        status_text.text(f"Đang dịch câu {i+1}/{total}: {translated_text}")
        
        srt_content += f"{i + 1}\n{start} --> {end}\n{translated_text}\n\n"
        
        # QUAN TRỌNG: Ngủ 1 chút để không bị Google chặn vì spam (Rate Limit)
        # Bản Free giới hạn khoảng 15 request/phút, nhưng Gemini Flash khá nhanh.
        # Để an toàn, nghỉ 1s mỗi câu (chấp nhận chậm hơn để được Free)
        time.sleep(1.5) 
    
    return srt_content

# --- GIAO DIỆN CHÍNH ---

st.title("🎬 AI Vietsub Pro (Powered by Gemini)")
st.markdown("Sử dụng **Whisper** (Nghe) + **Google Gemini** (Dịch thông minh).")

if API_KEY == "DÁN_API_KEY_CỦA_BẠN_VÀO_ĐÂY":
    st.error("⚠️ Bạn chưa điền API Key! Hãy mở file code và điền Key vào dòng số 13.")
else:
    model_type = st.selectbox("1. Chọn độ chính xác Whisper:", ["base", "small", "medium"], index=1)
    uploaded_files = st.file_uploader("2. Chọn video:", type=["mp4", "mkv", "mov"], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Bắt đầu xử lý (Chất lượng cao)"):
        clean_folders()
        
        with st.spinner(f"Đang tải Whisper ({model_type})..."):
            model = whisper.load_model(model_type)
        
        generated_srts = []
        main_progress = st.progress(0)
        status_area = st.empty()
        
        total_files = len(uploaded_files)

        for idx, uploaded_file in enumerate(uploaded_files):
            filename = uploaded_file.name
            status_area.markdown(f"### ⏳ Đang xử lý file {idx + 1}/{total_files}: **{filename}**")
            
            video_path = os.path.join(UPLOAD_FOLDER, filename)
            audio_path = os.path.join(UPLOAD_FOLDER, f"temp_{idx}.mp3")
            srt_filename = os.path.splitext(filename)[0] + ".srt"
            srt_path = os.path.join(OUTPUT_FOLDER, srt_filename)
            
            with open(video_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            try:
                # B1: Tách âm
                extract_audio(video_path, audio_path)
                
                # B2: Whisper nghe
                result = model.transcribe(audio_path, language="en")
                
                # B3: Gemini Dịch (Có hiển thị text đang dịch)
                translation_status = st.empty()
                srt_content = generate_srt_content(result['segments'], translation_status)
                translation_status.empty() # Xóa dòng trạng thái con
                
                # B4: Lưu
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
                
                generated_srts.append(srt_path)
                st.success(f"✅ Xong file: {filename}")
                
            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
            
            main_progress.progress((idx + 1) / total_files)

        if generated_srts:
            zip_filename = "Gemini_Subtitles_Pro.zip"
            zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for srt_file in generated_srts:
                    zipf.write(srt_file, arcname=os.path.basename(srt_file))
            
            with open(zip_path, "rb") as f:
                st.download_button("📦 Tải xuống tất cả", f, zip_filename, "application/zip")
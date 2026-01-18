import streamlit as st
import whisper
from moviepy.editor import VideoFileClip
import google.generativeai as genai
import os
import datetime
import zipfile
import shutil
import time

# --- 1. CẤU HÌNH TRANG WEB (Phải để đầu tiên) ---
st.set_page_config(page_title="Auto Vietsub Pro (Gemini)", layout="centered")

# --- 2. CẤU HÌNH API KEY TỪ SECRETS ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # Sử dụng model Flash cho nhanh và miễn phí
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("⚠️ Lỗi: Chưa cấu hình API Key trong phần 'Secrets' của Streamlit Cloud.")
    st.info("Bạn cần vào Settings -> Secrets và thêm dòng: GEMINI_API_KEY = 'Mã_Của_Bạn'")
    st.stop() # Dừng chương trình nếu không có key

# --- 3. CẤU HÌNH THƯ MỤC ---
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

def clean_folders():
    if os.path.exists(UPLOAD_FOLDER): shutil.rmtree(UPLOAD_FOLDER)
    if os.path.exists(OUTPUT_FOLDER): shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- 4. CÁC HÀM XỬ LÝ ---

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
    """Gửi text lên Google Gemini để dịch"""
    try:
        prompt = f"""
        Bạn là biên dịch viên phim. Dịch câu sau sang tiếng Việt.
        Yêu cầu: Ngắn gọn, tự nhiên, đời thường, đúng ngữ cảnh phim.
        Nội dung: "{text}"
        Chỉ trả về câu dịch, không giải thích.
        """
        response = model_gemini.generate_content(prompt)
        return response.text.strip()
    except:
        return text # Giữ nguyên nếu lỗi

def generate_srt_content(segments, status_text):
    srt_content = ""
    total = len(segments)
    
    for i, segment in enumerate(segments):
        start = format_timestamp(segment['start'])
        end = format_timestamp(segment['end'])
        original_text = segment['text'].strip()
        
        if not original_text: continue

        translated_text = translate_with_gemini(original_text)
        
        # Hiển thị tiến trình
        status_text.text(f"⏳ Đang dịch câu {i+1}/{total}: {translated_text}")
        
        srt_content += f"{i + 1}\n{start} --> {end}\n{translated_text}\n\n"
        
        # Nghỉ 1.5s để tránh bị Google chặn (Rate Limit)
        time.sleep(1.5) 
    
    return srt_content

# --- 5. GIAO DIỆN CHÍNH ---

st.title("🎬 AI Vietsub Pro (Gemini Edition)")
st.markdown("Công cụ tạo phụ đề tự động sử dụng **Whisper** và **Google Gemini**.")

model_type = st.selectbox("Chọn độ chính xác Whisper:", ["base", "small"], index=0)
st.caption("Lưu ý: Trên Cloud miễn phí chỉ nên dùng 'base' hoặc 'small' để tránh sập nguồn.")

uploaded_files = st.file_uploader("Chọn video (mp4, mkv, mov):", type=["mp4", "mkv", "mov"], accept_multiple_files=True)

if uploaded_files and st.button("🚀 Bắt đầu xử lý"):
    clean_folders()
    
    with st.spinner(f"Đang tải Model Whisper ({model_type})..."):
        try:
            model = whisper.load_model(model_type)
        except Exception as e:
            st.error(f"Lỗi tải Model: {e}. Hãy thử chọn model 'base'.")
            st.stop()
    
    generated_srts = []
    main_progress = st.progress(0)
    status_area = st.empty()
    total_files = len(uploaded_files)

    for idx, uploaded_file in enumerate(uploaded_files):
        filename = uploaded_file.name
        status_area.markdown(f"### 🎬 Đang xử lý: **{filename}** ({idx + 1}/{total_files})")
        
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        audio_path = os.path.join(UPLOAD_FOLDER, f"temp_{idx}.mp3")
        srt_filename = os.path.splitext(filename)[0] + ".srt"
        srt_path = os.path.join(OUTPUT_FOLDER, srt_filename)
        
        # Lưu file
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        try:
            # B1: Tách âm
            extract_audio(video_path, audio_path)
            
            # B2: Whisper nghe
            result = model.transcribe(audio_path, language="en")
            
            # B3: Gemini Dịch
            translation_status = st.empty()
            srt_content = generate_srt_content(result['segments'], translation_status)
            translation_status.empty()
            
            # B4: Lưu kết quả
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            
            generated_srts.append(srt_path)
            st.success(f"✅ Hoàn thành: {filename}")
            
        except Exception as e:
            st.error(f"❌ Có lỗi với file {filename}: {e}")
        
        main_progress.progress((idx + 1) / total_files)

    # Tạo file ZIP để tải về
    if generated_srts:
        zip_filename = "Vietsub_Done.zip"
        zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for srt_file in generated_srts:
                zipf.write(srt_file, arcname=os.path.basename(srt_file))
        
        with open(zip_path, "rb") as f:
            st.download_button(
                label="📦 Tải xuống tất cả (ZIP)",
                data=f,
                file_name=zip_filename,
                mime="application/zip"
            )

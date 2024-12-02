import requests
import pandas as pd
from bs4 import BeautifulSoup
from html import unescape
import google.generativeai as genai
import json
import time
from datetime import datetime, timedelta
from pypdf import PdfReader
from docx import Document
import pytz
from io import BytesIO
import os
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Suppress specific warnings from libraries
pd.options.mode.chained_assignment = None  # Suppress SettingWithCopyWarning
warnings.filterwarnings("ignore", category=UserWarning, module="bs4")
warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")
# Configuration
BASE_API_KEY = os.getenv('BASE_API_KEY')
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Schema for Gemini evaluation
evaluation_schema = {
    "type": "object",
    "properties": {
        "muc_do_phu_hop": {
            "type": "integer",
            "description": """Đánh giá độ phù hợp tổng thể của ứng viên với vị trí (0-10):
            - Kinh nghiệm trực tiếp với các dự án/công việc tương tự
            - Thời gian làm việc trong ngành/lĩnh vực
            - Các thành tích và kết quả công việc trước đây
            - Sự phù hợp với văn hóa và môi trường làm việc
            - Tiềm năng phát triển trong tương lai"""
        },
        "ky_nang_ky_thuat": {
            "type": "integer",
            "description": """Đánh giá kỹ năng kỹ thuật theo yêu cầu công việc (0-10):
            - Mức độ thành thạo các công nghệ/công cụ yêu cầu
            - Kiến thức chuyên môn và kỹ thuật
            - Khả năng áp dụng kiến thức vào thực tế
            - Các chứng chỉ kỹ thuật liên quan
            - Các dự án đã thực hiện thể hiện kỹ năng"""
        },
        "kinh_nghiem": {
            "type": "integer",
            "description": """Đánh giá kinh nghiệm làm việc (0-10):
            - Số năm kinh nghiệm trong vị trí tương tự
            - Quy mô và độ phức tạp của các dự án đã làm
            - Vai trò và trách nhiệm trong các dự án
            - Kinh nghiệm làm việc với các công nghệ/công cụ liên quan
            - Thành tích và kết quả đạt được"""
        },
        "trinh_do_hoc_van": {
            "type": "integer",
            "description": """Đánh giá trình độ học vấn và đào tạo (0-10):
            - Bằng cấp phù hợp với yêu cầu công việc
            - Các khóa học và chứng chỉ chuyên môn
            - Thành tích học tập và nghiên cứu
            - Các hoạt động phát triển chuyên môn liên tục
            - Kiến thức chuyên ngành và nền tảng lý thuyết"""
        },
        "ky_nang_mem": {
            "type": "integer",
            "description": """Đánh giá kỹ năng mềm và khả năng làm việc (0-10):
            - Kỹ năng giao tiếp và thuyết trình
            - Khả năng làm việc nhóm và phối hợp
            - Tư duy giải quyết vấn đề
            - Khả năng quản lý thời gian và tổ chức công việc
            - Sự chủ động và khả năng thích nghi"""
        },
        "tom_tat": {
            "type": "string",
            "description": """Tóm tắt đánh giá tổng quan về ứng viên trong 2 hoặc 3 câu có thể bao gồm:
            - Điểm mạnh nổi bật nhất
            - Những điểm cần cải thiện
            - Đánh giá tiềm năng phát triển"""
        }
    },
    "required": ["muc_do_phu_hop", "ky_nang_ky_thuat", "kinh_nghiem", "trinh_do_hoc_van", "ky_nang_mem", "tom_tat"]
}

def get_open_jobs():
    """Fetch all open jobs with status 10"""
    url = "https://hiring.base.vn/publicapi/v2/opening/list"
    payload = {'access_token': BASE_API_KEY}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    response = requests.post(url, headers=headers, data=payload)
    data = response.json()

    if 'openings' in data:
        openings = data['openings']
        df = pd.DataFrame(openings)
        # Convert HTML content to plain text
        df['content'] = df['content'].apply(lambda x: BeautifulSoup(x, "html.parser").get_text())
        # Filter for open jobs
        return df[df['status'] == '10'][df['content'].str.len() >= 10][['id', 'name', 'content']]
    return pd.DataFrame()

def get_recent_candidates(opening_id):
    """Fetch candidates from the last 1 days for a specific job"""
    url = "https://hiring.base.vn/publicapi/v2/candidate/list"
    end_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=1)

    payload = {
        'access_token': BASE_API_KEY,
        'opening_id': opening_id,
        'num_per_page': '10000',
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, headers=headers, data=payload)
    return response.json()

def get_pdf_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with BytesIO(response.content) as f:
            reader = PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + " "
        return ' '.join(text.split()) # Xóa khoảng trắng thừa nếu có
    except Exception as e:
        print(f"Lỗi khi tải hoặc trích xuất văn bản từ URL {url}: {str(e)}")
        return None

def get_docx_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        with BytesIO(response.content) as f:
            # Thử xử lý như file DOCX trước
            try:
                document = Document(f)
                text = ""
                for para in document.paragraphs:
                    text += para.text + "\n"
                return ' '.join(text.split())
            except:
                # Nếu không phải DOCX, thử đọc như văn bản thông thường
                try:
                    f.seek(0)  # Reset con trỏ file về đầu
                    raw_text = f.read().decode('utf-8', errors='ignore')
                    # Loại bỏ các ký tự không phải văn bản
                    clean_text = ''.join(char for char in raw_text if char.isprintable())
                    return ' '.join(clean_text.split())
                except:
                    print(f"Không thể đọc nội dung file từ URL {url}")
                    return None
    except Exception as e:
        print(f"Lỗi khi tải hoặc trích xuất văn bản từ URL {url}: {str(e)}")
        return None

def get_cv_text(cv_url):
    if not isinstance(cv_url, str):
        print(f"Invalid URL format: {cv_url}. Expected string, got {type(cv_url)}.")
        return None

    cv_url = cv_url.strip()

    if not cv_url:
        print("Empty URL provided.")
        return None

    if cv_url.lower().endswith('.pdf'):
        return get_pdf_text_from_url(cv_url)
    elif cv_url.lower().endswith(('.docx', '.doc')):  # Xử lý cả .doc và .docx
        return get_docx_text_from_url(cv_url)
    else:
        print(f"Unsupported file format for URL: {cv_url}")
        return None
def evaluate_cv(jd, cv_text):
    """Evaluate CV using Gemini"""
    model = genai.GenerativeModel('models/gemini-1.5-flash-latest',
                                generation_config={
                                    "response_mime_type": "application/json",
                                    "response_schema": evaluation_schema
                                })

    prompt = f"""
    Bạn là một chuyên gia nhân sự và tuyển dụng. Hãy đánh giá CV dưới đây dựa trên mô tả công việc và cung cấp phản hồi chính xác theo schema JSON được định nghĩa.
    Mô tả công việc:
    {jd}
    CV:
    {cv_text}
    Vui lòng trả về kết quả đánh giá theo đúng schema JSON đã định nghăa.
    """

    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"Error evaluating CV: {str(e)}")
        return None

def gui_ket_qua_cham_diem(email_gui, mat_khau, email_nhan, duong_dan_file,
                          ten_cong_ty="Công ty ABC"):
    """
    Gửi email tự động kết quả chấm điểm CV.

    Tham số:
    - email_gui: Email người gửi
    - mat_khau: Mật khẩu ứng dụng Gmail
    - email_nhan: Email người nhận
    - duong_dan_file: Đường dẫn đến file CSV chứa kết quả chấm điểm
    - ten_cong_ty: Tên công ty
    """

    # Định dạng ngày tháng
    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y")

    # Tạo message
    message = MIMEMultipart('alternative')
    message['From'] = f"HR {ten_cong_ty} <{email_gui}>"
    message['To'] = email_nhan
    message['Subject'] = f"Kết Quả Chấm Điểm CV Ứng Viên - {ngay_hien_tai}"

    # Tạo nội dung HTML
    noi_dung_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50;">Kết Quả Chấm Điểm CV Ứng Viên</h2>

            <p>Kính gửi Phòng Nhân sự,</p>

            <p>Đính kèm là file kết quả chấm điểm CV của các ứng viên ngày {ngay_hien_tai}.</p>

            <p>File bao gồm các thông tin:</p>
            <ul>
                <li>Thông tin ứng viên</li>
                <li>Điểm số đánh giá</li>
                <li>Tóm tắt và nhận xét về ứng viên</li>
            </ul>

            <p>Vui lòng xem xét và phản hồi nếu cần điều chỉnh.</p>

            <p style="margin-top: 20px;">Trân trọng,<br>
            Phòng Tuyển Dụng<br>
            {ten_cong_ty}</p>

            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666;">
                <p>Đây là email tự động. Vui lòng không trả lời email này.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Đính kèm nội dung HTML
    message.attach(MIMEText(noi_dung_html, 'html'))

    try:
        # Đọc file và lưu lại dưới dạng UTF-8-SIG nếu cần thiết
        csv_data = results_df.to_csv(index=False, encoding='utf-8-sig')  # Chuyển dữ liệu thành UTF-8-SIG

        # Ghi dữ liệu vào file tạm thời để gửi
        with open('temp_utf8_sig.csv', 'w', encoding='utf-8-sig') as temp_file:
            temp_file.write(csv_data)

        # Đính kèm file CSV
        with open('temp_utf8_sig.csv', "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="Ket_Qua_Cham_Diem_CV_{ngay_hien_tai.replace("/","_")}.csv"'
            )
            message.attach(part)

        # Kết nối SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_gui, mat_khau)

        # Gửi email
        server.send_message(message)
        print("Đã gửi kết quả chấm điểm thành công!")

    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file tại '{duong_dan_file}'")
    except smtplib.SMTPAuthenticationError:
        print("Lỗi xác thực: Vui lòng kiểm tra lại email và mật khẩu")
    except Exception as e:
        print(f"Đã xảy ra lỗi: {str(e)}")
    finally:
        server.quit()

# Sử dụng
if __name__ == "__main__":
    # Đầu tiên, thực hiện đánh giá CV
    print("Bắt đầu đánh giá CV...")
    open_jobs = get_open_jobs()
    print(f"Found {len(open_jobs)} open jobs")

    all_results = []

    # Process each job
    for _, job in open_jobs.iterrows():
        print(f"Processing job: {job['name']}")

        # Get recent candidates
        candidates_data = get_recent_candidates(job['id'])
        if 'candidates' not in candidates_data:
            print(f"No candidates found for job {job['name']}")
            continue

        # Process each candidate
        for candidate in tqdm(candidates_data['candidates'], desc=f"Processing candidates for {job['name']}", leave=False):
            if not candidate.get('cvs'):
                continue

            cv_url = candidate['cvs'][0] if isinstance(candidate['cvs'], list) and len(candidate['cvs']) > 0 else None
            if not cv_url:
                continue
            # Convert 'since' Unix timestamp to UTC+7
            time_apply = pd.to_datetime(int(candidate['since']), unit='s', utc=True).tz_convert('Asia/Ho_Chi_Minh')
            # Get CV text
            cv_text = get_cv_text(cv_url)
            if not cv_text:
                continue

            # Evaluate CV
            evaluation = evaluate_cv(job['content'], cv_text)
            if not evaluation:
                continue

            # Calculate overall score
            overall_score = round(sum([
                evaluation["muc_do_phu_hop"],
                evaluation["ky_nang_ky_thuat"],
                evaluation["kinh_nghiem"],
                evaluation["trinh_do_hoc_van"],
                evaluation["ky_nang_mem"]
            ]) / 5, 2)

            # Store results
            result = {
                'Job ID': job['id'],
                'Job Name': job['name'],
                'Candidate ID': candidate['id'],
                'Candidate Name': unescape(candidate['name']),
                'CV URL': cv_url,
                'Ngày ứng tuyển': time_apply,
                'Mức độ phù hợp': evaluation["muc_do_phu_hop"],
                'Kỹ năng kỹ thuật': evaluation["ky_nang_ky_thuat"],
                'Kinh nghiệm': evaluation["kinh_nghiem"],
                'Trình độ học vấn': evaluation["trinh_do_hoc_van"],
                'Kỹ năng mềm': evaluation["ky_nang_mem"],
                'Điểm tổng quát': overall_score,
                'Tóm tắt': evaluation["tom_tat"],
                'Link ứng viên': f"https://hiring.base.vn/opening/{job['id']}?candidate={candidate['id']}"
            }
            all_results.append(result)

            # Add delay to respect API limits
            time.sleep(3)

    # Create final DataFrame and save to CSV
    if all_results:
        results_df = pd.DataFrame(all_results)
        file_path = 'cv_evaluations.csv'
        results_df.to_csv(file_path, index=False, encoding='utf-8-sig')
    else:
        print("No results to save")

    # Sau đó, gửi email kết quả
    print("Bắt đầu gửi email kết quả...")
    email_gui = os.getenv('EMAIL')
    mat_khau = os.getenv('PASSWORD')  # Mật khẩu ứng dụng
    email_nhan = os.getenv('EMAIL_TO')

    gui_ket_qua_cham_diem(
        email_gui=email_gui,
        mat_khau=mat_khau,
        email_nhan=email_nhan,
        duong_dan_file=file_path,
        ten_cong_ty="Công ty A Plus Mineral Material Corporation"
    )

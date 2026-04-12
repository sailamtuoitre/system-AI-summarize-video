# 🚀 Hướng dẫn Setup 9router cho CDIO 3 Project

## 📋 Tổng quan

Tài liệu này hướng dẫn bạn cách tích hợp **9router** vào dự án **AI Video Assistant (CDIO 3)** để:
- ✅ Sử dụng Qwen API miễn phí không giới hạn thông qua 9router
- ✅ Có fallback tự động sang các model khác khi cần
- ✅ Theo dõi quota và usage chi tiết
- ✅ Không lo bị gián đoạn khi coding

---

## 🎯 Tại sao dùng 9router với CDIO 3?

Dự án CDIO 3 của bạn đang dùng **Qwen-3.6-Plus** thông qua **DashScope API**. 9router giúp:

1. **Miễn phí hoàn toàn**: Qwen cung cấp 3+ models miễn phí không giới hạn
2. **Auto fallback**: Tự động chuyển sang model khác nếu có lỗi
3. **Quota tracking**: Theo dõi số lượng request và tokens
4. **Multi-model support**: Dễ dàng chuyển đổi giữa các Qwen models

---

## 🔧 Bước 1: Cài đặt 9router

### Cách 1: Cài đặt Global (Khuyến nghị)

```bash
# Cài đặt 9router globally
npm install -g 9router

# Khởi động 9router
9router
```

Dashboard sẽ mở tự động tại: `http://localhost:20128`

### Cách 2: Chạy từ Source (Development)

```bash
# Di chuyển vào thư mục 9router
cd "C:\Users\leduc\OneDrive\Desktop\9router\9router"

# Cài đặt dependencies
npm install

# Copy file cấu hình
copy .env.example .env

# Chạy development server
npm run dev
```

Server sẽ chạy tại `http://localhost:20128`

---

## 🔐 Bước 2: Kết nối Qwen Provider

### 1. Mở Dashboard
Truy cập: `http://localhost:20128/dashboard`

### 2. Kết nối Qwen
1. Click **Providers** trong menu
2. Tìm **Qwen** và click **Connect**
3. Làm theo hướng dẫn Device Code Authorization
4. Đợi authorization hoàn tất

**Qwen cung cấp các models miễn phí:**
- `qw/qwen3-coder-plus` - Model coding mạnh mẽ
- `qw/qwen3-coder-flash` - Model nhanh hơn
- Các models khác (nếu có)

### 3. Xác nhận kết nối
Sau khi connect thành công, bạn sẽ thấy:
- ✅ Trạng thái: Connected
- 📊 Quota: Unlimited (miễn phí không giới hạn)
- 🎯 Available models được liệt kê

---

## 🎨 Bước 3: Tạo Combo cho CDIO 3

### Tạo Fallback Combo

1. Vào **Combos** → **Create New**

2. Đặt tên: `cdio3-qwen-stack`

3. Thêm models theo thứ tự ưu tiên:

```
1. qw/qwen3-coder-plus    (Primary - Qwen miễn phí)
2. if/qwen3-coder-plus    (Backup - qua iFlow)
3. glm/glm-4.7            (Cheap backup - $0.6/1M tokens)
```

4. **Save** combo

### Giải thích:
- **qw/qwen3-coder-plus**: Qwen trực tiếp, miễn phí 100%
- **if/qwen3-coder-plus**: Backup qua iFlow (cũng miễn phí)
- **glm/glm-4.7**: Rẻ nhất nếu cần backup ($0.6 cho 1M tokens)

---

## ⚙️ Bước 4: Cấu hình CDIO 3 Project

### 1. Lấy API Key từ 9router

1. Mở Dashboard: `http://localhost:20128`
2. Vào **Settings** hoặc **API Keys**
3. **Copy API Key** được cung cấp

### 2. Update file .env trong CDIO 3

Mở file `C:\Users\leduc\OneDrive\Desktop\CDIO 3\.env` và cập nhật:

```env
# --- AI CONFIGURATION (via 9router) ---
# 9router sẽ route đến Qwen API tự động
DASHSCOPE_API_KEY=your_9router_api_key_here
QWEN_ENDPOINT=http://localhost:20128/v1
QWEN_MODEL_NAME=qw/qwen3-coder-plus

# 9router Configuration
NINE_ROUTER_URL=http://localhost:20128/v1
NINE_ROUTER_API_KEY=your_9router_api_key_here

# --- DATABASE / STORAGE PATHS ---
DATA_DIR=./data
JOBS_DIR=./data/jobs

# --- SERVER CONFIGURATION ---
PORT=8000
HOST=0.0.0.0

# --- FEATURE FLAGS ---
ENABLE_VISUAL_PROCESSING=true
ENABLE_MAP_REDUCE=true
```

**Lưu ý**: Thay `your_9router_api_key_here` bằng API key thực tế từ dashboard.

---

## 🔌 Bước 5: Update Code để dùng 9router

### Option A: Giữ nguyên DashScope SDK (Recommended)

Nếu code hiện tại dùng DashScope SDK, bạn có thể giữ nguyên và chỉ thay đổi endpoint:

```python
# File: core/services/generation_service.py hoặc tương tự

from openai import OpenAI  # Hoặc dashscope SDK

class GenerationService:
    def __init__(self):
        # Dùng 9router endpoint thay vì DashScope trực tiếp
        self.client = OpenAI(
            api_key=os.getenv("NINE_ROUTER_API_KEY"),
            base_url=os.getenv("NINE_ROUTER_URL", "http://localhost:20128/v1")
        )
        self.model = os.getenv("QWEN_MODEL_NAME", "qw/qwen3-coder-plus")
    
    async def generate(self, prompt: str, context: str = "") -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an AI assistant for video education analysis."},
                {"role": "user", "content": f"{context}\n\n{prompt}"}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
```

### Option B: Dùng OpenAI-compatible API

9router cung cấp OpenAI-compatible endpoint, nên bạn có thể dùng OpenAI SDK:

```python
from openai import OpenAI

class GenerationService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("NINE_ROUTER_API_KEY"),
            base_url=os.getenv("NINE_ROUTER_URL", "http://localhost:20128/v1")
        )
        self.model = os.getenv("QWEN_MODEL_NAME", "qw/qwen3-coder-plus")
```

---

## ▶️ Bước 6: Chạy ứng dụng

### 1. Khởi động 9router

```bash
# Terminal 1 - Chạy 9router
9router
# Hoặc nếu dùng source:
cd "C:\Users\leduc\OneDrive\Desktop\9router\9router"
npm run dev
```

Dashboard: `http://localhost:20128`

### 2. Chạy Backend API

```bash
# Terminal 2 - Backend
cd "C:\Users\leduc\OneDrive\Desktop\CDIO 3"

# Cài đặt dependencies (nếu chưa làm)
pip install -r requirements.txt

# Chạy API server
python -m uvicorn apps.api.main:app --reload --port 8000
# Hoặc theo hướng dẫn cũ của project
```

### 3. Chạy Frontend UI

```bash
# Terminal 3 - Frontend
cd "C:\Users\leduc\OneDrive\Desktop\CDIO 3\apps\web-ui"
npm run dev
```

---

## ✅ Bước 7: Kiểm tra Integration

### 1. Test API Connection

Mở browser và truy cập: `http://localhost:20128/dashboard`

Kiểm tra:
- ✅ Qwen provider đang Connected
- ✅ Combo `cdio3-qwen-stack` đã được tạo
- ✅ API key đã được tạo

### 2. Test Request đầu tiên

Upload một video ngắn trong UI và kiểm tra:

1. Video được upload thành công
2. Pipeline xử lý chạy bình thường
3. Qwen model được gọi thông qua 9router
4. Kết quả trả về đúng

### 3. Monitor trong Dashboard

Trong lúc test, mở Dashboard để xem:
- 📊 Request logs
- 💰 Token usage (Qwen miễn phí nên sẽ là $0)
- 🔄 Routing status

---

## 🎯 Lợi ích khi dùng 9router

### Trước (Direct DashScope):
- ❌ Phải trả tiền cho DashScope API
- ❌ Giới hạn quota hàng tháng
- ❌ Không có fallback khi lỗi
- ❌ Khó theo dõi usage

### Sau (Via 9router):
- ✅ **Miễn phí 100%** với Qwen models
- ✅ **Unlimited requests** - không lo quota
- ✅ **Auto fallback** - luôn có backup
- ✅ **Real-time monitoring** - biết chính xác usage
- ✅ **Multi-model support** - dễ dàng test models khác nhau

---

## 💡 Mẹo và Best Practices

### 1. Sử dụng Combo thông minh

```
Combo: cdio3-production
1. qw/qwen3-coder-plus    (Chính - miễn phí)
2. if/kimi-k2-thinking    (Backup 1 - miễn phí)
3. glm/glm-4.7            (Backup 2 - rất rẻ)
```

### 2. Monitor Usage

Thường xuyên check Dashboard để:
- Xem model nào đang được dùng
- Token usage patterns
- Optimize prompts nếu cần

### 3. Enable Request Logs (Debug)

Trong `.env` của 9router:
```env
ENABLE_REQUEST_LOGS=true
```

Giúp debug dễ dàng hơn.

### 4. Test nhiều scenarios

- Video ngắn (< 10 phút)
- Video dài (> 60 phút) 
- Multiple languages (Tiếng Việt, English)
- Complex queries trong chat

---

## 🐛 Troubleshooting

### Lỗi: "Cannot connect to 9router"

**Nguyên nhân**: 9router chưa chạy
**Giải pháp**: 
```bash
9router
# hoặc
cd "C:\Users\leduc\OneDrive\Desktop\9router\9router" && npm run dev
```

### Lỗi: "Invalid API Key"

**Nguyên nhân**: API key trong .env không đúng
**Giải pháp**: 
1. Mở Dashboard: `http://localhost:20128`
2. Copy lại API key
3. Update file `.env` trong CDIO 3
4. Restart backend server

### Lỗi: "Model not found"

**Nguyên nhân**: Tên model không đúng hoặc Qwen chưa connect
**Giải pháp**:
1. Check Dashboard → Providers → Qwen đã connected chưa
2. Dùng đúng tên model: `qw/qwen3-coder-plus`
3. Check Dashboard → Combos để xem available models

### Lỗi: "Rate limit exceeded"

Qwen miễn phí không có rate limit nghiêm ngặt, nhưng nếu gặp lỗi:
- Check Dashboard để xem có issue gì không
- Thử chuyển sang model khác trong combo
- Restart 9router

---

## 📊 So sánh chi phí

### Setup hiện tại (Direct DashScope):
```
Qwen-3.6-Plus via DashScope:
- Input: ~$0.002/1K tokens
- Output: ~$0.006/1K tokens
- Estimated monthly: $10-50 (tùy usage)
```

### Setup mới (Via 9router):
```
Qwen via 9router:
- Cost: $0 (miễn phí 100%)
- Quota: Unlimited
- Backup models: Free hoặc rất rẻ
- Estimated monthly: $0-5
```

**Tiết kiệm: ~90-100% costs** 🎉

---

## 🔐 Security Notes

1. **Không commit API keys**: File `.env` đã có trong `.gitignore`
2. **9router chạy local**: Tất cả traffic là localhost, an toàn
3. **API keys được encrypt**: 9router lưu keys an toàn
4. **Không expose ra ngoài**: Chỉ dùng cho development local

---

## 📚 Tài liệu tham khảo

- [9router Documentation](C:\Users\leduc\OneDrive\Desktop\9router\9router\README.md)
- [CDIO 3 Documentation](C:\Users\leduc\OneDrive\Desktop\CDIO 3\README.md)
- [Qwen Models](https://help.aliyun.com/zh/model-studio/developer-reference/)
- [9router Website](https://9router.com)

---

## 🎓 Kiến trúc sau khi tích hợp

```
┌─────────────────────────────────────────────────────────────┐
│                      UI (React + Vite)                       │
│                        localhost:5173                        │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────────┐
│                Backend (FastAPI)                             │
│                   localhost:8000                             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Generation Service (qua 9router)                     │   │
│  │  base_url: http://localhost:20128/v1                  │   │
│  └──────────────────┬───────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                      │ OpenAI-compatible API
┌─────────────────────▼───────────────────────────────────────┐
│                  9router (Smart Router)                      │
│                   localhost:20128                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Combo: cdio3-qwen-stack                              │   │
│  │  1. qw/qwen3-coder-plus (Primary - FREE)             │   │
│  │  2. if/qwen3-coder-plus (Backup - FREE)              │   │
│  │  3. glm/glm-4.7 (Cheap - $0.6/1M)                    │   │
│  └──────────────────┬───────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│   Qwen API      │      │   Backup APIs   │
│   (FREE)        │      │   (Free/Cheap)  │
│   DashScope     │      │                 │
└─────────────────┘      └─────────────────┘
```

---

## 🚀 Quick Start Commands

```bash
# Terminal 1 - 9router
cd "C:\Users\leduc\OneDrive\Desktop\9router\9router"
npm install  # lần đầu tiên
npm run dev

# Terminal 2 - Backend
cd "C:\Users\leduc\OneDrive\Desktop\CDIO 3"
pip install -r requirements.txt  # lần đầu tiên
python -m uvicorn apps.api.main:app --reload --port 8000

# Terminal 3 - Frontend
cd "C:\Users\leduc\OneDrive\Desktop\CDIO 3\apps\web-ui"
npm install  # lần đầu tiên
npm run dev
```

**Truy cập:**
- 9router Dashboard: http://localhost:20128
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:5173

---

<p align="center">Made with ❤️ for CDIO 3 Project - AI Video Assistant</p>
<p align="center">Setup 9router + Qwen API = Free Unlimited AI Coding 🎉</p>

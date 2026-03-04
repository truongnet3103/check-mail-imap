# Mail Nexus 📧

Ứng dụng quản lý email IMAP với AI tích hợp.

## Tính năng

- ✅ Fetch email từ IMAP server (Gmail, Outlook, v.v.)
- ✅ Dịch email sang tiếng Việt (Google Translate)
- ✅ Tóm tắt email bằng AI (Gemini)
- ✅ 3 chế độ xem: Gốc | Dịch | AI
- ✅ Lưu trữ trên Firebase Firestore
- ✅ UI gọn gàng, tối ưu cho Streamlit Cloud

## Deploy lên Streamlit Cloud

1. Fork/push code lên GitHub
2. Vào [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Thêm secrets trong Settings:

```toml
[firebase]
type = "service_account"
project_id = "your-project"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n..."
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

5. Deploy!

## Cấu trúc

```
.
├── .streamlit/
│   ├── config.toml    # Theme config + ẩn menu
│   └── secrets.toml   # Firebase credentials
├── app.py             # Main application
└── requirements.txt   # Dependencies
```

## Sử dụng

1. Mở **⚙️ Cấu hình** ở footer sidebar
2. Nhập Gemini API Key
3. Cấu hình IMAP (host, username, app password)
4. Click **FETCH EMAILS** để lấy email
5. Click **Xem** để đọc email với 3 chế độ: Gốc / Dịch / AI

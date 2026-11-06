# عارض HTML

تطبيق Django: الأدمن يرفع ملف HTML بزرار، ويتعرض جوه التطبيق في iframe معزول.

## تشغيل محلي
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## النشر على Render
1. ارفع المشروع على GitHub.
2. في Render: New → Blueprint → اختار الريبو (هيقرأ `render.yaml`).
3. اكتب `DATABASE_URL` (رابط Neon) و`ADMIN_USERNAME` و`ADMIN_PASSWORD` لما يطلبهم.
4. بعد النشر افتح الرابط واعمل «دخول الأدمن».

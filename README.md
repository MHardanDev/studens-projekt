# رفيق الدراسة

موقع Web server-rendered عربي أولاً، قيد التأسيس لمنصة جامعية خفيفة تعمل جيداً على هواتف قديمة واتصال ضعيف.

## تشغيل محلي سريع

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

ثم افتح `http://127.0.0.1:8000/ar/`.

## PostgreSQL

الإعداد المفضل يستخدم PostgreSQL عبر `DATABASE_URL`.

```powershell
docker compose up -d db
$env:DATABASE_URL="postgresql://campus:campus@127.0.0.1:5432/campus"
.venv\Scripts\python manage.py migrate
```

إذا لم يتوفر Docker محلياً، يستخدم Django قاعدة SQLite للتشغيل والاختبارات المحلية فقط، ولا تعد بديلاً عن PostgreSQL في الإنتاج.

## الحالة الحالية للمشروع

تم إنجاز المراحل 0 حتى 7 بنجاح: الفهرس الأكاديمي، الحسابات والأدوار والنطاقات، رفع الملفات الآمن، سير عمل المراجعة والاعتماد والنسخ المنشورة، صفحة تفاصيل الملف، والتنزيل الخاص المتدفق مع دعم Range وCache-Control: no-store ووضع توفير البيانات.

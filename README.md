# Unified Charity Platform (MVP)

منصة موحدة تربط 3 جمعيات خيرية في نظام واحد لمنع تكرار صرف المساعدات لنفس المستفيد، مع دعم المتبرعين والإدارة.

## Features
- تسجيل / تسجيل دخول (JWT).
- أدوار: `admin`, `donor`, `beneficiary`.
- تسجيل المحتاج ورفع رابط مستندات.
- إدارة الحالات بكود موحد `CASE-XXXXXXXX` وأولوية.
- تبرع على حالة معينة مع توزيع تلقائي:
  - المطلوب يذهب للمحتاج.
  - أي زيادة تذهب لحساب الجمعية.
- تبرع مباشر للجمعية من الهوم.
- لوحة تحكم للإدارة (إجمالي التبرعات، عدد المتبرعين، عدد المحتاجين، تبرعات حسب الجمعية).

## Tech Stack
- Backend: FastAPI + SQLModel + SQLite
- Frontend: Jinja templates + Bootstrap + Chart.js

## Run
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

ثم افتح:
- Home: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

## Notes
- هذا الإصدار يركز على الفرونت/باك/API فقط.
- جزء الـ Data Engineering (Kafka/Spark/DWH) غير مضمّن حسب الطلب، ويمكن وصله لاحقًا عبر event bus.

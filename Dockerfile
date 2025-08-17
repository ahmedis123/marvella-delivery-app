# 1. استخدام صورة بايثون رسمية كأساس
FROM python:3.11-slim

# 2. تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# 3. نسخ ملف المكتبات المطلوبة
COPY requirements.txt .

# 4. تثبيت الحزم اللازمة لتشغيل WeasyPrint والمكتبات الأخرى
# (هذه الحزم ضرورية لبيئة Debian/Ubuntu التي تعتمد عليها صورة بايثون)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    pango1.0-tools \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 5. تثبيت مكتبات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# 6. نسخ كل ملفات المشروع إلى مجلد العمل في الحاوية
COPY . .

# 7. تحديد الأمر الذي سيتم تشغيله عند بدء تشغيل الحاوية
CMD ["python", "app.py"]

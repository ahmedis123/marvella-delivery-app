# app.py (Version 7.0 - Advanced Filtering & Automated Backups)

# =======================================================================
# | الجزء الأول: إعداد التطبيق والنماذج (Application Setup & Models)      |
# =======================================================================

# --- 1. استيراد المكتبات الأساسية ---
import os
import shutil
from datetime import datetime
from urllib.parse import quote
from pathlib import Path
from flask import (
    Flask, request, redirect, url_for, flash, render_template, 
    make_response, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, 
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from jinja2 import DictLoader
from sqlalchemy import func, or_
from weasyprint import HTML
from flask_apscheduler import APScheduler

# --- 2. تعريف قوالب HTML ---
templates = {
    "layout.html": """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}لوحة تحكم مارفيلا{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; background-color: #f8f9fa; }
        .navbar { background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,.1); }
        .nav-link.active { font-weight: bold; color: #d63384 !important; }
        .btn-primary { background-color: #d63384; border-color: #d63384; }
        .btn-primary:hover { background-color: #b02a6c; border-color: #b02a6c; }
        .table-hover tbody tr:hover { background-color: #f1f1f1; }
        .spinner-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 1060; display: none; justify-content: center; align-items: center; }
        .status-badge { font-size: 0.9em; }
        .status-جديد { background-color: #ffc107 !important; color: black; }
        .status-تم-الشراء { background-color: #0dcaf0 !important; color: white; }
        .status-في-الطريق { background-color: #fd7e14 !important; color: white; }
        .status-تم-التسليم { background-color: #198754 !important; color: white; }
        .payment-لم-يتم-الدفع { background-color: #dc3545 !important; color: white; }
        .payment-تم-الدفع { background-color: #198754 !important; color: white; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light mb-4">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}"><strong>مارفيلا 🛍️</strong></a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"><span class="navbar-toggler-icon"></span></button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item"><a class="nav-link {% if request.endpoint == 'dashboard' %}active{% endif %}" href="{{ url_for('dashboard') }}">إدارة الطلبات</a></li>
                    <li class="nav-item"><a class="nav-link {% if request.endpoint == 'statistics' %}active{% endif %}" href="{{ url_for('statistics') }}">الإحصائيات</a></li>
                    <li class="nav-item"><a class="nav-link {% if request.endpoint == 'system_management' %}active{% endif %}" href="{{ url_for('system_management') }}">إدارة النظام</a></li>
                    {% endif %}
                </ul>
                {% if current_user.is_authenticated %}
                <div class="d-flex align-items-center"><span class="navbar-text me-3">أهلاً, {{ current_user.username }}</span><a href="{{ url_for('logout') }}" class="btn btn-outline-danger">تسجيل الخروج</a></div>
                {% endif %}
            </div>
        </div>
    </nav>
    <main class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">{{ message }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endfor %}{% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </main>
    <div class="spinner-overlay" id="spinner-overlay"><div class="spinner-border text-light" role="status"><span class="visually-hidden">Loading...</span></div></div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function showSpinner() { document.getElementById('spinner-overlay').style.display = 'flex'; }
        function hideSpinner() { document.getElementById('spinner-overlay').style.display = 'none'; }
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>
""",
    "login.html": """
{% extends "layout.html" %}
{% block title %}تسجيل الدخول{% endblock %}
{% block content %}
<div class="row justify-content-center mt-5">
    <div class="col-md-5">
        <div class="card">
            <div class="card-body">
                <h3 class="card-title text-center mb-4">تسجيل الدخول</h3>
                <form method="POST" action="{{ url_for('login') }}">
                    <div class="mb-3">
                        <label for="username" class="form-label">اسم المستخدم</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">كلمة المرور</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">دخول</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",
    "dashboard.html": """
{% extends "layout.html" %}
{% block title %}إدارة الطلبات{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>إدارة الطلبات</h2>
    <a href="{{ url_for('add_order') }}" class="btn btn-primary"><i class="bi bi-plus-circle-fill me-2"></i>إضافة طلب جديد</a>
</div>
<div class="card mb-4">
    <div class="card-body">
        <form method="GET" action="{{ url_for('dashboard') }}" class="row g-3 align-items-center">
            <div class="col-md-5">
                <div class="input-group">
                    <span class="input-group-text"><i class="bi bi-search"></i></span>
                    <input type="text" class="form-control" name="search_term" placeholder="ابحث بالاسم، الهاتف، أو رقم الطلب..." value="{{ request.args.get('search_term', '') }}">
                </div>
            </div>
            <div class="col-md-3">
                <select name="order_status" class="form-select">
                    <option value="">كل حالات الطلب</option>
                    {% set statuses = ['جديد', 'تم الشراء', 'في الطريق', 'تم التسليم'] %}
                    {% for status in statuses %}
                    <option value="{{ status }}" {% if request.args.get('order_status') == status %}selected{% endif %}>{{ status }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-3">
                <select name="payment_status" class="form-select">
                    <option value="">كل حالات الدفع</option>
                    <option value="لم يتم الدفع" {% if request.args.get('payment_status') == 'لم يتم الدفع' %}selected{% endif %}>لم يتم الدفع</option>
                    <option value="تم الدفع" {% if request.args.get('payment_status') == 'تم الدفع' %}selected{% endif %}>تم الدفع</option>
                </select>
            </div>
            <div class="col-md-1">
                <button type="submit" class="btn btn-info w-100">فلترة</button>
            </div>
        </form>
    </div>
</div>
<div class="card">
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-hover align-middle">
                <thead class="table-light">
                    <tr>
                        <th>#</th><th>العميل</th><th>المدينة</th><th>الإجمالي</th>
                        <th>حالة الطلب</th><th>حالة الدفع</th><th>التاريخ</th><th>إجراءات</th>
                    </tr>
                </thead>
                <tbody>
                    {% for order in orders %}
                    <tr>
                        <td>{{ order.id }}</td>
                        <td>{{ order.customer_name }}<br><small class="text-muted">{{ order.customer_phone }}</small></td>
                        <td>{{ order.destination_city }}</td>
                        <td>{{ "%.2f"|format(order.total_cost) }} ج.س</td>
                        <td><span class="badge rounded-pill status-badge status-{{ order.order_status.replace(' ', '-') }}">{{ order.order_status }}</span></td>
                        <td><span class="badge rounded-pill status-badge payment-{{ order.payment_status.replace(' ', '-') }}">{{ order.payment_status }}</span></td>
                        <td>{{ order.created_at.strftime('%Y-%m-%d') }}</td>
                        <td>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">إجراءات</button>
                                <ul class="dropdown-menu">
                                    <li><a class="dropdown-item" href="{{ url_for('download_invoice_pdf', order_id=order.id) }}"><i class="bi bi-file-earmark-pdf me-2"></i>تحميل PDF</a></li>
                                    <li><a class="dropdown-item" href="{{ url_for('edit_order', order_id=order.id) }}"><i class="bi bi-pencil-square me-2"></i>تعديل</a></li>
                                </ul>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="8" class="text-center">لا توجد طلبات تطابق معايير البحث.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
""",
    "order_form.html": """
{% extends "layout.html" %}
{% block title %}{{ 'تعديل' if order else 'إضافة' }} طلب{% endblock %}
{% block content %}
<h2>{{ 'تعديل' if order else 'إضافة' }} طلب</h2>
<form method="POST" id="orderForm">
    <div class="card mt-4">
        <div class="card-header">معلومات العميل والطلب</div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6 mb-3"><label for="customer_name" class="form-label">اسم العميل</label><input type="text" class="form-control" id="customer_name" name="customer_name" value="{{ order.customer_name if order else '' }}" required></div>
                <div class="col-md-6 mb-3"><label for="customer_phone" class="form-label">رقم هاتف العميل</label><input type="text" class="form-control" id="customer_phone" name="customer_phone" value="{{ order.customer_phone if order else '' }}" required></div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3"><label for="destination_city" class="form-label">مدينة التوصيل</label><input type="text" class="form-control" id="destination_city" name="destination_city" value="{{ order.destination_city if order else '' }}" required></div>
                <div class="col-md-6 mb-3"><label for="shipping_cost" class="form-label">تكلفة الشحن (جنيه سوداني)</label><input type="number" step="0.01" class="form-control" id="shipping_cost" name="shipping_cost" value="{{ order.shipping_cost if order else 0.0 }}" required></div>
            </div>
            {% if order %}
            <div class="row">
                <div class="col-md-6 mb-3"><label for="order_status" class="form-label">حالة الطلب</label><select class="form-select" id="order_status" name="order_status">{% set statuses = ['جديد', 'تم الشراء', 'في الطريق', 'تم التسليم'] %}{% for status in statuses %}<option value="{{ status }}" {% if order.order_status == status %}selected{% endif %}>{{ status }}</option>{% endfor %}</select></div>
                <div class="col-md-6 mb-3"><label for="payment_status" class="form-label">حالة الدفع</label><select class="form-select" id="payment_status" name="payment_status"><option value="لم يتم الدفع" {% if order.payment_status == 'لم يتم الدفع' %}selected{% endif %}>لم يتم الدفع</option><option value="تم الدفع" {% if order.payment_status == 'تم الدفع' %}selected{% endif %}>تم الدفع</option></select></div>
            </div>
            {% endif %}
        </div>
    </div>
    <div class="card mt-4">
        <div class="card-header d-flex justify-content-between align-items-center"><span>المنتجات</span><button type="button" class="btn btn-sm btn-success" id="addProductBtn"><i class="bi bi-plus"></i> إضافة منتج</button></div>
        <div class="card-body"><div id="productsContainer">{% if order and order.products %}{% for product in order.products %}<div class="row product-row mb-2 align-items-center"><div class="col-md-7"><input type="text" name="product_description" class="form-control" placeholder="وصف المنتج" value="{{ product.description }}" required></div><div class="col-md-3"><input type="number" name="product_price" class="form-control" placeholder="السعر (ج.س)" step="0.01" value="{{ product.price }}" required></div><div class="col-md-2"><button type="button" class="btn btn-outline-danger remove-product">حذف</button></div></div>{% endfor %}{% endif %}</div></div>
        <div class="card-footer bg-white"><div class="d-flex justify-content-end align-items-center"><h4 class="me-3 mb-0">الإجمالي:</h4><h4 id="total-display" class="fw-bold text-primary mb-0">0.00 ج.س</h4></div></div>
    </div>
    <div class="mt-4"><button type="submit" class="btn btn-primary px-4">{{ 'حفظ التعديلات' if order else 'إنشاء الطلب' }}</button><a href="{{ url_for('dashboard') }}" class="btn btn-secondary">إلغاء</a>{% if order %}<a href="{{ url_for('delete_order', order_id=order.id) }}" class="btn btn-danger float-end" onclick="return confirm('هل أنت متأكد من حذف هذا الطلب وكل منتجاته؟')"><i class="bi bi-trash me-2"></i>حذف الطلب</a>{% endif %}</div>
</form>
{% endblock %}
{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    const addProductBtn = document.getElementById('addProductBtn');
    const productsContainer = document.getElementById('productsContainer');
    const shippingCostInput = document.getElementById('shipping_cost');
    const totalDisplay = document.getElementById('total-display');

    function calculateTotal() {
        let productsTotal = 0;
        document.querySelectorAll('.product-row').forEach(row => {
            const priceInput = row.querySelector('input[name="product_price"]');
            if (priceInput && priceInput.value) { productsTotal += parseFloat(priceInput.value); }
        });
        const shippingCost = parseFloat(shippingCostInput.value) || 0;
        const grandTotal = productsTotal + shippingCost;
        totalDisplay.textContent = grandTotal.toFixed(2) + ' ج.س';
    }

    function addProductRow(desc = '', price = '') {
        const productRow = document.createElement('div');
        productRow.className = 'row product-row mb-2 align-items-center';
        productRow.innerHTML = `<div class="col-md-7"><input type="text" name="product_description" class="form-control" placeholder="وصف المنتج" value="${desc}" required></div><div class="col-md-3"><input type="number" name="product_price" class="form-control" placeholder="السعر (ج.س)" step="0.01" value="${price}" required></div><div class="col-md-2"><button type="button" class="btn btn-outline-danger remove-product">حذف</button></div>`;
        productsContainer.appendChild(productRow);
    }

    addProductBtn.addEventListener('click', () => addProductRow());
    productsContainer.addEventListener('click', function(e) { if (e.target && e.target.classList.contains('remove-product')) { e.target.closest('.product-row').remove(); calculateTotal(); }});
    productsContainer.addEventListener('input', calculateTotal);
    shippingCostInput.addEventListener('input', calculateTotal);
    
    if (productsContainer.children.length === 0) { addProductRow(); }
    calculateTotal();
});
</script>
{% endblock %}
""",
    "statistics.html": """
{% extends "layout.html" %}
{% block title %}الإحصائيات{% endblock %}
{% block content %}
<style>
    .stat-card { text-align: center; padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }
    .stat-card:hover { transform: translateY(-5px); }
    .stat-card h3 { font-size: 2.5rem; font-weight: bold; }
    .stat-card p { font-size: 1.2rem; }
    .bg-revenue { background: linear-gradient(45deg, #28a745, #218838); }
    .bg-orders { background: linear-gradient(45deg, #17a2b8, #138496); }
    .bg-completed { background: linear-gradient(45deg, #007bff, #0069d9); }
    .bg-avg { background: linear-gradient(45deg, #fd7e14, #e36a02); }
</style>
<h2 class="mb-4">نظرة عامة على الأداء</h2>
<div class="row">
    <div class="col-md-6 col-lg-3"><div class="stat-card bg-revenue"><h3>{{ "%.0f"|format(stats.total_revenue) }}</h3><p>إجمالي الإيرادات (ج.س)</p></div></div>
    <div class="col-md-6 col-lg-3"><div class="stat-card bg-orders"><h3>{{ stats.total_orders }}</h3><p>إجمالي الطلبات</p></div></div>
    <div class="col-md-6 col-lg-3"><div class="stat-card bg-completed"><h3>{{ stats.completed_orders }}</h3><p>الطلبات المكتملة</p></div></div>
    <div class="col-md-6 col-lg-3"><div class="stat-card bg-avg"><h3>{{ "%.0f"|format(stats.average_order_value) }}</h3><p>متوسط قيمة الطلب (ج.س)</p></div></div>
</div>
<div class="row mt-4">
    <div class="col-md-12"><div class="card"><div class="card-header"><h4>أكثر المدن طلباً</h4></div><div class="card-body">{% if stats.top_cities %}<ul class="list-group">{% for city, count in stats.top_cities %}<li class="list-group-item d-flex justify-content-between align-items-center">{{ city }}<span class="badge bg-primary rounded-pill">{{ count }} طلبات</span></li>{% endfor %}</ul>{% else %}<p class="text-muted">لا توجد بيانات كافية لعرضها.</p>{% endif %}</div></div></div>
</div>
{% endblock %}
""",
    "system_management.html": """
{% extends "layout.html" %}
{% block title %}إدارة النظام{% endblock %}
{% block content %}
<h2>إدارة النظام</h2>
<div class="row mt-4">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h4><i class="bi bi-database-down me-2"></i>النسخ الاحتياطية الحالية</h4>
                <a href="{{ url_for('create_backup') }}" class="btn btn-primary" onclick="showSpinner()"><i class="bi bi-plus-circle me-2"></i>إنشاء نسخة جديدة</a>
            </div>
            <div class="card-body">
                <p>إدارة النسخ الاحتياطية. يمكنك استعادة بياناتك من نسخة سابقة أو تحميلها للاحتفاظ بها.</p>
                {% if backups %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead><tr><th>اسم الملف</th><th class="text-center">الإجراءات</th></tr></thead>
                        <tbody>
                            {% for backup in backups %}
                            <tr>
                                <td class="align-middle">{{ backup }}</td>
                                <td class="text-center">
                                    <a href="{{ url_for('download_backup', filename=backup) }}" class="btn btn-sm btn-success"><i class="bi bi-download me-1"></i> تحميل</a>
                                    <form method="POST" action="{{ url_for('restore_backup') }}" style="display: inline-block;" onsubmit="return confirm('تحذير! هذه العملية ستحذف جميع البيانات الحالية وتستبدلها بالبيانات من النسخة الاحتياطية {{ backup }}. هل أنت متأكد؟');">
                                        <input type="hidden" name="backup_file" value="{{ backup }}">
                                        <button type="submit" class="btn btn-sm btn-danger" onclick="showSpinner()"><i class="bi bi-arrow-counterclockwise me-1"></i> استعادة</button>
                                    </form>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <p class="text-muted">لا توجد نسخ احتياطية متاحة.</p>
                {% endif %}
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-header"><h4><i class="bi bi-upload me-2"></i>رفع نسخة احتياطية</h4></div>
            <div class="card-body">
                <p>يمكنك رفع ملف قاعدة بيانات (.db) من جهازك لاستخدامه كنسخة احتياطية.</p>
                <form action="{{ url_for('upload_backup') }}" method="post" enctype="multipart/form-data">
                    <div class="mb-3">
                        <input class="form-control" type="file" name="backup_file" accept=".db" required>
                    </div>
                    <button type="submit" class="btn btn-info w-100" onclick="showSpinner()">رفع واستعادة</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",
    "invoice_pdf_template.html": """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>فاتورة طلب #{{ order.id }}</title>
    <style>
        @font-face {
            font-family: 'Cairo';
            src: url('{{ cairo_regular_path }}');
            font-weight: normal;
        }
        @font-face {
            font-family: 'Cairo';
            src: url('{{ cairo_bold_path }}');
            font-weight: bold;
        }
        body { 
            font-family: 'Cairo', sans-serif; 
            direction: rtl; 
            font-size: 14px;
            color: #333;
        }
        .invoice-container {
            padding: 40px;
            max-width: 800px;
            margin: auto;
            background: #fff;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 40px;
            border-bottom: 2px solid #eee;
            padding-bottom: 20px;
        }
        .header .logo {
            max-width: 120px;
        }
        .header .invoice-details {
            text-align: left;
        }
        .header h1 {
            margin: 0;
            font-size: 32px;
            color: #333;
        }
        .header p {
            margin: 2px 0;
            color: #777;
        }
        .customer-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 40px;
        }
        .customer-info div {
            width: 48%;
        }
        .customer-info h4 {
            margin-bottom: 10px;
            color: #d63384;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }
        .customer-info p {
            margin: 4px 0;
        }
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }
        .items-table thead {
            background-color: #f9f9f9;
            border-bottom: 2px solid #d63384;
        }
        .items-table th {
            padding: 12px;
            text-align: right;
            font-weight: bold;
        }
        .items-table td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        .items-table tbody tr:last-child td {
            border-bottom: none;
        }
        .totals {
            width: 100%;
            text-align: left;
        }
        .totals table {
            width: 50%;
            margin-left: 50%;
            border-collapse: collapse;
        }
        .totals td {
            padding: 10px;
        }
        .totals .total-row td {
            border-top: 2px solid #333;
            font-weight: bold;
            font-size: 18px;
        }
        .footer {
            text-align: center;
            margin-top: 50px;
            color: #777;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="invoice-container">
        <div class="header">
            <div>
                <img src="{{ logo_path }}" alt="شعار الشركة" class="logo">
            </div>
            <div class="invoice-details">
                <h1>فاتورة</h1>
                <p>رقم: #{{ order.id }}</p>
                <p>التاريخ: {{ order.created_at.strftime('%Y-%m-%d') }}</p>
            </div>
        </div>

        <div class="customer-info">
            <div>
                <h4>فاتورة إلى:</h4>
                <p>{{ order.customer_name }}</p>
                <p>{{ order.customer_phone }}</p>
                <p>{{ order.destination_city }}</p>
            </div>
            <div>
                <h4>معلومات الدفع:</h4>
                <p><strong>حالة الدفع:</strong> {{ order.payment_status }}</p>
                <p><strong>حالة الطلب:</strong> {{ order.order_status }}</p>
            </div>
        </div>

        <table class="items-table">
            <thead>
                <tr>
                    <th>وصف المنتج</th>
                    <th style="text-align:center;">الكمية</th>
                    <th style="text-align:left;">السعر</th>
                </tr>
            </thead>
            <tbody>
                {% for product in order.products %}
                <tr>
                    <td>{{ product.description }}</td>
                    <td style="text-align:center;">1</td>
                    <td style="text-align:left;">{{ "%.2f"|format(product.price) }} ج.س</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="totals">
            <table>
                <tr>
                    <td>مجموع المنتجات:</td>
                    <td style="text-align:left;">{{ "%.2f"|format(order.products_cost) }} ج.س</td>
                </tr>
                <tr>
                    <td>تكلفة الشحن:</td>
                    <td style="text-align:left;">{{ "%.2f"|format(order.shipping_cost) }} ج.س</td>
                </tr>
                <tr class="total-row">
                    <td>الإجمالي:</td>
                    <td style="text-align:left;">{{ "%.2f"|format(order.total_cost) }} ج.س</td>
                </tr>
            </table>
        </div>

        <div class="footer">
            <p>شكراً لتعاملكم معنا!</p>
            <p>Marvella Fashion</p>
        </div>
    </div>
</body>
</html>
"""
}

# --- 3. إعدادات التطبيق الرئيسية ---
basedir = os.path.abspath(os.path.dirname(__file__))
DB_NAME = 'app_v7.db'
DB_PATH = os.path.join(basedir, 'instance', DB_NAME)
BACKUP_DIR = os.path.join(basedir, 'backups')
STATIC_DIR = os.path.join(basedir, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)
app.jinja_loader = DictLoader(templates)
app.config['SECRET_KEY'] = 'a-very-secret-key-for-v7.0'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# ... استكمالاً للكود السابق من الإجابة الماضية

app.config['SCHEDULER_API_ENABLED'] = True

os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# --- 4. تهيئة الإضافات (Extensions) ---
db = SQLAlchemy(app)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "الرجاء تسجيل الدخول للوصول إلى هذه الصفحة."
login_manager.login_message_category = "info"

# --- 5. نماذج قاعدة البيانات (Database Models) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    destination_city = db.Column(db.String(100), nullable=False)
    shipping_cost = db.Column(db.Float, nullable=False, default=0.0)
    order_status = db.Column(db.String(50), nullable=False, default='جديد')
    payment_status = db.Column(db.String(50), nullable=False, default='لم يتم الدفع')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='order', lazy=True, cascade="all, delete-orphan")
    
    @property
    def products_cost(self):
        return sum(p.price for p in self.products)
    
    @property
    def total_cost(self):
        return self.products_cost + self.shipping_cost

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# =======================================================================
# | الجزء الثاني: منطق التطبيق والواجهات (Application Logic & Views)     |
# =======================================================================

# --- 6. دوال التحكم (Routes / Views) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    query = Order.query
    search_term = request.args.get('search_term')
    order_status = request.args.get('order_status')
    payment_status = request.args.get('payment_status')

    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                Order.customer_name.ilike(search_pattern),
                Order.customer_phone.ilike(search_pattern),
                Order.id.like(search_pattern)
            )
        )
    if order_status:
        query = query.filter(Order.order_status == order_status)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)

    filtered_orders = query.order_by(Order.created_at.desc()).all()
    return render_template("dashboard.html", orders=filtered_orders)

@app.route('/order/add', methods=['GET', 'POST'])
@login_required
def add_order():
    if request.method == 'POST':
        form = request.form
        new_order = Order(
            customer_name=form['customer_name'],
            customer_phone=form['customer_phone'],
            destination_city=form['destination_city'],
            shipping_cost=float(form['shipping_cost'])
        )
        db.session.add(new_order)
        
        product_descriptions = form.getlist('product_description')
        product_prices = form.getlist('product_price')
        
        for desc, price in zip(product_descriptions, product_prices):
            if desc and price:
                db.session.add(Product(description=desc, price=float(price), order=new_order))
        
        db.session.commit()
        flash('تم إنشاء الطلب بنجاح!', 'success')
        return redirect(url_for('dashboard'))
    return render_template("order_form.html", order=None)

@app.route('/order/edit/<int:order_id>', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    order_to_edit = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        form = request.form
        order_to_edit.customer_name = form['customer_name']
        order_to_edit.customer_phone = form['customer_phone']
        order_to_edit.destination_city = form['destination_city']
        order_to_edit.shipping_cost = float(form['shipping_cost'])
        order_to_edit.order_status = form['order_status']
        order_to_edit.payment_status = form['payment_status']
        
        for product in order_to_edit.products:
            db.session.delete(product)
        
        product_descriptions = form.getlist('product_description')
        product_prices = form.getlist('product_price')
        
        for desc, price in zip(product_descriptions, product_prices):
            if desc and price:
                db.session.add(Product(description=desc, price=float(price), order=order_to_edit))
        
        db.session.commit()
        flash('تم تحديث الطلب بنجاح!', 'success')
        return redirect(url_for('dashboard'))
    return render_template("order_form.html", order=order_to_edit)

@app.route('/order/delete/<int:order_id>')
@login_required
def delete_order(order_id):
    order_to_delete = Order.query.get_or_404(order_id)
    db.session.delete(order_to_delete)
    db.session.commit()
    flash('تم حذف الطلب بنجاح.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/statistics')
@login_required
def statistics():
    paid_orders = Order.query.filter_by(payment_status='تم الدفع').all()
    total_revenue = sum(order.total_cost for order in paid_orders)
    total_orders = Order.query.count()
    completed_orders = Order.query.filter_by(order_status='تم التسليم').count()
    average_order_value = total_revenue / len(paid_orders) if paid_orders else 0
    top_cities_query = db.session.query(
        Order.destination_city, 
        func.count(Order.id).label('city_count')
    ).group_by(Order.destination_city).order_by(func.count(Order.id).desc()).limit(5).all()
    
    stats = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'average_order_value': average_order_value,
        'top_cities': top_cities_query
    }
    return render_template('statistics.html', stats=stats)

@app.route('/invoice/download/<int:order_id>')
@login_required
def download_invoice_pdf(order_id):
    order = Order.query.get_or_404(order_id)
    
    logo_uri = (Path(app.static_folder) / 'logo.png').as_uri()
    cairo_regular_uri = (Path(app.static_folder) / 'Cairo-Regular.ttf').as_uri()
    cairo_bold_uri = (Path(app.static_folder) / 'Cairo-Bold.ttf').as_uri()
    
    rendered_html = render_template(
        'invoice_pdf_template.html', 
        order=order, 
        logo_path=logo_uri,
        cairo_regular_path=cairo_regular_uri,
        cairo_bold_path=cairo_bold_uri
    )
    
    try:
        html = HTML(string=rendered_html)
        pdf_file = html.write_pdf()
        
        customer_name_formatted = order.customer_name.replace(' ', '_')
        invoice_date = order.created_at.strftime('%Y-%m-%d')
        filename = f"فاتورة-{customer_name_formatted}-{invoice_date}.pdf"
        
        response = make_response(pdf_file)
        response.headers['Content-Type'] = 'application/pdf'
        
        encoded_filename = quote(filename)
        response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"
        
        return response
    except Exception as e:
        flash(f'خطأ في إنشاء ملف PDF: {e}', 'danger')
        return redirect(url_for('dashboard'))

# --- دوال إدارة النظام (النسخ الاحتياطي) ---
def perform_backup():
    with app.app_context():
        try:
            if not os.path.exists(DB_PATH):
                print("Warning: Database not found for scheduled backup.")
                return
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            backup_filename = f'auto-backup-{timestamp}.db'
            backup_path = os.path.join(BACKUP_DIR, backup_filename)
            shutil.copy2(DB_PATH, backup_path)
            print(f"Successfully created scheduled backup: {backup_filename}")
        except Exception as e:
            print(f"Error during scheduled backup: {e}")

@app.route('/system')
@login_required
def system_management():
    backup_files = sorted(os.listdir(BACKUP_DIR), reverse=True)
    return render_template('system_management.html', backups=backup_files)

@app.route('/system/backup/create')
@login_required
def create_backup():
    perform_backup()
    flash('تم إنشاء نسخة احتياطية يدوية بنجاح.', 'success')
    return redirect(url_for('system_management'))

@app.route('/system/backup/restore', methods=['POST'])
@login_required
def restore_backup():
    try:
        backup_file = request.form.get('backup_file')
        if not backup_file:
            flash('الرجاء اختيار ملف نسخة احتياطية.', 'warning')
            return redirect(url_for('system_management'))
        backup_path = os.path.join(BACKUP_DIR, backup_file)
        if not os.path.exists(backup_path):
            flash('ملف النسخة الاحتياطية المختار غير موجود.', 'danger')
            return redirect(url_for('system_management'))
        shutil.copy2(backup_path, DB_PATH)
        flash(f'تم استعادة النظام بنجاح من النسخة الاحتياطية: {backup_file}.', 'success')
    except Exception as e:
        flash(f'حدث خطأ أثناء استعادة النسخة الاحتياطية: {e}', 'danger')
    return redirect(url_for('system_management'))

@app.route('/system/backup/download/<filename>')
@login_required
def download_backup(filename):
    try:
        return send_from_directory(directory=BACKUP_DIR, path=filename, as_attachment=True)
    except FileNotFoundError:
        flash("الملف المطلوب غير موجود.", "danger")
        return redirect(url_for('system_management'))

@app.route('/system/backup/upload', methods=['POST'])
@login_required
def upload_backup():
    if 'backup_file' not in request.files:
        flash('لم يتم العثور على جزء الملف في الطلب.', 'danger')
        return redirect(url_for('system_management'))
    
    file = request.files['backup_file']
    
    if file.filename == '':
        flash('لم يتم اختيار أي ملف.', 'warning')
        return redirect(url_for('system_management'))
    
    if file and file.filename.endswith('.db'):
        try:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            new_filename = f"uploaded-backup-{timestamp}-{filename}"
            
            upload_path = os.path.join(BACKUP_DIR, new_filename)
            file.save(upload_path)
            
            shutil.copy2(upload_path, DB_PATH)
            flash(f'تم رفع واستعادة النسخة الاحتياطية "{filename}" بنجاح.', 'success')
        except Exception as e:
            flash(f'حدث خطأ أثناء رفع واستعادة الملف: {e}', 'danger')
    else:
        flash('صيغة الملف غير مسموح بها. الرجاء رفع ملف .db فقط.', 'danger')
        
    return redirect(url_for('system_management'))

# --- 7. نقطة انطلاق التطبيق ---

@scheduler.task('cron', id='scheduled_backup_job', hour=3, minute=0)
def scheduled_backup_job():
    print("Running scheduled backup job...")
    perform_backup()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            print("Creating default admin user...")
            default_admin = User(username='admin')
            default_admin.set_password('admin_password')
            db.session.add(default_admin)
            db.session.commit()
            print("Default admin user created with username 'admin' and password 'admin_password'")
    
    app.run(debug=True, host='0.0.0.0')


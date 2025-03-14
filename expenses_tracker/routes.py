from flask import render_template, url_for, flash, redirect, request, jsonify
from expenses_tracker import app, db, bcrypt
from expenses_tracker.forms import RegistrationForm, LoginForm, UpdateAccountForm, ExpenseForm
from expenses_tracker.models import User, Topic, Category, Income, Expense
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
from datetime import datetime

@app.route("/home")
@app.route("/")
def home():
    return render_template('home.html')

@app.route("/index")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    current_month = datetime.now().strftime('%Y-%m')
    first_day = f"{current_month}-01"

    # Lấy tổng chi tiêu theo danh mục trong tháng hiện tại
    expense_by_category = db.session.query(
        Category.name,
        db.func.sum(Expense.amount).label('total')
    ).join(Expense).filter(
        Expense.user_id == current_user.id,
        db.func.strftime('%Y-%m', Expense.date) == current_month
    ).group_by(Category.name).all()

    # Lấy tổng thu nhập theo danh mục trong tháng hiện tại
    income_by_category = db.session.query(
        Category.name,
        db.func.sum(Income.amount).label('total')
    ).join(Income).filter(
        Income.user_id == current_user.id,
        db.func.strftime('%Y-%m', Income.date) == current_month
    ).group_by(Category.name).all()

    # Tính tổng thu nhập và chi tiêu
    total_expense = sum(float(item.total or 0) for item in expense_by_category)
    total_income = sum(float(item.total or 0) for item in income_by_category)
    total_balance = total_income - total_expense

    # Chuẩn bị dữ liệu cho biểu đồ
    expense_data = {
        'categories': [item.name for item in expense_by_category],
        'amounts': [float(item.total or 0) for item in expense_by_category]
    }

    # Lấy dữ liệu theo tháng cho biểu đồ xu hướng (6 tháng gần nhất)
    monthly_data = db.session.query(
        db.func.strftime('%Y-%m', Expense.date).label('month'),
        db.func.sum(Expense.amount).label('expense_total')
    ).filter(
        Expense.user_id == current_user.id
    ).group_by('month').order_by('month').limit(6).all()

    income_monthly = db.session.query(
        db.func.strftime('%Y-%m', Income.date).label('month'),
        db.func.sum(Income.amount).label('income_total')
    ).filter(
        Income.user_id == current_user.id
    ).group_by('month').order_by('month').limit(6).all()

    # Tạo dictionary để map thu nhập theo tháng
    income_map = {item.month: float(item.income_total or 0) for item in income_monthly}

    monthly_trend = {
        'months': [item.month for item in monthly_data],
        'expenses': [float(item.expense_total or 0) for item in monthly_data],
        'incomes': [income_map.get(item.month, 0) for item in monthly_data]
    }

    # Lấy dữ liệu chi tiêu hàng ngày trong tháng hiện tại
    daily_data = db.session.query(
        db.func.date(Expense.date).label('date'),
        db.func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= first_day
    ).group_by('date').order_by('date').all()

    daily_spending = {
        'dates': [item.date.strftime('%d/%m') if isinstance(item.date, datetime) else item.date for item in daily_data],
        'amounts': [float(item.total or 0) for item in daily_data]
    }

    # Lấy các giao dịch gần đây
    recent_transactions = []
    
    # Lấy chi tiêu gần đây
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).limit(5).all()
    for expense in expenses:
        recent_transactions.append({
            'date': expense.date.strftime('%d/%m/%Y'),
            'category_name': expense.category.name,
            'amount': float(expense.amount),
            'description': expense.description,
            'type': 'expense'
        })
    
    # Lấy thu nhập gần đây
    incomes = Income.query.filter_by(user_id=current_user.id).order_by(Income.date.desc()).limit(5).all()
    for income in incomes:
        recent_transactions.append({
            'date': income.date.strftime('%d/%m/%Y'),
            'category_name': income.category.name,
            'amount': float(income.amount),
            'description': income.description,
            'type': 'income'
        })
    
    # Sắp xếp theo ngày giảm dần và giới hạn 5 giao dịch
    recent_transactions.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y'), reverse=True)
    recent_transactions = recent_transactions[:5]

    return render_template('index.html',
                         title='Trang Chủ',
                         expense_data=expense_data,
                         total_expense=total_expense,
                         total_income=total_income,
                         total_balance=total_balance,
                         recent_transactions=recent_transactions,
                         monthly_trend=monthly_trend,
                         daily_spending=daily_spending)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account has been created! Please log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))  
    form = LoginForm() 
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check username and password', 'danger')      
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Account has been updated', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image)
    return render_template('account.html', title='Account', image_file=image_file, form=form)

@app.route("/DanhMuc", methods=['GET'])
@login_required
def DanhMuc():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Lấy cả expenses và incomes
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).paginate(page=page, per_page=per_page)
    incomes = Income.query.filter_by(user_id=current_user.id).order_by(Income.date.desc()).paginate(page=page, per_page=per_page)
    
    form = ExpenseForm()

    default_topic = 'expense'
    categories = Category.query.filter_by(type=default_topic, user_id=current_user.id).all()
    form.category.choices = [(c.id, c.name) for c in categories] if categories else []
    
    form.date.data = datetime.now().date()
    return render_template('DanhMuc.html', title='Danh Mục', form=form, expenses=expenses, incomes=incomes)

@app.route("/add_expense", methods=['POST'])
@login_required
def add_expense():
    form = ExpenseForm(meta={'csrf': True})
    
    # Lấy topic type từ form
    topic_type = request.form.get('topic')
    
    # Lấy danh sách categories dựa trên topic type
    system_user = User.query.filter_by(username='system').first()
    system_user_id = system_user.id if system_user else None
    
    topic = Topic.query.filter_by(type=topic_type).first()
    if not topic:
        flash("Loại giao dịch không hợp lệ!", "danger")
        return redirect(url_for('DanhMuc'))
        
    categories = Category.query.filter(
        (Category.topic_id == topic.id) & 
        ((Category.user_id == current_user.id) | (Category.user_id == system_user_id))
    ).all()
    
        
    form.category.choices = [(c.id, c.name) for c in categories]
    
    if not form.validate_on_submit():
        flash(f"Dữ liệu nhập không hợp lệ: {form.errors}", "danger")
        return redirect(url_for('DanhMuc'))
    
    # Manual validation for category
    category_id = request.form.get('category')
    if not category_id:
        flash("Vui lòng chọn danh mục!", "danger")
        return redirect(url_for('DanhMuc'))
    
    # Check if the category exists and belongs to either the current user or system user
    category = Category.query.filter(
        (Category.id == category_id) &
        (Category.type == topic_type) &
        ((Category.user_id == current_user.id) | (Category.user_id == system_user_id))
    ).first()
    
    if not category:
        flash("Danh mục không hợp lệ!", "danger")
        return redirect(url_for('DanhMuc'))
    
    # Continue with your existing code...
    if topic_type == 'income':
        entry = Income(
            user_id=current_user.id,
            category_id=category.id,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data
        )
    else:
        entry = Expense(
            user_id=current_user.id,
            category_id=category.id,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data
        )

    db.session.add(entry)
    db.session.commit()
    flash('Thêm thành công!', 'success')
    return redirect(url_for('DanhMuc'))

@app.route("/delete_expenses", methods=['POST'])
@login_required
def delete_expenses():
    expense_ids = request.form.getlist('expense_ids')
    if not expense_ids:
        flash('Không có chi tiêu nào được chọn để xóa.', 'danger')
        return redirect(url_for('DanhMuc'))

    Expense.query.filter(Expense.id.in_(expense_ids), Expense.user_id == current_user.id).delete(synchronize_session=False)
    Income.query.filter(Income.id.in_(expense_ids), Income.user_id == current_user.id).delete(synchronize_session=False)
    db.session.commit()

    flash(f'Đã xóa thành công {len(expense_ids)} mục.', 'success')
    return redirect(url_for('DanhMuc'))


@app.route("/get_categories/<topic_type>")
@login_required
def get_categories(topic_type):
    # Get topic based on type
    topic = Topic.query.filter_by(type=topic_type).first()
    
    if not topic:
        return jsonify({'categories': []})

    # Get system user
    system_user = User.query.filter_by(username='system').first()
    system_user_id = system_user.id if system_user else None
    
    # Get categories for both current user and system user
    categories = Category.query.filter(
        (Category.topic_id == topic.id) & 
        ((Category.user_id == current_user.id) | (Category.user_id == system_user_id))
    ).all()
    
    # Format categories for JSON response
    categories_data = [{'id': cat.id, 'name': cat.name} for cat in categories]
    
    return jsonify({'categories': categories_data})
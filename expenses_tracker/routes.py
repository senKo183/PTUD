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
    return render_template('index.html')

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
    page = request.args.get('page', 1, type=int)  # Lấy số trang từ URL, mặc định là trang 1
    per_page = 10  # Số dòng mỗi trang
    
    # Lấy danh sách chi tiêu của người dùng hiện tại và phân trang
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).paginate(page=page, per_page=per_page)

    form = ExpenseForm()

    # Đảm bảo category có giá trị ban đầu để tránh lỗi
    default_topic = 'expense'
    categories = Category.query.filter_by(type=default_topic, user_id=current_user.id).all()
    form.category.choices = [(c.id, c.name) for c in categories] if categories else [("", "No categories available")]

    # Set ngày mặc định cho form
    form.date.data = datetime.now().date()

    return render_template('DanhMuc.html', title='Danh Mục', form=form, expenses=expenses)




@app.route("/add_expense", methods=['POST'])
@login_required
def add_expense():
    form = ExpenseForm()

    # Ensure form.topic is populated before accessing category
    if not form.topic.data:
        flash("Please select a topic first.", "danger")
        return redirect(url_for('DanhMuc'))
    
    # Get categories based on selected topic
    categories = Category.query.filter_by(type=form.topic.data, user_id=current_user.id).all()
    form.category.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        category = Category.query.get(form.category.data)
        if not category:
            flash("Invalid category selection.", "danger")
            return redirect(url_for('DanhMuc'))

        if form.topic.data == 'income':
            income = Income(
                user_id=current_user.id,
                category_id=form.category.data,
                amount=form.amount.data,
                date=form.date.data,
                description=form.description.data
            )
            db.session.add(income)
            flash('Thu nhập đã được thêm thành công!', 'success')
        else:
            expense = Expense(
                user_id=current_user.id,
                category_id=form.category.data,
                amount=form.amount.data,
                date=form.date.data,
                description=form.description.data
            )
            db.session.add(expense)
            flash('Chi tiêu đã được thêm thành công!', 'success')

        db.session.commit()
        return redirect(url_for('DanhMuc'))

    flash('Đã xảy ra lỗi, vui lòng kiểm tra lại!', 'danger')
    return redirect(url_for('DanhMuc'))


@app.route("/delete_expenses", methods=['POST'])
@login_required
def delete_expenses():
    expense_ids = request.form.getlist('expense_ids')
    
    if not expense_ids:
        flash('Không có chi tiêu nào được chọn để xóa.', 'danger')
        return redirect(url_for('DanhMuc'))
    
    # Count successful deletions
    delete_count = 0
    
    for expense_id in expense_ids:
        # Check if ID is for Income or Expense
        expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
        income = Income.query.filter_by(id=expense_id, user_id=current_user.id).first()
        
        if expense:
            db.session.delete(expense)
            delete_count += 1
        elif income:
            db.session.delete(income)
            delete_count += 1
    
    if delete_count > 0:
        db.session.commit()
        flash(f'Đã xóa thành công {delete_count} mục.', 'success')
    else:
        flash('Không thể xóa các mục đã chọn.', 'danger')
    
    return redirect(url_for('DanhMuc'))

@app.route("/get_categories/<topic_type>")
@login_required
def get_categories(topic_type):
    # Get topic based on type
    topic = Topic.query.filter_by(type=topic_type).first()
    
    if not topic:
        return jsonify({'categories': []})

    # Get categories for the current user only
    categories = Category.query.filter(
        (Category.topic_id == topic.id) & (Category.user_id == current_user.id)
    ).all()
    
    # Format categories for JSON response
    categories_data = [{'id': cat.id, 'name': cat.name} for cat in categories]
    
    return jsonify({'categories': categories_data})

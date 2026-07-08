# flask framework - a python framework for creating lightweight web applications
from flask import *
import os
import pymysql
from sms import send_sms

app = Flask(__name__)
app.secret_key = "qwer1234tyui"

connection = pymysql.connect(host='localhost', user="root", password="", database="Nyati")

# Auto-create the orders table if it doesn't exist yet
with connection.cursor() as setup_cursor:
    setup_cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT,
            product_name VARCHAR(255),
            quantity INT DEFAULT 1,
            price DECIMAL(10,2),
            full_name VARCHAR(255),
            phone VARCHAR(50),
            email VARCHAR(255),
            county VARCHAR(100),
            town VARCHAR(100),
            address VARCHAR(255),
            notes TEXT,
            payment_method VARCHAR(50),
            status VARCHAR(50) DEFAULT 'Pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
connection.commit()
from functools import wraps

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'email' not in session or not session['email']:
            flash('Please log in to place an order.')
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return wrapper

# Hardcoded admin login — change these before going live
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@app.route("/")
def home():
    connection = pymysql.connect(host='localhost', user="root", password="", database="Nyati")

    # SQL queries for each category
    sql_clothes      = "SELECT * FROM products WHERE product_category='clothes'"
    sql_smartphones  = "SELECT * FROM products WHERE product_category='smartphones'"
    sql_detergents   = "SELECT * FROM products WHERE product_category='detergents'"
    sql_bags         = "SELECT * FROM products WHERE product_category='bags'"
    sql_electronics  = "SELECT * FROM products WHERE product_category='electronics'"
    sql_groceries    = "SELECT * FROM products WHERE product_category='groceries'"
    sql_home         = "SELECT * FROM products WHERE product_category='home'"

    # Create cursors
    cur_clothes     = connection.cursor()
    cur_smartphones = connection.cursor()
    cur_detergents  = connection.cursor()
    cur_bags        = connection.cursor()
    cur_electronics = connection.cursor()
    cur_groceries   = connection.cursor()
    cur_home        = connection.cursor()

    # Execute queries
    cur_clothes.execute(sql_clothes)
    cur_smartphones.execute(sql_smartphones)
    cur_detergents.execute(sql_detergents)
    cur_bags.execute(sql_bags)
    cur_electronics.execute(sql_electronics)
    cur_groceries.execute(sql_groceries)
    cur_home.execute(sql_home)

    # Fetch results
    clothes     = cur_clothes.fetchall()
    smartphones = cur_smartphones.fetchall()
    detergents  = cur_detergents.fetchall()
    bags        = cur_bags.fetchall()
    electronics = cur_electronics.fetchall()
    groceries   = cur_groceries.fetchall()
    home_items  = cur_home.fetchall()

    return render_template("home.html",
        myclothes=clothes,
        mysmartphones=smartphones,
        mydetergents=detergents,
        mybags=bags,
        myelectronics=electronics,
        mygroceries=groceries,
        myhome=home_items
    )


@app.route("/single/<product_id>")
def single_item(product_id):
    sql_single_item = 'SELECT * FROM products WHERE product_id=%s'
    cursor_single = connection.cursor()
    cursor_single.execute(sql_single_item, (product_id,))
    single = cursor_single.fetchone()

    if single is None:
        return render_template("single.html", message="No product found")

    # Fetch similar products
    category = single[4]
    sql2 = 'SELECT * FROM products WHERE product_category=%s LIMIT 4'
    cursor2 = connection.cursor()
    cursor2.execute(sql2, (category,))
    similar = cursor2.fetchall()

    return render_template("single.html", single_item=single, similar_products=similar)


@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username         = request.form['username']
        email            = request.form['email']
        phone            = request.form['phone']
        password         = request.form['password']
        confirm_password = request.form['confirm_password']

        if " " in username:
            return render_template("signup.html", error="Username must be one word")
        elif "@" not in email:
            return render_template("signup.html", error="Email must contain @")
        elif not phone.startswith("+254"):
            return render_template("signup.html", error="Phone must start with +254")
        elif len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters")
        elif password != confirm_password:
            return render_template("signup.html", error="Passwords do not match")
        else:
            sql = "INSERT INTO users(username, email, phone, password) VALUES(%s, %s, %s, %s)"
            cursor = connection.cursor()
            cursor.execute(sql, (username, email, phone, password))
            connection.commit()
            return render_template("signup.html", success="Registration successful")
    else:
        return render_template("signup.html")


@app.route("/signin", methods=['POST', 'GET'])
def signin():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        sql = 'SELECT * FROM users WHERE email=%s AND password=%s'
        cursor = connection.cursor()
        cursor.execute(sql, (email, password))
        user = cursor.fetchone()

        if user is None:
            return render_template("signin.html", error="Invalid login. Please try again.")
        else:
            session['email'] = email
            return redirect("/")
    else:
        return render_template("signin.html")


@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/')


@app.route('/checkout/<product_id>')
@login_required
def checkout(product_id):
    sql = 'SELECT * FROM products WHERE product_id=%s'
    cursor = connection.cursor()
    cursor.execute(sql, (product_id,))
    single = cursor.fetchone()
    return render_template('checkout.html', single_item=single)


@app.route('/add_to_cart/<product_id>')
@login_required
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    cart = session['cart']
    if product_id not in cart:
        cart.append(product_id)
    session['cart'] = cart
    return redirect('/cart')


@app.route('/cart')
def cart():
    cart_ids   = session.get('cart', [])
    cart_items = []
    cart_total = 0
    for pid in cart_ids:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM products WHERE product_id=%s', (pid,))
        item = cursor.fetchone()
        if item:
            cart_items.append(item)
            cart_total += item[3]
    return render_template('cart.html', cart_items=cart_items, cart_total=cart_total)


@app.route('/remove_from_cart/<product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    if product_id in cart:
        cart.remove(product_id)
    session['cart'] = cart
    return redirect('/cart')


@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    product_id = request.form.get('product_id')

    product_name = None
    price = 0
    if product_id:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM products WHERE product_id=%s', (product_id,))
        product = cursor.fetchone()
        if product:
            product_name = product[1]
            price = product[3]

    sql = """INSERT INTO orders
        (product_id, product_name, quantity, price, full_name, phone, email,
         county, town, address, notes, payment_method, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')"""
    cursor = connection.cursor()
    cursor.execute(sql, (
        product_id,
        product_name,
        1,
        price,
        request.form.get('full_name'),
        request.form.get('phone'),
        request.form.get('email'),
        request.form.get('county'),
        request.form.get('town'),
        request.form.get('address'),
        request.form.get('notes'),
        request.form.get('payment_method'),
    ))
    connection.commit()

    customer_phone = request.form.get('phone')
    if customer_phone:
        message = (
            f"Hi {request.form.get('full_name') or 'there'}, your order for "
            f"{product_name or 'your item'} (KES {price}) has been received and is being processed. "
            f"Thank you for shopping with Soko Garden!"
        )
        try:
            send_sms(customer_phone, message)
        except Exception as sms_error:
            print("SMS sending failed:", sms_error)

    session.pop('cart', None)  # clear cart after order
    return render_template('confirmation.html')


@app.route('/blog')
def blog():
    return render_template('blog.html')
@app.route('/about')
def about():
    return render_template('about.html')


def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/admin/login')
        return func(*args, **kwargs)
    return wrapper


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect('/admin')
        return render_template('admin_login.html', error="Invalid admin credentials")
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect('/admin/login')


@app.route('/admin')
@admin_required
def admin_dashboard():
    status_filter = request.args.get('status', 'All')
    search = request.args.get('search', '').strip()

    sql = "SELECT * FROM orders WHERE 1=1"
    params = []
    if status_filter != 'All':
        sql += " AND status=%s"
        params.append(status_filter)
    if search:
        sql += " AND (full_name LIKE %s OR phone LIKE %s OR product_name LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])
    sql += " ORDER BY created_at DESC"

    cursor = connection.cursor()
    cursor.execute(sql, params)
    orders = cursor.fetchall()

    summary_cursor = connection.cursor()
    summary_cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    summary = dict(summary_cursor.fetchall())

    return render_template('admin_orders.html', orders=orders, summary=summary,
                            status_filter=status_filter, search=search)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    new_status = request.form.get('status')
    cursor = connection.cursor()
    cursor.execute("UPDATE orders SET status=%s WHERE order_id=%s", (new_status, order_id))
    connection.commit()
    return redirect(url_for('admin_dashboard'))


app.run(debug=True)

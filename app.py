from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "smartgrocerysecret"

# MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="nehababuraj@2006",
    database="smart_grocery"
)

cursor = db.cursor(dictionary=True)

# -----------------------------------
# HOME PAGE
# -----------------------------------
@app.route('/')
def home():

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    return render_template(
        'index.html',
        products=products
    )


# -----------------------------------
# SEARCH PRODUCT
# -----------------------------------
@app.route('/search')
def search():

    keyword = request.args.get('keyword')

    cursor.execute(
        "SELECT * FROM products WHERE product_name LIKE %s",
        ('%' + keyword + '%',)
    )

    products = cursor.fetchall()

    message = None

    if len(products) == 0:
        message = "Product not available"

    return render_template(
        'index.html',
        products=products,
        message=message
    )


# -----------------------------------
# REGISTER
# -----------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        sql = """
        INSERT INTO users(name,email,password)
        VALUES(%s,%s,%s)
        """

        cursor.execute(sql, (name, email, password))
        db.commit()

        flash("Registration Successful!")

        return redirect('/login')

    return render_template('register.html')


# -----------------------------------
# LOGIN
# -----------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cursor.execute(
            """
            SELECT * FROM users
            WHERE email=%s AND password=%s
            """,
            (email, password)
        )

        user = cursor.fetchone()

        if user:

            session['user_id'] = user['user_id']
            session['name'] = user['name']

            flash("Login Successful")

            return redirect('/')

        flash("Invalid Email or Password")

    return render_template('login.html')


# -----------------------------------
# LOGOUT
# -----------------------------------
@app.route('/logout')
def logout():

    session.clear()

    flash("Logged Out Successfully")

    return redirect('/')


# -----------------------------------
# ADD TO CART
# -----------------------------------
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute(
        """
        SELECT * FROM cart
        WHERE user_id=%s AND product_id=%s
        """,
        (user_id, product_id)
    )

    item = cursor.fetchone()

    if item:

        cursor.execute(
            """
            UPDATE cart
            SET quantity = quantity + 1
            WHERE cart_id=%s
            """,
            (item['cart_id'],)
        )

    else:

        cursor.execute(
            """
            INSERT INTO cart(user_id, product_id, quantity)
            VALUES(%s, %s, 1)
            """,
            (user_id, product_id)
        )

    db.commit()

    return redirect('/')


# -----------------------------------
# VIEW CART
# -----------------------------------
@app.route('/cart')
def cart():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute(
        """
        SELECT
            cart.cart_id,
            cart.quantity,
            products.product_name,
            products.price
        FROM cart
        JOIN products
        ON cart.product_id = products.product_id
        WHERE cart.user_id=%s
        """,
        (user_id,)
    )

    cart_items = cursor.fetchall()

    total = 0

    for item in cart_items:
        total += item['price'] * item['quantity']

    return render_template(
        'cart.html',
        cart_items=cart_items,
        total=total
    )


# -----------------------------------
# REMOVE CART ITEM
# -----------------------------------
@app.route('/remove_cart/<int:cart_id>')
def remove_cart(cart_id):

    cursor.execute(
        "DELETE FROM cart WHERE cart_id=%s",
        (cart_id,)
    )

    db.commit()

    return redirect('/cart')

@app.route('/increase_quantity/<int:cart_id>')
def increase_quantity(cart_id):

    cursor.execute(
        """
        UPDATE cart
        SET quantity = quantity + 1
        WHERE cart_id=%s
        """,
        (cart_id,)
    )

    db.commit()

    return redirect('/cart')


@app.route('/decrease_quantity/<int:cart_id>')
def decrease_quantity(cart_id):

    cursor.execute(
        "SELECT quantity FROM cart WHERE cart_id=%s",
        (cart_id,)
    )

    item = cursor.fetchone()

    if item:

        if item['quantity'] > 1:

            cursor.execute(
                """
                UPDATE cart
                SET quantity = quantity - 1
                WHERE cart_id=%s
                """,
                (cart_id,)
            )

        else:

            cursor.execute(
                "DELETE FROM cart WHERE cart_id=%s",
                (cart_id,)
            )

        db.commit()

    return redirect('/cart')
@app.route('/checkout')
def checkout():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute("""
        SELECT cart.product_id,
               cart.quantity,
               products.price
        FROM cart
        JOIN products
        ON cart.product_id = products.product_id
        WHERE cart.user_id=%s
    """, (user_id,))

    items = cursor.fetchall()

    if not items:
        return redirect('/cart')

    total = 0

    for item in items:
        total += item['price'] * item['quantity']

    cursor.execute(
        """
        INSERT INTO orders(user_id,total_amount)
        VALUES(%s,%s)
        """,
        (user_id, total)
    )

    db.commit()

    order_id = cursor.lastrowid

    for item in items:

        cursor.execute(
            """
            INSERT INTO order_items
            (order_id,product_id,quantity,price)
            VALUES(%s,%s,%s,%s)
            """,
            (
                order_id,
                item['product_id'],
                item['quantity'],
                item['price']
            )
        )

    db.commit()

    cursor.execute(
        "DELETE FROM cart WHERE user_id=%s",
        (user_id,)
    )

    db.commit()

    return render_template(
    'order_success.html',
    order_id=order_id,
    total=total
)
    
@app.route('/orders')
def orders():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id=%s
        ORDER BY order_id DESC
        """,
        (user_id,)
    )

    orders = cursor.fetchall()

    return render_template(
        'orders.html',
        orders=orders
    )
# -----------------------------------
# ADMIN LOGIN
# -----------------------------------

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            """
            SELECT * FROM admin
            WHERE username=%s AND password=%s
            """,
            (username, password)
        )

        admin = cursor.fetchone()

        if admin:

            session['admin_id'] = admin['admin_id']

            return redirect('/admin_dashboard')

        flash("Invalid Admin Credentials")

    return render_template('admin_login.html')


# -----------------------------------
# ADMIN DASHBOARD
# -----------------------------------

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin_id' not in session:
        return redirect('/admin_login')

    cursor.execute("SELECT * FROM products")

    products = cursor.fetchall()

    return render_template(
        'admin_dashboard.html',
        products=products
    )


# -----------------------------------
# ADD PRODUCT
# -----------------------------------

@app.route('/add_product', methods=['POST'])
def add_product():

    if 'admin_id' not in session:
        return redirect('/admin_login')

    product_name = request.form['product_name']
    category = request.form['category']
    price = request.form['price']
    stock = request.form['stock']
    description = request.form['description']

    cursor.execute(
        """
        INSERT INTO products
        (product_name, category, price, stock, description)
        VALUES(%s, %s, %s, %s, %s)
        """,
        (
            product_name,
            category,
            price,
            stock,
            description
        )
    )

    db.commit()

    return redirect('/admin_dashboard')


# -----------------------------------
# DELETE PRODUCT
# -----------------------------------

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):

    if 'admin_id' not in session:
        return redirect('/admin_login')

    cursor.execute(
        "DELETE FROM products WHERE product_id=%s",
        (product_id,)
    )

    db.commit()

    return redirect('/admin_dashboard')


# -----------------------------------
# ADMIN LOGOUT
# -----------------------------------

@app.route('/admin_logout')
def admin_logout():

    session.pop('admin_id', None)

    return redirect('/admin_login')

@app.route('/admin_orders')
def admin_orders():

    if 'admin_id' not in session:
        return redirect('/admin_login')

    cursor.execute("""
        SELECT orders.*,
               users.name
        FROM orders
        JOIN users
        ON orders.user_id = users.user_id
        ORDER BY order_id DESC
    """)

    orders = cursor.fetchall()

    return render_template(
        'admin_orders.html',
        orders=orders
    )
@app.route('/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):

    if 'admin_id' not in session:
        return redirect('/admin_login')

    status = request.form['status']

    cursor.execute(
        """
        UPDATE orders
        SET status=%s
        WHERE order_id=%s
        """,
        (status, order_id)
    )

    db.commit()

    return redirect('/admin_orders')

    
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):

    if 'admin_id' not in session:
        return redirect('/admin_login')

    if request.method == 'POST':

        product_name = request.form['product_name']
        category = request.form['category']
        price = request.form['price']
        stock = request.form['stock']
        description = request.form['description']

        cursor.execute("""
            UPDATE products
            SET product_name=%s,
                category=%s,
                price=%s,
                stock=%s,
                description=%s
            WHERE product_id=%s
        """,
        (
            product_name,
            category,
            price,
            stock,
            description,
            product_id
        ))

        db.commit()

        return redirect('/admin_dashboard')

    cursor.execute(
        "SELECT * FROM products WHERE product_id=%s",
        (product_id,)
    )

    product = cursor.fetchone()

    return render_template(
        'edit_product.html',
        product=product
    )
# -----------------------------------
# RUN APP
# -----------------------------------

if __name__ == "__main__":
    app.run(debug=True)
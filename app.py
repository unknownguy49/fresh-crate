from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON

app = Flask(__name__)
app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

class Delivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    phone = db.Column(db.String(15), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=False)
    cart_details = db.Column(JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationship to the Delivery table
    delivery = db.relationship('Delivery', backref=db.backref('orders', lazy=True))

# Initialize the database
@app.before_request
def setup():
    db.create_all()
    if not Product.query.first():
        products = [
            Product(name="Tomatoes", price=20.0),
            Product(name="Potatoes", price=10.0),
            Product(name="Onions", price=15.0),
            Product(name="Carrots", price=25.0),
        ]
        db.session.add_all(products)
        db.session.commit()

# Routes
@app.route('/')
def signin():
    return render_template('signin.html')

@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/index')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = Product.query.get(product_id)
    if 'cart' not in session:
        session['cart'] = []
    cart = session['cart']
    cart.append({'id': product.id, 'name': product.name, 'price': product.price})
    session['cart'] = cart
    flash(f"{product.name} added to cart!", "success")
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    return render_template('cart.html', cart=session.get('cart', []))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    session['cart'] = [item for item in cart if item['id'] != product_id]
    flash("Item removed from cart!", "success")
    return redirect(url_for('cart'))

@app.route('/delivery', methods=['GET', 'POST'])
def delivery():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']

        # Get cart items from the session
        cart_items = session.get('cart', [])

        # Calculate the total cost of the cart
        total_cost = sum(item['price'] for item in cart_items)

        # Define shipping charges (you can change this logic)
        shipping_charge = 10.0  # Static shipping charge, or calculate based on cart value or location

        # Calculate the total order amount (items + shipping)
        total_order_amount = total_cost + shipping_charge

        # Save delivery details to the database
        new_delivery = Delivery(name=name, address=address, phone=phone)
        db.session.add(new_delivery)
        db.session.commit()

        # Create an order entry for the newly created delivery
        new_order = Order(
            delivery_id=new_delivery.id,
            cart_details=cart_items
        )
        db.session.add(new_order)
        db.session.commit()

        flash(f"Order placed successfully! Total amount: ₹{total_order_amount}", "success")
        session.pop('cart', None)  # Clear the cart
        return redirect(url_for('home'))

    # Calculate the total cost and shipping charges for displaying on the delivery page
    cart_items = session.get('cart', [])
    total_cost = sum(item['price'] for item in cart_items)
    shipping_charge = 10.0  # Shipping charge
    total_order_amount = total_cost + shipping_charge

    return render_template('delivery.html', cart_items=cart_items, total_cost=total_cost, shipping_charge=shipping_charge, total_order_amount=total_order_amount)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'cart' not in session or not session['cart']:
        flash("Your cart is empty!", "error")
        return redirect(url_for('cart'))

    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone']
    
    # Convert cart items to a string for storage
    cart_items = session['cart']
    cart_items_str = ', '.join([f"{item['name']} (x{item.get('quantity', 1)})" for item in cart_items])

    # Save the order to the database
    new_delivery = Delivery(name=name, address=address, phone=phone)
    db.session.add(new_delivery)
    db.session.commit()

    new_order = Order(
        delivery_id=new_delivery.id,
        cart_details=cart_items
    )
    db.session.add(new_order)
    db.session.commit()

    # Clear the cart after order placement
    session.pop('cart', None)

    flash("Order placed successfully!", "success")
    return redirect(url_for('index'))

@app.route('/owner_orders')
def owner_orders():
    # Fetch all orders from the database, ordered by most recent
    orders = Order.query.order_by(Order.created_at.desc()).all()  # Fetching orders in reverse order (most recent first)
    return render_template('owner_orders.html', orders=orders)

@app.route('/order/<int:order_id>')
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    delivery = Delivery.query.get_or_404(order.delivery_id)
    return render_template('order_details.html', order=order, delivery=delivery)

if __name__ == '__main__':
    app.run(debug=True)

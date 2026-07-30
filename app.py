from flask import Flask, render_template, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
ab
app = Flask(__name__, static_folder='static')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

PAYSTACK_SECRET_KEY = "sk_test_63f3504a3964f9c62bc5e8ac1535a92daf562cfc"

from flask_migrate import Migrate


db = SQLAlchemy(app)
app.secret_key = "your_secret_key"
bcrypt = Bcrypt(app)

migrate = Migrate(app, db)


from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'   # or your mail server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

import os
from werkzeug.utils import secure_filename

# Configure upload folder
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    usertype = db.Column(db.String(20), nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)
    item_title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="Pending") # Pending, In Progress, Completed

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)

    product = db.relationship('Product', backref=db.backref('images', lazy=True))

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)

class ServiceImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)

    service = db.relationship('Service', backref=db.backref('images', lazy=True))


with app.app_context():
    db.create_all()

@app.route("/submit", methods=["POST"])
def submit():
    username = request.form["username"]
    return redirect(url_for("login"))

# --- Sign-up route ---
@app.route("/", methods=["GET", "POST"])
def signup():
    error_message = None
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        usertype = request.form["usertype"]

        # Check if passwords match
        if password != confirm_password:
            error_message = "Passwords do not match!"
            return render_template("index.html", error=error_message)

        # Hash password only after validation
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        new_user = User(username=username, email=email, password=hashed_password, usertype=usertype)
        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            error_message = f"Error: {e}"
            return render_template("index.html", error=error_message)

        return redirect(url_for("login"))
    return render_template("index.html")

# --- Login route ---
@app.route("/login", methods=["GET", "POST"])
def login():
    error_message = None
    message_type = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session["username"] = user.username
            session["usertype"] = user.usertype

            if user.usertype == "Vendor":
                 return redirect(url_for("vendor_homepage"))
            else:
                return redirect(url_for("homepage"))
        else:
            error_message = "Wrong email or password!"
            message_type = "error"
    return render_template("login.html", error=error_message, message_type=message_type)

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if user:
            token = serializer.dumps(email, salt="password-reset-salt")
            reset_url = url_for("reset_with_token", token=token, _external=True)
            msg = Message("Password Reset Request",
                          sender="your_email@gmail.com",
                          recipients=[email])
            msg.body = f"Click the link to reset your password: {reset_url}"
            mail.send(msg)
            return "Password reset email sent!"
        else:
            return "Email not found."
    return render_template("forgot_password.html")

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_with_token(token):
    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=3600)  # 1 hour expiry
    except Exception:
        return "The reset link is invalid or has expired."

    if request.method == "POST":
        new_password = request.form.get("password")
        hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
        user = User.query.filter_by(email=email).first()
        user.password = hashed_password
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)


# --- Home route ---
from sqlalchemy import func

@app.route("/homepage")
def homepage():
    if "username" not in session:
        return redirect(url_for("login"))

    # Top 3 vendors by bookings (return Service objects)
    top_vendors = (
        db.session.query(Service)
        .outerjoin(
            Booking,
            db.and_(Booking.item_title == Service.title, Booking.item_type == "service")
        )
        .group_by(Service.id)
        .order_by(func.count(Booking.id).desc())
        .limit(3)
        .all()
    )

    # Top 3 products by images (return Product objects)
    top_products = (
        db.session.query(Product)
        .outerjoin(ProductImage)
        .group_by(Product.id)
        .order_by(func.count(ProductImage.id).desc())
        .limit(3)
        .all()
    )

    return render_template(
        "homepage.html",
        username=session["username"],
        top_vendors=top_vendors,
        top_products=top_products
    )


@app.route("/aboutus")
def aboutus():
        return render_template("aboutus.html")

@app.route("/vendors")
def vendors():
        all_products = Product.query.all()
        all_services = Service.query.all()
        return render_template("vendors.html", products=all_products, services=all_services)

@app.route("/goods")
def goods():
    all_products = Product.query.all()
    return render_template("goods.html", products=all_products)

@app.route("/services")
def services():
    all_services = Service.query.all()
    return render_template("services.html", services=all_services)

@app.route('/bookings')
def bookings():
    all_bookings = Booking.query.all()
    return render_template('bookings.html', bookings=all_bookings)

@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        item_type = request.form.get('item_type')  # "service" or "product"
        item_title = request.form.get('title')
        date = request.form.get('date')
        payment_method = request.form.get('payment_method')

        # Decide whether to query Service or Product
        if item_type == "service":
            item_obj = Service.query.filter_by(title=item_title).first()
        else:
            item_obj = Product.query.filter_by(title=item_title).first()

        price = item_obj.price if item_obj else 0

        if price <= 0:
            return "Invalid price. Please contact support."

        # Initialize Paystack payment
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "email": email,
            "amount": int(price * 100),  # pesewas
            "callback_url": url_for("payment_callback", _external=True)
        }

        response = requests.post("https://api.paystack.co/transaction/initialize",
                                 json=data, headers=headers)
        res_data = response.json()

        if res_data.get("status"):
            session["pending_booking"] = {
                "name": name,
                "email": email,
                "item_type": item_type,
                "title": item_title,
                "date": date,
                "payment_method": payment_method
            }
            return redirect(res_data["data"]["authorization_url"])
        else:
            return f"Payment initialization failed: {res_data}"

    item_type = request.args.get('item_type')
    title = request.args.get('title')
    return render_template('book.html', item_type=item_type, title=title)


import requests

@app.route("/payment_callback")
def payment_callback():
    reference = request.args.get("reference")

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    response = requests.get(verify_url, headers=headers)
    res_data = response.json()

    if res_data.get("status") and res_data["data"]["status"] == "success":
        booking_data = session.pop("pending_booking", None)
        if booking_data:
            new_booking = Booking(
                customer_name=booking_data["name"],
                email=booking_data["email"],
                item_type=booking_data["item_type"],
                item_title=booking_data["title"],
                date=booking_data["date"],
                payment_method=booking_data["payment_method"],
                status="Completed"
            )
            db.session.add(new_booking)
            db.session.commit()
        return redirect(url_for("bookings"))
    else:
        return "Payment failed. Please try again."

@app.route("/vendor_homepage")
def vendor_homepage():
    if "username" in session and session.get("usertype") == "Vendor":
        return render_template("vendor_homepage.html", username=session["username"])
    return redirect(url_for("login"))

@app.route("/vendor_bookings")
def vendor_bookings():
    if "username" in session and session.get("usertype") == "Vendor":
        all_bookings = Booking.query.all()
        return render_template("vendor_bookings.html", bookings=all_bookings)
    return redirect(url_for("login"))

@app.route("/vendor_add_product", methods=["GET", "POST"])
def vendor_add_product():
    if "username" in session and session.get("usertype") == "Vendor":
        if request.method == "POST":
            title = request.form["title"]
            description = request.form["description"]
            price = request.form["price"]
            images = request.files.getlist("images")  # <-- multiple files

            new_product = Product(
                vendor_name=session["username"],
                title=title,
                description=description,
                price=float(price)
            )
            db.session.add(new_product)
            db.session.commit()

            # Save each image
            for image in images:
                if image.filename:
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    product_image = ProductImage(product_id=new_product.id, filename=filename)
                    db.session.add(product_image)

            db.session.commit()

        vendor_products = Product.query.filter_by(vendor_name=session["username"]).all()
        return render_template("vendor_add_product.html", products=vendor_products)
    return redirect(url_for("login"))

@app.route("/vendor_add_service", methods=["GET", "POST"])
def vendor_add_service():
    if "username" in session and session.get("usertype") == "Vendor":
        if request.method == "POST":
            title = request.form["title"]
            description = request.form["description"]
            price = request.form["price"]
            images = request.files.getlist("images")  # <-- multiple files

            new_service = Service(
                vendor_name=session["username"],
                title=title,
                description=description,
                price=float(price)
            )
            db.session.add(new_service)
            db.session.commit()

            # Save each image
            for image in images:
                if image.filename:
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    service_image = ServiceImage(service_id=new_service.id, filename=filename)
                    db.session.add(service_image)

            db.session.commit()

        vendor_services = Service.query.filter_by(vendor_name=session["username"]).all()
        return render_template("vendor_add_service.html", services=vendor_services)
    return redirect(url_for("login"))

@app.route("/vendor_edit_product/<int:product_id>", methods=["GET", "POST"])
def vendor_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if "username" in session and session.get("usertype") == "Vendor":
        if request.method == "POST":
            product.title = request.form["title"]
            product.description = request.form["description"]
            product.price = float(request.form["price"])
            db.session.commit()
            return redirect(url_for("vendor_homepage"))
        return render_template("vendor_edit_product.html", product=product)
    return redirect(url_for("login"))

@app.route("/vendor_delete_product/<int:product_id>", methods=["POST"])
def vendor_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if "username" in session and session.get("usertype") == "Vendor":
        db.session.delete(product)
        db.session.commit()
        return redirect(url_for("vendor_homepage"))
    return redirect(url_for("login"))

@app.route("/vendor_edit_service/<int:service_id>", methods=["GET", "POST"])
def vendor_edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    if "username" in session and session.get("usertype") == "Vendor":
        if request.method == "POST":
            service.title = request.form["title"]
            service.description = request.form["description"]
            service.price = float(request.form["price"])
            db.session.commit()
            return redirect(url_for("vendor_homepage"))
        return render_template("vendor_edit_service.html", service=service)
    return redirect(url_for("login"))

@app.route("/vendor_delete_service/<int:service_id>", methods=["POST"])
def vendor_delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    if "username" in session and session.get("usertype") == "Vendor":
        db.session.delete(service)
        db.session.commit()
        return redirect(url_for("vendor_homepage"))
    return redirect(url_for("login"))

@app.route("/vendor_update_booking_status/<int:booking_id>", methods=["POST"])
def vendor_update_booking_status(booking_id):
    if "username" in session and session.get("usertype") == "Vendor":
        booking = Booking.query.get_or_404(booking_id)
        new_status = request.form.get("status")
        booking.status = new_status
        db.session.commit()
        return redirect(url_for("vendor_bookings"))
    return redirect(url_for("login"))

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()

    if request.method == "POST":
        # Update only if new values are provided
        if request.form.get("username"):
            user.username = request.form["username"]
        if request.form.get("fname"):
            user.fname = request.form["fname"]
        if request.form.get("mnane"):
            user.mnane = request.form["mnane"]
        if request.form.get("lname"):
            user.lname = request.form["lname"]
        if request.form.get("dob"):
            user.dob = request.form["dob"]
        if request.form.get("email"):
            user.email = request.form["email"]
        if request.form.get("usertype"):
            user.usertype = request.form["usertype"]

        # Update password only if entered
        new_password = request.form.get("password")
        if new_password and new_password.strip() != "":
            user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")

        try:
            db.session.commit()
            return render_template(
                "profile.html", user=user, success="Profile updated successfully!",
                bookings=Booking.query.all(),
                products=Product.query.filter_by(vendor_name=user.username).all(),
                services=Service.query.filter_by(vendor_name=user.username).all()
            )
        except Exception as e:
            return render_template(
                "profile.html", user=user, error=f"Error: {e}",
                bookings=Booking.query.all(),
                products=Product.query.filter_by(vendor_name=user.username).all(),
                services=Service.query.filter_by(vendor_name=user.username).all()
            )

    return render_template(
        "profile.html", user=user,
        bookings=Booking.query.all(),
        products=Product.query.filter_by(vendor_name=user.username).all(),
        services=Service.query.filter_by(vendor_name=user.username).all()
    )

@app.route("/upload_profile_picture", methods=["POST"])
def upload_profile_picture():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    image = request.files.get("profile_image")

    if image and image.filename:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user.image_filename = filename
        db.session.commit()

    return redirect(url_for("profile"))

@app.route("/customer_profile", methods=["GET", "POST"])
def customer_profile():
    if "username" not in session or session.get("usertype") != "Customer":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()

    if request.method == "POST":
        # Update only if new values are provided
        if request.form.get("username"):
            user.username = request.form["username"]
        if request.form.get("fname"):
            user.fname = request.form["fname"]
        if request.form.get("lname"):
            user.lname = request.form["lname"]
        if request.form.get("dob"):
            user.dob = request.form["dob"]
        if request.form.get("email"):
            user.email = request.form["email"]

        # Update password only if entered
        new_password = request.form.get("password")
        if new_password and new_password.strip() != "":
            user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")

        try:
            db.session.commit()
            return render_template(
                "customer_profile.html", user=user, success="Profile updated successfully!",
                bookings=Booking.query.filter_by(email=user.email).all()
            )
        except Exception as e:
            return render_template(
                "customer_profile.html", user=user, error=f"Error: {e}",
                bookings=Booking.query.filter_by(email=user.email).all()
            )

    return render_template(
        "customer_profile.html", user=user,
        bookings=Booking.query.filter_by(email=user.email).all()
    )

@app.route("/upload_customer_picture", methods=["POST"])
def upload_customer_picture():
    if "username" not in session or session.get("usertype") != "Customer":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    image = request.files.get("profile_image")

    if image and image.filename:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user.image_filename = filename
        db.session.commit()

    return redirect(url_for("customer_profile"))


# --- Logout route ---
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)

# F&L (Fashion & Lifestyle) E-Commerce Platform

A production-ready e-commerce backend built with Django, PostgreSQL, and Razorpay. This project demonstrates a robust, scalable architecture with a focus on data integrity, payment reliability, and security.

## 🚀 Features

* **Secure Authentication:** Password hashing on creation, OTP-based email verification, and rate-limiting.
* **Progressive Search:** Intelligent fallback search algorithm (Exact Match → Prefix/Partial → SubCategory → Category → Section) to ensure relevant results.
* **Shopping Cart & Wishlist:** Fully functional cart and wishlist with AJAX updates and strict database constraints (`quantity >= 1`).
* **Reliable Checkout:** Handles critical race conditions during stock reduction using PostgreSQL row-level locks (`select_for_update`).
* **Payments integration:** End-to-end Razorpay integration with asynchronous webhook verification to guarantee transaction integrity even if the user drops connection.

## 🛠️ Tech Stack

* **Framework:** Django 5
* **Database:** PostgreSQL (Neon)
* **Storage:** Cloudinary (for Media/Uploads), WhiteNoise (for Static files)
* **Emails:** Brevo HTTP API (bypasses cloud SMTP firewalls)
* **Payments:** Razorpay API
* **Frontend:** HTML, Vanilla CSS, Bootstrap 5, Vanilla JS

## 📐 Architectural Decisions

* **Atomic Transactions (`transaction.atomic`):** The entire checkout process (order creation, payment generation, stock deduction, cart clearing) is wrapped in a single database transaction. If any step fails (e.g., out of stock), the entire operation rolls back safely.
* **Database-Level Constraints:** Enforced `price >= 0` and `quantity >= 1` using Django `CheckConstraint`. Data integrity is pushed to the database engine level, preventing negative stock or prices regardless of application logic bugs.
* **Brevo HTTP API for Emails:** Cloud providers (like Render or AWS) often throttle or block outbound SMTP ports (587, 25). To ensure 100% reliable OTP delivery, email sending utilizes the Brevo REST API via HTTPS, completely avoiding socket timeout issues.
* **Immediate Password Hashing:** User passwords are encrypted instantly via `make_password` and stored securely even while waiting for OTP verification in the temporary profile table.

## ⚙️ Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/your-username/FNL_dev.git
cd FNL_dev
```

2. **Create a virtual environment and install dependencies**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure Environment Variables**
Create a `.env` file in the root directory (alongside `manage.py`) with the following keys:
```env
SECRET_KEY=your_django_secret_key
DEBUG=True
DATABASE_URL=your_postgresql_url

# Brevo HTTP API for Emails (Generate at app.brevo.com/settings/keys/api)
BREVO_API_KEY=xkeysib-...
DEFAULT_FROM_EMAIL=your_email@domain.com

# Razorpay
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

4. **Run Migrations & Start the Server**
```bash
python manage.py migrate
python manage.py runserver
```

## 🌐 Deployment
This project is configured for seamless deployment on platforms like Render. It uses WhiteNoise to serve static assets efficiently without requiring a separate CDN, while user-uploaded media is offloaded to Cloudinary, making the application horizontally scalable and stateless.

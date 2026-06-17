import os
import json
import bcrypt
import stripe
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, abort)
from dotenv import load_dotenv

import database as db
import engine

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUB_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FREE_LIMIT = int(os.getenv("FREE_ANALYSES_LIMIT", "1"))

db.init_db()


# ── AUTH HELPERS ──

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Inicia sesión para continuar.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def current_user():
    if "user_id" not in session:
        return None
    return db.get_user_by_id(session["user_id"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ── PUBLIC ROUTES ──

@app.route("/")
def index():
    user = current_user()
    return render_template("landing.html", user=user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not email or not password:
            flash("Email y contraseña son obligatorios.", "error")
        elif len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "error")
        elif password != confirm:
            flash("Las contraseñas no coinciden.", "error")
        else:
            user_id = db.create_user(email, hash_password(password))
            if user_id is None:
                flash("Ya existe una cuenta con ese email.", "error")
            else:
                session["user_id"] = user_id
                flash("¡Cuenta creada! Bienvenido a Vibiz.", "success")
                return redirect(url_for("dashboard"))

    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.get_user_by_email(email)

        if user and check_password(password, user["password_hash"]):
            session["user_id"] = user["id"]
            flash("¡Bienvenido de nuevo!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Email o contraseña incorrectos.", "error")

    return render_template("auth.html", mode="login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ── APP ROUTES ──

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    projects = db.get_user_projects(user["id"])
    return render_template("dashboard.html", user=user, projects=projects,
                           free_limit=FREE_LIMIT)


@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    user = current_user()

    if request.method == "GET":
        return render_template("analyze.html", user=user,
                               free_limit=FREE_LIMIT, stripe_pub=STRIPE_PUB_KEY)

    # POST — API call from frontend
    data = request.get_json()
    url = (data or {}).get("url", "").strip()

    if not url:
        return jsonify({"error": "Introduce una URL válida."}), 400

    # Check quota
    is_pro = user["plan"] == "pro"
    if not is_pro and user["analyses_used"] >= FREE_LIMIT:
        return jsonify({
            "error": "Has usado tu análisis gratuito. Suscríbete para análisis ilimitados.",
            "upgrade": True
        }), 402

    if not ANTHROPIC_KEY:
        return jsonify({"error": "API key de Claude no configurada en el servidor."}), 500

    try:
        scraped = engine.scrape_website(url)
    except Exception as e:
        return jsonify({"error": f"No se pudo acceder a la web: {e}"}), 422

    try:
        report = engine.generate_report(ANTHROPIC_KEY, scraped)
    except json.JSONDecodeError:
        return jsonify({"error": "Error procesando la respuesta IA. Inténtalo de nuevo."}), 500
    except Exception as e:
        return jsonify({"error": f"Error de IA: {e}"}), 500

    db.increment_analyses(user["id"])
    title = report.get("dna_negocio", {}).get("nombre") or scraped.get("title") or url
    project_id = db.save_project(user["id"], scraped["url"], title, report)

    return jsonify({"project_id": project_id})


@app.route("/project/<int:project_id>")
@login_required
def project(project_id):
    user = current_user()
    proj = db.get_project(project_id, user["id"])
    if not proj:
        abort(404)
    return render_template("project.html", user=user, project=proj,
                           report=proj["report"])


@app.route("/project/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    user = current_user()
    db.delete_project(project_id, user["id"])
    flash("Proyecto eliminado.", "info")
    return redirect(url_for("dashboard"))


@app.route("/settings")
@login_required
def settings():
    user = current_user()
    return render_template("settings.html", user=user, stripe_pub=STRIPE_PUB_KEY)


# ── STRIPE ──

@app.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    user = current_user()
    if not stripe.api_key or not STRIPE_PRICE_ID:
        flash("Pagos no configurados todavía. Contacta al soporte.", "error")
        return redirect(url_for("settings"))

    try:
        checkout = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            customer_email=user["email"],
            metadata={"user_id": str(user["id"])},
            success_url=url_for("payment_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("settings", _external=True),
        )
        return redirect(checkout.url, code=303)
    except Exception as e:
        flash(f"Error al crear sesión de pago: {e}", "error")
        return redirect(url_for("settings"))


@app.route("/payment/success")
@login_required
def payment_success():
    session_id = request.args.get("session_id")
    if session_id and stripe.api_key:
        try:
            checkout = stripe.checkout.Session.retrieve(session_id)
            user_id = int(checkout.metadata.get("user_id", 0))
            if user_id:
                db.update_user_plan(
                    user_id, "pro",
                    stripe_customer_id=checkout.customer,
                    stripe_subscription_id=checkout.subscription,
                )
        except Exception:
            pass

    flash("¡Suscripción activada! Ya tienes acceso ilimitado.", "success")
    return redirect(url_for("dashboard"))


@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig = request.headers.get("Stripe-Signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        return jsonify(ok=True)

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        abort(400)

    if event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        if customer_id:
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE users SET plan='free' WHERE stripe_customer_id=?",
                    (customer_id,),
                )

    if event["type"] in ("customer.subscription.updated", "invoice.payment_succeeded"):
        sub = event["data"]["object"].get("subscription") or event["data"]["object"].get("id")
        customer_id = event["data"]["object"].get("customer")
        if customer_id:
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE users SET plan='pro' WHERE stripe_customer_id=?",
                    (customer_id,),
                )

    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

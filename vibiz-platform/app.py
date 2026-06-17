import os
import io
import csv
import json
import zipfile
import bcrypt
import stripe
import requests as http_requests
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, abort, send_file, Response)
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

    # Fire webhook if configured (Zapier / Make.com)
    webhook_url = user["webhook_url"] if "webhook_url" in user.keys() else None
    if webhook_url:
        try:
            payload = {
                "project_id": project_id,
                "url": scraped["url"],
                "negocio": report.get("dna_negocio", {}).get("nombre"),
                "google_ad_1": report.get("google_ads", [{}])[0],
                "facebook_ad_1": report.get("facebook_ads", [{}])[0],
                "instagram_post_1": report.get("instagram_posts", [{}])[0],
                "tweet_1": report.get("twitter_posts", [{}])[0].get("texto"),
                "seo_top": report.get("seo_recomendaciones", [{}])[0],
            }
            http_requests.post(webhook_url, json=payload, timeout=5)
        except Exception:
            pass

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


@app.route("/project/<int:project_id>/export")
@login_required
def export_project(project_id):
    user = current_user()
    proj = db.get_project(project_id, user["id"])
    if not proj:
        abort(404)

    r = proj["report"]
    dna = r.get("dna_negocio", {})
    nombre = dna.get("nombre", "negocio")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # Google Ads
        lines = []
        for i, ad in enumerate(r.get("google_ads", []), 1):
            lines += [f"--- VARIANTE {i} ({ad.get('enfoque','')}) ---",
                      f"T1: {ad['titulo_1']} | T2: {ad['titulo_2']} | T3: {ad['titulo_3']}",
                      f"D1: {ad['descripcion_1']}",
                      f"D2: {ad['descripcion_2']}", ""]
        zf.writestr("ads/google_ads.txt", "\n".join(lines))

        # Facebook Ads
        lines = []
        for i, ad in enumerate(r.get("facebook_ads", []), 1):
            lines += [f"--- VARIANTE {i} | Formato: {ad.get('formato_recomendado','')} ---",
                      f"GANCHO: {ad['gancho']}", "", ad["cuerpo"],
                      f"\n👉 {ad['cta_boton']}", ""]
        zf.writestr("ads/facebook_instagram_ads.txt", "\n".join(lines))

        # Instagram posts
        lines = []
        for i, p in enumerate(r.get("instagram_posts", []), 1):
            lines += [f"--- POST {i} · {p.get('tipo','')} ---",
                      p["caption"], "", p["hashtags"],
                      f"\n💡 Visual: {p.get('idea_visual','')}", ""]
        zf.writestr("social/instagram_posts.txt", "\n".join(lines))

        # Twitter
        lines = [f"{i}. {t['texto']}\n" for i, t in enumerate(r.get("twitter_posts", []), 1)]
        zf.writestr("social/twitter_posts.txt", "\n".join(lines))

        # Emails
        lines = []
        for e in r.get("emails", []):
            lines += [f"=== {e['tipo'].upper()} ===",
                      f"ASUNTO: {e['asunto']}",
                      f"PREVIEW: {e['preview_text']}", "",
                      e["cuerpo"], "\n"]
        zf.writestr("email/secuencia_emails.txt", "\n".join(lines))

        # Landing copy
        lp = r.get("landing_page", {})
        lp_text = [
            f"HEADLINE: {lp.get('headline','')}",
            f"SUBHEADLINE: {lp.get('subheadline','')}",
            f"CTA: {lp.get('cta_principal','')}",
            "", "BENEFICIOS:",
            *[f"  {b.get('icono','')} {b['titulo']}: {b['descripcion']}" for b in lp.get("beneficios", [])],
            "", f"PRUEBA SOCIAL: {lp.get('prueba_social','')}",
            "", "FAQ:",
            *[f"  Q: {f['pregunta']}\n  A: {f['respuesta']}" for f in lp.get("faq", [])],
        ]
        zf.writestr("landing/copy_landing_page.txt", "\n".join(lp_text))

        # SEO
        lines = []
        for rec in r.get("seo_recomendaciones", []):
            lines += [f"[{rec['impacto'].upper()}] {rec['titulo']}",
                      f"Problema: {rec['problema']}",
                      f"Solución: {rec['solucion']}",
                      f"Esfuerzo: {rec['esfuerzo']}", ""]
        zf.writestr("seo/recomendaciones_seo.txt", "\n".join(lines))

        # Calendar CSV
        cal_buf = io.StringIO()
        writer = csv.DictWriter(cal_buf, fieldnames=["dia", "red", "tipo", "tema", "gancho"])
        writer.writeheader()
        writer.writerows(r.get("calendario_contenido", []))
        zf.writestr("calendario/calendario_30_dias.csv", cal_buf.getvalue())

        # Business DNA summary
        dna_text = [
            f"NEGOCIO: {dna.get('nombre','')}",
            f"SECTOR: {dna.get('sector','')}",
            f"RESUMEN: {dna.get('resumen','')}",
            f"PÚBLICO: {dna.get('publico_objetivo','')}",
            f"PROPUESTA DE VALOR: {dna.get('propuesta_valor','')}",
            f"TONO: {dna.get('tono_de_voz','')}",
            f"KEYWORDS: {', '.join(dna.get('palabras_clave_marca', []))}",
        ]
        zf.writestr("business_dna.txt", "\n".join(dna_text))

    buf.seek(0)
    filename = f"vibiz-{nombre.lower().replace(' ', '-')}-kit.zip"
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name=filename)


@app.route("/project/<int:project_id>/landing")
@login_required
def download_landing(project_id):
    user = current_user()
    if user["plan"] != "pro":
        flash("La landing page descargable es exclusiva del plan Pro.", "error")
        return redirect(url_for("project", project_id=project_id))

    proj = db.get_project(project_id, user["id"])
    if not proj:
        abort(404)

    if not ANTHROPIC_KEY:
        flash("API key no configurada.", "error")
        return redirect(url_for("project", project_id=project_id))

    try:
        html = engine.generate_landing_html(ANTHROPIC_KEY, proj["report"])
    except Exception as e:
        flash(f"Error generando la landing: {e}", "error")
        return redirect(url_for("project", project_id=project_id))

    dna = proj["report"].get("dna_negocio", {})
    nombre = dna.get("nombre", "negocio").lower().replace(" ", "-")
    return Response(html, mimetype="text/html",
                    headers={"Content-Disposition": f'attachment; filename="landing-{nombre}.html"'})


@app.route("/compare", methods=["GET", "POST"])
@login_required
def compare():
    user = current_user()
    if user["plan"] != "pro":
        flash("El análisis de competencia es exclusivo del plan Pro.", "error")
        return redirect(url_for("settings"))

    if request.method == "GET":
        return render_template("compare.html", user=user)

    data = request.get_json()
    url1 = (data or {}).get("url1", "").strip()
    url2 = (data or {}).get("url2", "").strip()

    if not url1 or not url2:
        return jsonify({"error": "Introduce las dos URLs."}), 400

    if not ANTHROPIC_KEY:
        return jsonify({"error": "API key no configurada."}), 500

    try:
        s1 = engine.scrape_website(url1)
        s2 = engine.scrape_website(url2)
    except Exception as e:
        return jsonify({"error": f"No se pudo acceder a una de las webs: {e}"}), 422

    try:
        result = engine.analyze_competitor(ANTHROPIC_KEY, s1, s2)
    except Exception as e:
        return jsonify({"error": f"Error en el análisis: {e}"}), 500

    result["url1"] = s1["url"]
    result["url2"] = s2["url"]
    return jsonify(result)


@app.route("/settings")
@login_required
def settings():
    user = current_user()
    return render_template("settings.html", user=user, stripe_pub=STRIPE_PUB_KEY)


@app.route("/settings/webhook", methods=["POST"])
@login_required
def save_webhook():
    user = current_user()
    webhook_url = request.form.get("webhook_url", "").strip()
    db.update_webhook(user["id"], webhook_url)
    flash("Webhook guardado correctamente.", "success")
    return redirect(url_for("settings"))


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

import html
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from xml.sax.saxutils import escape as xml_escape

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

# Explicit paths: standard layout next to this file (templates/, static/).
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me-for-production")
app.config["WTF_CSRF_TIME_LIMIT"] = None

# Railway (and most PaaS hosts) terminate HTTPS at a proxy and forward plain
# HTTP to the app, adding X-Forwarded-* headers. Without this, url_for(...,
# _external=True) and request.url_root would render as http:// instead of
# https:// in production, breaking the canonical URL, OG image URL, and
# sitemap that were tuned for SEO.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

csrf = CSRFProtect(app)

BUSINESS_LEGAL_NAME = "JD Home Improvement LLC"
BUSINESS_PUBLIC_NAME = "JD Home Improvement"
CONTACT_EMAIL_PUBLIC = "info@JDHomeImprovementLLC.com"

META_HOME = {
    # Kept near Google's practical SERP display limits (~60 chars for titles,
    # ~155-160 for descriptions) so nothing gets cut off mid-phrase in search results.
    "meta_title": (
        "Home Remodeling & Improvement | Northern VA & MD | JD Home Improvement"
    ),
    "meta_description": (
        "Trusted remodeling and home improvement contractor serving Northern "
        "Virginia and Silver Spring, MD. Kitchens, baths, decks, repairs. "
        "Free estimates."
    ),
    "og_title": (
        "Home Improvement & Remodeling | Northern VA & MD | JD Home Improvement LLC"
    ),
    "og_description": (
        "Trusted remodeling contractors serving Arlington VA, Springfield VA, "
        "Tysons Corner, Burke VA, and Silver Spring MD. Kitchen and bath remodels, "
        "repairs, decks, painting, and exterior improvements; detail-focused and "
        "professional."
    ),
    "twitter_title": (
        "JD Home Improvement | Northern VA & Silver Spring MD"
    ),
    "twitter_description": (
        "Remodeling and home improvement contractor serving Arlington, "
        "Springfield, Tysons Corner, Burke VA, and Silver Spring, MD. "
        "Free estimates."
    ),
}

SCHEMA_DESCRIPTION = (
    f"{BUSINESS_PUBLIC_NAME}, a home improvement and remodeling contractor serving "
    "homeowners in Northern Virginia and Maryland. Services include interior and "
    "exterior remodeling, repairs, decks, painting, carpentry, roofing, flooring, "
    "and exterior improvements, with emphasis on craftsmanship and clear "
    "communication."
)

SERVICE_AREA_LABELS = [
    "Arlington, VA",
    "Springfield, VA",
    "Tysons Corner, VA",
    "Silver Spring, MD",
    "Burke, VA",
]

# Dedicated 1200x630 share image (standard OG/Twitter card ratio) instead of
# reusing the transparent logo, which renders poorly on colored feed backgrounds.
OG_IMAGE_FILENAME = "images/og-share.jpg"
OG_IMAGE_WIDTH = 1200
OG_IMAGE_HEIGHT = 630

FAQ_ITEMS: List[Dict[str, str]] = [
    {
        "q": "Do you offer home remodeling in Arlington, VA?",
        "a": (
            "Yes. We work with homeowners throughout Arlington on kitchen and bath "
            "remodels, interior updates, repairs, and exterior improvements, with "
            "the same attention to detail we bring to every project in Northern Virginia."
        ),
    },
    {
        "q": "What areas around Northern Virginia and Maryland do you serve?",
        "a": (
            "We regularly serve Arlington, Springfield, Tysons Corner, and Burke in "
            "Virginia, and Silver Spring in Maryland, along with nearby communities. "
            "If you are close to these areas, reach out with your project. We are happy "
            "to confirm availability."
        ),
    },
    {
        "q": "Do you provide free estimates in Silver Spring, MD?",
        "a": (
            "We welcome questions about scope and pricing. Contact us through the form "
            "or email and we will outline next steps, including how we approach quotes "
            "and site visits for Silver Spring and Montgomery County projects."
        ),
    },
    {
        "q": "What types of projects do you take on?",
        "a": (
            "Our team handles remodeling, home repairs, decks and outdoor living, "
            "painting and finishing, carpentry and built-ins, roofing repairs and "
            "weatherproofing, flooring, and exterior improvements. That range works well "
            "for local homeowners who want one reliable partner for many phases of work."
        ),
    },
]

TOPIC_LABELS = {
    "general": "General question",
    "quote": "Free quote",
    "remodeling": "Remodeling",
    "repairs": "Repairs & maintenance",
    "painting": "Painting & finishing",
    "other": "Other",
}

MAX_NAME = 120
MAX_PHONE = 40
MAX_MESSAGE = 5000
MIN_MESSAGE = 10

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _local_business_schema(canonical_url: str, og_image_url: str) -> Dict[str, Any]:
    area_served = [{"@type": "AdministrativeArea", "name": label} for label in SERVICE_AREA_LABELS]
    services_offered = [
        "Home remodeling",
        "Kitchen and bathroom remodeling",
        "Home repairs and maintenance",
        "Deck construction and outdoor living",
        "Interior and exterior painting",
        "Carpentry and built-ins",
        "Roofing repairs",
        "Flooring and trim",
        "Exterior improvements",
        "Power washing",
    ]
    return {
        "@type": "HomeAndConstructionBusiness",
        "name": BUSINESS_PUBLIC_NAME,
        "legalName": BUSINESS_LEGAL_NAME,
        "description": SCHEMA_DESCRIPTION,
        "url": canonical_url,
        "image": og_image_url,
        "email": CONTACT_EMAIL_PUBLIC,
        "areaServed": area_served,
        "priceRange": "$$",
        "knowsAbout": services_offered,
    }


def _faq_schema() -> Dict[str, Any]:
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in FAQ_ITEMS
        ],
    }


def _page_vars(endpoint: str) -> dict:
    canonical_url = url_for(endpoint, _external=True)
    og_image_url = url_for("static", filename=OG_IMAGE_FILENAME, _external=True)
    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            _local_business_schema(canonical_url, og_image_url),
            _faq_schema(),
        ],
    }
    return {
        "canonical_url": canonical_url,
        "og_image_url": og_image_url,
        "og_image_width": OG_IMAGE_WIDTH,
        "og_image_height": OG_IMAGE_HEIGHT,
        "og_url": canonical_url,
        "structured_data": structured_data,
        "faq_items": FAQ_ITEMS,
        "service_areas": SERVICE_AREA_LABELS,
    }


def _wants_json_response() -> bool:
    if request.is_json:
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    accept = request.headers.get("Accept") or ""
    return "application/json" in accept


@app.errorhandler(CSRFError)
def handle_csrf_error(_e: CSRFError):
    if _wants_json_response():
        return jsonify(ok=False, error="csrf"), 400
    return redirect(url_for("index") + "?error=csrf#contact", code=303)


def _get_form_data() -> Dict[str, Any]:
    if request.is_json:
        body = request.get_json(silent=True) or {}
        return {
            "name": (body.get("name") or "").strip(),
            "email": (body.get("email") or "").strip(),
            "phone": (body.get("phone") or "").strip(),
            "topic": (body.get("topic") or "").strip(),
            "message": (body.get("message") or "").strip(),
            "company": (body.get("company") or "").strip(),
        }
    return {
        "name": (request.form.get("name") or "").strip(),
        "email": (request.form.get("email") or "").strip(),
        "phone": (request.form.get("phone") or "").strip(),
        "topic": (request.form.get("topic") or "").strip(),
        "message": (request.form.get("message") or "").strip(),
        "company": (request.form.get("company") or "").strip(),
    }


def _validate_contact(data: Dict[str, Any]) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    name = data.get("name") or ""
    email = data.get("email") or ""
    phone = data.get("phone") or ""
    topic = data.get("topic") or ""
    message = data.get("message") or ""

    if not name:
        errors["name"] = "Please enter your name."
    elif len(name) > MAX_NAME:
        errors["name"] = "Name is too long."

    if not email:
        errors["email"] = "Please enter your email."
    elif not EMAIL_RE.match(email):
        errors["email"] = "Please enter a valid email address."
    elif len(email) > 254:
        errors["email"] = "Email is too long."

    if len(phone) > MAX_PHONE:
        errors["phone"] = "Phone number is too long."

    if topic not in TOPIC_LABELS:
        errors["topic"] = "Please choose a topic."

    if not message:
        errors["message"] = "Please enter a message."
    elif len(message) < MIN_MESSAGE:
        errors["message"] = f"Message must be at least {MIN_MESSAGE} characters."
    elif len(message) > MAX_MESSAGE:
        errors["message"] = "Message is too long."

    return errors


def _get_ses_to_addr() -> str:
    # SES_TO_EMAIL is the documented/required variable name; CONTACT_TO_EMAIL is
    # kept as a fallback so any existing local .env from before this change still works.
    return (
        os.environ.get("SES_TO_EMAIL", "").strip()
        or os.environ.get("CONTACT_TO_EMAIL", "").strip()
    )


def _send_via_ses(
    name: str,
    email: str,
    phone: str,
    topic: str,
    message: str,
) -> None:
    region = os.environ.get("AWS_REGION", "us-east-1")
    from_addr = os.environ.get("SES_FROM_EMAIL", "").strip()
    to_addr = _get_ses_to_addr()

    if not from_addr or not to_addr:
        raise RuntimeError("SES_FROM_EMAIL and SES_TO_EMAIL must be set.")

    topic_label = TOPIC_LABELS.get(topic, topic)
    phone_display = phone or "(not provided)"
    submitted_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")

    text_body = (
        "New Website Inquiry\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Phone: {phone_display}\n"
        f"Topic: {topic_label}\n"
        f"Message:\n{message}\n\n"
        f"Submitted at: {submitted_at}\n"
    )

    # Escape every visitor-supplied value before it goes into the HTML body so
    # the message content can never break out of its layout or inject markup.
    esc_name = html.escape(name)
    esc_email = html.escape(email)
    esc_phone = html.escape(phone_display)
    esc_topic = html.escape(topic_label)
    esc_message = html.escape(message).replace("\n", "<br>")
    esc_submitted_at = html.escape(submitted_at)

    html_body = f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#f4f2ee;font-family:Arial,Helvetica,sans-serif;color:#2a2a28;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f2ee;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #e4e0d8;">
            <tr>
              <td style="background:#1f1c17;padding:18px 24px;">
                <span style="color:#f5c542;font-size:16px;font-weight:bold;letter-spacing:0.02em;">New Website Inquiry</span>
              </td>
            </tr>
            <tr>
              <td style="padding:24px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;line-height:1.6;">
                  <tr><td style="padding:6px 0;width:110px;color:#6b6b66;vertical-align:top;">Name:</td><td style="padding:6px 0;">{esc_name}</td></tr>
                  <tr><td style="padding:6px 0;color:#6b6b66;vertical-align:top;">Email:</td><td style="padding:6px 0;">{esc_email}</td></tr>
                  <tr><td style="padding:6px 0;color:#6b6b66;vertical-align:top;">Phone:</td><td style="padding:6px 0;">{esc_phone}</td></tr>
                  <tr><td style="padding:6px 0;color:#6b6b66;vertical-align:top;">Topic:</td><td style="padding:6px 0;">{esc_topic}</td></tr>
                  <tr><td style="padding:12px 0 6px;color:#6b6b66;vertical-align:top;">Message:</td><td style="padding:12px 0 6px;">{esc_message}</td></tr>
                </table>
                <p style="margin:18px 0 0;padding-top:14px;border-top:1px solid #eee;font-size:12px;color:#9a9a94;">Submitted at: {esc_submitted_at}</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    client = boto3.client("ses", region_name=region)
    client.send_email(
        Source=from_addr,
        Destination={"ToAddresses": [to_addr]},
        Message={
            "Subject": {
                "Data": f"[JD Home] Website: {topic_label} | {name}",
                "Charset": "UTF-8",
            },
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        },
        ReplyToAddresses=[email],
    )


@app.route("/")
def index():
    return render_template(
        "index.html",
        **_page_vars("index"),
        **META_HOME,
        contact_sent=request.args.get("sent"),
        contact_error=request.args.get("error"),
    )


@app.post("/contact/submit")
def contact_submit():
    data = _get_form_data()

    # Honeypot: if filled, pretend success (bots)
    if data.get("company"):
        if _wants_json_response():
            return jsonify(ok=True)
        return redirect(url_for("index") + "?sent=1#contact", code=303)

    errors = _validate_contact(data)
    if errors:
        if _wants_json_response():
            return jsonify(ok=False, errors=errors), 400
        return redirect(url_for("index") + "?error=validation#contact", code=303)

    name = data["name"]
    email = data["email"]
    phone = data["phone"]
    topic = data["topic"]
    message = data["message"]

    dry_run_flag = os.environ.get("CONTACT_DRY_RUN", "").strip() in ("1", "true", "yes")
    ses_ready = bool(os.environ.get("SES_FROM_EMAIL", "").strip() and _get_ses_to_addr())
    dry_run = dry_run_flag or not ses_ready

    if dry_run:
        app.logger.info(
            "Contact form (dry run: set SES + CONTACT_DRY_RUN=0 to send): "
            "name=%s email=%s topic=%s",
            name,
            email,
            topic,
        )
    else:
        try:
            _send_via_ses(name, email, phone, topic, message)
        except ClientError as exc:
            app.logger.exception("Amazon SES error: %s", exc)
            if _wants_json_response():
                return jsonify(
                    ok=False,
                    error="send",
                    message="We couldn’t send your message right now. Please try again or email us directly.",
                ), 502
            return redirect(url_for("index") + "?error=send#contact", code=303)
        except Exception as exc:
            app.logger.exception("Contact send error: %s", exc)
            if _wants_json_response():
                return jsonify(
                    ok=False,
                    error="send",
                    message="We couldn’t send your message right now. Please try again or email us directly.",
                ), 502
            return redirect(url_for("index") + "?error=send#contact", code=303)

    if _wants_json_response():
        return jsonify(ok=True)

    return redirect(url_for("index") + "?sent=1#contact", code=303)


@app.route("/about")
def about():
    """Legacy URL: site is single-page; anchor for bookmarks and external links."""
    return redirect(url_for("index", _anchor="about"), code=301)


@app.route("/services")
def services():
    return redirect(url_for("index", _anchor="services"), code=301)


@app.route("/projects")
def projects():
    return redirect(url_for("index", _anchor="projects"), code=301)


@app.route("/contact")
def contact():
    return redirect(url_for("index", _anchor="contact"), code=301)


@app.route("/robots.txt")
def robots_txt():
    base = request.url_root.rstrip("/")
    body = f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n"
    return Response(body, mimetype="text/plain; charset=utf-8")


@app.route("/sitemap.xml")
def sitemap_xml():
    base = request.url_root.rstrip("/")
    loc = xml_escape(base + "/")
    lastmod = datetime.now(timezone.utc).date().isoformat()
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod>"
        "<changefreq>weekly</changefreq><priority>1.0</priority></url>"
        "</urlset>"
    )
    return Response(xml, mimetype="application/xml; charset=utf-8")


if __name__ == "__main__":
    # Default dev port 5050: on macOS, port 5000 is often used by AirPlay Receiver,
    # which answers plain HTTP with 403 and looks like a broken Flask app.
    port = int(os.environ.get("PORT", "5050"))
    app.run(debug=True, host="127.0.0.1", port=port)

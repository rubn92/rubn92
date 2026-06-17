import os
import re
import json
import requests
from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def scrape_website(url: str) -> dict:
    """Extract key content from a website URL."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.SSLError:
        resp = requests.get(url, headers=headers, timeout=15, verify=False)

    soup = BeautifulSoup(resp.text, "lxml")

    def meta(name=None, prop=None):
        if name:
            tag = soup.find("meta", attrs={"name": name})
        else:
            tag = soup.find("meta", attrs={"property": prop})
        return tag["content"].strip() if tag and tag.get("content") else ""

    title = soup.title.string.strip() if soup.title else ""
    description = meta(name="description") or meta(prop="og:description")
    og_title = meta(prop="og:title")
    og_image = meta(prop="og:image")
    keywords = meta(name="keywords")

    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")][:3]
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")][:6]

    # Remove script/style/nav/footer noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    paragraphs = [
        p.get_text(strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 60
    ][:8]

    # Collect CTA buttons/links text
    ctas = [
        a.get_text(strip=True)
        for a in soup.find_all(["a", "button"])
        if a.get_text(strip=True) and len(a.get_text(strip=True)) < 60
    ]
    cta_unique = list(dict.fromkeys(ctas))[:10]

    return {
        "url": url,
        "title": title,
        "og_title": og_title,
        "description": description,
        "keywords": keywords,
        "og_image": og_image,
        "h1s": h1s,
        "h2s": h2s,
        "paragraphs": paragraphs,
        "ctas": cta_unique,
    }


def build_prompt(data: dict) -> str:
    return f"""Eres un experto en marketing digital, copywriting y SEO con 15 años de experiencia.
Analiza la siguiente información extraída del sitio web y genera un informe completo de marketing.

=== DATOS DEL SITIO WEB ===
URL: {data['url']}
Título: {data['title']}
OG Título: {data['og_title']}
Meta descripción: {data['description']}
Keywords: {data['keywords']}
Headings H1: {', '.join(data['h1s']) or 'No encontrados'}
Headings H2: {', '.join(data['h2s']) or 'No encontrados'}
Textos principales:
{chr(10).join(f'- {p}' for p in data['paragraphs']) or 'No encontrado'}
Llamadas a la acción detectadas: {', '.join(data['ctas']) or 'No detectadas'}

=== INSTRUCCIONES ===
Responde ÚNICAMENTE con un objeto JSON válido con esta estructura exacta (sin markdown, sin texto extra):

{{
  "resumen_negocio": "Descripción del negocio en 2-3 frases claras",
  "publico_objetivo": "Descripción detallada del público objetivo ideal",
  "propuesta_valor": "La propuesta de valor principal del negocio",
  "anuncios_google": [
    {{
      "titulo_1": "Máx 30 caracteres",
      "titulo_2": "Máx 30 caracteres",
      "titulo_3": "Máx 30 caracteres",
      "descripcion_1": "Máx 90 caracteres",
      "descripcion_2": "Máx 90 caracteres"
    }},
    {{
      "titulo_1": "...",
      "titulo_2": "...",
      "titulo_3": "...",
      "descripcion_1": "...",
      "descripcion_2": "..."
    }},
    {{
      "titulo_1": "...",
      "titulo_2": "...",
      "titulo_3": "...",
      "descripcion_1": "...",
      "descripcion_2": "..."
    }}
  ],
  "anuncios_facebook": [
    {{
      "hook": "Primera frase gancho (máx 40 palabras)",
      "cuerpo": "Texto principal del anuncio (60-100 palabras)",
      "cta": "Llamada a la acción (ej: Saber más, Comprar ahora)"
    }},
    {{
      "hook": "...",
      "cuerpo": "...",
      "cta": "..."
    }},
    {{
      "hook": "...",
      "cuerpo": "...",
      "cta": "..."
    }}
  ],
  "posts_instagram": [
    {{
      "caption": "Caption completo para Instagram (máx 150 palabras)",
      "hashtags": "#hashtag1 #hashtag2 #hashtag3 (mínimo 10 hashtags relevantes)"
    }},
    {{
      "caption": "...",
      "hashtags": "..."
    }},
    {{
      "caption": "...",
      "hashtags": "..."
    }}
  ],
  "recomendaciones_seo": [
    {{
      "titulo": "Nombre de la mejora",
      "problema": "Qué está mal actualmente",
      "solucion": "Cómo solucionarlo",
      "impacto": "alto/medio/bajo"
    }},
    {{
      "titulo": "...",
      "problema": "...",
      "solucion": "...",
      "impacto": "..."
    }},
    {{
      "titulo": "...",
      "problema": "...",
      "solucion": "...",
      "impacto": "..."
    }},
    {{
      "titulo": "...",
      "problema": "...",
      "solucion": "...",
      "impacto": "..."
    }},
    {{
      "titulo": "...",
      "problema": "...",
      "solucion": "...",
      "impacto": "..."
    }}
  ],
  "estrategia_contenido": [
    "Idea de contenido 1 con descripción breve",
    "Idea de contenido 2 con descripción breve",
    "Idea de contenido 3 con descripción breve",
    "Idea de contenido 4 con descripción breve"
  ],
  "puntuacion_marketing": {{
    "seo": 0,
    "copy": 0,
    "conversion": 0,
    "presencia_social": 0,
    "nota_general": "Comentario sobre la puntuación global"
  }}
}}

Las puntuaciones son del 1 al 10. Sé honesto y específico. Responde en español."""


def analyze_with_claude(scraped: dict) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = build_prompt(scraped)

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract text content (skip thinking blocks)
    raw = ""
    for block in message.content:
        if block.type == "text":
            raw = block.text
            break

    # Strip potential markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    return json.loads(raw)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()

    if not url:
        return jsonify({"error": "Por favor introduce una URL válida."}), 400

    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "API key de Claude no configurada. Añade ANTHROPIC_API_KEY al archivo .env"}), 500

    try:
        scraped = scrape_website(url)
    except Exception as e:
        return jsonify({"error": f"No se pudo acceder a la web: {str(e)}"}), 422

    try:
        result = analyze_with_claude(scraped)
    except json.JSONDecodeError:
        return jsonify({"error": "Error al procesar la respuesta de la IA. Inténtalo de nuevo."}), 500
    except Exception as e:
        return jsonify({"error": f"Error al analizar con IA: {str(e)}"}), 500

    result["url_analizada"] = scraped["url"]
    result["titulo_web"] = scraped["title"] or scraped["og_title"]
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

import re
import json
import requests
from bs4 import BeautifulSoup
import anthropic


def scrape_website(url: str) -> dict:
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
        tag = soup.find("meta", attrs={"name": name} if name else {"property": prop})
        return tag["content"].strip() if tag and tag.get("content") else ""

    title = soup.title.string.strip() if soup.title else ""
    description = meta(name="description") or meta(prop="og:description")
    og_title = meta(prop="og:title")
    keywords = meta(name="keywords")

    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")][:3]
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")][:8]

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    paragraphs = [
        p.get_text(strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 50
    ][:10]

    ctas = list(dict.fromkeys([
        a.get_text(strip=True)
        for a in soup.find_all(["a", "button"])
        if a.get_text(strip=True) and len(a.get_text(strip=True)) < 60
    ]))[:12]

    return {
        "url": url,
        "title": title,
        "og_title": og_title,
        "description": description,
        "keywords": keywords,
        "h1s": h1s,
        "h2s": h2s,
        "paragraphs": paragraphs,
        "ctas": ctas,
    }


def _build_prompt(data: dict) -> str:
    return f"""Eres un experto en marketing digital, copywriting, SEO y estrategia de contenidos con 20 años de experiencia trabajando con marcas globales y startups.

Analiza la siguiente información extraída del sitio web y genera un informe de marketing COMPLETO y DETALLADO.

=== DATOS EXTRAÍDOS ===
URL: {data['url']}
Título: {data['title']}
OG Título: {data['og_title']}
Meta descripción: {data['description']}
Keywords: {data['keywords']}
H1: {', '.join(data['h1s']) or 'No detectado'}
H2: {', '.join(data['h2s']) or 'No detectado'}
Textos:
{chr(10).join(f'• {p}' for p in data['paragraphs']) or 'No detectado'}
CTAs detectados: {', '.join(data['ctas']) or 'No detectado'}

=== INSTRUCCIONES ===
Responde ÚNICAMENTE con un objeto JSON válido (sin markdown, sin texto antes o después). Usa este esquema exacto:

{{
  "dna_negocio": {{
    "nombre": "Nombre del negocio o marca",
    "resumen": "Qué hace este negocio en 2-3 frases",
    "sector": "Sector o industria",
    "publico_objetivo": "Descripción del cliente ideal (edad, profesión, necesidades)",
    "propuesta_valor": "Su propuesta de valor principal y diferenciadores",
    "tono_de_voz": "Descripción del tono (ej: profesional y cercano, dinámico y juvenil...)",
    "palabras_clave_marca": ["kw1", "kw2", "kw3", "kw4", "kw5"]
  }},
  "puntuacion": {{
    "seo": 7,
    "copy": 6,
    "conversion": 5,
    "redes_sociales": 4,
    "general": 6,
    "resumen": "Comentario honesto de 1-2 frases sobre el estado actual del marketing"
  }},
  "google_ads": [
    {{
      "titulo_1": "máx 30 chars",
      "titulo_2": "máx 30 chars",
      "titulo_3": "máx 30 chars",
      "descripcion_1": "máx 90 chars",
      "descripcion_2": "máx 90 chars",
      "enfoque": "Qué estrategia sigue este anuncio (ej: problema-solución, oferta, beneficio)"
    }},
    {{ "titulo_1": "...", "titulo_2": "...", "titulo_3": "...", "descripcion_1": "...", "descripcion_2": "...", "enfoque": "..." }},
    {{ "titulo_1": "...", "titulo_2": "...", "titulo_3": "...", "descripcion_1": "...", "descripcion_2": "...", "enfoque": "..." }}
  ],
  "facebook_ads": [
    {{
      "gancho": "Primera frase impactante (máx 15 palabras)",
      "cuerpo": "Texto completo del anuncio (80-120 palabras)",
      "cta_boton": "Texto del botón (ej: Más información, Comprar ahora)",
      "formato_recomendado": "imagen/carrusel/video"
    }},
    {{ "gancho": "...", "cuerpo": "...", "cta_boton": "...", "formato_recomendado": "..." }},
    {{ "gancho": "...", "cuerpo": "...", "cta_boton": "...", "formato_recomendado": "..." }}
  ],
  "instagram_posts": [
    {{
      "tipo": "Reels/Carrusel/Feed",
      "caption": "Caption completo listo para publicar (máx 200 palabras)",
      "hashtags": "#h1 #h2 #h3 #h4 #h5 #h6 #h7 #h8 #h9 #h10 #h11 #h12",
      "idea_visual": "Descripción de qué imagen o video usar"
    }},
    {{ "tipo": "...", "caption": "...", "hashtags": "...", "idea_visual": "..." }},
    {{ "tipo": "...", "caption": "...", "hashtags": "...", "idea_visual": "..." }},
    {{ "tipo": "...", "caption": "...", "hashtags": "...", "idea_visual": "..." }},
    {{ "tipo": "...", "caption": "...", "hashtags": "...", "idea_visual": "..." }}
  ],
  "twitter_posts": [
    {{ "texto": "Tweet listo (máx 280 chars, puede incluir emojis y hashtags)" }},
    {{ "texto": "..." }},
    {{ "texto": "..." }},
    {{ "texto": "..." }},
    {{ "texto": "..." }}
  ],
  "emails": [
    {{
      "tipo": "Bienvenida",
      "asunto": "Asunto del email",
      "preview_text": "Texto de preview (máx 90 chars)",
      "cuerpo": "Cuerpo completo del email en texto (150-250 palabras)"
    }},
    {{
      "tipo": "Nurturing",
      "asunto": "...",
      "preview_text": "...",
      "cuerpo": "..."
    }},
    {{
      "tipo": "Conversión",
      "asunto": "...",
      "preview_text": "...",
      "cuerpo": "..."
    }}
  ],
  "landing_page": {{
    "headline": "Titular principal impactante (máx 10 palabras)",
    "subheadline": "Subtítulo explicativo (máx 20 palabras)",
    "cta_principal": "Texto del botón principal",
    "beneficios": [
      {{ "icono": "emoji", "titulo": "Beneficio corto", "descripcion": "Descripción en 1-2 frases" }},
      {{ "icono": "emoji", "titulo": "...", "descripcion": "..." }},
      {{ "icono": "emoji", "titulo": "...", "descripcion": "..." }}
    ],
    "prueba_social": "Estadística o testimonio imaginario pero creíble para usar como referencia",
    "faq": [
      {{ "pregunta": "Pregunta frecuente 1", "respuesta": "Respuesta concisa" }},
      {{ "pregunta": "...", "respuesta": "..." }},
      {{ "pregunta": "...", "respuesta": "..." }}
    ]
  }},
  "seo_recomendaciones": [
    {{
      "titulo": "Nombre de la mejora",
      "problema": "Qué está mal o falta",
      "solucion": "Cómo solucionarlo exactamente",
      "impacto": "alto/medio/bajo",
      "esfuerzo": "alto/medio/bajo"
    }},
    {{ "titulo": "...", "problema": "...", "solucion": "...", "impacto": "...", "esfuerzo": "..." }},
    {{ "titulo": "...", "problema": "...", "solucion": "...", "impacto": "...", "esfuerzo": "..." }},
    {{ "titulo": "...", "problema": "...", "solucion": "...", "impacto": "...", "esfuerzo": "..." }},
    {{ "titulo": "...", "problema": "...", "solucion": "...", "impacto": "...", "esfuerzo": "..." }}
  ],
  "calendario_contenido": [
    {{ "dia": 1, "red": "Instagram", "tipo": "Reels", "tema": "Descripción del tema", "gancho": "Primera frase" }},
    {{ "dia": 3, "red": "Facebook", "tipo": "Post", "tema": "...", "gancho": "..." }},
    {{ "dia": 5, "red": "Instagram", "tipo": "Carrusel", "tema": "...", "gancho": "..." }},
    {{ "dia": 7, "red": "Twitter", "tipo": "Thread", "tema": "...", "gancho": "..." }},
    {{ "dia": 9, "red": "LinkedIn", "tipo": "Artículo", "tema": "...", "gancho": "..." }},
    {{ "dia": 11, "red": "Instagram", "tipo": "Stories", "tema": "...", "gancho": "..." }},
    {{ "dia": 14, "red": "Facebook", "tipo": "Video", "tema": "...", "gancho": "..." }},
    {{ "dia": 16, "red": "Twitter", "tipo": "Tweet", "tema": "...", "gancho": "..." }},
    {{ "dia": 18, "red": "Instagram", "tipo": "Reels", "tema": "...", "gancho": "..." }},
    {{ "dia": 21, "red": "LinkedIn", "tipo": "Post", "tema": "...", "gancho": "..." }}
  ]
}}

Todos los textos deben estar en español. Sé específico, creativo y usa el tono de voz que identificaste para esa marca."""


def generate_landing_html(api_key: str, report: dict) -> str:
    """Generate a complete deployable HTML landing page from the report."""
    dna = report.get("dna_negocio", {})
    lp = report.get("landing_page", {})
    beneficios = lp.get("beneficios", [])
    faq = lp.get("faq", [])
    kws = dna.get("palabras_clave_marca", [])

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""Genera una landing page HTML completa, moderna y profesional lista para publicar.

DATOS DEL NEGOCIO:
- Nombre: {dna.get('nombre', '')}
- Sector: {dna.get('sector', '')}
- Público objetivo: {dna.get('publico_objetivo', '')}
- Propuesta de valor: {dna.get('propuesta_valor', '')}
- Tono de voz: {dna.get('tono_de_voz', '')}
- Palabras clave: {', '.join(kws)}

COPY YA CREADO:
- Headline: {lp.get('headline', '')}
- Subheadline: {lp.get('subheadline', '')}
- CTA: {lp.get('cta_principal', '')}
- Beneficios: {json.dumps(beneficios, ensure_ascii=False)}
- Prueba social: {lp.get('prueba_social', '')}
- FAQ: {json.dumps(faq, ensure_ascii=False)}

REQUISITOS TÉCNICOS:
- Un único archivo HTML con todo el CSS inline en <style>
- Sin dependencias externas excepto Google Fonts (una fuente moderna)
- Diseño oscuro y moderno (fondo oscuro, acentos de color según el sector)
- Secciones: hero con CTA, beneficios (3 cards), prueba social/stats, FAQ, footer con email de contacto
- Totalmente responsive (mobile first)
- Botón CTA debe tener href="#contacto" y un formulario de contacto básico al final
- Variables CSS para colores para fácil personalización
- Comentarios HTML indicando qué personalizar (URL del CTA, email, teléfono)

IMPORTANTE: Responde ÚNICAMENTE con el código HTML completo, empezando con <!DOCTYPE html>. Sin markdown, sin explicaciones."""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    html = message.content[0].text.strip()
    html = re.sub(r"^```(?:html)?\s*", "", html)
    html = re.sub(r"\s*```$", "", html)
    return html


def analyze_competitor(api_key: str, scraped1: dict, scraped2: dict) -> dict:
    """Compare two businesses and return strategic opportunities."""
    client = anthropic.Anthropic(api_key=api_key)

    def fmt(d):
        return f"""URL: {d['url']}
Título: {d['title']}
Descripción: {d['description']}
H1: {', '.join(d['h1s'])}
H2: {', '.join(d['h2s'])}
Textos: {' | '.join(d['paragraphs'][:5])}
CTAs: {', '.join(d['ctas'][:6])}"""

    prompt = f"""Eres un estratega de marketing experto en análisis competitivo.

=== TU NEGOCIO ===
{fmt(scraped1)}

=== COMPETIDOR ===
{fmt(scraped2)}

Responde ÚNICAMENTE con JSON válido (sin markdown):

{{
  "tu_negocio": {{
    "nombre": "...",
    "fortalezas": ["...", "...", "..."],
    "debilidades": ["...", "...", "..."],
    "puntuacion_web": 7
  }},
  "competidor": {{
    "nombre": "...",
    "fortalezas": ["...", "...", "..."],
    "debilidades": ["...", "...", "..."],
    "puntuacion_web": 6
  }},
  "ganador_general": "tu_negocio/competidor/empate",
  "oportunidades": [
    {{"titulo": "Oportunidad 1", "descripcion": "Cómo aprovecharla específicamente", "prioridad": "alta/media/baja"}},
    {{"titulo": "...", "descripcion": "...", "prioridad": "..."}},
    {{"titulo": "...", "descripcion": "...", "prioridad": "..."}},
    {{"titulo": "...", "descripcion": "...", "prioridad": "..."}},
    {{"titulo": "...", "descripcion": "...", "prioridad": "..."}}
  ],
  "acciones_inmediatas": [
    "Acción concreta 1 que puedes implementar esta semana",
    "Acción concreta 2",
    "Acción concreta 3"
  ],
  "diferenciacion": "Cómo deberías posicionarte para destacar frente a este competidor en 2-3 frases",
  "keywords_sin_cubrir": ["kw que el competidor no ataca bien", "....", "..."]
}}

Responde en español, sé muy específico con los datos reales de cada web."""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    raw = ""
    for block in message.content:
        if block.type == "text":
            raw = block.text
            break

    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    return json.loads(raw)


def generate_report(api_key: str, scraped: dict) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(scraped)

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    raw = ""
    for block in message.content:
        if block.type == "text":
            raw = block.text
            break

    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    return json.loads(raw)

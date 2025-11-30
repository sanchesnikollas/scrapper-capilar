import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ==========================
# Configurações globais
# ==========================

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# Delay aleatório entre requisições para respeitar os sites
REQUEST_DELAY_SECONDS: Tuple[float, float] = (1.0, 3.0)


# Claims configurados: coluna -> {label para humanos, lista de palavras-chave}
CLAIMS_CONFIG: Dict[str, Dict[str, List[str]]] = {
    "claim_sem_sulfato": {
        "label": "Sem sulfato",
        "keywords": ["sem sulfato", "sem sulfatos", "sem sal", "sulfate free", "sulfate-free"],
    },
    "claim_sem_parabenos": {
        "label": "Sem parabenos",
        "keywords": ["sem parabenos", "sem parabeno", "livre de parabenos", "paraben free", "paraben-free"],
    },
    "claim_vegano": {
        "label": "Vegano",
        "keywords": ["vegano", "vegana", "vegan"],
    },
    "claim_organico": {
        "label": "Orgânico",
        "keywords": ["orgânico", "organico", "organic"],
    },
    "claim_natural": {
        "label": "Natural",
        "keywords": ["natural", "ingredientes naturais", "origem natural"],
    },
    "claim_hipoalergenico": {
        "label": "Hipoalergênico",
        "keywords": ["hipoalergênico", "hipoalergenico"],
    },
    "claim_peta": {
        "label": "PETA",
        "keywords": ["peta"],
    },
    "claim_cruelty_free": {
        "label": "Cruelty-free",
        "keywords": ["cruelty free", "cruelty-free", "não testado em animais", "nao testado em animais"],
    },
    "claim_fragrance_free": {
        "label": "Fragrance-free",
        "keywords": ["fragrance free", "sem fragrância", "sem fragrancia", "sem perfume"],
    },
    "claim_silicone_free": {
        "label": "Silicone-free",
        "keywords": ["silicone free", "sem silicone", "livre de silicones"],
    },
    "claim_oftalmologicamente_testado": {
        "label": "Oftalmologicamente testado",
        "keywords": ["oftalmologicamente testado"],
    },
    "claim_dermatologicamente_testado": {
        "label": "Dermatologicamente testado",
        "keywords": ["dermatologicamente testado"],
    },
    "claim_filtro_uv": {
        "label": "Filtro UV",
        "keywords": ["filtro uv", "proteção uv", "protecao uv", "protetor solar para cabelos", "proteção solar", "protecao solar", "uva/uvb"],
    },
    "claim_protecao_termica": {
        "label": "Proteção térmica",
        "keywords": ["proteção térmica", "protecao termica", "protetor térmico", "protetor termico", "thermal protection"],
    },
    "claim_low_poo": {
        "label": "Low Poo",
        "keywords": ["low poo", "low-poo"],
    },
    "claim_no_poo": {
        "label": "No Poo",
        "keywords": ["no poo", "no-poo"],
    },
}

# Grupos de ingredientes para inferência
HUMECTANTS = {
    "glycerin", "glicerina",
    "propylenglycol", "propylene glycol",
    "sodium pca", "sodium lactate",
    "panthenol", "d-panthenol",
    "aloe barbadensis leaf juice", "aloe vera", "babosa",
    "hyaluronic acid", "sodium hyaluronate", "acido hialuronico",
    "extract", "extrato"
}

OILS_LIGHT = {
    "argania spinosa kernel oil", "argan",
    "simmondsia chinensis seed oil", "jojoba",
    "vitis vinifera seed oil", "semente de uva",
    "macadamia integrifolia seed oil", "macadamia",
    "helianthus annuus seed oil", "girassol",
    "prunus amygdalus dulcis oil", "amendoas doces", "amêndoas doces"
}

OILS_HEAVY = {
    "cocos nucifera oil", "coconut oil", "oleo de coco", "óleo de coco",
    "ricinus communis seed oil", "castor oil", "oleo de ricino", "óleo de rícino",
    "butyrospermum parkii butter", "shea butter", "manteiga de karite", "manteiga de karité",
    "theobroma cacao seed butter", "cocoa butter", "manteiga de cacau",
    "petrolatum", "mineral oil", "paraffinum liquidum", "oleo mineral", "óleo mineral",
    "murumuru", "persea gratissima", "avocado oil", "abacate"
}

PROTEINS = {
    "hydrolyzed keratin", "keratin", "queratina",
    "hydrolyzed collagen", "collagen", "colageno", "colágeno",
    "hydrolyzed wheat protein", "proteina do trigo",
    "hydrolyzed soy protein", "proteina da soja",
    "hydrolyzed rice protein", "proteina do arroz",
    "bamboo extract", "bambusa vulgaris extract", "bambu"
}

AMINOACIDS = {
    "arginine", "arginina",
    "lysine", "lisina",
    "proline", "prolina",
    "serine", "serina",
    "cysteine", "cisteina", "cisteína",
    "glycine", "glicina",
    "tyrosine", "tirosina"
}

SILICONES_HEAVY = {
    "dimethicone", "amodimethicone", "simethicone",
}

SILICONES_VOLATILE = {
    "cyclopentasiloxane", "cyclohexasiloxane",
}

PRODUCT_TYPES = [
    ("shampoo", "Shampoo"),
    ("condicionador", "Condicionador"),
    ("máscara", "Máscara"),
    ("mascara", "Máscara"),
    ("leave-in", "Leave-in"),
    ("leave in", "Leave-in"),
    ("óleo", "Óleo"),
    ("oleo", "Óleo"),
    ("spray", "Spray"),
    ("finalizador", "Finalizador"),
    ("tônico", "Tônico"),
    ("tonico", "Tônico"),
    ("ampola", "Ampola"),
    ("serum", "Sérum"),
]


# ==========================
# Utilitários
# ==========================

def polite_sleep() -> None:
    """Espera um tempo aleatório entre as requisições."""
    time.sleep(random.uniform(*REQUEST_DELAY_SECONDS))


def normalize_space(text: str) -> str:
    """Normaliza espaços em um texto."""
    return re.sub(r"\s+", " ", text).strip()


def get_domain(url: str) -> str:
    """Extrai o domínio de uma URL, sem 'www.'."""
    netloc = urlparse(url).netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def fetch_html(session: requests.Session, url: str) -> str:
    """Faz uma requisição HTTP segura e retorna o HTML como string."""
    try:
        resp = session.get(url, timeout=30)
    except Exception as exc:
        logging.warning("Erro ao acessar %s: %s", url, exc)
        return ""
    if resp.status_code != 200:
        logging.warning("Status %s ao acessar %s", resp.status_code, url)
        return ""
    return resp.text


def extract_section_by_label(
    full_text: str,
    labels: List[str],
    stop_markers: Optional[List[str]] = None,
    max_chars: int = 2000,
) -> str:
    """
    Extrai um trecho do texto a partir de um label (ex.: 'Modo de usar')
    até encontrar um dos stop_markers ou atingir max_chars.
    """
    if not full_text:
        return ""
    text = full_text
    lower_text = text.lower()

    start_idx = -1
    for label in labels:
        idx = lower_text.find(label.lower())
        if idx != -1 and (start_idx == -1 or idx < start_idx):
            start_idx = idx

    if start_idx == -1:
        return ""

    section = text[start_idx:]
    if stop_markers:
        lower_section = section.lower()
        stop_positions: List[int] = []
        for stop in stop_markers:
            pos = lower_section.find(stop.lower(), len(labels[0]))
            if pos != -1:
                stop_positions.append(pos)
        if stop_positions:
            section = section[: min(stop_positions)]

    if len(section) > max_chars:
        section = section[:max_chars]

    return section.strip()


def extract_ph(full_text: str) -> Optional[float]:
    """Extrai o valor de pH, se estiver presente no texto."""
    if not full_text:
        return None
    match = re.search(r"pH\s*([\d]{1,2}(?:[.,]\d)?)", full_text, flags=re.IGNORECASE)
    if match:
        val = match.group(1).replace(",", ".")
        try:
            return float(val)
        except ValueError:
            return None
    return None


def extract_audience(full_text: str) -> str:
    """Define o público/idade alvo com base em palavras-chave no texto."""
    if not full_text:
        return ""
    lower = full_text.lower()
    if any(w in lower for w in ["bebê", "bebe", "recém-nascido", "0+", "baby"]):
        return "Infantil (0-3)"
    if any(w in lower for w in ["infantil", "criança", "crianca", "kid", "kids"]):
        return "Infantil (3-12)"
    if "teen" in lower or "adolescente" in lower:
        return "Teen"
    # Se nada for encontrado, consideramos adulto / geral
    return "Adulto"


def extract_hair_type_from_text(text: str) -> str:
    """Extrai tipo de cabelo declarado diretamente na descrição."""
    if not text:
        return ""
    lower = text.lower()
    mapping = [
        ("cabelos cacheados", "Cacheado/Crespo"),
        ("cabelos crespos", "Cacheado/Crespo"),
        ("cabelos ondulados", "Ondulado"),
        ("cabelos lisos", "Liso"),
        ("cabelos oleosos", "Oleoso/Fino"),
        ("couro cabeludo oleoso", "Oleoso/Fino"),
        ("cabelos mistos", "Misto"),
        ("cabelos secos", "Seco/Ressecado"),
        ("cabelos ressecados", "Seco/Ressecado"),
        ("cabelos danificados", "Danificado/Quimicamente tratado"),
        ("cabelos quimicamente tratados", "Danificado/Quimicamente tratado"),
        ("cabelos coloridos", "Colorido/Quimicamente tratado"),
        ("cabelos tingidos", "Colorido/Quimicamente tratado"),
        ("cabelos loiros", "Loiro"),
    ]
    for keyword, label in mapping:
        if keyword in lower:
            return label
    return ""

def parse_ingredients_list(raw_ingredients: str) -> List[str]:
    """Normaliza e separa a lista de ingredientes."""
    if not raw_ingredients:
        return []
    text = raw_ingredients.lower()
    text = text.replace(";", ",")
    # Remove prefixos comuns como "ingredientes:" ou "composição:"
    text = re.sub(r'^(ingredientes|composição|composition)[:\s]*', '', text)
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return parts

def ingredient_weight(position: int) -> float:
    """Calcula o peso do ingrediente baseado na posição (0-indexed)."""
    # 0 = mais importante, 9 = menos
    return max(1.0 - position * 0.1, 0)

def classify_cronograma(ingredients: List[str]) -> Dict[str, object]:
    """Classifica o produto em H, N, R com scores."""
    h_score = n_score = r_score = 0.0

    # Considerar apenas os top 10 ingredientes para pontuação principal
    top_ingredients = ingredients[:10]

    for i, ing in enumerate(top_ingredients):
        w = ingredient_weight(i)
        
        # Check partial matches for flexibility
        if any(term in ing for term in HUMECTANTS):
            h_score += 1.0 * w
        
        if any(term in ing for term in OILS_LIGHT) or any(term in ing for term in OILS_HEAVY):
            n_score += 1.0 * w
            
        if any(term in ing for term in PROTEINS) or any(term in ing for term in AMINOACIDS):
            r_score += 1.0 * w

    total = h_score + n_score + r_score
    if total == 0:
        return {"fase": "Indefinido", "scores": {"H": 0.0, "N": 0.0, "R": 0.0}}

    h = round(h_score / total, 2)
    n = round(n_score / total, 2)
    r = round(r_score / total, 2)

    scores = {"H": h, "N": n, "R": r}
    fase = max(scores, key=scores.get)

    # Verifica empate ou proximidade para Mix
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if len(ordered) > 1 and (ordered[0][1] - ordered[1][1] < 0.15):
        fase = f"{ordered[0][0]}+{ordered[1][0]}"

    return {"fase": fase, "scores": scores}

def score_fine_hair(ingredients: List[str], product_category: str) -> Dict[str, object]:
    """Calcula score de adequação para cabelos finos."""
    top_ingredients = ingredients[:10]
    
    heavy_count = 0
    light_count = 0
    humectant_count = 0
    protein_count = 0
    volatile_silicone_count = 0
    
    product_category_lower = product_category.lower()

    for ing in top_ingredients:
        if any(term in ing for term in OILS_HEAVY) or any(term in ing for term in SILICONES_HEAVY):
            heavy_count += 1
        if any(term in ing for term in OILS_LIGHT):
            light_count += 1
        if any(term in ing for term in HUMECTANTS):
            humectant_count += 1
        if any(term in ing for term in PROTEINS) or any(term in ing for term in AMINOACIDS):
            protein_count += 1
        if any(term in ing for term in SILICONES_VOLATILE):
            volatile_silicone_count += 1

    score = 0.0
    score += light_count * 0.8
    score += humectant_count * 0.6
    score += protein_count * 0.7
    score += volatile_silicone_count * 0.5
    score -= heavy_count * 1.2

    if "máscara" in product_category_lower or "mascara" in product_category_lower:
        score -= 0.5
    if "spray" in product_category_lower:
        score += 0.5
    if "leave-in" in product_category_lower:
        score += 0.2

    if score >= 2.0:
        label = "Sim"
    elif score >= 0.5:
        label = "Talvez"
    else:
        label = "Não"
        
    return {"score_fine": round(score, 2), "adequacao_cabelos_finos": label}


def infer_product_type_from_name_and_breadcrumbs(name: str, soup: BeautifulSoup) -> str:
    """Infere o tipo de produto usando nome e possíveis breadcrumbs."""
    sources = [name.lower()]
    for selector in ("nav.breadcrumb", "div.breadcrumb", "ol.breadcrumb"):
        bc = soup.select_one(selector)
        if bc:
            sources.append(bc.get_text(" ", strip=True).lower())
    full = " ".join(sources)
    for kw, label in PRODUCT_TYPES:
        if kw in full:
            return label
    return "Outros"


def extract_image_urls_generic(soup: BeautifulSoup, base_url: str) -> Tuple[str, str]:
    """Tenta extrair URLs de imagem frontal e verso de forma genérica."""
    candidates = []
    selectors = [
        "div.product-images img",
        "div.product-image img",
        "div.images img",
        "figure.woocommerce-product-gallery__wrapper img",
        "img#image-main",
        "img.wp-post-image",
        ".product-gallery__image img"
    ]
    for sel in selectors:
        candidates.extend(soup.select(sel))
    if not candidates:
        candidates = soup.find_all("img")

    urls: List[str] = []
    for img in candidates:
        src = img.get("src") or img.get("data-src") or img.get("data-large_image")
        if src:
            full_url = urljoin(base_url, src)
            # Filtra imagens muito pequenas ou ícones comuns
            if "icon" not in full_url.lower() and "logo" not in full_url.lower():
                urls.append(full_url)

    if not urls:
        return "", ""

    # Remove duplicatas mantendo ordem
    unique_urls = []
    seen = set()
    for u in urls:
        if u not in seen:
            unique_urls.append(u)
            seen.add(u)
    
    urls = unique_urls

    front = urls[0] if urls else ""
    back = ""
    if len(urls) > 1:
        for u in urls[1:]:
            lower = u.lower()
            if any(tag in lower for tag in ("back", "verso", "traseira", "tabela", "ingredientes", "rotulo")):
                back = u
                break
        if not back:
            back = urls[1]

    return front, back


def detect_claims(soup: BeautifulSoup, full_text: str) -> Dict[str, object]:
    """Marca os claims (booleans) com base em texto e metadados de imagens."""
    text = (full_text or "").lower()

    img_bits: List[str] = []
    for img in soup.find_all("img"):
        for attr in ("alt", "title"):
            val = img.get(attr)
            if val:
                img_bits.append(val.lower())
        src = img.get("src") or ""
        if src:
            img_bits.append(src.lower())
    text = text + "\n" + "\n".join(img_bits)

    result: Dict[str, object] = {}
    active_labels: List[str] = []

    for key, conf in CLAIMS_CONFIG.items():
        found = False
        for kw in conf["keywords"]:
            if kw.lower() in text:
                found = True
                break
        result[key] = found
        if found:
            active_labels.append(conf["label"])

    result["claims_list"] = ", ".join(sorted(active_labels)) if active_labels else ""
    return result


# ==========================
# Estrutura de parsers
# ==========================

@dataclass
class BrandParser:
    domain: str
    get_product_links: Callable[[requests.Session, str], List[str]]
    parse_product: Callable[[requests.Session, str], Optional[Dict[str, object]]]


BRAND_PARSERS: Dict[str, BrandParser] = {}


def register_brand_parser(parser: BrandParser) -> None:
    BRAND_PARSERS[parser.domain] = parser


# ==========================
# Parser StiloHair
# ==========================

def get_all_product_links_stilohair(session: requests.Session, brand_page_url: str) -> List[str]:
    """
    Coleta links de produtos na página da marca no site StiloHair, incluindo paginação.
    """
    product_links: List[str] = []
    page_url: Optional[str] = brand_page_url
    visited: set = set()

    while page_url and page_url not in visited:
        visited.add(page_url)
        html = fetch_html(session, page_url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")

        anchors: List[BeautifulSoup] = []
        selectors = [
            "a.product-name",
            "a.nome_produto",
            "a.nome-produto",
            "div.product-name a",
            "h2.product-name a",
            "h2.nome-produto a",
            "div.product-item a",
        ]
        for sel in selectors:
            anchors.extend(soup.select(sel))

        # Fallback: âncoras que parecem produto
        if not anchors:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                txt = (a.get_text() or "").strip().lower()
                if any(
                    word in href
                    for word in ["/escova-", "/produto", "/produtos", "progressiva", "shampoo", "mascara", "máscara"]
                ):
                    anchors.append(a)

        for a in anchors:
            href = a.get("href")
            if href:
                full_url = urljoin(page_url, href)
                if full_url not in product_links:
                    product_links.append(full_url)

        # Paginação
        next_url: Optional[str] = None
        link_next = soup.find("link", rel="next")
        if link_next and link_next.get("href"):
            next_url = urljoin(page_url, link_next["href"])

        if not next_url:
            for a in soup.find_all("a", href=True):
                text = (a.get_text() or "").strip().lower()
                if "próxima" in text or "proxima" in text or text in (">>", "›"):
                    next_url = urljoin(page_url, a["href"])
                    break

        page_url = next_url
        polite_sleep()

    return product_links


def parse_product_stilohair(session: requests.Session, product_url: str) -> Optional[Dict[str, object]]:
    """Extrai todos os campos relevantes de um produto no site StiloHair."""
    html = fetch_html(session, product_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text("\n", strip=True)
    full_text_lower = full_text.lower()

    # Nome do produto
    title_tag = soup.find("h1") or soup.find("h2")
    product_name = normalize_space(title_tag.get_text()) if title_tag else ""

    # Marca
    brand = ""
    match_marca = re.search(r"Marca:\s*([^\n\r]+)", full_text)
    if match_marca:
        brand = match_marca.group(1).strip()
    else:
        if "1ka" in full_text_lower:
            brand = "1Ka Hair"
        else:
            brand = "StiloHair"

    # Descrição
    desc_tag = (
        soup.select_one("div.product-description")
        or soup.select_one("div.descricao")
        or soup.select_one("div#descricao")
    )
    description = ""
    if desc_tag:
        description = normalize_space(desc_tag.get_text(separator=" "))
    if not description:
        for p in soup.find_all("p"):
            txt = normalize_space(p.get_text())
            if len(txt) > 80:
                description = txt
                break

    # Modo de uso
    usage = extract_section_by_label(
        full_text,
        ["Modo de usar", "Modo de uso", "Como usar"],
        stop_markers=["Ingredientes", "Composição", "Produtos relacionados"],
    )

    # Ingredientes
    ingredients_raw = extract_section_by_label(
        full_text,
        ["Ingredientes", "Composição"],
        stop_markers=["Modo de usar", "Modo de uso", "Como usar", "Produtos relacionados"],
    )
    ingredients_raw = ingredients_raw.replace("\n", " ").strip()
    ingredients_list = parse_ingredients_list(ingredients_raw)

    # Tipo de cabelo
    hair_type_declared = extract_hair_type_from_text(description or full_text)

    # Imagens
    image_front_url, image_back_url = extract_image_urls_generic(soup, product_url)

    # pH e público
    ph_value = extract_ph(full_text)
    audience = extract_audience(full_text)

    # Tipo de produto
    product_type = infer_product_type_from_name_and_breadcrumbs(product_name, soup)

    # Cronograma e Fine Hair
    cronograma_info = classify_cronograma(ingredients_list)
    fine_hair_info = score_fine_hair(ingredients_list, product_type)

    # Claims
    claims = detect_claims(soup, full_text + "\n" + ingredients_raw)

    record: Dict[str, object] = {
        "source_url": product_url,
        "brand": brand,
        "product_name": product_name,
        "product_type": product_type,
        "description": description,
        "function_objective": description,
        "hair_type_declared": hair_type_declared,
        "usage_instructions": usage,
        "ingredients_raw": ingredients_raw,
        "ingredients_list": ", ".join(ingredients_list),
        "image_front_url": image_front_url,
        "image_back_url": image_back_url,
        "ph": ph_value,
        "target_audience": audience,
        "cronograma_fase": cronograma_info["fase"],
        "cronograma_scores": str(cronograma_info["scores"]),
        "adequacao_cabelos_finos": fine_hair_info["adequacao_cabelos_finos"],
        "score_cabelos_finos": fine_hair_info["score_fine"]
    }
    record.update(claims)
    return record


register_brand_parser(
    BrandParser(
        domain="stilohair.com.br",
        get_product_links=get_all_product_links_stilohair,
        parse_product=parse_product_stilohair,
    )
)


# ==========================
# Parser Aline Brasil (WooCommerce genérico)
# ==========================

def get_all_product_links_aline(session: requests.Session, brand_page_url: str) -> List[str]:
    """
    Coleta links de produtos na loja da Aline Brasil (WooCommerce-like).
    """
    product_links: List[str] = []
    page_url: Optional[str] = brand_page_url
    visited: set = set()

    while page_url and page_url not in visited:
        visited.add(page_url)
        html = fetch_html(session, page_url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")

        anchors: List[BeautifulSoup] = []
        selectors = [
            "ul.products li.product a.woocommerce-LoopProduct-link",
            "li.product a.woocommerce-LoopProduct-link",
            "a.woocommerce-LoopProduct-link",
            "h2.woocommerce-loop-product__title a",
        ]
        for sel in selectors:
            anchors.extend(soup.select(sel))

        if not anchors:
            for li in soup.select("li.product"):
                for a in li.find_all("a", href=True):
                    anchors.append(a)

        if not anchors:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/produto/" in href or "/product/" in href:
                    anchors.append(a)

        for a in anchors:
            href = a.get("href")
            if href:
                full_url = urljoin(page_url, href)
                if full_url not in product_links:
                    product_links.append(full_url)

        # Paginação
        next_url: Optional[str] = None
        a_next = soup.select_one("a.page-numbers.next")
        if a_next and a_next.get("href"):
            next_url = urljoin(page_url, a_next["href"])

        page_url = next_url
        polite_sleep()

    return product_links


def parse_product_aline(session: requests.Session, product_url: str) -> Optional[Dict[str, object]]:
    """
    Parser de produto pensado para um site WooCommerce típico.
    """
    html = fetch_html(session, product_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text("\n", strip=True)

    # Nome do produto
    title_tag = soup.select_one("h1.product_title") or soup.find("h1")
    product_name = normalize_space(title_tag.get_text()) if title_tag else ""

    # Marca
    brand = "Aline Brasil Cosmetics"

    # Descrição
    desc_tag = (
        soup.select_one("div.woocommerce-product-details__short-description")
        or soup.select_one("div#tab-description")
        or soup.select_one("div.product-description")
    )
    description = ""
    if desc_tag:
        description = normalize_space(desc_tag.get_text(separator=" "))
    if not description:
        for p in soup.find_all("p"):
            txt = normalize_space(p.get_text())
            if len(txt) > 80:
                description = txt
                break

    # Ingredientes
    ingredients_raw = extract_section_by_label(
        full_text,
        ["Ingredientes", "Composição"],
        stop_markers=["Modo de usar", "Modo de uso", "Como usar"],
    )
    ingredients_raw = ingredients_raw.replace("\n", " ").strip()
    ingredients_list = parse_ingredients_list(ingredients_raw)

    # Modo de uso
    usage = extract_section_by_label(
        full_text,
        ["Modo de usar", "Modo de uso", "Como usar"],
        stop_markers=["Ingredientes", "Composição"],
    )

    # Tipo de cabelo
    hair_type_declared = extract_hair_type_from_text(description or full_text)

    # Imagens
    image_front_url, image_back_url = extract_image_urls_generic(soup, product_url)

    # Extras
    ph_value = extract_ph(full_text)
    audience = extract_audience(full_text)
    
    # Tipo de produto
    product_type = infer_product_type_from_name_and_breadcrumbs(product_name, soup)

    # Cronograma e Fine Hair
    cronograma_info = classify_cronograma(ingredients_list)
    fine_hair_info = score_fine_hair(ingredients_list, product_type)

    # Claims
    claims = detect_claims(soup, full_text + "\n" + ingredients_raw)

    record: Dict[str, object] = {
        "source_url": product_url,
        "brand": brand,
        "product_name": product_name,
        "product_type": product_type,
        "description": description,
        "function_objective": description,
        "hair_type_declared": hair_type_declared,
        "usage_instructions": usage,
        "ingredients_raw": ingredients_raw,
        "ingredients_list": ", ".join(ingredients_list),
        "image_front_url": image_front_url,
        "image_back_url": image_back_url,
        "ph": ph_value,
        "target_audience": audience,
        "cronograma_fase": cronograma_info["fase"],
        "cronograma_scores": str(cronograma_info["scores"]),
        "adequacao_cabelos_finos": fine_hair_info["adequacao_cabelos_finos"],
        "score_cabelos_finos": fine_hair_info["score_fine"]
    }
    record.update(claims)
    return record


register_brand_parser(
    BrandParser(
        domain="alinebrasilcosmetics.com.br",
        get_product_links=get_all_product_links_aline,
        parse_product=parse_product_aline,
    )
)


# ==========================
# Parser Genérico (Fallback)
# ==========================

def get_all_product_links_generic(session: requests.Session, brand_page_url: str) -> List[str]:
    """
    Parser genérico que tenta coletar links de produtos de qualquer site.
    Usa múltiplas estratégias para encontrar produtos.
    """
    product_links: List[str] = []
    visited: Set[str] = set()
    pages_to_visit: List[str] = [brand_page_url]
    max_pages = 10  # Limitar páginas para não demorar muito

    # Padrões comuns de URLs de produtos
    product_url_patterns = [
        r'/produto/', r'/product/', r'/produtos/', r'/products/',
        r'/item/', r'/p/', r'/loja/', r'/shop/',
        r'-p-\d+', r'/dp/', r'\.html$',
    ]

    # Padrões para ignorar (não são produtos)
    ignore_patterns = [
        r'/carrinho', r'/cart', r'/login', r'/cadastro', r'/register',
        r'/contato', r'/contact', r'/sobre', r'/about', r'/politica',
        r'/termos', r'/faq', r'/ajuda', r'/help', r'facebook\.com',
        r'instagram\.com', r'twitter\.com', r'youtube\.com', r'whatsapp',
        r'/checkout', r'/minha-conta', r'/account', r'/wishlist',
        r'/blog/', r'/categoria/', r'/category/', r'/brand/', r'/marca/',
    ]

    page_count = 0

    while pages_to_visit and page_count < max_pages:
        page_url = pages_to_visit.pop(0)
        if page_url in visited:
            continue
        visited.add(page_url)
        page_count += 1

        html = fetch_html(session, page_url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(brand_page_url).netloc

        # Estratégia 1: Seletores comuns de e-commerce
        product_selectors = [
            # WooCommerce
            "ul.products li.product a",
            "li.product a.woocommerce-LoopProduct-link",
            # Shopify
            ".product-card a",
            ".product-item a",
            ".product-grid-item a",
            # VTEX
            ".shelf-item a",
            ".prateleira a",
            # Tray/Loja Integrada
            "div.product-name a",
            "h2.product-name a",
            ".product-box a",
            ".produto a",
            # Genéricos
            ".product a",
            ".products a",
            "[data-product] a",
            ".card-product a",
            ".product-card a",
            ".item-product a",
        ]

        found_anchors: List[BeautifulSoup] = []
        for sel in product_selectors:
            found_anchors.extend(soup.select(sel))

        # Estratégia 2: Links com padrões de URL de produto
        if not found_anchors:
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                href_lower = href.lower()

                # Ignorar links externos ou indesejados
                if any(re.search(pat, href_lower) for pat in ignore_patterns):
                    continue

                # Verificar se parece URL de produto
                if any(re.search(pat, href_lower) for pat in product_url_patterns):
                    found_anchors.append(a)

        # Estratégia 3: Links dentro de containers de produtos
        if not found_anchors:
            product_containers = soup.select("div[class*='product'], div[class*='produto'], article[class*='product']")
            for container in product_containers:
                for a in container.find_all("a", href=True):
                    found_anchors.append(a)

        # Processar links encontrados
        for a in found_anchors:
            href = a.get("href", "")
            if not href:
                continue

            full_url = urljoin(page_url, href)
            parsed = urlparse(full_url)

            # Verificar se é do mesmo domínio
            if base_domain not in parsed.netloc:
                continue

            # Verificar se não é link ignorado
            if any(re.search(pat, full_url.lower()) for pat in ignore_patterns):
                continue

            if full_url not in product_links:
                product_links.append(full_url)

        # Procurar paginação
        pagination_selectors = [
            "a.next", "a.page-numbers.next", "a[rel='next']",
            "link[rel='next']", ".pagination a", ".paginacao a",
            "a:contains('Próxima')", "a:contains('próxima')",
        ]

        for sel in pagination_selectors:
            try:
                next_link = soup.select_one(sel)
                if next_link:
                    next_href = next_link.get("href")
                    if next_href:
                        next_url = urljoin(page_url, next_href)
                        if next_url not in visited and next_url not in pages_to_visit:
                            pages_to_visit.append(next_url)
                            break
            except:
                continue

        polite_sleep()

    # Remover duplicatas e URLs muito curtas
    unique_links = []
    seen = set()
    for link in product_links:
        normalized = link.rstrip('/')
        if normalized not in seen and len(normalized) > 30:
            seen.add(normalized)
            unique_links.append(link)

    return unique_links[:100]  # Limitar a 100 produtos por site


def parse_product_generic(session: requests.Session, product_url: str) -> Optional[Dict[str, object]]:
    """
    Parser genérico que tenta extrair dados de qualquer página de produto.
    Usa múltiplas heurísticas para encontrar informações.
    """
    html = fetch_html(session, product_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text("\n", strip=True)
    full_text_lower = full_text.lower()

    # === NOME DO PRODUTO ===
    product_name = ""
    name_selectors = [
        "h1.product-title", "h1.product_title", "h1.product-name",
        "h1[itemprop='name']", ".product-name h1", ".product-title",
        "h1.entry-title", "h1.nome-produto", "h1.productName",
        "h1", "h2.product-name",
    ]
    for sel in name_selectors:
        tag = soup.select_one(sel)
        if tag:
            product_name = normalize_space(tag.get_text())
            if len(product_name) > 5:
                break

    if not product_name:
        title_tag = soup.find("title")
        if title_tag:
            product_name = normalize_space(title_tag.get_text().split("|")[0].split("-")[0])

    # === MARCA ===
    brand = ""
    brand_selectors = [
        "[itemprop='brand']", ".product-brand", ".brand",
        "a[href*='/marca/']", "a[href*='/brand/']",
        ".manufacturer", "[data-brand]",
    ]
    for sel in brand_selectors:
        tag = soup.select_one(sel)
        if tag:
            brand = normalize_space(tag.get_text())
            if brand:
                break

    # Tentar extrair marca do texto
    if not brand:
        match = re.search(r"(?:Marca|Brand)[:\s]+([^\n\r,]+)", full_text, re.IGNORECASE)
        if match:
            brand = match.group(1).strip()

    # Extrair do domínio como fallback
    if not brand:
        domain = get_domain(product_url)
        brand = domain.replace(".com.br", "").replace(".com", "").replace("www.", "").title()

    # === DESCRIÇÃO ===
    description = ""
    desc_selectors = [
        "[itemprop='description']", ".product-description", "#description",
        ".description", ".descricao", "#tab-description",
        ".woocommerce-product-details__short-description",
        ".product-info", ".product-details", ".sobre-produto",
    ]
    for sel in desc_selectors:
        tag = soup.select_one(sel)
        if tag:
            description = normalize_space(tag.get_text(separator=" "))
            if len(description) > 50:
                break

    # Fallback: primeiro parágrafo longo
    if not description or len(description) < 50:
        for p in soup.find_all("p"):
            txt = normalize_space(p.get_text())
            if len(txt) > 100 and "cookie" not in txt.lower():
                description = txt
                break

    # === INGREDIENTES ===
    ingredients_raw = ""

    # Seletores específicos
    ingredient_selectors = [
        "#ingredientes", ".ingredientes", "[data-ingredientes]",
        "#ingredients", ".ingredients", "[itemprop='ingredients']",
        ".composicao", "#composicao", ".composition",
    ]
    for sel in ingredient_selectors:
        tag = soup.select_one(sel)
        if tag:
            ingredients_raw = normalize_space(tag.get_text())
            if ingredients_raw:
                break

    # Buscar por labels no texto
    if not ingredients_raw:
        ingredients_raw = extract_section_by_label(
            full_text,
            ["Ingredientes:", "Ingredientes", "Composição:", "Composição",
             "INCI:", "INCI", "Ingredients:", "Composition:"],
            stop_markers=["Modo de usar", "Modo de uso", "Como usar",
                         "Precauções", "Cuidados", "Informações", "Avaliações"],
            max_chars=3000,
        )

    ingredients_raw = ingredients_raw.replace("\n", " ").strip()

    # Limpar prefixos
    ingredients_raw = re.sub(r'^(ingredientes|composição|inci|ingredients|composition)[:\s]*',
                             '', ingredients_raw, flags=re.IGNORECASE)

    ingredients_list = parse_ingredients_list(ingredients_raw)

    # === MODO DE USO ===
    usage = extract_section_by_label(
        full_text,
        ["Modo de usar", "Modo de uso", "Como usar", "Modo de aplicação",
         "Instruções de uso", "How to use", "Aplicação"],
        stop_markers=["Ingredientes", "Composição", "Precauções", "Advertências"],
    )

    # === IMAGENS ===
    image_front_url, image_back_url = extract_image_urls_generic(soup, product_url)

    # === OUTROS DADOS ===
    hair_type_declared = extract_hair_type_from_text(description or full_text)
    ph_value = extract_ph(full_text)
    audience = extract_audience(full_text)
    product_type = infer_product_type_from_name_and_breadcrumbs(product_name, soup)

    # === CRONOGRAMA E CABELOS FINOS ===
    cronograma_info = classify_cronograma(ingredients_list)
    fine_hair_info = score_fine_hair(ingredients_list, product_type)

    # === CLAIMS ===
    claims = detect_claims(soup, full_text + "\n" + ingredients_raw)

    record: Dict[str, object] = {
        "source_url": product_url,
        "brand": brand,
        "product_name": product_name,
        "product_type": product_type,
        "description": description,
        "function_objective": description,
        "hair_type_declared": hair_type_declared,
        "usage_instructions": usage,
        "ingredients_raw": ingredients_raw,
        "ingredients_list": ", ".join(ingredients_list),
        "image_front_url": image_front_url,
        "image_back_url": image_back_url,
        "ph": ph_value,
        "target_audience": audience,
        "cronograma_fase": cronograma_info["fase"],
        "cronograma_scores": str(cronograma_info["scores"]),
        "adequacao_cabelos_finos": fine_hair_info["adequacao_cabelos_finos"],
        "score_cabelos_finos": fine_hair_info["score_fine"],
        "_parser": "generic",
    }
    record.update(claims)
    return record


# Parser genérico como fallback
GENERIC_PARSER = BrandParser(
    domain="*",  # Wildcard para qualquer domínio
    get_product_links=get_all_product_links_generic,
    parse_product=parse_product_generic,
)


# ==========================
# Engine principal
# ==========================

def load_brand_urls(file_path: str) -> List[str]:
    """Lê URLs de um arquivo de texto, ignorando linhas vazias ou comentários."""
    urls = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Tenta extrair a URL (assumindo que seja a última parte se houver tabulação)
                parts = line.split("\t")
                url = parts[-1].strip()
                if url.startswith("http"):
                    urls.append(url)
    except FileNotFoundError:
        logging.error(f"Arquivo {file_path} não encontrado.")
    return urls

def scrape_brands(
    brand_urls: List[str],
    output_excel_path: str = "produtos_capilares.xlsx",
    log_level: int = logging.INFO,
) -> pd.DataFrame:
    """
    Executa o scraping para uma lista de URLs base de marcas e salva em Excel.
    Retorna o DataFrame resultante.
    """
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    all_records: List[Dict[str, object]] = []

    for base_url in brand_urls:
        domain = get_domain(base_url)
        parser = BRAND_PARSERS.get(domain)

        if not parser:
            # Usa o parser genérico como fallback
            logging.info("Usando parser genérico para o domínio %s", domain)
            parser = GENERIC_PARSER

        logging.info("Coletando links de produtos para domínio %s em %s", domain, base_url)
        product_links = parser.get_product_links(session, base_url)
        logging.info("Domínio %s: %d produtos encontrados", domain, len(product_links))

        for idx, product_url in enumerate(product_links, start=1):
            logging.info("(%d/%d) Scrapando produto %s", idx, len(product_links), product_url)
            try:
                record = parser.parse_product(session, product_url)
                if record:
                    all_records.append(record)
            except Exception as e:
                logging.error(f"Erro ao processar {product_url}: {e}")
            polite_sleep()

    if not all_records:
        logging.warning("Nenhum produto foi coletado.")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    df.to_excel(output_excel_path, index=False)
    # Export to JSON for web dashboard
    json_path = output_excel_path.replace(".xlsx", ".json")
    df.to_json(json_path, orient="records", force_ascii=False)
    logging.info("Extração concluída. %d produtos salvos em %s e %s", len(df), output_excel_path, json_path)
    return df


if __name__ == "__main__":
    import sys
    import os

    # Se passar arquivo como argumento, usa ele. Senão, tenta brand_urls.txt
    urls_file = "brand_urls.txt"
    if len(sys.argv) > 1:
        urls_file = sys.argv[1]
    
    if os.path.exists(urls_file):
        print(f"Lendo URLs de {urls_file}...")
        brand_urls_list = load_brand_urls(urls_file)
    else:
        # Fallback para exemplo
        print("Arquivo de URLs não encontrado. Usando lista de exemplo.")
        brand_urls_list = [
            "https://www.stilohair.com.br/marca/1ka-hair.html",
            "https://alinebrasilcosmetics.com.br/loja/",
        ]
    
    # Para teste rápido, limitar a lista se for muito grande (opcional)
    # brand_urls_list = brand_urls_list[:2] 

    scrape_brands(brand_urls_list)

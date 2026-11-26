"""Collects news, academic papers and reports on AI & digital infrastructure in Africa.
Run daily by GitHub Actions. Results accumulate in resources.json (deduplicated by URL).
Edit the CONFIG section below to change sources, search queries and themes."""
import hashlib, html, json, os, re, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

# ───────────────────────── CONFIG ─────────────────────────
NOW = datetime.now(timezone.utc)
NEWS_LOOKBACK_DAYS = 30        # how far back each daily run looks for news
PAPER_LOOKBACK_DAYS = 730      # how far back to look for academic papers
KEEP_NEWS_DAYS = 548           # news older than this is pruned (papers/reports are kept)
OUTPUT, MANUAL = "resources.json", "manual_resources.json"
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")  # optional, makes OpenAlex API faster

# Major outlets, searched through Google News RSS (the "site:" filter picks the outlet).
# Paywalled outlets (Reuters, NYT, Financial Times, Bloomberg) are excluded.
OUTLETS = {"BBC": "bbc.com", "The Guardian": "theguardian.com", "Al Jazeera": "aljazeera.com",
           "CNN": "cnn.com", "Semafor": "semafor.com"}
NEWS_QUERIES = ['Africa "artificial intelligence"', 'Africa "data centre" OR "data center"',
                'Africa broadband OR "submarine cable" OR "fibre"', 'Africa "digital infrastructure"']

# Country-focused searches: a practical starter set of countries with substantial
# digital infrastructure, AI, and research activity across the continent. These
# are a coverage focus, not a strict publication-volume ranking.
COUNTRY_FOCUS = ("South Africa", "Nigeria", "Kenya", "Egypt", "Ghana",
                 "Ethiopia", "Rwanda", "Uganda", "Tanzania", "Morocco")
COUNTRY_NEWS_QUERY_GROUPS = (
    '("artificial intelligence" OR "AI governance" OR "AI policy" OR "AI adoption" OR "machine learning")',
    '("digital infrastructure" OR "digital public infrastructure" OR "digital connectivity" OR '
    '"broadband infrastructure" OR "internet access" OR "data infrastructure" OR "cloud computing" OR '
    '"technology cooperation" OR "digital learning" OR "digital skills" OR "digital inclusion")',
)
# OpenAlex uses a free-text search rather than Google-style Boolean query syntax.
# Pair focused topic searches with a country, then verify the country is mentioned.
COUNTRY_PAPER_QUERY_GROUPS = ("artificial intelligence", "digital infrastructure")

# Specialist outlets with their own RSS feeds (already tech-focused).
DIRECT_FEEDS = [("TechCabal", "https://techcabal.com/feed/", "News"),
                ("Rest of World", "https://restofworld.org/feed/", "News"),
                ("Africanews", "https://www.africanews.com/feed/rss", "News"),
                ("Disrupt Africa", "https://disrupt-africa.com/feed/", "News"),
                ("Brookings", "https://www.brookings.edu/feed/", "Report")]  # add think-tank feeds here

# Academic search (OpenAlex, free, no key needed)
PAPER_QUERIES = ["artificial intelligence Africa", "AI governance Africa", "data centres Africa",
                 "digital infrastructure Africa", "broadband connectivity Africa", "cloud computing Africa",
                 "machine learning African languages", "digital public infrastructure Africa"]

# Strict OpenAlex primary-field allowlist. OpenAlex does not have a field literally
# named "Digital technology", so Computer Science is its closest broad field proxy.
# Public policy/administration and political science may appear as fields or
# subfields; Social Sciences is included as requested. Missing/unmatched metadata
# fails closed so papers from unrelated or unclassified fields are excluded.
ALLOWED_PRIMARY_FIELDS = {
    "computer science",
    "social sciences",
    "political science and international relations",
    "political science",
    "public administration",
}

# Theme = first rule that matches. Order matters. Add/rename freely; the website updates itself.
THEME_RULES = [
    ("AI policy & governance", r"regulat|policy|strateg|governance|ethic|law\b|legislat|framework|AU |african union|data protection|privacy"),
    ("Data centres & cloud", r"data cent|datacent|cloud|hyperscal|colocation|aws|azure|google cloud|equinix|teraco|raxio"),
    ("Connectivity & telecoms", r"broadband|fib(er|re)|submarine|subsea|cable|5g|4g|spectrum|telecom|satellite|starlink|internet|mobile network|connectivity"),
    ("Energy & compute", r"energy|power|electric|grid|solar|gpu|chip|semiconductor|compute"),
    ("Digital public infrastructure", r"digital id|e-government|egovernment|payment|mobile money|fintech|public infrastructure|digital public"),
    ("Startups & investment", r"startup|invest|fund|venture|raise|acqui|unicorn|billion|million"),
    ("Skills & research", r"skill|education|universit|research|train|talent|language|dataset|lab\b"),
    ("AI applications", r"health|agricult|farm|climate|machine learning|generative|chatbot|llm|\bai\b|artificial intelligence"),
]
DEFAULT_THEME = "General"

COUNTRIES = {
    "South Africa": r"south africa|johannesburg|cape town|pretoria", "Nigeria": r"nigeria|lagos|abuja",
    "Kenya": r"kenya|nairobi", "Egypt": r"egypt|cairo", "Ethiopia": r"ethiopia|addis", "Ghana": r"ghana|accra",
    "Rwanda": r"rwanda|kigali", "Morocco": r"morocc|rabat|casablanca", "Tanzania": r"tanzania|dar es salaam",
    "Uganda": r"uganda|kampala", "Senegal": r"senegal|dakar", "Tunisia": r"tunisia|tunis",
    "Algeria": r"algeria|algiers", "Zambia": r"zambia|lusaka", "Zimbabwe": r"zimbabwe|harare",
    "Mozambique": r"mozambique|maputo", "Angola": r"angola|luanda", "DRC": r"\bdrc\b|congo|kinshasa",
    "Côte d'Ivoire": r"ivory coast|côte d.ivoire|abidjan", "Cameroon": r"cameroon", "Namibia": r"namibia",
    "Botswana": r"botswana", "Mauritius": r"mauritius", "Malawi": r"malawi", "Sudan": r"\bsudan\b|khartoum",
    "Somalia": r"somalia", "Mali": r"\bmali\b", "Libya": r"libya", "Djibouti": r"djibouti",
}
AFRICA_RE = re.compile(r"africa|" + "|".join(COUNTRIES.values()) + r"|sahel|sahara", re.I)
RELEVANT_RE = re.compile(r"\bAI\b|artificial intelligence|AI governance|AI policy|AI adoption|machine learning|generative|\bLLMs?\b|data cent|cloud|hyperscal|"
    r"broadband|fib(er|re)|submarine|subsea|\b[45]G\b|spectrum|telecom|satellite|starlink|internet|connectivity|"
    r"digital|technology cooperation|semiconductor|\bGPUs?\b|compute|fintech|mobile money|cyber|digital learning|digital skills|digital inclusion", re.I)
STOP = set("africa african the and for with from that this into after over amid says said have been its was are has new will than more".split())
# ──────────────────────────────────────────────────────────

def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AIAfricaDatabase/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  ! {url[:90]} -> {e}")

def clean(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()

def primary_topic_in_scope(work):
    """Keep papers only when OpenAlex's primary topic is in an allowed field."""
    primary_topic = work.get("primary_topic") or {}
    field = (primary_topic.get("field") or {}).get("display_name", "")
    return field.strip().casefold() in ALLOWED_PRIMARY_FIELDS

def parse_date(s):
    if not s: return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try: d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception: return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)

def theme_of(text):
    for name, pat in THEME_RULES:
        if re.search(pat, text, re.I): return name
    return DEFAULT_THEME

def country_of(text):
    hits = [c for c, p in COUNTRIES.items() if re.search(p, text, re.I)]
    return hits[0] if len(hits) == 1 else ("Multiple countries" if hits else "Pan-African")

def keywords_of(title):
    w = re.sub(r"[^a-z\s]", " ", title.lower()).split()
    return [x for x in w if len(x) > 3 and x not in STOP][:4]

def make(title, desc, url, date, rtype, source, authors=""):
    text = f"{title} {desc}"
    return {"id": hashlib.sha1(url.encode()).hexdigest()[:12], "title": title, "desc": desc[:300],
            "url": url, "date": date.strftime("%Y-%m-%d"), "type": rtype, "source": source,
            "theme": theme_of(text), "country": country_of(text), "authors": authors,
            "keywords": keywords_of(title)}

def rss_items(content):
    try: root = ET.fromstring(content)
    except Exception: return
    for it in root.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"): continue
        f = {c.tag.split("}")[-1]: c for c in it}
        link = f["link"].text if "link" in f and f["link"].text else (f["link"].get("href") if "link" in f else "")
        txt = lambda k: clean(f[k].text) if k in f else ""
        yield (txt("title"), txt("description") or txt("summary"), (link or "").strip(),
               txt("pubDate") or txt("published") or txt("updated"), f.get("source"))

def collect_news():
    out, cutoff = [], NOW - timedelta(days=NEWS_LOOKBACK_DAYS)
    for outlet, domain in OUTLETS.items():
        queries = [(q, None) for q in NEWS_QUERIES]
        queries.extend((f"{group} AND ({country})", country)
                       for country in COUNTRY_FOCUS for group in COUNTRY_NEWS_QUERY_GROUPS)
        for q, country in queries:
            qs = urllib.parse.urlencode({"q": f"{q} site:{domain} when:{NEWS_LOOKBACK_DAYS}d", "hl": "en", "gl": "US", "ceid": "US:en"})
            data = get(f"https://news.google.com/rss/search?{qs}")
            for title, desc, link, pub, _ in rss_items(data or b""):
                title = re.sub(r"\s+-\s+[^-]+$", "", title)  # drop " - Reuters" suffix
                d = parse_date(pub)
                geography_matches = (AFRICA_RE.search(title) if country is None
                                     else re.search(COUNTRIES[country], title, re.I))
                if d and d >= cutoff and link and geography_matches and RELEVANT_RE.search(title):
                    out.append(make(title, "", link, d, "News", outlet))
    for name, url, rtype in DIRECT_FEEDS:
        for title, desc, link, pub, _ in rss_items(get(url) or b""):
            d, text = parse_date(pub), f"{title} {desc}"
            if d and d >= NOW - timedelta(days=NEWS_LOOKBACK_DAYS) and link and AFRICA_RE.search(text) and RELEVANT_RE.search(text):
                out.append(make(title, desc, link, d, rtype, name))
    return out

def abstract_of(inv):
    pos = {i: w for w, ix in (inv or {}).items() for i in ix}
    return " ".join(pos[i] for i in sorted(pos))

def collect_papers():
    out, since = [], (NOW - timedelta(days=PAPER_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    queries = [(q, None) for q in PAPER_QUERIES]
    queries.extend((f"{topic} {country}", country)
                   for country in COUNTRY_FOCUS for topic in COUNTRY_PAPER_QUERY_GROUPS)
    for q, country in queries:
        params = {"search": q, "filter": f"from_publication_date:{since},type:article|preprint|book-chapter",
                  "sort": "relevance_score:desc", "per-page": 25}
        if CONTACT_EMAIL: params["mailto"] = CONTACT_EMAIL
        data = get("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
        for w in (json.loads(data).get("results", []) if data else []):
            title, abs_ = clean(w.get("title")), clean(abstract_of(w.get("abstract_inverted_index")))
            text = f"{title} {abs_}"
            loc = w.get("primary_location") or {}
            url = w.get("doi") or loc.get("landing_page_url") or w.get("id")
            d = parse_date(w.get("publication_date"))
            geography_matches = (AFRICA_RE.search(text) if country is None
                                 else re.search(COUNTRIES[country], text, re.I))
            if not (title and url and d and geography_matches and RELEVANT_RE.search(text)
                    and primary_topic_in_scope(w)): continue
            authors = ", ".join(a["author"]["display_name"] for a in w.get("authorships", [])[:4])
            if len(w.get("authorships", [])) > 4: authors += " et al."
            out.append(make(title, abs_, url, d, "Academic paper", (loc.get("source") or {}).get("display_name") or "OpenAlex", authors))
    return out

def load(path, default):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def main():
    existing = {r["id"]: r for r in load(OUTPUT, {}).get("resources", [])}
    n_before = len(existing)
    new = collect_news() + collect_papers()
    for r in new: existing.setdefault(r["id"], r)
    for m in load(MANUAL, []):  # hand-curated entries: title, url, type, source, date (YYYY-MM-DD); rest is auto-filled
        d = parse_date(m.get("date", "")) or NOW
        r = make(m["title"], m.get("desc", ""), m["url"], d, m.get("type", "Report"), m.get("source", ""), m.get("authors", ""))
        r.update({k: m[k] for k in ("theme", "country") if k in m})
        existing[r["id"]] = r  # manual entries always win
    added = len(existing) - n_before
    cutoff = (NOW - timedelta(days=KEEP_NEWS_DAYS)).strftime("%Y-%m-%d")
    res = [r for r in existing.values() if r["type"] != "News" or r["date"] >= cutoff]
    res.sort(key=lambda r: r["date"], reverse=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"updated": NOW.strftime("%Y-%m-%d %H:%M UTC"), "count": len(res), "resources": res}, f, ensure_ascii=False, indent=1)
    print(f"Done: {added} new, {len(res)} total.")

if __name__ == "__main__":
    main()

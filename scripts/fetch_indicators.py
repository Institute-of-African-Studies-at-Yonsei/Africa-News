"""
아프리카 디지털·AI 격차 정형 지표 수집 스크립트
- 출처: World Bank Indicators API (무료, 키 불필요)
- 출력: 연구계획서 DB 스키마(그림 6-1)를 따르는 4개 테이블
    data/country.json   (country_table)
    data/digitalx.json  (digitalx_table)
    data/aidivide.json  (aidivide_table)
    data/source.json    (source_table)
  + 연구용 CSV 사본: data/csv/*.csv
- GitHub Actions에서 매월 자동 실행 (.github/workflows/indicators.yml)
"""
import csv
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")
START_YEAR = 2000
END_YEAR = datetime.now(KST).year
API = "https://api.worldbank.org/v2"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# ── 국가 기본정보 (아프리카연합 54개 회원국 중 UN 회원 54개국, AU 지역 구분) ──
COUNTRIES = {
    # 북부
    "DZA": ("알제리", "North"), "EGY": ("이집트", "North"), "LBY": ("리비아", "North"),
    "MRT": ("모리타니", "North"), "MAR": ("모로코", "North"), "TUN": ("튀니지", "North"),
    # 서부
    "BEN": ("베냉", "West"), "BFA": ("부르키나파소", "West"), "CPV": ("카보베르데", "West"),
    "CIV": ("코트디부아르", "West"), "GMB": ("감비아", "West"), "GHA": ("가나", "West"),
    "GIN": ("기니", "West"), "GNB": ("기니비사우", "West"), "LBR": ("라이베리아", "West"),
    "MLI": ("말리", "West"), "NER": ("니제르", "West"), "NGA": ("나이지리아", "West"),
    "SEN": ("세네갈", "West"), "SLE": ("시에라리온", "West"), "TGO": ("토고", "West"),
    # 중부
    "BDI": ("부룬디", "Central"), "CMR": ("카메룬", "Central"), "CAF": ("중앙아프리카공화국", "Central"),
    "TCD": ("차드", "Central"), "COG": ("콩고공화국", "Central"), "COD": ("콩고민주공화국", "Central"),
    "GNQ": ("적도기니", "Central"), "GAB": ("가봉", "Central"), "STP": ("상투메프린시페", "Central"),
    # 동부
    "COM": ("코모로", "East"), "DJI": ("지부티", "East"), "ERI": ("에리트레아", "East"),
    "ETH": ("에티오피아", "East"), "KEN": ("케냐", "East"), "MDG": ("마다가스카르", "East"),
    "MUS": ("모리셔스", "East"), "RWA": ("르완다", "East"), "SYC": ("세이셸", "East"),
    "SOM": ("소말리아", "East"), "SSD": ("남수단", "East"), "SDN": ("수단", "East"),
    "TZA": ("탄자니아", "East"), "UGA": ("우간다", "East"),
    # 남부
    "AGO": ("앙골라", "Southern"), "BWA": ("보츠와나", "Southern"), "SWZ": ("에스와티니", "Southern"),
    "LSO": ("레소토", "Southern"), "MWI": ("말라위", "Southern"), "MOZ": ("모잠비크", "Southern"),
    "NAM": ("나미비아", "Southern"), "ZAF": ("남아프리카공화국", "Southern"),
    "ZMB": ("잠비아", "Southern"), "ZWE": ("짐바브웨", "Southern"),
}

# ── 지표 목록 ──
# table: digitalx(디지털 전환) / aidivide(AI 격차)
# category: digitalx는 Indicator_Category, aidivide는 AI_Dimension
# 새 지표를 추가하려면 World Bank 지표 코드로 한 줄만 추가하면 됨
INDICATORS = [
    # 디지털 전환 - 인프라·접근성
    {"code": "IT.NET.USER.ZS", "table": "digitalx", "category": "접근성",
     "name": "인터넷 이용자 비율", "unit": "% of population", "source": "ITU"},
    {"code": "IT.CEL.SETS.P2", "table": "digitalx", "category": "인프라",
     "name": "이동통신 가입 건수", "unit": "per 100 people", "source": "ITU"},
    {"code": "IT.NET.BBND.P2", "table": "digitalx", "category": "인프라",
     "name": "유선 초고속인터넷 가입 건수", "unit": "per 100 people", "source": "ITU"},
    {"code": "EG.ELC.ACCS.ZS", "table": "digitalx", "category": "인프라",
     "name": "전력 접근률", "unit": "% of population", "source": "WB_WDI"},
    # 디지털 전환 - 디지털 금융 (Global Findex)
    {"code": "FX.OWN.TOTL.ZS", "table": "digitalx", "category": "디지털 금융",
     "name": "금융계좌 보유율", "unit": "% of age 15+", "source": "WB_FINDEX"},
    # AI 격차 - 인적 자본·연구·산업 기반
    {"code": "SE.TER.ENRR", "table": "aidivide", "category": "인적 자본",
     "name": "고등교육 총취학률", "unit": "% gross", "source": "WB_WDI"},
    {"code": "GB.XPD.RSDV.GD.ZS", "table": "aidivide", "category": "연구개발",
     "name": "R&D 지출", "unit": "% of GDP", "source": "WB_WDI"},
    {"code": "IT.NET.SECR.P6", "table": "aidivide", "category": "디지털 산업 기반",
     "name": "보안 인터넷 서버 수", "unit": "per 1 million people", "source": "WB_WDI"},
    {"code": "BX.GSR.CCIS.ZS", "table": "aidivide", "category": "디지털 산업 기반",
     "name": "ICT 서비스 수출 비중", "unit": "% of service exports", "source": "WB_WDI"},
]

# ── 자료 출처 (source_table) ──
SOURCES = {
    "WB_WDI": {"Source_Name": "World Bank World Development Indicators",
               "Source_Type": "국제기구 통계",
               "Source_URL": "https://databank.worldbank.org/source/world-development-indicators",
               "License": "CC BY 4.0",
               "License_URL": "https://data.worldbank.org/summary-terms-of-use"},
    "ITU": {"Source_Name": "ITU World Telecommunication/ICT Indicators (via World Bank WDI)",
            "Source_Type": "국제기구 통계",
            "Source_URL": "https://datahub.itu.int/",
            "License": "CC BY 4.0 (World Bank WDI 제공 조건, 원 출처 ITU)",
            "License_URL": "https://data.worldbank.org/summary-terms-of-use"},
    "WB_FINDEX": {"Source_Name": "World Bank Global Findex (via World Bank WDI)",
                  "Source_Type": "국제기구 설문 통계",
                  "Source_URL": "https://www.worldbank.org/en/publication/globalfindex",
                  "License": "CC BY 4.0",
                  "License_URL": "https://data.worldbank.org/summary-terms-of-use"},
}


def get_json(url, retries=4):
    """World Bank API 호출 (실패 시 재시도)"""
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "IAS-Yonsei-AfricaDB/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"  ! 재시도 {i + 1}/{retries}: {e}")
            time.sleep(3 * (i + 1))
    return None


def fetch_countries():
    """국가 메타데이터(소득그룹) 수집 → country_table"""
    codes = ";".join(COUNTRIES)
    data = get_json(f"{API}/country/{codes}?format=json&per_page=100")
    meta = {}
    if data and len(data) > 1 and data[1]:
        for c in data[1]:
            meta[c["id"]] = {"name_en": c["name"], "income": c["incomeLevel"]["value"]}
    rows = []
    for iso, (ko, region) in COUNTRIES.items():
        m = meta.get(iso, {})
        rows.append({
            "Country_ID": iso,
            "Country_Name": ko,
            "Country_Name_EN": m.get("name_en", ""),
            "Region": region,
            "Income_Group": m.get("income", ""),
        })
    return rows


def fetch_indicator(ind):
    """지표 하나를 54개국 전체 연도로 수집"""
    codes = ";".join(COUNTRIES)
    url = (f"{API}/country/{codes}/indicator/{ind['code']}"
           f"?format=json&date={START_YEAR}:{END_YEAR}&per_page=20000")
    data = get_json(url)
    if not data or len(data) < 2 or data[1] is None:
        return None
    rows = []
    for d in data[1]:
        if d.get("value") is None:
            continue  # 결측치는 저장하지 않음
        iso = d.get("countryiso3code")
        if iso not in COUNTRIES:
            continue
        rows.append({
            "Country_ID": iso,
            "Year": int(d["date"]),
            "Indicator_Code": ind["code"],
            "Indicator_Name": ind["name"],
            "Value": round(float(d["value"]), 3),
            "Unit": ind["unit"],
            "Source_ID": ind["source"],
        })
    return rows


def load_existing(name):
    path = os.path.join(OUT, f"{name}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("rows", [])
    return []


def save(name, rows, extra=None):
    os.makedirs(os.path.join(OUT, "csv"), exist_ok=True)
    payload = {"table": f"{name}_table", "updated": TODAY, "count": len(rows), "rows": rows}
    if extra:
        payload.update(extra)
    with open(os.path.join(OUT, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    if rows:
        with open(os.path.join(OUT, "csv", f"{name}.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"✔ {name}: {len(rows)} rows")


def main():
    print(f"== 지표 수집 시작 {TODAY} ==")
    countries = fetch_countries()

    tables = {"digitalx": [], "aidivide": []}
    old = {t: load_existing(t) for t in tables}
    status = {}

    for ind in INDICATORS:
        print(f"- {ind['code']} {ind['name']}")
        rows = fetch_indicator(ind)
        if rows is None:
            # API 실패 시 이전 데이터를 그대로 유지 (데이터가 지워지지 않도록)
            kept = [r for r in old[ind["table"]] if r.get("Indicator_Code") == ind["code"]]
            tables[ind["table"]].extend(kept)
            status[ind["code"]] = "수집 실패 - 이전 데이터 유지"
            print(f"  ✘ 실패, 이전 데이터 {len(kept)}건 유지")
            continue
        for r in rows:
            r["Indicator_Category" if ind["table"] == "digitalx" else "AI_Dimension"] = ind["category"]
        tables[ind["table"]].extend(rows)
        status[ind["code"]] = "정상"
        print(f"  ✔ {len(rows)}건")

    # 컬럼 순서를 스키마에 맞게 정리
    order = {
        "digitalx": ["Country_ID", "Year", "Indicator_Category", "Indicator_Code",
                     "Indicator_Name", "Value", "Unit", "Source_ID"],
        "aidivide": ["Country_ID", "Year", "AI_Dimension", "Indicator_Code",
                     "Indicator_Name", "Value", "Unit", "Source_ID"],
    }
    for t, rows in tables.items():
        rows = [{k: r[k] for k in order[t]} for r in rows]
        rows.sort(key=lambda r: (r["Indicator_Code"], r["Country_ID"], r["Year"]))
        tables[t] = rows

    source_rows = [{
        "Source_ID": sid,
        **s,
        "Collection_Date": TODAY,
        "Update_Date": TODAY,
        "Verification_Status": "자동 수집",
        "Reliability_Level": "High",
    } for sid, s in SOURCES.items()]

    indicator_meta = [{k: i[k] for k in ("code", "table", "category", "name", "unit", "source")}
                      for i in INDICATORS]

    save("country", countries)
    save("digitalx", tables["digitalx"])
    save("aidivide", tables["aidivide"])
    save("source", source_rows, {"indicators": indicator_meta, "fetch_status": status})
    print("== 완료 ==")


if __name__ == "__main__":
    main()

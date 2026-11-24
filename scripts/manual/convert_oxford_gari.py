"""
Oxford Insights Government AI Readiness Index 엑셀 → data/manual/ 표준 CSV 변환 (연 1회 수동 실행)

사용법:
  1. oxfordinsights.com에서 해당 연도 데이터 엑셀을 내려받는다.
  2. pip install openpyxl   (이 스크립트만 외부 패키지 사용. GitHub Actions에서는 실행하지 않음)
  3. python scripts/manual/convert_oxford_gari.py 내려받은파일.xlsx 2025
  4. 생성된 data/manual/oxford_gari_<연도>.csv 를 저장소에 올린다.
     매월 자동 수집(fetch_indicators.py) 때 aidivide_table에 합쳐진다.

라이선스: CC BY-SA 4.0 (Oxford Insights). 가공 데이터도 같은 조건으로 공개.
주의: 2025년판부터 지표 체계가 바뀌어(6개 Pillar, 14개 Dimension) 이전 연도와 점수를 직접 비교하지 않는다.
"""
import csv
import os
import sys

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "..", "data", "manual")

# 엑셀의 국가 표기 → ISO3 (아프리카 54개국)
AFRICA = {
    "Algeria": "DZA", "Angola": "AGO", "Benin": "BEN", "Botswana": "BWA", "Burkina Faso": "BFA",
    "Burundi": "BDI", "Cabo Verde": "CPV", "Cameroon": "CMR", "Central African Republic": "CAF",
    "Chad": "TCD", "Comoros": "COM", "Congo": "COG", "Côte D'Ivoire": "CIV",
    "Democratic Republic of the Congo": "COD", "Djibouti": "DJI", "Egypt": "EGY",
    "Equatorial Guinea": "GNQ", "Eritrea": "ERI", "Eswatini": "SWZ", "Ethiopia": "ETH",
    "Gabon": "GAB", "Gambia (Republic of The)": "GMB", "Ghana": "GHA", "Guinea": "GIN",
    "Guinea Bissau": "GNB", "Kenya": "KEN", "Lesotho": "LSO", "Liberia": "LBR", "Libya": "LBY",
    "Madagascar": "MDG", "Malawi": "MWI", "Mali": "MLI", "Mauritania": "MRT", "Mauritius": "MUS",
    "Morocco": "MAR", "Mozambique": "MOZ", "Namibia": "NAM", "Niger": "NER", "Nigeria": "NGA",
    "Rwanda": "RWA", "Sao Tome and Principe": "STP", "Senegal": "SEN", "Seychelles": "SYC",
    "Sierra Leone": "SLE", "Somalia": "SOM", "South Africa": "ZAF", "South Sudan": "SSD",
    "Sudan": "SDN", "Togo": "TGO", "Tunisia": "TUN", "Uganda": "UGA",
    "United Republic of Tanzania": "TZA", "Zambia": "ZMB", "Zimbabwe": "ZWE",
}

# 엑셀 열 이름 → (지표 코드, 한글 지표명, 구분)
COLUMNS = {
    "Total Score": ("OXF.GARI.TOTAL", "정부 AI 준비도 지수 (종합)", "total"),
    "Global Rank": ("OXF.GARI.RANK", "정부 AI 준비도 세계 순위 (195개국 중)", "rank"),
    "Policy Capacity": ("OXF.GARI.P.POLICY", "AI 준비도: 정책 역량", "pillar"),
    "AI Infrastructure": ("OXF.GARI.P.INFRA", "AI 준비도: AI 인프라", "pillar"),
    "Governance": ("OXF.GARI.P.GOV", "AI 준비도: 거버넌스", "pillar"),
    "Public Sector Adoption": ("OXF.GARI.P.PUBLIC", "AI 준비도: 공공부문 도입", "pillar"),
    "Development & Diffusion": ("OXF.GARI.P.DEV", "AI 준비도: 개발·확산", "pillar"),
    "Resilience": ("OXF.GARI.P.RESIL", "AI 준비도: 회복력", "pillar"),
    "Policy vision": ("OXF.GARI.D.VISION", "AI 준비도 세부: 정책 비전", "dimension"),
    "Policy commitment": ("OXF.GARI.D.COMMIT", "AI 준비도 세부: 정책 이행 의지", "dimension"),
    "Compute capacity": ("OXF.GARI.D.COMPUTE", "AI 준비도 세부: 컴퓨팅 역량", "dimension"),
    "Enabling technical infrastructure": ("OXF.GARI.D.TECHINFRA", "AI 준비도 세부: 기반 기술 인프라", "dimension"),
    "Data quality": ("OXF.GARI.D.DATA", "AI 준비도 세부: 데이터 품질", "dimension"),
    "Governance principles": ("OXF.GARI.D.PRINCIPLES", "AI 준비도 세부: 거버넌스 원칙", "dimension"),
    "Regulatory compliance": ("OXF.GARI.D.REGUL", "AI 준비도 세부: 규제 준수", "dimension"),
    "Government digital policy": ("OXF.GARI.D.DIGPOLICY", "AI 준비도 세부: 정부 디지털 정책", "dimension"),
    "e-Government delivery": ("OXF.GARI.D.EGOV", "AI 준비도 세부: 전자정부 서비스 제공", "dimension"),
    "Human capital": ("OXF.GARI.D.HUMAN", "AI 준비도 세부: 인적 자본", "dimension"),
    "AI sector maturity": ("OXF.GARI.D.SECTOR", "AI 준비도 세부: AI 산업 성숙도", "dimension"),
    "AI technology diffusion": ("OXF.GARI.D.DIFFUSION", "AI 준비도 세부: AI 기술 확산", "dimension"),
    "Societal transition": ("OXF.GARI.D.SOCIETY", "AI 준비도 세부: 사회적 전환", "dimension"),
    "Safety and security": ("OXF.GARI.D.SAFETY", "AI 준비도 세부: 안전·보안", "dimension"),
}


def main(path, year):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Dimensions-Pillars"]
    rows = list(ws.iter_rows(values_only=True))
    header_idx = next(i for i, r in enumerate(rows) if r and "Country" in r and "Total Score" in r)
    header = rows[header_idx]
    col = {name: i for i, name in enumerate(header) if name}
    col["Global Rank"] = col["Ranking"]

    out, found = [], set()
    for r in rows[header_idx + 1:]:
        name = r[col["Country"]] if len(r) > col["Country"] else None
        iso = AFRICA.get(name)
        if not iso:
            continue
        found.add(iso)
        for xl_name, (code, ko, kind) in COLUMNS.items():
            v = r[col[xl_name]]
            if v is None:
                continue
            out.append({
                "Country_ID": iso, "Year": year, "Indicator_Code": code, "Indicator_Name": ko,
                "Value": int(v) if kind == "rank" else round(float(v), 2),
                "Unit": "rank (1 = highest)" if kind == "rank" else "score (0–100)",
                "Source_ID": "OXF_GARI", "Level": kind,
            })
    missing = set(AFRICA.values()) - found
    if missing:
        sys.exit(f"엑셀에서 찾지 못한 국가: {sorted(missing)} → AFRICA 표기를 엑셀에 맞게 고칠 것")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "oxford_gari_meta.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Indicator_Code", "Name_EN", "Definition_EN"])
        for xl_name, (code, ko, kind) in COLUMNS.items():
            if kind == "total":
                name_en = "Government AI Readiness Index: total score"
                d = ("Overall score (0-100) of the Oxford Insights Government AI Readiness Index, which assesses how "
                     "ready governments are to implement AI in the delivery of public services. The 2025 edition "
                     "examines 69 indicators across 14 dimensions within six pillars: Policy Capacity, Governance, "
                     "AI Infrastructure, Public Sector Adoption, Development & Diffusion and Resilience.")
            elif kind == "rank":
                name_en = "Government AI Readiness Index: global rank"
                d = "Global rank of the government in the Oxford Insights Government AI Readiness Index (1 = highest)."
            elif kind == "pillar":
                name_en = f"Government AI Readiness Index pillar: {xl_name}"
                d = f"Pillar score (0-100) for '{xl_name}' in the Oxford Insights Government AI Readiness Index."
            else:
                name_en = f"Government AI Readiness Index dimension: {xl_name}"
                d = f"Dimension score (0-100) for '{xl_name}' in the Oxford Insights Government AI Readiness Index."
            w.writerow([code, name_en, d])
    dest = os.path.join(OUT_DIR, f"oxford_gari_{year}.csv")
    with open(dest, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"✔ {dest}: {len(found)}개국, {len(out)}행")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("사용법: python scripts/manual/convert_oxford_gari.py <엑셀파일> <연도>")
    main(sys.argv[1], int(sys.argv[2]))

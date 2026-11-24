"""
ITU ICT Development Index(IDI) 데이터셋 엑셀 → data/manual/itu_idi.csv (연 1회 수동 실행)

사용법:
  1. ITU IDI 웹사이트(또는 DataHub IDI 대시보드)에서 최신판 데이터셋 엑셀을 내려받는다.
     최신판 파일에 이전 판(2023~) 시트가 모두 들어 있으므로 최신 파일 하나면 된다.
  2. pip install openpyxl   (이 스크립트만 외부 패키지 사용. GitHub Actions에서는 실행하지 않음)
  3. python scripts/manual/convert_itu_idi.py IDI2026dataset.xlsx
  4. 생성된 data/manual/itu_idi.csv 를 올리고 Actions에서 Monthly Africa Indicators Update 실행.

- 2023년판부터 새 방법론(10개 지표, 2개 축). 2023~현재 판은 서로 비교 가능.
- Year는 '판(edition)' 연도. 각 판의 지표값은 대체로 2년 전 자료다 (예: 2026년판 = 2024년 자료).
- 라이선스: ITU DataHub 이용 조건(CC BY-NC-SA 3.0 IGO). 아프리카 값의 출처는 ITU 추정·각국 규제기관·World Bank WDI.
"""
import csv
import os
import re
import sys

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "data", "manual", "itu_idi.csv")

AFRICA = {
    "DZA", "EGY", "LBY", "MRT", "MAR", "TUN", "BEN", "BFA", "CPV", "CIV", "GMB", "GHA", "GIN", "GNB",
    "LBR", "MLI", "NER", "NGA", "SEN", "SLE", "TGO", "BDI", "CMR", "CAF", "TCD", "COG", "COD", "GNQ",
    "GAB", "STP", "COM", "DJI", "ERI", "ETH", "KEN", "MDG", "MUS", "RWA", "SYC", "SOM", "SSD", "SDN",
    "TZA", "UGA", "AGO", "BWA", "SWZ", "LSO", "MWI", "MOZ", "NAM", "ZAF", "ZMB", "ZWE",
}

# 열 머리글(앞부분 일치) → (지표 코드, 한글 이름, 화면 표시)
SCORES = {
    "ICT Development Index": ("ITU.IDI", "ICT 발전지수 (IDI 종합)", "main"),
    "Universal Connectivity Pillar": ("ITU.IDI.UNIVERSAL", "IDI: 보편적 연결성", "main"),
    "Meaningful Connectivity Pillar": ("ITU.IDI.MEANINGFUL", "IDI: 의미 있는 연결성", "main"),
}

# 영문 이름·정의 (IDI 2026 보고서 방법론 기준)
META_EN = {
    "ITU.IDI": ("ICT Development Index (IDI) score",
                "Composite index (0-100) published by ITU measuring universal and meaningful connectivity. "
                "It combines 10 indicators organized in two pillars of equal weight: Universal connectivity and "
                "Meaningful connectivity. New methodology since the 2023 edition; the year is the edition year "
                "and indicator values generally refer to two years earlier."),
    "ITU.IDI.UNIVERSAL": ("IDI Universal connectivity pillar score",
                          "Pillar score (0-100) of the ITU ICT Development Index: average of normalized scores for "
                          "individuals using the Internet, households with Internet access at home, and active "
                          "mobile-broadband subscriptions per 100 inhabitants."),
    "ITU.IDI.MEANINGFUL": ("IDI Meaningful connectivity pillar score",
                           "Pillar score (0-100) of the ITU ICT Development Index: average of normalized scores for "
                           "3G and 4G/LTE network coverage, mobile- and fixed-broadband Internet traffic per "
                           "subscription, mobile data and voice and fixed-broadband basket prices, and individuals "
                           "owning a mobile phone."),
}


def main(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for sheet in wb.sheetnames:
        m = re.match(r"IDI (\d{4}) Data", sheet)
        if not m:
            continue
        edition = int(m.group(1))
        rows = list(wb[sheet].iter_rows(values_only=True))
        hi = next(i for i, r in enumerate(rows)
                  if r and any(isinstance(c, str) and c.strip().startswith("ICT Development Index") for c in r))
        header = rows[hi]
        cols = {}
        for key, spec in SCORES.items():
            # 같은 이름이 여러 번 나오면 맨 뒤(종합 점수 영역)를 쓴다
            idx = [j for j, c in enumerate(header) if isinstance(c, str) and c.strip().startswith(key)]
            cols[key] = idx[-1]
        for r in rows[hi + 1:]:
            if not r or r[0] not in AFRICA:
                continue
            for key, (code, name, level) in SCORES.items():
                v = r[cols[key]]
                if not isinstance(v, (int, float)):
                    continue
                out.append({"Country_ID": r[0], "Year": edition, "Indicator_Code": code, "Indicator_Name": name,
                            "Value": round(float(v), 2), "Unit": "score (0–100)", "Source_ID": "ITU_IDI",
                            "Category": "ICT 발전지수", "Level": level})

    out.sort(key=lambda o: (o["Indicator_Code"], o["Country_ID"], o["Year"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    with open(OUT.replace(".csv", "_meta.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Indicator_Code", "Name_EN", "Definition_EN"])
        for code, (name_en, definition) in sorted(META_EN.items()):
            w.writerow([code, name_en, definition])
    print(f"✔ {OUT}: {len(out)}행")
    for y in sorted({o["Year"] for o in out}):
        print(f"  {y}년판: {len({o['Country_ID'] for o in out if o['Year'] == y})}개국")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python scripts/manual/convert_itu_idi.py <IDI 데이터셋 엑셀>")
    main(sys.argv[1])

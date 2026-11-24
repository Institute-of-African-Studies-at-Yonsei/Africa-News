"""
ITU DataHub 내려받기 CSV → data/manual/itu_datahub.csv 표준 CSV 변환 (수동 실행, 표준 라이브러리만 사용)

사용법:
  1. https://datahub.itu.int/query 에서 아래 SERIES의 지표를 고르고,
     국가는 Africa + Arab States(북아프리카 포함)를 선택해 CSV로 내려받는다.
  2. python scripts/manual/convert_itu_datahub.py 내려받은파일.csv
  3. 생성된 data/manual/itu_datahub.csv 를 저장소에 올린다 (원본 CSV는 올리지 않는다).
     매월 자동 수집(fetch_indicators.py) 때 digitalx_table에 합쳐진다.

라이선스: ITU DataHub, CC BY-NC-SA 3.0 IGO (비상업·출처 표시·동일 조건).
출처 열(Source)이 ITU 추정치 또는 각국 정부·규제기관인 자료만 사용한다 (상업 제3자 자료 제외).
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "data", "manual", "itu_datahub.csv")

AFRICA = {
    "DZA", "EGY", "LBY", "MRT", "MAR", "TUN", "BEN", "BFA", "CPV", "CIV", "GMB", "GHA", "GIN", "GNB",
    "LBR", "MLI", "NER", "NGA", "SEN", "SLE", "TGO", "BDI", "CMR", "CAF", "TCD", "COG", "COD", "GNQ",
    "GAB", "STP", "COM", "DJI", "ERI", "ETH", "KEN", "MDG", "MUS", "RWA", "SYC", "SOM", "SSD", "SDN",
    "TZA", "UGA", "AGO", "BWA", "SWZ", "LSO", "MWI", "MOZ", "NAM", "ZAF", "ZMB", "ZWE",
}

# ITU SeriesCode → (우리 지표 코드, 한글 지표명, 단위, 분류, 화면 표시 여부)
SERIES = {
    "xHH6_IDI": ("ITU.HH.INTERNET", "가정 내 인터넷 접속 가구 비율", "% of households", "접근성", "main"),
    "xHH18_IDI": ("ITU.MOBILE.OWN", "휴대전화 보유율", "% of individuals", "접근성", "main"),
    "HHU271own-%_POP-FEMALE-": ("ITU.MOBILE.OWN.FE", "휴대전화 보유율 (여성)", "% of individuals", "접근성", "main"),
    "HHU271own-%_POP-MALE-": ("ITU.MOBILE.OWN.MA", "휴대전화 보유율 (남성)", "% of individuals", "접근성", "main"),
    "i911mw": ("ITU.MBB.SUBS", "모바일 브로드밴드 가입 건수", "per 100 people", "인프라", "main"),
    "i271G": ("ITU.COV.3G", "3G 커버리지 인구 비율", "% of population", "인프라", "main"),
    "i271GA": ("ITU.COV.4G", "4G/LTE 커버리지 인구 비율", "% of population", "인프라", "main"),
    "i271G5_pop": ("ITU.COV.5G", "5G 커버리지 인구 비율", "% of population", "인프라", "main"),
}


def main(path):
    best = {}  # (code, iso, year) -> row ; 세부 구분 없는 값(빈칸) 우선, 다음 'Total'
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            spec = SERIES.get(r["SeriesCode"])
            iso = r["AreaCode"]
            if not spec or iso not in AFRICA or not r["Value"]:
                continue
            grp = r["DisaggregationGroup"]
            if grp not in ("", "Total", "Gender"):
                continue
            key = (spec[0], iso, int(r["Year"]))
            rank = 0 if grp in ("", "Gender") else 1
            if key not in best or rank < best[key][0]:
                best[key] = (rank, r, spec)

    out = []
    for (code, iso, year), (_, r, spec) in sorted(best.items()):
        _, name, unit, cat, level = spec
        out.append({
            "Country_ID": iso, "Year": year, "Indicator_Code": code, "Indicator_Name": name,
            "Value": round(float(r["Value"]), 3), "Unit": unit, "Source_ID": "ITU_DH",
            "Category": cat, "Level": level,
        })

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    print(f"✔ {OUT}: {len(out)}행")
    for code in sorted({o["Indicator_Code"] for o in out}):
        cs = {o["Country_ID"] for o in out if o["Indicator_Code"] == code}
        ys = sorted({o["Year"] for o in out if o["Indicator_Code"] == code})
        print(f"  {code:20s} {len(cs):2d}개국  {ys[0]}–{ys[-1]}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python scripts/manual/convert_itu_datahub.py <DataHub CSV>")
    main(sys.argv[1])

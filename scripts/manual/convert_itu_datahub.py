"""
ITU DataHub 내려받기 CSV → data/manual/itu_datahub.csv 표준 CSV 변환 (수동 실행, 표준 라이브러리만 사용)

사용법:
  1. https://datahub.itu.int/query 에서 아래 SERIES의 지표를 고르고,
     국가는 Africa + Arab States(북아프리카 포함)를 선택해 CSV로 내려받는다.
     (요금 지표는 별도 Price Basket 자료라 따로 받아도 된다)
  2. python scripts/manual/convert_itu_datahub.py 파일1.csv [파일2.csv ...]
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

# ITU SeriesCode → (우리 지표 코드, 한글 지표명, 단위, 분류, 화면 표시, 영문 지표명, 영문 정의)
# 영문 정의는 ITU IDI 데이터셋 Definitions 시트 문구를 따른다 (5G·데이터 전용 요금은 ITU 시리즈 기준으로 작성)
# 요금 부담(Price Basket)은 1인당 국민소득 대비 % — 값이 클수록 비쌈
SERIES = {
    'xHH6_IDI': ('ITU.HH.INTERNET', '가정 내 인터넷 접속 가구 비율', '% of households', '접근성', 'main',
        'Households with Internet access at home (%)',
        'Proportion of households with Internet access at home. Internet access at home means that the Internet is generally available for use by all members of the household at any time, regardless of whether it is actually used. The connection and devices may or may not be owned by the household but should be considered household assets. If one member of the household has a mobile phone with connection to the Internet and makes it available for all members, then it should be considered that the household has access to the Internet. An Internet connection in the household should be working at the time of the survey.'),
    'xHH18_IDI': ('ITU.MOBILE.OWN', '휴대전화 보유율', '% of individuals', '접근성', 'main',
        'Individuals owning a mobile phone (%)',
        'Proportion of individuals who own a mobile phone. An individual owns a mobile cellular phone if he/she has a mobile cellular phone device with at least one active SIM card for personal use. It includes mobile cellular phones supplied by employers that can be used for personal reasons (to make personal calls, access the Internet, etc.) and those who have a mobile phone for personal use that is not registered under his/her name. It excludes individuals who have only active SIM card(s) and not a mobile phone device.'),
    'HHU271own-%_POP-FEMALE-': ('ITU.MOBILE.OWN.FE', '휴대전화 보유율 (여성)', '% of individuals', '접근성', 'main',
        'Individuals owning a mobile phone, female (%)',
        'Proportion of individuals who own a mobile phone. An individual owns a mobile cellular phone if he/she has a mobile cellular phone device with at least one active SIM card for personal use. It includes mobile cellular phones supplied by employers that can be used for personal reasons (to make personal calls, access the Internet, etc.) and those who have a mobile phone for personal use that is not registered under his/her name. It excludes individuals who have only active SIM card(s) and not a mobile phone device. Female population only.'),
    'HHU271own-%_POP-MALE-': ('ITU.MOBILE.OWN.MA', '휴대전화 보유율 (남성)', '% of individuals', '접근성', 'main',
        'Individuals owning a mobile phone, male (%)',
        'Proportion of individuals who own a mobile phone. An individual owns a mobile cellular phone if he/she has a mobile cellular phone device with at least one active SIM card for personal use. It includes mobile cellular phones supplied by employers that can be used for personal reasons (to make personal calls, access the Internet, etc.) and those who have a mobile phone for personal use that is not registered under his/her name. It excludes individuals who have only active SIM card(s) and not a mobile phone device. Male population only.'),
    'i911mw': ('ITU.MBB.SUBS', '모바일 브로드밴드 가입 건수', 'per 100 people', '인프라', 'main',
        'Active mobile-broadband subscriptions per 100 inhabitants',
        'Active mobile-broadband subscriptions per 100 inhabitants. Active mobile-broadband subscriptions refers to the sum of standard mobile-broadband and dedicated mobile-broadband subscriptions to the public Internet. It covers actual subscribers, not potential subscribers, even though the latter may have broadband enabled-handsets. Subscriptions must include a recurring subscription fee or if in the prepayment modality, pass a usage requirement – users must have accessed the Internet in the last three months.'),
    'i271G': ('ITU.COV.3G', '3G 커버리지 인구 비율', '% of population', '인프라', 'main',
        'Population covered by at least a 3G mobile network (%)',
        'Percentage of the population covered by at least a 3G mobile network refers to the percentage of inhabitants that are within range of at least a 3G mobile-cellular signal, irrespective of whether or not they are subscribers. This is calculated by dividing the number of inhabitants that are covered by at least a 3G mobile-cellular signal by the total population and multiplying by 100.'),
    'i271GA': ('ITU.COV.4G', '4G/LTE 커버리지 인구 비율', '% of population', '인프라', 'main',
        'Population covered by at least a 4G/LTE mobile network (%)',
        'Percentage of the population covered by at least a 4G/LTE mobile network refers to the percentage of inhabitants that live within range of LTE/LTE-Advanced, mobile WiMAX/WirelessMAN or other more advanced mobile-cellular networks, irrespective of whether or not they are subscribers. This is calculated by dividing the number of inhabitants that are covered by the previously mentioned mobile-cellular technologies by the total population and multiplying by 100. It excludes people covered only by HSPA, UMTS, EV-DO and previous 3G technologies, and also excludes fixed WiMAX coverage.'),
    'i271G5_pop': ('ITU.COV.5G', '5G 커버리지 인구 비율', '% of population', '인프라', 'main',
        'Population covered by at least a 5G mobile network (%)',
        'Percentage of inhabitants that are within range of at least a 5G mobile-cellular signal, irrespective of whether or not they are subscribers (ITU series i271G5_pop).'),
    'i271mb_high_2GB_GNI': ('ITU.PRICE.MOBILE', '모바일 데이터·음성 요금 부담 (고사용량: 140분·70건·2GB)', '% of GNI per capita', '요금 부담', 'main',
        'Mobile data and voice high-consumption basket price (% of GNI per capita)',
        'Mobile-broadband data and voice high-consumption basket price as a percentage of GNI per capita (p.c.). The basket refers to the cheapest mobile broadband plan (and add-on) providing at least 2 GB of monthly data using at least 3G technology, 140 minutes of voice and 70 SMSs. See ITU ICT price statistics website for detailed data collection rules.'),
    'i271mb_2GB_GNI': ('ITU.PRICE.MOBILE.DATA', '모바일 데이터 전용 요금 부담 (2GB)', '% of GNI per capita', '요금 부담', 'main',
        'Data-only mobile-broadband basket price, 2 GB (% of GNI per capita)',
        'Price of the cheapest data-only mobile-broadband plan providing at least 2 GB of monthly data, as a percentage of GNI per capita. See the ITU ICT price statistics website for detailed data collection rules (ITU series i271mb_2GB_GNI).'),
    'i154_FBB5_GNI': ('ITU.PRICE.FIXED', '유선 브로드밴드 요금 부담 (5GB)', '% of GNI per capita', '요금 부담', 'main',
        'Fixed-broadband Internet basket price (% of GNI per capita)',
        'Entry-level fixed-broadband basket price as percentage of GNI per capita. The basket is composed of the cheapest plan providing at least 5GB of monthly high-speed data (256Kbit/s or higher) from the operator with the largest market share in each economy. See ITU ICT price statistics website for detailed data collection rules.'),
}


def write_meta(path, meta):
    """지표 코드별 영문 이름·정의 (지표 DB 변수 설명서에 쓰임)"""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Indicator_Code", "Name_EN", "Definition_EN"])
        for code, (name_en, definition) in sorted(meta.items()):
            w.writerow([code, name_en, definition])


def main(paths):
    best = {}  # (code, iso, year) -> row ; 세부 구분 없는 값(빈칸) 우선, 다음 'Total'
    for path in paths:
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
        _, name, unit, cat, level, name_en, definition = spec
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

    write_meta(OUT.replace(".csv", "_meta.csv"), {v[0]: (v[5], v[6]) for v in SERIES.values()})
    print(f"✔ {OUT}: {len(out)}행")
    for code in sorted({o["Indicator_Code"] for o in out}):
        cs = {o["Country_ID"] for o in out if o["Indicator_Code"] == code}
        ys = sorted({o["Year"] for o in out if o["Indicator_Code"] == code})
        print(f"  {code:20s} {len(cs):2d}개국  {ys[0]}–{ys[-1]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("사용법: python scripts/manual/convert_itu_datahub.py <DataHub CSV> [CSV ...]")
    main(sys.argv[1:])

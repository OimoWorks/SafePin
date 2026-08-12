#!/usr/bin/env python3
"""
松山市オープンデータから pins-data.json を生成するスクリプト
Usage: python3 scripts/build_pins.py
前提: scripts/raw/ に以下が存在すること
  - evacuation.csv   (緊急避難場所)
  - aed.csv          (AED)
  - school.csv       (学校座標)
  - shelter.csv      (指定避難所 - OCR等で変換済みのもの, 任意)
  - manhole.csv      (マンホールトイレ一覧 - 手動整備, 任意)
出力: lib/pins-data.json
"""

import csv
import io
import json
import os
import re
import time
import unicodedata

import chardet
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "lib", "pins-data.json")


def read_csv(filename: str) -> list[dict]:
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        return []
    raw = open(path, "rb").read()
    enc = chardet.detect(raw).get("encoding") or "utf-8"
    if enc.lower() in ("shift_jis", "shift-jis", "sjis"):
        enc = "cp932"
    text = raw.decode(enc, errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s).replace(" ", "").replace("　", "")


def safe_float(v: str) -> float | None:
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None


def geocode_address(address: str) -> tuple[float, float] | None:
    url = "https://msearch.gsi.go.jp/address-search/AddressSearch"
    try:
        r = requests.get(url, params={"q": address}, timeout=10)
        data = r.json()
        if data:
            coord = data[0]["geometry"]["coordinates"]
            return (float(coord[1]), float(coord[0]))
    except Exception:
        pass
    return None


def build_school_index(rows: list[dict]) -> dict[str, tuple[float, float]]:
    index = {}
    for row in rows:
        biko = normalize(row.get("備考", "") or "")
        if "廃校" in biko or "休校" in biko:
            continue
        name_raw = (row.get("名称") or row.get("施設名") or "").strip()
        name = normalize(name_raw)
        if not name:
            continue
        lat = safe_float(row.get("Y") or row.get("緯度") or "")
        lng = safe_float(row.get("X") or row.get("経度") or "")
        if lat and lng and abs(lat) > 1 and abs(lng) > 1:
            index[name] = (lat, lng)
    return index


def lookup_school(school_index: dict, name: str) -> tuple[float, float] | None:
    key = normalize(name)
    if key in school_index:
        return school_index[key]
    for k, v in school_index.items():
        if key in k or k in key:
            return v
    return None


def parse_evacuation(rows: list[dict]) -> list[dict]:
    pins = []
    for i, row in enumerate(rows):
        lat = safe_float(row.get("緯度") or row.get("Y") or "")
        lng = safe_float(row.get("経度") or row.get("X") or "")
        if not lat or not lng:
            continue
        name = (row.get("名称") or "").strip()
        address = (row.get("所在地_連結表記") or row.get("住所") or "").strip()
        capacity_raw = row.get("想定収容人数") or ""
        try:
            capacity = int(re.sub(r"[^\d]", "", capacity_raw)) if capacity_raw.strip() else 0
        except ValueError:
            capacity = 0
        disaster_keys = ["洪水", "崖崩れ", "高潮", "地震", "津波", "大規模な火事", "内水氾濫", "火山現象"]
        applicable = [k for k in disaster_keys if str(row.get(f"災害種別_{k}") or row.get(k) or "").strip() == "1"]
        notes = "対応: " + "・".join(applicable) if applicable else "緊急避難場所"
        pins.append({
            "id": f"evac-{i+1}", "category": "evacuation_site",
            "name": name, "address": address,
            "lat": round(lat, 6), "lng": round(lng, 6),
            "detail": {"capacity": capacity, "notes": notes},
            "updatedAt": "2024-04-01",
        })
    return pins


def parse_aed(rows: list[dict]) -> list[dict]:
    pins = []
    for i, row in enumerate(rows):
        lat = safe_float(row.get("緯度") or row.get("Y") or "")
        lng = safe_float(row.get("経度") or row.get("X") or "")
        if not lat or not lng:
            continue
        name = (row.get("名称") or "").strip()
        address = (row.get("所在地_連結表記") or row.get("住所") or "").strip()
        location = (row.get("設置位置") or "").strip()
        biko = (row.get("備考") or row.get("利用可能日時特記事項") or "").strip()
        notes_parts = [p for p in [location, biko] if p]
        notes = "、".join(notes_parts) if notes_parts else "AED設置箇所"
        pins.append({
            "id": f"aed-{i+1}", "category": "aed",
            "name": f"AED（{name}）", "address": address,
            "lat": round(lat, 6), "lng": round(lng, 6),
            "detail": {"facilityName": name, "notes": notes},
            "updatedAt": "2024-04-01",
        })
    return pins


def parse_manhole(rows: list[dict], school_index: dict) -> list[dict]:
    toilet_pins, water_pins = [], []
    for i, row in enumerate(rows):
        school_name = (row.get("学校名") or "").strip()
        manhole_count = int(re.sub(r"[^\d]", "", row.get("マンホールトイレ基数") or "0") or 0)
        has_water = str(row.get("応急給水栓") or "").strip() in ("○", "〇", "有", "1", "true")
        year = (row.get("整備年度") or "").strip()
        coords = lookup_school(school_index, school_name)
        if not coords:
            print(f"  [WARN] 座標不明: {school_name}")
            continue
        lat, lng = coords
        if manhole_count > 0:
            toilet_pins.append({
                "id": f"toilet-{i+1}", "category": "toilet",
                "name": f"マンホールトイレ（{school_name}）",
                "address": f"松山市 {school_name}",
                "lat": round(lat, 6), "lng": round(lng, 6),
                "detail": {"capacity": manhole_count * 5, "notes": f"{manhole_count}基設置（{year}年度整備）・災害時開放"},
                "updatedAt": "2024-04-01",
            })
        if has_water:
            water_pins.append({
                "id": f"water-{i+1}", "category": "water",
                "name": f"応急給水栓（{school_name}）",
                "address": f"松山市 {school_name}",
                "lat": round(lat + 0.00005, 6), "lng": round(lng + 0.00005, 6),
                "detail": {"supplyAmount": "災害時供給", "notes": f"{school_name}構内・災害時開放（{year}年度整備）"},
                "updatedAt": "2024-04-01",
            })
    return toilet_pins + water_pins


def parse_shelter_csv(rows: list[dict], school_index: dict) -> list[dict]:
    pins = []
    geocode_cache = {}
    for i, row in enumerate(rows):
        name = (row.get("施設名") or "").strip()
        address = (row.get("住所") or "").strip()
        if not name:
            continue
        lat = safe_float(row.get("緯度") or row.get("Y") or "")
        lng = safe_float(row.get("経度") or row.get("X") or "")
        if not lat or not lng:
            coords = lookup_school(school_index, name)
            if coords:
                lat, lng = coords
            elif address:
                if address not in geocode_cache:
                    print(f"  Geocoding: {name}...", end=" ", flush=True)
                    result = geocode_address(address)
                    geocode_cache[address] = result
                    time.sleep(0.5)
                    print("OK" if result else "FAIL")
                coords = geocode_cache.get(address)
                if coords:
                    lat, lng = coords
        if not lat or not lng:
            print(f"  [SKIP] 座標取得できず: {name}")
            continue
        disaster_keys = ["地震", "津波", "高潮", "洪水", "土砂"]
        applicable = [k for k in disaster_keys if str(row.get(k) or "").strip() in ("○", "〇", "△", "1")]
        notes = ("対応: " + "・".join(applicable)) if applicable else "指定避難所"
        pins.append({
            "id": f"shelter-{i+1}", "category": "shelter",
            "name": name, "address": address,
            "lat": round(lat, 6), "lng": round(lng, 6),
            "detail": {"capacity": 0, "notes": notes},
            "updatedAt": "2024-04-01",
        })
    return pins


def main():
    print("=== SafePin ピンデータ生成 ===\n")
    school_rows = read_csv("school.csv")
    school_index = build_school_index(school_rows)
    print(f"学校座標: {len(school_index)}件 読み込み")
    all_pins = []

    evac_rows = read_csv("evacuation.csv")
    if evac_rows:
        evac_pins = parse_evacuation(evac_rows)
        all_pins.extend(evac_pins)
        print(f"緊急避難場所: {len(evac_pins)}件")
    else:
        print("[WARN] evacuation.csv が見つかりません")

    shelter_rows = read_csv("shelter.csv")
    if shelter_rows:
        shelter_pins = parse_shelter_csv(shelter_rows, school_index)
        all_pins.extend(shelter_pins)
        print(f"指定避難所: {len(shelter_pins)}件")
    else:
        print("[SKIP] shelter.csv なし（指定避難所PDFのOCR変換が必要）")

    aed_rows = read_csv("aed.csv")
    if aed_rows:
        aed_pins = parse_aed(aed_rows)
        all_pins.extend(aed_pins)
        print(f"AED: {len(aed_pins)}件")
    else:
        print("[WARN] aed.csv が見つかりません")

    manhole_rows = read_csv("manhole.csv")
    if manhole_rows:
        facility_pins = parse_manhole(manhole_rows, school_index)
        toilet_count = sum(1 for p in facility_pins if p["category"] == "toilet")
        water_count = sum(1 for p in facility_pins if p["category"] == "water")
        all_pins.extend(facility_pins)
        print(f"マンホールトイレ: {toilet_count}件、応急給水栓: {water_count}件")
    else:
        print("[SKIP] manhole.csv なし（手動整備が必要）")

    print(f"\n合計: {len(all_pins)}件")
    out = {"pins": all_pins, "generatedAt": "2024-04-01", "source": "松山市オープンデータ (CC BY 4.0)"}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n出力完了: {OUT_PATH}")


if __name__ == "__main__":
    main()

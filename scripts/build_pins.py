#!/usr/bin/env python3
"""
松山市オープンデータから pins-data.json を生成するスクリプト
Usage: python3 scripts/build_pins.py

前提: scripts/raw/ に以下が存在すること
  必須:
  - 38201_1.csv          (国土地理院 指定避難所 438件)
  - 38201_2.csv          (国土地理院 指定緊急避難場所 391件)
  - aed.csv              (AED)
  - school.csv           (学校座標 - マンホールトイレ座標補完用)
  - public_facility.csv  (公共施設一覧 - マンホールトイレ座標補完用)
  任意:
  - manhole.csv          (マンホールトイレ一覧 - 手動整備)

出力: lib/pins-data.json
  - "pins": [...]        通常ピンデータ
"""

import csv
import io
import json
import os
import re
import unicodedata

import chardet

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "lib", "pins-data.json")


# ── ユーティリティ ────────────────────────────────────────────

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


# ── 座標ソース: 学校・公共施設インデックス（マンホールトイレ座標補完用） ──

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
        if key in k and len(key) >= len(k) * 0.7:
            return v
        if k in key and len(k) >= len(key) * 0.7:
            return v
    return None


def build_facility_index(rows: list[dict]) -> dict[str, tuple[float, float]]:
    index = {}
    for row in rows:
        name_raw = (row.get("名称") or "").strip()
        name_clean = re.sub(r'[（(][^）)]*[）)]', '', name_raw).strip()
        name = normalize(name_clean)
        if not name:
            continue
        lat = safe_float(row.get("緯度") or "")
        lng = safe_float(row.get("経度") or "")
        if lat and lng and abs(lat) > 1 and abs(lng) > 1:
            index[name] = (lat, lng)
    return index


_FACILITY_VARIANTS: list[tuple[str, str]] = [
    ("分館", "集会所"),
    ("集会所", "分館"),
    ("分校", "小学校"),
    ("小学校", "分校"),
    ("出張所", "支所"),
    ("支所", "出張所"),
]


def _facility_variants(key: str) -> list[str]:
    variants = []
    for src, dst in _FACILITY_VARIANTS:
        if src in key:
            variants.append(key.replace(src, dst))
    return variants


def lookup_facility(facility_index: dict, name: str) -> tuple[float, float] | None:
    key = normalize(name)
    if key in facility_index:
        return facility_index[key]
    for variant in _facility_variants(key):
        if variant in facility_index:
            return facility_index[variant]
    return None


# ── ピン生成：指定避難所（国土地理院 38201_1.csv） ────────────────────────

def parse_shelter_gsi(rows: list[dict]) -> list[dict]:
    """
    国土地理院「指定避難所」CSVを処理してPinリストを返す。
    列: NO,共通ID,施設・場所名,住所,指定緊急避難場所との住所同一,
        その他市町村長が必要と認める事項,受入対象者,緯度,経度,備考
    緯度・経度はCSVに完備されているため座標補完は不要。
    """
    pins: list[dict] = []
    for i, row in enumerate(rows):
        name = (row.get("施設・場所名") or "").strip()
        address = (row.get("住所") or "").strip()
        if not name:
            continue
        lat = safe_float(row.get("緯度") or "")
        lng = safe_float(row.get("経度") or "")
        if not lat or not lng:
            print(f"  [SKIP] 座標なし: {name}")
            continue

        notes_parts = []
        extra = (row.get("その他市町村長が必要と認める事項") or "").strip()
        target = (row.get("受入対象者") or "").strip()
        if extra:
            notes_parts.append(extra)
        if target:
            notes_parts.append(f"受入: {target}")
        notes = "　".join(notes_parts) if notes_parts else ""

        pins.append({
            "id": f"shelter-{i + 1}",
            "category": "shelter",
            "name": name,
            "address": address,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "detail": {"capacity": 0, "notes": notes},
            "updatedAt": "2025-04-01",
        })
    return pins


# ── ピン生成：緊急避難場所（国土地理院 38201_2.csv） ─────────────────────

def parse_evacuation_gsi(rows: list[dict]) -> list[dict]:
    """
    国土地理院「指定緊急避難場所」CSVを処理してPinリストを返す。
    列: NO,共通ID,施設・場所名,住所,洪水,崖崩れ・土石流及び地滑り,高潮,
        地震,津波,大規模な火事,内水氾濫,火山現象,指定避難所との住所同一,緯度,経度,備考
    """
    disaster_cols = ["洪水", "崖崩れ、土石流及び地滑り", "高潮", "地震", "津波", "大規模な火事", "内水氾濫", "火山現象"]
    disaster_labels = ["洪水", "崖崩れ・土石流", "高潮", "地震", "津波", "大規模な火事", "内水氾濫", "火山現象"]

    pins: list[dict] = []
    for i, row in enumerate(rows):
        name = (row.get("施設・場所名") or "").strip()
        address = (row.get("住所") or "").strip()
        if not name:
            continue
        lat = safe_float(row.get("緯度") or "")
        lng = safe_float(row.get("経度") or "")
        if not lat or not lng:
            print(f"  [SKIP] 座標なし: {name}")
            continue

        applicable = [
            label for col, label in zip(disaster_cols, disaster_labels)
            if str(row.get(col) or "").strip() == "1"
        ]
        notes = "対応: " + "・".join(applicable) if applicable else "緊急避難場所"

        pins.append({
            "id": f"evac-{i + 1}",
            "category": "evacuation_site",
            "name": name,
            "address": address,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "detail": {"capacity": 0, "notes": notes},
            "updatedAt": "2025-04-01",
        })
    return pins


# ── ピン生成：AED ──────────────────────────────────────────────────────

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
            "id": f"aed-{i + 1}", "category": "aed",
            "name": f"AED（{name}）", "address": address,
            "lat": round(lat, 6), "lng": round(lng, 6),
            "detail": {"facilityName": name, "notes": notes},
            "updatedAt": "2025-04-01",
        })
    return pins


# ── ピン生成：マンホールトイレ・応急給水栓 ─────────────────────────────

def parse_manhole(rows: list[dict], school_index: dict, facility_index: dict) -> list[dict]:
    toilet_pins, water_pins = [], []
    if rows:
        print(f"  [DEBUG] manhole.csv 列名: {list(rows[0].keys())}")
    _AREA_PATTERN = re.compile(r'エリア|地区|地域|中心部')
    for i, row in enumerate(rows):
        school_name = (
            row.get("学校名") or row.get("施設名") or row.get("名称") or ""
        ).strip()
        school_name = re.sub(r'[（(]PDF[^）)]*[）)]', '', school_name).strip()
        if not school_name or _AREA_PATTERN.search(school_name):
            continue
        manhole_raw = row.get("マンホールトイレ基数") or row.get("基数") or "0"
        manhole_count = int(re.sub(r"[^\d]", "", str(manhole_raw)) or 0)
        water_raw = str(
            row.get("応急給水栓") or row.get("応急給水") or row.get("給水栓") or ""
        ).strip()
        has_water = water_raw in ("○", "〇", "有", "1", "true")
        year = (row.get("整備年度") or row.get("年度") or "").strip()
        coords = lookup_school(school_index, school_name)
        if not coords:
            coords = lookup_facility(facility_index, school_name)
        if not coords:
            print(f"  [WARN] 座標不明: {school_name}")
            continue
        lat, lng = coords
        if manhole_count > 0:
            toilet_pins.append({
                "id": f"toilet-{i + 1}", "category": "toilet",
                "name": f"マンホールトイレ（{school_name}）",
                "address": f"松山市 {school_name}",
                "lat": round(lat, 6), "lng": round(lng, 6),
                "detail": {"capacity": manhole_count * 5, "notes": f"{manhole_count}基設置（{year}年度整備）・災害時開放"},
                "updatedAt": "2025-04-01",
            })
        if has_water:
            water_pins.append({
                "id": f"water-{i + 1}", "category": "water",
                "name": f"応急給水栓（{school_name}）",
                "address": f"松山市 {school_name}",
                "lat": round(lat + 0.00005, 6), "lng": round(lng + 0.00005, 6),
                "detail": {"supplyAmount": "災害時供給", "notes": f"{school_name}構内・災害時開放（{year}年度整備）"},
                "updatedAt": "2025-04-01",
            })
    return toilet_pins + water_pins


# ── メイン ─────────────────────────────────────────────────────────────

def main():
    print("=== SafePin ピンデータ生成 ===\n")

    school_rows = read_csv("school.csv")
    school_index = build_school_index(school_rows)
    print(f"学校座標: {len(school_index)}件 読み込み")

    facility_rows = read_csv("public_facility.csv")
    facility_index = build_facility_index(facility_rows)
    print(f"公共施設座標: {len(facility_index)}件 読み込み")

    print()

    all_pins: list[dict] = []

    shelter_rows = read_csv("38201_1.csv")
    if shelter_rows:
        shelter_pins = parse_shelter_gsi(shelter_rows)
        all_pins.extend(shelter_pins)
        print(f"指定避難所: {len(shelter_pins)}件")
    else:
        print("[WARN] 38201_1.csv が見つかりません")

    evac_rows = read_csv("38201_2.csv")
    if evac_rows:
        evac_pins = parse_evacuation_gsi(evac_rows)
        all_pins.extend(evac_pins)
        print(f"緊急避難場所: {len(evac_pins)}件")
    else:
        print("[WARN] 38201_2.csv が見つかりません")

    aed_rows = read_csv("aed.csv")
    if aed_rows:
        aed_pins = parse_aed(aed_rows)
        all_pins.extend(aed_pins)
        print(f"AED: {len(aed_pins)}件")
    else:
        print("[WARN] aed.csv が見つかりません")

    manhole_rows = read_csv("manhole.csv")
    if manhole_rows:
        facility_pins = parse_manhole(manhole_rows, school_index, facility_index)
        toilet_count = sum(1 for p in facility_pins if p["category"] == "toilet")
        water_count  = sum(1 for p in facility_pins if p["category"] == "water")
        all_pins.extend(facility_pins)
        print(f"マンホールトイレ: {toilet_count}件、応急給水栓: {water_count}件")
    else:
        print("[SKIP] manhole.csv なし（手動整備が必要）")

    print(f"\n合計: {len(all_pins)}件")

    out = {
        "pins": all_pins,
        "generatedAt": "2025-04-01",
        "source": "国土地理院 指定緊急避難場所・指定避難所データ / 松山市オープンデータ (CC BY 4.0)",
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n出力完了: {OUT_PATH}")


if __name__ == "__main__":
    main()

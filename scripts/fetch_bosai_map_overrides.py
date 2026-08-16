#!/usr/bin/env python3
"""
bosai-map.com から指定避難所の緯度経度を取得し、
scripts/raw/shelter_overrides.csv に書き出す。

Usage:
  python3 scripts/fetch_bosai_map_overrides.py [url_file]

  url_file のデフォルト: scripts/bosai_map_urls.txt
  フォーマット: 施設名|URL （1行1件）

出力: scripts/raw/shelter_overrides.csv
  列: 施設名, 住所, lat, lng
  - 「住所」列は同名施設を区別するための部分住所文字列（不要な場合は空）
  - build_pins.py は「住所」が非空のとき shelter.csv の住所に部分一致で照合する
"""

import csv
import os
import re
import sys
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUT = os.path.join(RAW_DIR, "shelter_overrides.csv")


def parse_display_name(raw: str) -> tuple[str, str]:
    """
    URL ファイルの施設名フィールドをパースして (正式名称, 住所ヒント) を返す。

    パターン1: 末尾が「（Xの可能性）」→ X を正式名称の末尾として採用
      例: 「立岩公民館渇裾分館（湯裾分館の可能性）」
          → ("立岩公民館湯裾分館", "")

    パターン2: 「）」の後ろに住所らしき文字列が続く → 住所ヒントとして返す
      例: 「聖カタリナ学園高等学校（体育館）永代町10-1」
          → ("聖カタリナ学園高等学校（体育館）", "永代町10-1")

    それ以外: そのまま返す
    """
    raw = raw.strip()

    # パターン1: 末尾が「（Xの可能性）」
    m = re.search(r'（([^）]+)の可能性）$', raw)
    if m:
        correct_suffix = m.group(1)     # e.g. "湯裾分館"
        base = raw[:m.start()]          # e.g. "立岩公民館渇裾分館"
        # correct_suffix と同じ長さの末尾を置換（"渇裾分館" → "湯裾分館"）
        clean_name = base[:-len(correct_suffix)] + correct_suffix
        return clean_name, ""

    # パターン2: ）の後ろに住所テキスト
    m = re.search(r'）(.+)$', raw)
    if m:
        addr_hint = m.group(1).strip()
        clean_name = raw[:m.start() + 1]   # ）を含む
        return clean_name, addr_hint

    return raw, ""


def fetch_coords(url: str, session: requests.Session) -> tuple[float, float] | None:
    """bosai-map.com の詳細ページから緯度経度を取得する。"""
    try:
        r = session.get(
            url,
            timeout=15,
            headers={"User-Agent": "SafePin/1.0 (disaster-preparedness PWA; contact: github.com/oimoworks/safepin)"},
        )
        r.raise_for_status()
        m = re.search(r'緯度経度[：:]\ *([\ d.]+)[,、\ ]+([\ d.]+)', r.text)
        if m:
            return float(m.group(1)), float(m.group(2))
        print(f"  [WARN] 緯度経度テキストが見つかりません: {url}")
    except Exception as e:
        print(f"  [ERR] {url}: {e}")
    return None


def main() -> None:
    url_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCRIPT_DIR, "bosai_map_urls.txt")
    if not os.path.exists(url_file):
        print(f"URL ファイルが見つかりません: {url_file}")
        print("scripts/bosai_map_urls.txt に配置するか、引数でパスを指定してください。")
        sys.exit(1)

    entries: list[tuple[str, str, str]] = []
    with open(url_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            raw_name, url = line.split("|", 1)
            clean_name, addr_hint = parse_display_name(raw_name.strip())
            entries.append((clean_name, addr_hint, url.strip()))

    print(f"{len(entries)} 件の URL を読み込みました")
    print(f"出力先: {OUT}\n")

    results: list[tuple[str, str, float, float]] = []
    failed: list[str] = []
    session = requests.Session()

    for i, (name, addr_hint, url) in enumerate(entries, 1):
        print(f"[{i:2d}/{len(entries)}] {name} ...", end=" ", flush=True)
        coords = fetch_coords(url, session)
        if coords:
            lat, lng = coords
            results.append((name, addr_hint, lat, lng))
            print(f"OK ({lat}, {lng})")
        else:
            failed.append(name)
            print("FAIL")
        time.sleep(0.5)

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["施設名", "住所", "lat", "lng"])
        for name, addr_hint, lat, lng in results:
            writer.writerow([name, addr_hint, lat, lng])

    print(f"\n完了: {len(results)}/{len(entries)} 件を {OUT} に書き出しました")
    if failed:
        print(f"失敗 ({len(failed)} 件):")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()

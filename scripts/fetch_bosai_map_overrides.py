#!/usr/bin/env python3
"""
bosai-map.com から指定避難所の緯度経度を取得し、
scripts/raw/shelter_overrides.csv に書き出す（追記モード対応）。

Usage:
  python3 scripts/fetch_bosai_map_overrides.py [url_file] [--merge partial.csv]

  url_file のデフォルト: scripts/bosai_map_urls.txt
  フォーマット: 施設名|URL （1行1件）

  --merge partial.csv
    既存の部分結果CSV（列: 名称/施設名, 住所, 緯度/lat, 経度/lng）を
    shelter_overrides.csv に取り込んでから、残りのURLをフェッチする。

出力: scripts/raw/shelter_overrides.csv
  列: 施設名, 住所, lat, lng
  - 「住所」列は同名施設を区別するための部分住所文字列（不要な場合は空）
  - build_pins.py は「住所」が非空のとき shelter.csv の住所に部分一致で照合する
"""

import csv
import json
import os
import re
import sys
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUT = os.path.join(RAW_DIR, "shelter_overrides.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)
COORDS_TEXT_RE = re.compile(r'緯度経度[：:]\s*([\d.]+)[,、\s]+([\d.]+)')


# ── 名前パース ────────────────────────────────────────────────────────────────────────────

def parse_display_name(raw: str) -> tuple[str, str]:
    """
    URLファイルの施設名フィールドをパースして (正式同名称, 住所ヒント) を返す。

    パターン1: 末尾が「（Xの可能性）」→ X を正式名称の末尾として採用
      例: 「立岩公民館渇裾分館（湯裾分館の可能性）」 → ("立岩公民館湯裾分館", "")

    パターン2: 「）」の後ろに住所らしき文字列が続く → 住所ヒントとして返す
      例: 「聖カタリナ学園高等学校（体育館）永代町10-1」
          → ("聖カタリナ学園高等学校（体育館）", "永代町10-1")

    それ以外: そのまま返す
    """
    raw = raw.strip()

    m = re.search(r'（([^）]+)の可能性）$', raw)
    if m:
        correct_suffix = m.group(1)
        base = raw[:m.start()]
        clean_name = base[:-len(correct_suffix)] + correct_suffix
        return clean_name, ""

    m = re.search(r'）(.+)$', raw)
    if m:
        addr_hint = m.group(1).strip()
        clean_name = raw[:m.start() + 1]
        return clean_name, addr_hint

    return raw, ""


# ── 坐標取得 ──────────────────────────────────────────────────────────────────────────

def _find_coords_in_obj(obj, depth: int = 0) -> tuple[float, float] | None:
    """JSON オブジェクトを再帰的に探索して緯度経度を返す。"""
    if depth > 10 or not isinstance(obj, (dict, list)):
        return None
    if isinstance(obj, dict):
        for lat_key in ("lat", "latitude", "緯度"):
            for lng_key in ("lng", "longitude", "経度"):
                if lat_key in obj and lng_key in obj:
                    try:
                        return float(obj[lat_key]), float(obj[lng_key])
                    except (TypeError, ValueError):
                        pass
        for v in obj.values():
            r = _find_coords_in_obj(v, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = _find_coords_in_obj(item, depth + 1)
            if r:
                return r
    return None


def fetch_coords(url: str, session: requests.Session) -> tuple[float, float] | None:
    """
    bosai-map.com の詳細ページから緯度経度を取得する。
    1. __NEXT_DATA__ JSON をパース（lat/lng/latitude/longitude を再帰探索）
    2. 見つからなければ「緯度経度：」テキストをフォールバックとして使う
    429 は1回だけ10秒待ってリトライ。
    """
    for attempt in range(2):
        try:
            r = session.get(url, timeout=15, headers=HEADERS)
            if r.status_code == 429:
                if attempt == 0:
                    print("  [429] 10秒待ってリトライ...", end=" ", flush=True)
                    time.sleep(10)
                    continue
                print(f"  [ERR] 429 Too Many Requests: {url}")
                return None
            r.raise_for_status()
        except Exception as e:
            print(f"  [ERR] {url}: {e}")
            return None

        # ── 方法1: __NEXT_DATA__ JSON ────────────────────────────────────────────────────
        m = NEXT_DATA_RE.search(r.text)
        if m:
            try:
                next_data = json.loads(m.group(1))
                coords = _find_coords_in_obj(next_data)
                if coords:
                    return coords
                print(f"  [WARN] __NEXT_DATA__ に lat/lng キーが見つかりません: {url}")
                page_props = next_data.get("props", {}).get("pageProps", {})
                top_keys = list(page_props.keys()) if isinstance(page_props, dict) else []
                print(f"         pageProps トップキー: {top_keys}")
            except json.JSONDecodeError as e:
                print(f"  [WARN] __NEXT_DATA__ JSON パース失敗: {e}")
        else:
            print(f"  [WARN] __NEXT_DATA__ タグが見つかりません: {url}")

        # ── 方法2: テキスト「緯度経度：」（フォールバック）─────────────────────────
        m2 = COORDS_TEXT_RE.search(r.text)
        if m2:
            return float(m2.group(1)), float(m2.group(2))

        print(f"  [WARN] 坐標を取得できませんでした: {url}")
        return None

    return None


# ── 既存 CSV 読み込み ───────────────────────────────────────────────────────────────────

def load_existing(path: str) -> list[tuple[str, str, float, float]]:
    """
    shelter_overrides.csv（列: 施設名,住所,lat,lng）を読み込む。
    列名の摂れ（名称/施設名、緯度/lat、経度/lng）にも対応。
    """
    if not os.path.exists(path):
        return []
    results = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("施設名") or row.get("名称") or "").strip()
            addr = (row.get("住所") or "").strip()
            lat_raw = (row.get("lat") or row.get("緯度") or "").strip()
            lng_raw = (row.get("lng") or row.get("経度") or "").strip()
            if not name or not lat_raw or not lng_raw:
                continue
            try:
                results.append((name, addr, float(lat_raw), float(lng_raw)))
            except ValueError:
                pass
    return results


def load_merge_csv(
    path: str, entries: list[tuple[str, str, str]]
) -> list[tuple[str, str, float, float]]:
    """
    部分結果 CSV を読み込み、URL ファイルの addr_hint で住所列を上書きして返す。
    entries: [(name, addr_hint, url), ...]
    """
    addr_hint_map: dict[str, str] = {name: addr for name, addr, _ in entries if addr}

    rows = load_existing(path)
    converted = []
    for name, addr_full, lat, lng in rows:
        addr_hint = addr_hint_map.get(name, "")
        if not addr_hint:
            for n, a in addr_hint_map.items():
                if n == name and a and a in addr_full:
                    addr_hint = a
                    break
        converted.append((name, addr_hint, lat, lng))
    return converted


# ── メイン ─────────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]
    merge_path: str | None = None
    url_file = os.path.join(SCRIPT_DIR, "bosai_map_urls.txt")

    i = 0
    while i < len(args):
        if args[i] == "--merge" and i + 1 < len(args):
            merge_path = args[i + 1]
            i += 2
        else:
            url_file = args[i]
            i += 1

    if not os.path.exists(url_file):
        print(f"URL ファイルが見つかりません: {url_file}")
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

    os.makedirs(RAW_DIR, exist_ok=True)

    existing: list[tuple[str, str, float, float]] = []
    if merge_path:
        print(f"部分結果をマージします: {merge_path}")
        existing = load_merge_csv(merge_path, entries)
        print(f"  マージ: {len(existing)} 件")
    elif os.path.exists(OUT):
        existing = load_existing(OUT)
        print(f"既存の出力ファイルから {len(existing)} 件を読み込みました")

    done: set[tuple[str, str]] = {(name, addr) for name, addr, _, _ in existing}

    todo = [(name, addr, url) for name, addr, url in entries if (name, addr) not in done]
    print(f"取得済み: {len(existing)} 件 / 未取得: {len(todo)} 件")
    print(f"出力先: {OUT}\n")

    if not todo:
        print("全件取得済みです。")
        _write_csv(OUT, existing)
        return

    results = list(existing)
    failed: list[str] = []
    session = requests.Session()

    for idx, (name, addr_hint, url) in enumerate(todo, 1):
        label = f"{name}({addr_hint})" if addr_hint else name
        print(f"[{idx:2d}/{len(todo)}] {label} ...", end=" ", flush=True)
        coords = fetch_coords(url, session)
        if coords:
            lat, lng = coords
            results.append((name, addr_hint, lat, lng))
            print(f"OK ({lat}, {lng})")
        else:
            failed.append(label)
            print("FAIL")
        if idx < len(todo):
            time.sleep(2.5)

    _write_csv(OUT, results)
    print(f"\n完了: {len(results)}/{len(entries)} 件を {OUT} に書き出しました")
    if failed:
        print(f"失敗 ({len(failed)} 件):")
        for name in failed:
            print(f"  - {name}")


def _write_csv(path: str, results: list[tuple[str, str, float, float]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["施設名", "住所", "lat", "lng"])
        for name, addr_hint, lat, lng in results:
            writer.writerow([name, addr_hint, lat, lng])


if __name__ == "__main__":
    main()

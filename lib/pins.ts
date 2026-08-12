import { Pin } from './types'

// ── ダミーデータ（実データ生成前のフォールバック） ──────────────────────────
// 実データに置き換える場合:
//   1. python3 scripts/fetch_data.py
//   2. python3 scripts/build_pins.py
//   3. python3 scripts/generate_pins_ts.py
// で lib/pins.ts を自動上書きしてください。

const FALLBACK_PINS: Pin[] = [
  {
    id: 'shelter-1',
    category: 'shelter',
    name: '松山市総合コミュニティセンター',
    address: '愛媛県松山市湊町七丁目5番地',
    lat: 33.8392,
    lng: 132.7657,
    detail: { capacity: 500, notes: '体育館あり・指定避難所' },
    updatedAt: '2026-06-01',
  },
  {
    id: 'shelter-2',
    category: 'shelter',
    name: '松山市立番町小学校',
    address: '愛媛県松山市番町三丁目2番地1号',
    lat: 33.8421,
    lng: 132.7701,
    detail: { capacity: 300, notes: '校庭も使用可・指定避難所' },
    updatedAt: '2026-06-01',
  },
  {
    id: 'evac-1',
    category: 'evacuation_site',
    name: '城山公園（緊急避難場所）',
    address: '愛媛県松山市丸之内',
    lat: 33.8436,
    lng: 132.7659,
    detail: { capacity: 0, notes: '対応: 地震・大規模な火事' },
    updatedAt: '2026-06-01',
  },
  {
    id: 'evac-2',
    category: 'evacuation_site',
    name: '堀之内公園（緊急避難場所）',
    address: '愛媛県松山市堀之内',
    lat: 33.8378,
    lng: 132.7689,
    detail: { capacity: 0, notes: '対応: 地震・洪水' },
    updatedAt: '2026-06-01',
  },
  {
    id: 'toilet-1',
    category: 'toilet',
    name: 'マンホールトイレ（城山公園）',
    address: '愛媛県松山市丸之内',
    lat: 33.8437,
    lng: 132.766,
    detail: { capacity: 20, notes: '災害時開放' },
    updatedAt: '2026-06-01',
  },
  {
    id: 'water-1',
    category: 'water',
    name: '松山市役所 給水ポイント',
    address: '愛媛県松山市二番町四丁目7-2',
    lat: 33.8398,
    lng: 132.7712,
    detail: { supplyAmount: '1日2000L', notes: '災害時開放' },
    updatedAt: '2026-06-01',
  },
  {
    id: 'aed-1',
    category: 'aed',
    name: 'AED（松山市役所1F）',
    address: '愛媛県松山市二番町四丁目7-2',
    lat: 33.8399,
    lng: 132.7713,
    detail: { facilityName: '松山市役所', notes: '1階エントランス' },
    updatedAt: '2026-06-01',
  },
]

export const DUMMY_PINS: Pin[] = FALLBACK_PINS

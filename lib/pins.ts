import { Pin } from './types'

// ── ダミーデータ（実データ生成前のフォールバック） ──────────────────────────

const FALLBACK_PINS: Pin[] = [
  {
    id: '1',
    category: 'shelter',
    name: '松山市総合コミュニティセンター',
    address: '愛媛県松山市湊町七丁目5番地',
    lat: 33.8392,
    lng: 132.7657,
    detail: { capacity: 500, notes: '体育館あり' },
    updatedAt: '2026-06-01',
  },
  {
    id: '2',
    category: 'shelter',
    name: '松山市立番町小学校',
    address: '愛媛県松山市番町三丁目2番地1号',
    lat: 33.8421,
    lng: 132.7701,
    detail: { capacity: 300, notes: '校庭も使用可' },
    updatedAt: '2026-06-01',
  },
  {
    id: '3',
    category: 'toilet',
    name: 'マンホールトイレ（城山公園）',
    address: '愛媛県松山市丸之内',
    lat: 33.8436,
    lng: 132.7659,
    detail: { capacity: 20, notes: '災害時開放' },
    updatedAt: '2026-06-01',
  },
  {
    id: '4',
    category: 'toilet',
    name: 'マンホールトイレ（堀之内公園）',
    address: '愛媛県松山市堀之内',
    lat: 33.8378,
    lng: 132.7689,
    detail: { capacity: 15, notes: '災害時開放' },
    updatedAt: '2026-06-01',
  },
  {
    id: '5',
    category: 'water',
    name: '松山市役所 給水ポイント',
    address: '愛媛県松山市二番町四丁目7-2',
    lat: 33.8398,
    lng: 132.7712,
    detail: { supplyAmount: '1日2000L', notes: '災害時開放' },
    updatedAt: '2026-06-01',
  },
  {
    id: '6',
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
// 実データに置き換える場合: scripts/build_pins.py を実行後、
// FALLBACK_PINS の定義を pins-data.json の内容で上書きしてください。
// または scripts/generate_pins_ts.py で lib/pins.ts を自動生成してください。

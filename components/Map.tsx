'use client'

import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import { Pin, PinCategory, CATEGORIES } from '@/lib/types'
import { DUMMY_PINS } from '@/lib/pins'
import CategoryFilter from './CategoryFilter'
import PinDetail from './PinDetail'
import Attribution from './Attribution'

const ALL_CATEGORIES = new Set<PinCategory>(['shelter', 'evacuation_site', 'toilet', 'water', 'aed'])
const DEFAULT_CENTER: [number, number] = [33.8392, 132.7657]
const DEFAULT_ZOOM = 15
const LOCATE_ZOOM = 16

function createPinIcon(category: PinCategory) {
  const cat = CATEGORIES[category]
  return L.divIcon({
    html: `<div style="
      background:${cat.color};
      width:36px;height:36px;
      border-radius:50% 50% 50% 0;
      transform:rotate(-45deg);
      border:3px solid white;
      box-shadow:0 2px 6px rgba(0,0,0,0.4);
      display:flex;align-items:center;justify-content:center;
    "><span style="transform:rotate(45deg);font-size:16px;line-height:1;">${cat.icon}</span></div>`,
    className: '',
    iconSize: [36, 36],
    iconAnchor: [18, 36],
    popupAnchor: [0, -36],
  })
}

export default function Map() {
  const mapRef = useRef<HTMLDivElement>(null)
  const leafletMap = useRef<L.Map | null>(null)
  const markersRef = useRef<globalThis.Map<string, L.Marker>>(new globalThis.Map())
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null)
  const [activeCategories, setActiveCategories] = useState<Set<PinCategory>>(new Set(ALL_CATEGORIES))
  const [selectedPin, setSelectedPin] = useState<Pin | null>(null)
  const [locating, setLocating] = useState(true)

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return

    const map = L.map(mapRef.current, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      zoomControl: false,
    })

    L.control.zoom({ position: 'bottomright' }).addTo(map)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)

    leafletMap.current = map

    localStorage.setItem('lastUpdated', new Date().toLocaleDateString('ja-JP'))

    const clusterGroup = L.markerClusterGroup({
      maxClusterRadius: 60,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
    })

    for (const pin of DUMMY_PINS) {
      const marker = L.marker([pin.lat, pin.lng], { icon: createPinIcon(pin.category) })
      marker.on('click', () => setSelectedPin(pin))
      clusterGroup.addLayer(marker)
      markersRef.current.set(pin.id, marker)
    }

    clusterGroup.addTo(map)
    clusterGroupRef.current = clusterGroup

    // 起動時に現在地を自動取得して中心に移動する（失敗してもフォールバック）
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          map.setView([pos.coords.latitude, pos.coords.longitude], LOCATE_ZOOM)
          setLocating(false)
        },
        () => {
          setLocating(false)
        },
        { timeout: 5000, maximumAge: 60000 }
      )
    } else {
      setLocating(false)
    }

    return () => {
      map.remove()
      leafletMap.current = null
      clusterGroupRef.current = null
    }
  }, [])

  useEffect(() => {
    const clusterGroup = clusterGroupRef.current
    if (!clusterGroup) return
    for (const pin of DUMMY_PINS) {
      const marker = markersRef.current.get(pin.id)
      if (!marker) continue
      if (activeCategories.has(pin.category)) {
        clusterGroup.addLayer(marker)
      } else {
        clusterGroup.removeLayer(marker)
      }
    }
  }, [activeCategories])

  function toggleCategory(category: PinCategory) {
    setActiveCategories((prev) => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
    if (selectedPin?.category === category) {
      setSelectedPin(null)
    }
  }

  function locateUser() {
    if (!leafletMap.current) return
    leafletMap.current.locate({ setView: true, maxZoom: LOCATE_ZOOM })
  }

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full" />

      {locating && (
        <div className="absolute inset-0 z-[500] flex items-center justify-center pointer-events-none">
          <div className="bg-white/80 rounded-2xl px-5 py-3 flex items-center gap-3 shadow-md text-sm text-gray-600">
            <svg className="animate-spin w-5 h-5 text-red-500" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            現在地を取得中…
          </div>
        </div>
      )}

      <CategoryFilter activeCategories={activeCategories} onToggle={toggleCategory} />

      <button
        onClick={locateUser}
        className="absolute bottom-20 right-4 z-[1000] bg-white rounded-full w-12 h-12 shadow-md flex items-center justify-center text-2xl hover:bg-gray-50 active:bg-gray-100"
        aria-label="現在地"
      >
        📍
      </button>

      <Attribution />

      {selectedPin && (
        <PinDetail pin={selectedPin} onClose={() => setSelectedPin(null)} />
      )}
    </div>
  )
}

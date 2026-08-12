'use client'

import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Pin, PinCategory, CATEGORIES } from '@/lib/types'
import { DUMMY_PINS } from '@/lib/pins'
import { savePins, saveLastUpdated } from '@/lib/indexeddb'
import CategoryFilter from './CategoryFilter'
import PinDetail from './PinDetail'
import Attribution from './Attribution'

const ALL_CATEGORIES = new Set<PinCategory>(['shelter', 'evacuation_site', 'toilet', 'water', 'aed'])

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
  const [activeCategories, setActiveCategories] = useState<Set<PinCategory>>(new Set(ALL_CATEGORIES))
  const [selectedPin, setSelectedPin] = useState<Pin | null>(null)

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return

    const map = L.map(mapRef.current, {
      center: [33.8392, 132.7657],
      zoom: 15,
      zoomControl: false,
    })

    L.control.zoom({ position: 'bottomright' }).addTo(map)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)

    leafletMap.current = map

    savePins(DUMMY_PINS)
    saveLastUpdated(new Date().toLocaleDateString('ja-JP'))

    for (const pin of DUMMY_PINS) {
      const marker = L.marker([pin.lat, pin.lng], { icon: createPinIcon(pin.category) })
      marker.on('click', () => setSelectedPin(pin))
      marker.addTo(map)
      markersRef.current.set(pin.id, marker)
    }

    return () => {
      map.remove()
      leafletMap.current = null
    }
  }, [])

  useEffect(() => {
    if (!leafletMap.current) return
    for (const pin of DUMMY_PINS) {
      const marker = markersRef.current.get(pin.id)
      if (!marker) continue
      if (activeCategories.has(pin.category)) {
        marker.addTo(leafletMap.current)
      } else {
        marker.remove()
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
    leafletMap.current.locate({ setView: true, maxZoom: 16 })
  }

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full" />

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

'use client'

import { useEffect, useState, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Custom marker with device name
const createDeviceMarker = (name: string, isRunning: boolean, index: number) => {
  const color = isRunning ? '#22c55e' : '#3b82f6'
  const bgColor = isRunning ? '#16a34a' : '#2563eb'

  return L.divIcon({
    className: 'device-marker',
    html: `
      <div style="position: relative;">
        <div style="
          background: ${color};
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: 3px solid white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.4);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: bold;
          font-size: 14px;
        ">${index + 1}</div>
        <div style="
          position: absolute;
          bottom: -8px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 8px solid transparent;
          border-right: 8px solid transparent;
          border-top: 10px solid ${color};
        "></div>
        <div style="
          position: absolute;
          top: -28px;
          left: 50%;
          transform: translateX(-50%);
          background: ${bgColor};
          color: white;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
          white-space: nowrap;
          box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        ">${name}</div>
      </div>
    `,
    iconSize: [36, 44],
    iconAnchor: [18, 44],
    popupAnchor: [0, -44]
  })
}

// Direction arrow marker
const createArrowMarker = (color: string, direction: number) => {
  return L.divIcon({
    className: 'arrow-marker',
    html: `
      <div style="
        width: 16px;
        height: 16px;
        transform: rotate(${direction}deg);
      ">
        <svg viewBox="0 0 24 24" fill="${color}" width="16" height="16">
          <path d="M12 2L4 20h16L12 2z"/>
        </svg>
      </div>
    `,
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  })
}

interface Device {
  id: number
  name: string
  latitude?: number
  longitude?: number
  ign_state?: number
  speed?: number
  mileage?: number
  fuel_litres?: number
  battery_voltage?: number
  temp_inner?: number
  direction?: number
}

interface TrackPoint {
  latitude: number
  longitude: number
  timestamp: string
  speed: number
  ign_state: number
}

// Component to fit bounds to all markers
function FitBounds({ devices }: { devices: Device[] }) {
  const map = useMap()

  useEffect(() => {
    if (devices.length > 0) {
      const bounds = L.latLngBounds(
        devices
          .filter(d => d.latitude !== undefined && d.longitude !== undefined)
          .map(d => [d.latitude!, d.longitude!])
      )
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50] })
      }
    }
  }, [devices, map])

  return null
}

// Track line component
function DeviceTrack({
  deviceId,
  showTrack,
  token
}: {
  deviceId: number
  showTrack: boolean
  token: string | null
}) {
  const [track, setTrack] = useState<TrackPoint[]>([])
  const map = useMap()

  useEffect(() => {
    if (!showTrack || !token) {
      setTrack([])
      return
    }

    const fetchTrack = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/devices/${deviceId}/track?hours=24`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) {
          const data = await res.json()
          setTrack(data)
        }
      } catch (err) {
        console.error('Failed to fetch track:', err)
      }
    }

    fetchTrack()
  }, [deviceId, showTrack, token])

  if (!showTrack || track.length < 2) {
    return null
  }

  // Helper to interpolate color from orange to green based on position in track
  const getColor = (index: number, total: number) => {
    const ratio = index / Math.max(total - 1, 1)
    // Orange (#f59e0b) to Green (#22c55e)
    const r = Math.round(245 - ratio * (245 - 34))
    const g = Math.round(158 + ratio * (197 - 158))
    const b = Math.round(11 + ratio * (94 - 11))
    return `rgb(${r}, ${g}, ${b})`
  }

  // Create gradient segments - draw each segment with its own color
  const gradientSegments: { positions: [number, number][], color: string }[] = []

  // Only show segments where vehicle was moving (ignition on)
  for (let i = 0; i < track.length - 1; i++) {
    const current = track[i]
    const next = track[i + 1]

    // Only draw if vehicle was moving at this point
    if (current.ign_state === 1 || next.ign_state === 1) {
      gradientSegments.push({
        positions: [[current.latitude, current.longitude], [next.latitude, next.longitude]],
        color: getColor(i, track.length)
      })
    }
  }

  return (
    <>
      {/* Gradient track segments */}
      {gradientSegments.map((segment, i) => (
        <Polyline
          key={i}
          positions={segment.positions}
          pathOptions={{
            color: segment.color,
            weight: 4,
            opacity: 0.9
          }}
        />
      ))}
    </>
  )
}

export default function DevicesMap({
  devices,
  onSelectDevice
}: {
  devices: Device[]
  onSelectDevice: (id: number) => void
}) {
  const [showTracks, setShowTracks] = useState(false)
  const [selectedTrackDevice, setSelectedTrackDevice] = useState<number | null>(null)
  const [token, setToken] = useState<string | null>(null)

  // Get token from localStorage
  useEffect(() => {
    setToken(localStorage.getItem('token'))
  }, [])

  // Filter devices with valid coordinates
  const devicesWithCoords = devices.filter(
    d =>
      d.latitude !== undefined &&
      d.longitude !== undefined &&
      d.latitude !== null &&
      d.longitude !== null &&
      !isNaN(d.latitude) &&
      !isNaN(d.longitude)
  )

  if (devicesWithCoords.length === 0) {
    return null
  }

  // Default center (will be overridden by FitBounds)
  const center: [number, number] = [
    devicesWithCoords[0].latitude!,
    devicesWithCoords[0].longitude!
  ]

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="text-2xl">🗺️</span>
          Расположение транспортных средств ({devicesWithCoords.length})
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setShowTracks(!showTracks)
              if (showTracks) {
                setSelectedTrackDevice(null)
              }
            }}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              showTracks
                ? 'bg-amber-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {showTracks ? '🎯 Скрыть треки' : '📍 Показать треки'}
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-3 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-green-500"></div>
          <span className="text-slate-400">Двигатель работает</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-blue-500"></div>
          <span className="text-slate-400">На охране</span>
        </div>
        {showTracks && (
          <div className="flex items-center gap-2">
            <div className="w-16 h-2 rounded" style={{ background: 'linear-gradient(to right, #f59e0b, #22c55e)' }}></div>
            <span className="text-slate-400">Маршрут (оранжевый → начало, зелёный → конец)</span>
          </div>
        )}
      </div>

      <div className="rounded-lg overflow-hidden border border-slate-700" style={{ height: '500px' }}>
        <MapContainer
          center={center}
          zoom={13}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds devices={devicesWithCoords} />

          {/* Show tracks for all devices or selected device */}
          {showTracks && devicesWithCoords.map(device => (
            <DeviceTrack
              key={device.id}
              deviceId={device.id}
              showTrack={selectedTrackDevice === null || selectedTrackDevice === device.id}
              token={token}
            />
          ))}

          {/* Device markers */}
          {devicesWithCoords.map((device, index) => (
            <Marker
              key={device.id}
              position={[device.latitude!, device.longitude!]}
              icon={createDeviceMarker(device.name, !!device.ign_state, index)}
              eventHandlers={{
                click: () => {
                  if (showTracks) {
                    setSelectedTrackDevice(selectedTrackDevice === device.id ? null : device.id)
                  } else {
                    onSelectDevice(device.id)
                  }
                }
              }}
            >
              <Popup>
                <div className="p-1 min-w-[200px]">
                  <div className="font-bold text-lg mb-2">{device.name}</div>
                  <div className="space-y-1 text-sm">
                    <div className="flex items-center gap-2">
                      <span>{device.ign_state ? '🚗' : '🔒'}</span>
                      <span>{device.ign_state ? 'Двигатель работает' : 'На охране'}</span>
                    </div>
                    <div>⚡ Скорость: {device.speed ?? 0} км/ч</div>
                    <div>🔋 Напряжение: {device.battery_voltage ?? '-'} В</div>
                    <div>🌡️ Температура: {device.temp_inner ?? '-'}°C</div>
                    {device.mileage !== undefined && device.mileage !== null && (
                      <div>📏 Пробег: {device.mileage.toLocaleString()} км</div>
                    )}
                    {device.fuel_litres !== undefined && device.fuel_litres !== null && (
                      <div>⛽ Топливо: {device.fuel_litres} л</div>
                    )}
                  </div>
                  <div className="mt-3 pt-2 border-t flex gap-2">
                    <a
                      href={`https://www.openstreetmap.org/?mlat=${device.latitude}&mlon=${device.longitude}#map=16/${device.latitude}/${device.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline text-xs"
                      onClick={e => e.stopPropagation()}
                    >
                      OSM
                    </a>
                    <a
                      href={`https://yandex.ru/maps/?pt=${device.longitude},${device.latitude}&z=16&l=map`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline text-xs"
                      onClick={e => e.stopPropagation()}
                    >
                      Яндекс
                    </a>
                    <a
                      href={`https://www.google.com/maps?q=${device.latitude},${device.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline text-xs"
                      onClick={e => e.stopPropagation()}
                    >
                      Google
                    </a>
                  </div>
                  {showTracks && (
                    <button
                      className="mt-2 w-full px-2 py-1 bg-amber-600 text-white rounded text-xs hover:bg-amber-700"
                      onClick={e => {
                        e.stopPropagation()
                        setSelectedTrackDevice(selectedTrackDevice === device.id ? null : device.id)
                      }}
                    >
                      {selectedTrackDevice === device.id ? 'Показать все треки' : 'Только этот трек'}
                    </button>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}

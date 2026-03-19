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
  token,
  hours
}: {
  deviceId: number
  showTrack: boolean
  token: string | null
  hours: number
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
        const res = await fetch(`${API_BASE}/api/devices/${deviceId}/track?hours=${hours}`, {
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
  }, [deviceId, showTrack, token, hours])

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
  const [enabledTracks, setEnabledTracks] = useState<Set<number>>(new Set())
  const [token, setToken] = useState<string | null>(null)
  const [trackHours, setTrackHours] = useState(24)

  // Period options for track
  const periodOptions = [
    { value: 6, label: '6 часов' },
    { value: 12, label: '12 часов' },
    { value: 24, label: '24 часа' },
    { value: 72, label: '3 дня' },
    { value: 168, label: '7 дней' },
    { value: 720, label: '30 дней' },
  ]

  // Get token from localStorage
  useEffect(() => {
    setToken(localStorage.getItem('token'))
  }, [])

  // Initialize all tracks enabled when showTracks becomes true
  useEffect(() => {
    if (showTracks) {
      setEnabledTracks(new Set(devicesWithCoords.map(d => d.id)))
    }
  }, [showTracks])

  const toggleTrack = (deviceId: number) => {
    const newEnabled = new Set(enabledTracks)
    if (newEnabled.has(deviceId)) {
      newEnabled.delete(deviceId)
    } else {
      newEnabled.add(deviceId)
    }
    setEnabledTracks(newEnabled)
  }

  const enableAllTracks = () => {
    setEnabledTracks(new Set(devicesWithCoords.map(d => d.id)))
  }

  const disableAllTracks = () => {
    setEnabledTracks(new Set())
  }

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
        <div className="flex items-center gap-3">
          {showTracks && (
            <>
              <select
                value={trackHours}
                onChange={(e) => setTrackHours(Number(e.target.value))}
                className="px-3 py-1.5 rounded text-sm bg-slate-700 text-slate-300 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {periodOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <button
                onClick={enableAllTracks}
                className="px-2 py-1 rounded text-xs bg-slate-600 text-slate-300 hover:bg-slate-500"
                title="Включить все треки"
              >
                ✓ Все
              </button>
              <button
                onClick={disableAllTracks}
                className="px-2 py-1 rounded text-xs bg-slate-600 text-slate-300 hover:bg-slate-500"
                title="Выключить все треки"
              >
                ✕ Сброс
              </button>
            </>
          )}
          <button
            onClick={() => {
              setShowTracks(!showTracks)
              if (!showTracks) {
                setEnabledTracks(new Set(devicesWithCoords.map(d => d.id)))
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

      {/* Legend and Track Toggles */}
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

      {/* Device track toggles */}
      {showTracks && (
        <div className="flex flex-wrap gap-2 mb-3">
          {devicesWithCoords.map(device => (
            <label
              key={device.id}
              className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-700/50 cursor-pointer hover:bg-slate-700 transition-colors"
            >
              <input
                type="checkbox"
                checked={enabledTracks.has(device.id)}
                onChange={() => toggleTrack(device.id)}
                className="w-4 h-4 rounded border-slate-500 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="text-sm text-slate-300">{device.name}</span>
            </label>
          ))}
        </div>
      )}

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

          {/* Show tracks for enabled devices */}
          {showTracks && devicesWithCoords.map(device => (
            <DeviceTrack
              key={device.id}
              deviceId={device.id}
              showTrack={enabledTracks.has(device.id)}
              token={token}
              hours={trackHours}
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
                  onSelectDevice(device.id)
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
                        toggleTrack(device.id)
                      }}
                    >
                      {enabledTracks.has(device.id) ? 'Скрыть трек' : 'Показать трек'}
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

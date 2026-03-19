'use client'

import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix for default marker icon in react-leaflet
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
})

L.Marker.prototype.options.icon = defaultIcon

// Custom colored icons for different states
const createColoredIcon = (color: string) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      background-color: ${color};
      width: 30px;
      height: 30px;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      border: 2px solid white;
      box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30]
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

export default function DevicesMap({
  devices,
  onSelectDevice
}: {
  devices: Device[]
  onSelectDevice: (id: number) => void
}) {
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
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <span className="text-2xl">🗺️</span>
        Расположение транспортных средств ({devicesWithCoords.length})
      </h2>
      <div className="rounded-lg overflow-hidden border border-slate-700" style={{ height: '400px' }}>
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
          {devicesWithCoords.map(device => (
            <Marker
              key={device.id}
              position={[device.latitude!, device.longitude!]}
              icon={createColoredIcon(device.ign_state ? '#22c55e' : '#3b82f6')}
              eventHandlers={{
                click: () => onSelectDevice(device.id)
              }}
            >
              <Popup>
                <div className="p-1">
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
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}

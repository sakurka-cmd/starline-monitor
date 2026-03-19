'use client'

import { useState, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'

// Dynamic import for Leaflet map (SSR disabled)
const DevicesMap = dynamic(() => import('@/components/DevicesMap'), {
  ssr: false,
  loading: () => (
    <div className="mt-8 h-[400px] rounded-lg border border-slate-700 bg-slate-800/50 flex items-center justify-center">
      <div className="text-slate-400">Загрузка карты...</div>
    </div>
  )
})
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import {
  Shield, Flame, Thermometer, Battery, Droplet, Gauge, Clock, MapPin,
  Plus, Trash2, LogOut, Car, Wrench, AlertTriangle, CheckCircle,
  TrendingUp, Calendar, FuelIcon, Settings
} from 'lucide-react'
import { toast } from 'sonner'

// Types
interface User {
  id: number
  email: string
  name: string
}

interface Device {
  id: number
  name: string
  starline_device_id: string | null
  device_name: string | null
  is_active: number
  last_update: string | null
  created_at: string
  arm_state?: number
  ign_state?: number
  temp_inner?: number
  temp_engine?: number
  balance?: number
  latitude?: number
  longitude?: number
  state_timestamp?: string
  mileage?: number
  fuel_litres?: number
  motohrs?: number
  speed?: number
  battery_voltage?: number
}

interface DeviceState {
  timestamp: string
  arm_state: number
  ign_state: number
  temp_inner: number
  temp_engine: number
  balance: number
  latitude: number
  longitude: number
  speed: number
  mileage: number
  fuel_litres: number
  motohrs: number
  battery_voltage: number
}

interface ServiceType {
  id: number
  name: string
  default_interval_km: number | null
  default_interval_hours: number | null
}

interface MaintenanceRecord {
  id: number
  device_id: number
  service_type: string
  description: string | null
  mileage_at_service: number | null
  motohrs_at_service: number | null
  service_date: string
  next_service_mileage: number | null
  next_service_motohrs: number | null
  cost: number | null
  notes: string | null
  created_at: string
  current_mileage?: number
  current_motohrs?: number
  km_since_service?: number
  hours_since_service?: number
}

interface UpcomingMaintenance extends MaintenanceRecord {
  km_left?: number
  hours_left?: number
  is_overdue: boolean
}

interface Stats {
  current: { mileage: number; motohrs: number; timestamp: string } | null
  previous: { mileage: number; motohrs: number; timestamp: string } | null
  mileage_diff?: number
  motohrs_diff?: number
  fuel_stats?: { avg_fuel: number; min_fuel: number; max_fuel: number }
}

// API Base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Auth context
function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async (token: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data)
        localStorage.setItem('token', token)
      } else {
        localStorage.removeItem('token')
      }
    } catch {
      localStorage.removeItem('token')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchUser(token)
    } else {
      setLoading(false)
    }
  }, [fetchUser])

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) throw new Error('Неверные данные')
    const data = await res.json()
    localStorage.setItem('token', data.token)
    setUser(data.user)
    return data
  }

  const register = async (email: string, password: string, name: string) => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name })
    })
    if (!res.ok) throw new Error('Ошибка регистрации')
    const data = await res.json()
    localStorage.setItem('token', data.token)
    setUser(data.user)
    return data
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  return { user, loading, login, register, logout }
}

// Auth Form Component
function AuthForm({ onLogin, onRegister }: {
  onLogin: (email: string, password: string) => Promise<void>
  onRegister: (email: string, password: string, name: string) => Promise<void>
}) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isLogin) {
        await onLogin(email, password)
      } else {
        await onRegister(email, password, name)
      }
      toast.success(isLogin ? 'Вход выполнен' : 'Регистрация успешна')
    } catch (err: any) {
      toast.error(err.message || 'Ошибка')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      <Card className="w-full max-w-md bg-slate-800/50 border-slate-700 backdrop-blur">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Car className="h-12 w-12 text-blue-500" />
          </div>
          <CardTitle className="text-2xl text-white">StarLine Monitor</CardTitle>
          <CardDescription className="text-slate-400">
            {isLogin ? 'Войдите в аккаунт' : 'Создайте аккаунт'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="name" className="text-slate-300">Имя</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="bg-slate-700/50 border-slate-600 text-white"
                  required={!isLogin}
                />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-slate-300">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="bg-slate-700/50 border-slate-600 text-white"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-slate-300">Пароль</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="bg-slate-700/50 border-slate-600 text-white"
                required
              />
            </div>
            <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-700" disabled={loading}>
              {loading ? 'Загрузка...' : (isLogin ? 'Войти' : 'Зарегистрироваться')}
            </Button>
          </form>
          <div className="mt-4 text-center">
            <Button
              variant="link"
              onClick={() => setIsLogin(!isLogin)}
              className="text-slate-400 hover:text-white"
            >
              {isLogin ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Device Card Component
function DeviceCard({ device, onClick, onDelete }: {
  device: Device
  onClick: () => void
  onDelete: () => void
}) {
  const formatDate = (date: string | null) => {
    if (!date) return 'Нет данных'
    return new Date(date).toLocaleString('ru-RU')
  }

  const isRecent = (date: string | null) => {
    if (!date) return false
    const diff = Date.now() - new Date(date).getTime()
    return diff < 5 * 60 * 1000 // 5 minutes
  }

  return (
    <Card
      className="bg-slate-800/50 border-slate-700 hover:border-blue-500/50 transition-all cursor-pointer"
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg text-white">{device.name}</CardTitle>
            <CardDescription className="text-slate-400">
              {device.device_name || 'Синхронизация...'}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            {isRecent(device.state_timestamp) && (
              <Badge variant="default" className="bg-green-600">Онлайн</Badge>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-slate-400 hover:text-red-400"
              onClick={(e) => { e.stopPropagation(); onDelete() }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex items-center gap-2">
            <Shield className={`h-4 w-4 ${device.arm_state ? 'text-green-500' : 'text-slate-500'}`} />
            <span className="text-sm text-slate-300">
              {device.arm_state ? 'Охрана' : 'Снято'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Flame className={`h-4 w-4 ${device.ign_state ? 'text-orange-500' : 'text-slate-500'}`} />
            <span className="text-sm text-slate-300">
              {device.ign_state ? 'Зажигание' : 'Выкл'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Thermometer className="h-4 w-4 text-blue-400" />
            <span className="text-sm text-slate-300">
              {device.temp_inner?.toFixed(0) ?? '--'}° / {device.temp_engine?.toFixed(0) ?? '--'}°
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-purple-400" />
            <span className="text-sm text-slate-300">
              {device.speed ?? 0} км/ч
            </span>
          </div>
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-cyan-400" />
            <span className="text-sm text-slate-300">
              {device.mileage?.toLocaleString() ?? '--'} км
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Droplet className="h-4 w-4 text-yellow-400" />
            <span className="text-sm text-slate-300">
              {device.fuel_litres?.toFixed(1) ?? '--'} л
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Battery className="h-4 w-4 text-green-400" />
            <span className="text-sm text-slate-300">
              {device.battery_voltage?.toFixed(1) ?? '--'} В
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">💰</span>
            <span className="text-sm text-slate-300">
              {device.balance?.toFixed(0) ?? '--'} ₽
            </span>
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-3">
          Обновлено: {formatDate(device.state_timestamp)}
        </p>
      </CardContent>
    </Card>
  )
}

// Add Device Dialog
function AddDeviceDialog({ open, onOpenChange, onAdd }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (data: { name: string; app_id: string; app_secret: string; starline_login: string; starline_password: string }) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [appId, setAppId] = useState('')
  const [appSecret, setAppSecret] = useState('')
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onAdd({ name, app_id: appId, app_secret: appSecret, starline_login: login, starline_password: password })
      toast.success('Устройство добавлено')
      onOpenChange(false)
      setName(''); setAppId(''); setAppSecret(''); setLogin(''); setPassword('')
    } catch (err: any) {
      toast.error(err.message || 'Ошибка')
    }
    setLoading(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-white">Добавить устройство</DialogTitle>
          <DialogDescription className="text-slate-400">
            Введите данные для подключения к StarLine API
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label className="text-slate-300">Название</Label>
            <Input value={name} onChange={e => setName(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" required />
          </div>
          <div className="space-y-2">
            <Label className="text-slate-300">App ID</Label>
            <Input value={appId} onChange={e => setAppId(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" required />
          </div>
          <div className="space-y-2">
            <Label className="text-slate-300">App Secret</Label>
            <Input type="password" value={appSecret} onChange={e => setAppSecret(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" required />
          </div>
          <div className="space-y-2">
            <Label className="text-slate-300">Логин StarLine</Label>
            <Input value={login} onChange={e => setLogin(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" required />
          </div>
          <div className="space-y-2">
            <Label className="text-slate-300">Пароль StarLine</Label>
            <Input type="password" value={password} onChange={e => setPassword(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" required />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} className="border-slate-600">Отмена</Button>
            <Button type="submit" disabled={loading} className="bg-blue-600 hover:bg-blue-700">
              {loading ? 'Добавление...' : 'Добавить'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// Add Maintenance Dialog
function AddMaintenanceDialog({ open, onOpenChange, onAdd, serviceTypes, currentMileage, currentMotohrs }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (data: any) => Promise<void>
  serviceTypes: ServiceType[]
  currentMileage?: number
  currentMotohrs?: number
}) {
  const [serviceType, setServiceType] = useState('')
  const [description, setDescription] = useState('')
  const [mileage, setMileage] = useState<string>('')
  const [motohrs, setMotohrs] = useState<string>('')
  const [serviceDate, setServiceDate] = useState(new Date().toISOString().split('T')[0])
  const [nextMileage, setNextMileage] = useState<string>('')
  const [nextMotohrs, setNextMotohrs] = useState<string>('')
  const [cost, setCost] = useState<string>('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)

  // Initialize form with current values when dialog opens
  const handleOpenChange = (open: boolean) => {
    if (open) {
      if (currentMileage !== undefined) setMileage(currentMileage.toString())
      if (currentMotohrs !== undefined) setMotohrs(currentMotohrs.toString())
    }
    onOpenChange(open)
  }

  const handleServiceTypeChange = (value: string) => {
    setServiceType(value)
    const selected = serviceTypes.find(s => s.name === value)
    if (selected) {
      const currentMileageNum = parseInt(mileage) || currentMileage || 0
      const currentMotohrsNum = parseInt(motohrs) || currentMotohrs || 0
      if (selected.default_interval_km) {
        setNextMileage((currentMileageNum + selected.default_interval_km).toString())
      }
      if (selected.default_interval_hours) {
        setNextMotohrs((currentMotohrsNum + selected.default_interval_hours).toString())
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onAdd({
        service_type: serviceType,
        description: description || null,
        mileage_at_service: mileage ? parseInt(mileage) : null,
        motohrs_at_service: motohrs ? parseInt(motohrs) : null,
        service_date: serviceDate,
        next_service_mileage: nextMileage ? parseInt(nextMileage) : null,
        next_service_motohrs: nextMotohrs ? parseInt(nextMotohrs) : null,
        cost: cost ? parseFloat(cost) : null,
        notes: notes || null
      })
      toast.success('Запись добавлена')
      onOpenChange(false)
    } catch (err: any) {
      toast.error(err.message || 'Ошибка')
    }
    setLoading(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-white">Добавить запись ТО</DialogTitle>
          <DialogDescription className="text-slate-400">
            Запишите проведённое обслуживание
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label className="text-slate-300">Тип обслуживания</Label>
            <Select value={serviceType} onValueChange={handleServiceTypeChange}>
              <SelectTrigger className="bg-slate-700/50 border-slate-600 text-white">
                <SelectValue placeholder="Выберите тип" />
              </SelectTrigger>
              <SelectContent className="bg-slate-700 border-slate-600">
                {serviceTypes.map(st => (
                  <SelectItem key={st.id} value={st.name} className="text-white hover:bg-slate-600">
                    {st.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-slate-300">Описание</Label>
            <Input value={description} onChange={e => setDescription(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Пробег (км)</Label>
              <Input type="number" value={mileage} onChange={e => setMileage(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Моточасы</Label>
              <Input type="number" value={motohrs} onChange={e => setMotohrs(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" />
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-slate-300">Дата обслуживания</Label>
            <Input type="date" value={serviceDate} onChange={e => setServiceDate(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">След. ТО (км)</Label>
              <Input type="number" value={nextMileage} onChange={e => setNextMileage(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">След. ТО (мч)</Label>
              <Input type="number" value={nextMotohrs} onChange={e => setNextMotohrs(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" />
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-slate-300">Стоимость (₽)</Label>
            <Input type="number" value={cost} onChange={e => setCost(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" />
          </div>
          <div className="space-y-2">
            <Label className="text-slate-300">Заметки</Label>
            <Textarea value={notes} onChange={e => setNotes(e.target.value)} className="bg-slate-700/50 border-slate-600 text-white" />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} className="border-slate-600">Отмена</Button>
            <Button type="submit" disabled={loading} className="bg-blue-600 hover:bg-blue-700">
              {loading ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// Device Detail Component
function DeviceDetail({ deviceId, onBack }: { deviceId: number; onBack: () => void }) {
  const [device, setDevice] = useState<Device | null>(null)
  const [states, setStates] = useState<DeviceState[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [maintenance, setMaintenance] = useState<MaintenanceRecord[]>([])
  const [upcoming, setUpcoming] = useState<UpcomingMaintenance[]>([])
  const [serviceTypes, setServiceTypes] = useState<ServiceType[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [addMaintOpen, setAddMaintOpen] = useState(false)
  const [chartHours, setChartHours] = useState(24)

  // Period options for charts
  const chartPeriodOptions = [
    { value: 6, label: '6 часов' },
    { value: 12, label: '12 часов' },
    { value: 24, label: '24 часа' },
    { value: 72, label: '3 дня' },
    { value: 168, label: '7 дней' },
    { value: 720, label: '30 дней' },
  ]

  const fetchData = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) return

    setLoading(true)
    try {
      const headers = { Authorization: `Bearer ${token}` }

      const [deviceRes, statesRes, statsRes, maintRes, upcomingRes, typesRes] = await Promise.all([
        fetch(`${API_BASE}/api/devices/${deviceId}/latest`, { headers }),
        fetch(`${API_BASE}/api/devices/${deviceId}/state?hours=${chartHours}`, { headers }),
        fetch(`${API_BASE}/api/devices/${deviceId}/stats?days=7`, { headers }),
        fetch(`${API_BASE}/api/devices/${deviceId}/maintenance`, { headers }),
        fetch(`${API_BASE}/api/devices/${deviceId}/maintenance/upcoming`, { headers }),
        fetch(`${API_BASE}/api/service-types`, { headers })
      ])

      if (deviceRes.ok) {
        const data = await deviceRes.json()
        setDevice(data.device)
      }
      if (statesRes.ok) setStates(await statesRes.json())
      if (statsRes.ok) setStats(await statsRes.json())
      if (maintRes.ok) setMaintenance(await maintRes.json())
      if (upcomingRes.ok) setUpcoming(await upcomingRes.json())
      if (typesRes.ok) setServiceTypes(await typesRes.json())
    } catch (err) {
      toast.error('Ошибка загрузки данных')
    }
    setLoading(false)
  }, [deviceId, chartHours])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData()
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [fetchData])

  const addMaintenance = async (data: any) => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_BASE}/api/devices/${deviceId}/maintenance`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })
    if (!res.ok) throw new Error('Ошибка')
    fetchData()
  }

  const deleteMaintenance = async (mid: number) => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_BASE}/api/devices/${deviceId}/maintenance/${mid}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('Ошибка')
    fetchData()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    )
  }

  if (!device) {
    return (
      <div className="text-center text-slate-400">
        Устройство не найдено
        <Button onClick={onBack} variant="link" className="block mx-auto mt-2">Назад</Button>
      </div>
    )
  }

  const chartData = states.map(s => {
    const date = new Date(s.timestamp)
    return {
      time: date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      date: date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
      fullDate: date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }),
      temp_inner: s.temp_inner,
      temp_engine: s.temp_engine,
      mileage: s.mileage,
      fuel: s.fuel_litres,
      speed: s.speed,
      battery_voltage: s.battery_voltage,
      balance: s.balance
    }
  }).reverse()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={onBack} className="text-slate-400 hover:text-white">
            ← Назад
          </Button>
          <div>
            <h2 className="text-2xl font-bold text-white">{device.name}</h2>
            <p className="text-slate-400">{device.device_name || 'Синхронизация...'}</p>
          </div>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Shield className={`h-5 w-5 ${device.arm_state ? 'text-green-500' : 'text-slate-500'}`} />
              <div>
                <p className="text-sm text-slate-400">Охрана</p>
                <p className="text-lg font-semibold text-white">{device.arm_state ? 'Включена' : 'Выключена'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Flame className={`h-5 w-5 ${device.ign_state ? 'text-orange-500' : 'text-slate-500'}`} />
              <div>
                <p className="text-sm text-slate-400">Зажигание</p>
                <p className="text-lg font-semibold text-white">{device.ign_state ? 'Включено' : 'Выключено'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Gauge className="h-5 w-5 text-purple-400" />
              <div>
                <p className="text-sm text-slate-400">Скорость</p>
                <p className="text-lg font-semibold text-white">{device.speed ?? 0} км/ч</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Battery className="h-5 w-5 text-green-400" />
              <div>
                <p className="text-sm text-slate-400">Баланс</p>
                <p className="text-lg font-semibold text-white">{device.balance?.toFixed(0) ?? '--'} ₽</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <MapPin className="h-6 w-6 text-cyan-400" />
              <div>
                <p className="text-sm text-slate-400">Пробег</p>
                <p className="text-2xl font-bold text-white">{device.mileage?.toLocaleString() ?? '--'} км</p>
                {stats?.mileage_diff && (
                  <p className="text-xs text-green-400">+{stats.mileage_diff.toLocaleString()} км за 7 дней</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Droplet className="h-6 w-6 text-yellow-400" />
              <div>
                <p className="text-sm text-slate-400">Топливо</p>
                <p className="text-2xl font-bold text-white">{device.fuel_litres?.toFixed(1) ?? '--'} л</p>
                {stats?.fuel_stats && (
                  <p className="text-xs text-slate-400">Средн: {stats.fuel_stats.avg_fuel?.toFixed(1)} л</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Battery className="h-6 w-6 text-green-400" />
              <div>
                <p className="text-sm text-slate-400">Напряжение АКБ</p>
                <p className="text-2xl font-bold text-white">{device.battery_voltage?.toFixed(1) ?? '--'} В</p>
                <p className="text-xs text-slate-500">
                  {(device.battery_voltage ?? 0) >= 12.5 ? '✓ Норма' : (device.battery_voltage ?? 0) >= 12.0 ? '⚠ Низкое' : '❌ Критическое'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Upcoming Maintenance Alerts */}
      {upcoming.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Предстоящее ТО
          </h3>
          <div className="grid gap-2">
            {upcoming.map(u => (
              <Alert
                key={u.id}
                className={u.is_overdue ? 'bg-red-900/30 border-red-700' : 'bg-yellow-900/30 border-yellow-700'}
              >
                <AlertTriangle className={`h-4 w-4 ${u.is_overdue ? 'text-red-500' : 'text-yellow-500'}`} />
                <AlertTitle className="text-white">{u.service_type}</AlertTitle>
                <AlertDescription className="text-slate-300">
                  {u.km_left !== null && u.km_left !== undefined && (
                    <span className={u.km_left < 0 ? 'text-red-400' : ''}>
                      Осталось {u.km_left.toLocaleString()} км
                    </span>
                  )}
                  {u.hours_left !== null && u.hours_left !== undefined && (
                    <span className={u.hours_left < 0 ? 'text-red-400' : ''}>
                      {' / '}{u.hours_left.toLocaleString()} мч
                    </span>
                  )}
                </AlertDescription>
              </Alert>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-slate-800 border-slate-700">
          <TabsTrigger value="overview" className="data-[state=active]:bg-slate-700">Обзор</TabsTrigger>
          <TabsTrigger value="maintenance" className="data-[state=active]:bg-slate-700">ТО</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Period Selector */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400">Период графиков:</span>
            <select
              value={chartHours}
              onChange={(e) => setChartHours(Number(e.target.value))}
              className="px-3 py-1.5 rounded text-sm bg-slate-700 text-slate-300 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {chartPeriodOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Temperature Chart */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">Температура</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #374151' }}
                      labelStyle={{ color: '#fff' }}
                      labelFormatter={(label, payload) => {
                        const data = payload?.[0]?.payload
                        return data ? `${data.date} ${label}` : label
                      }}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="temp_inner" stroke="#3b82f6" name="Салон" dot={false} />
                    <Line type="monotone" dataKey="temp_engine" stroke="#ef4444" name="Двигатель" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Battery Voltage Chart */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">Напряжение АКБ</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" domain={[11, 15]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #374151' }}
                      labelStyle={{ color: '#fff' }}
                      labelFormatter={(label, payload) => {
                        const data = payload?.[0]?.payload
                        return data ? `${data.date} ${label}` : label
                      }}
                      formatter={(value: number) => [`${value?.toFixed(1)} В`, 'Напряжение']}
                    />
                    <Line type="monotone" dataKey="battery_voltage" stroke="#22c55e" name="Напряжение (В)" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Speed Chart */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">Скорость</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #374151' }}
                      labelStyle={{ color: '#fff' }}
                      labelFormatter={(label, payload) => {
                        const data = payload?.[0]?.payload
                        return data ? `${data.date} ${label}` : label
                      }}
                      formatter={(value: number) => [`${value ?? 0} км/ч`, 'Скорость']}
                    />
                    <Line type="monotone" dataKey="speed" stroke="#f59e0b" name="Скорость (км/ч)" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Fuel Chart */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">Топливо</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #374151' }}
                      labelStyle={{ color: '#fff' }}
                      labelFormatter={(label, payload) => {
                        const data = payload?.[0]?.payload
                        return data ? `${data.date} ${label}` : label
                      }}
                      formatter={(value: number) => [`${value?.toFixed(1)} л`, 'Топливо']}
                    />
                    <Line type="monotone" dataKey="fuel" stroke="#eab308" name="Топливо (л)" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Balance Chart */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">Баланс SIM</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #374151' }}
                      labelStyle={{ color: '#fff' }}
                      labelFormatter={(label, payload) => {
                        const data = payload?.[0]?.payload
                        return data ? `${data.date} ${label}` : label
                      }}
                      formatter={(value: number) => [`${value?.toFixed(0)} ₽`, 'Баланс']}
                    />
                    <Line type="monotone" dataKey="balance" stroke="#8b5cf6" name="Баланс (₽)" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="maintenance" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-white">История обслуживания</h3>
            <Button onClick={() => setAddMaintOpen(true)} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="h-4 w-4 mr-2" /> Добавить запись
            </Button>
          </div>

          {maintenance.length === 0 ? (
            <Card className="bg-slate-800/50 border-slate-700">
              <CardContent className="p-8 text-center text-slate-400">
                <Wrench className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Записей ТО пока нет</p>
                <p className="text-sm">Нажмите "Добавить запись" чтобы начать</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-slate-800/50 border-slate-700">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-700 hover:bg-slate-700/50">
                    <TableHead className="text-slate-400">Дата</TableHead>
                    <TableHead className="text-slate-400">Тип</TableHead>
                    <TableHead className="text-slate-400">Пробег</TableHead>
                    <TableHead className="text-slate-400">Моточасы</TableHead>
                    <TableHead className="text-slate-400">Стоимость</TableHead>
                    <TableHead className="text-slate-400"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {maintenance.map(m => (
                    <TableRow key={m.id} className="border-slate-700 hover:bg-slate-700/50">
                      <TableCell className="text-white">{new Date(m.service_date).toLocaleDateString('ru-RU')}</TableCell>
                      <TableCell className="text-white">{m.service_type}</TableCell>
                      <TableCell className="text-white">{m.mileage_at_service?.toLocaleString() ?? '--'} км</TableCell>
                      <TableCell className="text-white">{m.motohrs_at_service?.toLocaleString() ?? '--'} мч</TableCell>
                      <TableCell className="text-white">{m.cost ? `${m.cost.toLocaleString()} ₽` : '--'}</TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-slate-400 hover:text-red-400"
                          onClick={() => { deleteMaintenance(m.id); toast.success('Запись удалена') }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      <AddMaintenanceDialog
        open={addMaintOpen}
        onOpenChange={setAddMaintOpen}
        onAdd={addMaintenance}
        serviceTypes={serviceTypes}
        currentMileage={device.mileage}
        currentMotohrs={device.motohrs}
      />
    </div>
  )
}

// Main App Component
export default function Home() {
  const { user, loading, login, register, logout } = useAuth()
  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState<number | null>(null)
  const [addDeviceOpen, setAddDeviceOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const fetchDevices = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) return

    try {
      const res = await fetch(`${API_BASE}/api/devices`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setDevices(await res.json())
      }
    } catch (err) {
      console.error('Failed to fetch devices:', err)
    }
  }, [])

  useEffect(() => {
    if (user) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchDevices()
      const interval = setInterval(fetchDevices, 60000)
      return () => clearInterval(interval)
    }
  }, [user, fetchDevices])

  const addDevice = async (data: { name: string; app_id: string; app_secret: string; starline_login: string; starline_password: string }) => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_BASE}/api/devices`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })
    if (!res.ok) throw new Error('Ошибка')
    fetchDevices()
  }

  const deleteDevice = async (id: number) => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_BASE}/api/devices/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('Ошибка')
    fetchDevices()
    toast.success('Устройство удалено')
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchDevices()
    setRefreshing(false)
    toast.success('Данные обновлены')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    )
  }

  if (!user) {
    return <AuthForm onLogin={login} onRegister={register} />
  }

  if (selectedDevice !== null) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 md:p-6">
        <DeviceDetail deviceId={selectedDevice} onBack={() => setSelectedDevice(null)} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Car className="h-8 w-8 text-blue-500" />
            <div>
              <h1 className="text-xl font-bold text-white">StarLine Monitor</h1>
              <p className="text-sm text-slate-400">Добро пожаловать, {user.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleRefresh}
              disabled={refreshing}
              className="border-slate-600 text-slate-300 hover:bg-slate-700"
            >
              {refreshing ? 'Обновление...' : 'Обновить'}
            </Button>
            <Button
              variant="outline"
              onClick={() => setAddDeviceOpen(true)}
              className="border-slate-600 text-slate-300 hover:bg-slate-700"
            >
              <Plus className="h-4 w-4 mr-2" /> Добавить
            </Button>
            <Button
              variant="ghost"
              onClick={logout}
              className="text-slate-400 hover:text-white"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {devices.length === 0 ? (
          <div className="text-center py-12">
            <Car className="h-16 w-16 mx-auto text-slate-600 mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Нет устройств</h2>
            <p className="text-slate-400 mb-6">Добавьте ваше первое устройство StarLine</p>
            <Button onClick={() => setAddDeviceOpen(true)} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="h-4 w-4 mr-2" /> Добавить устройство
            </Button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {devices.map(device => (
                <DeviceCard
                  key={device.id}
                  device={device}
                  onClick={() => setSelectedDevice(device.id)}
                  onDelete={() => deleteDevice(device.id)}
                />
              ))}
            </div>

            {/* Map Section */}
            <DevicesMap devices={devices} onSelectDevice={setSelectedDevice} />
          </>
        )}
      </main>

      <AddDeviceDialog
        open={addDeviceOpen}
        onOpenChange={setAddDeviceOpen}
        onAdd={addDevice}
      />
    </div>
  )
}

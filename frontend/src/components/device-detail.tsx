'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import type { Device, DeviceState, DeviceStats } from '@/lib/types';
import { 
  Shield, 
  Key, 
  Thermometer, 
  Fuel, 
  Gauge, 
  Battery, 
  Clock,
  ArrowLeft,
  Ruble,
  TrendingUp,
  Activity
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { formatDistanceToNow, format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface DeviceDetailProps {
  device: Device | null;
  stateHistory: DeviceState[];
  stats: DeviceStats | null;
  isLoading: boolean;
  onBack: () => void;
  children?: React.ReactNode;
}

export function DeviceDetail({ 
  device, 
  stateHistory, 
  stats, 
  isLoading, 
  onBack,
  children 
}: DeviceDetailProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <Skeleton className="h-8 w-48" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!device) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
        <Gauge className="w-16 h-16 mb-4 opacity-50" />
        <p>Устройство не найдено</p>
        <Button variant="outline" onClick={onBack} className="mt-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Назад к списку
        </Button>
      </div>
    );
  }

  const state = device.latest_state;
  
  const formatTime = (timestamp: string | undefined) => {
    if (!timestamp) return 'Нет данных';
    try {
      return formatDistanceToNow(new Date(timestamp), { 
        addSuffix: true, 
        locale: ru 
      });
    } catch {
      return 'Нет данных';
    }
  };

  const formatValue = (value: number | null | undefined, suffix: string = '') => {
    if (value === null || value === undefined) return '—';
    return `${value.toFixed(1)}${suffix}`;
  };

  // Prepare chart data
  const chartData = stateHistory
    .filter(s => s.timestamp)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map(s => ({
      time: format(new Date(s.timestamp), 'HH:mm', { locale: ru }),
      fullTime: format(new Date(s.timestamp), 'dd.MM HH:mm', { locale: ru }),
      temp_inner: s.temp_inner,
      temp_engine: s.temp_engine,
      mileage: s.mileage,
      fuel_litres: s.fuel_litres,
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button 
          variant="ghost" 
          onClick={onBack}
          className="text-slate-400 hover:text-white hover:bg-slate-800"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Назад
        </Button>
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-lg bg-blue-600/20 border border-blue-500/30">
            <Gauge className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">{device.name}</h1>
            <p className="text-sm text-slate-400">
              Обновлено: {formatTime(state?.timestamp)}
            </p>
          </div>
        </div>
      </div>

      {/* Status Badges */}
      <div className="flex flex-wrap gap-3">
        <Badge 
          variant={state?.arm_state ? "default" : "secondary"}
          className={state?.arm_state 
            ? "bg-green-600/80 text-white hover:bg-green-700/80 text-base px-4 py-1" 
            : "bg-slate-700 text-slate-300 text-base px-4 py-1"}
        >
          <Shield className="w-4 h-4 mr-2" />
          Охрана {state?.arm_state ? 'ВКЛ' : 'ВЫКЛ'}
        </Badge>
        <Badge 
          variant={state?.ign_state ? "default" : "secondary"}
          className={state?.ign_state 
            ? "bg-orange-600/80 text-white hover:bg-orange-700/80 text-base px-4 py-1" 
            : "bg-slate-700 text-slate-300 text-base px-4 py-1"}
        >
          <Key className="w-4 h-4 mr-2" />
          Зажигание {state?.ign_state ? 'ВКЛ' : 'ВЫКЛ'}
        </Badge>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-600/20">
                <Ruble className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-xs text-slate-400">Баланс</p>
                <p className="text-lg font-semibold text-white">
                  {formatValue(state?.balance, ' ₽')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-600/20">
                <Gauge className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-slate-400">Пробег</p>
                <p className="text-lg font-semibold text-white">
                  {formatValue(state?.mileage, ' км')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-600/20">
                <Fuel className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <p className="text-xs text-slate-400">Топливо</p>
                <p className="text-lg font-semibold text-white">
                  {formatValue(state?.fuel_litres, ' л')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-600/20">
                <Clock className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-xs text-slate-400">Моточасы</p>
                <p className="text-lg font-semibold text-white">
                  {state?.motohrs?.toFixed(1) || '—'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-cyan-600/20">
                <Activity className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <p className="text-xs text-slate-400">Скорость</p>
                <p className="text-lg font-semibold text-white">
                  {formatValue(state?.speed, ' км/ч')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-600/20">
                <Battery className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs text-slate-400">Напряжение АКБ</p>
                <p className="text-lg font-semibold text-white">
                  {formatValue(state?.battery_voltage, ' В')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-teal-600/20">
                <Thermometer className="w-5 h-5 text-teal-400" />
              </div>
              <div>
                <p className="text-xs text-slate-400">Темп. салон</p>
                <p className="text-lg font-semibold text-white">
                  {formatValue(state?.temp_inner, '°C')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-600/20">
                <Thermometer className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <p className="text-xs text-slate-400">Темп. двигатель</p>
                <p className="text-lg font-semibold text-white">
                  {formatValue(state?.temp_engine, '°C')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="bg-gradient-to-br from-blue-900/50 to-slate-800/50 border-blue-700/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                Пробег за 7 дней
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-white">
                {stats.mileage_diff.toFixed(0)} км
              </p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-900/50 to-slate-800/50 border-purple-700/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                <Clock className="w-4 h-4 text-purple-400" />
                Моточасы за 7 дней
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-white">
                {stats.motohrs_diff.toFixed(1)} ч
              </p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-yellow-900/50 to-slate-800/50 border-yellow-700/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                <Fuel className="w-4 h-4 text-yellow-400" />
                Средний уровень топлива
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-white">
                {stats.fuel_avg.toFixed(1)} л
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Мин: {stats.fuel_min.toFixed(1)} / Макс: {stats.fuel_max.toFixed(1)}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Temperature Chart */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Thermometer className="w-5 h-5 text-blue-400" />
              История температур
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1E293B', 
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#fff'
                      }}
                      labelFormatter={(value, payload) => {
                        const item = payload?.[0]?.payload;
                        return item?.fullTime || value;
                      }}
                    />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="temp_inner" 
                      name="Салон" 
                      stroke="#06B6D4" 
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                    <Line 
                      type="monotone" 
                      dataKey="temp_engine" 
                      name="Двигатель" 
                      stroke="#F97316" 
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  Нет данных для отображения
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Fuel Chart */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Fuel className="w-5 h-5 text-yellow-400" />
              История уровня топлива
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1E293B', 
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#fff'
                      }}
                      labelFormatter={(value, payload) => {
                        const item = payload?.[0]?.payload;
                        return item?.fullTime || value;
                      }}
                    />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="fuel_litres" 
                      name="Топливо (л)" 
                      stroke="#EAB308" 
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  Нет данных для отображения
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Mileage Chart */}
        <Card className="bg-slate-800/50 border-slate-700 lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Gauge className="w-5 h-5 text-blue-400" />
              История пробега
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1E293B', 
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#fff'
                      }}
                      labelFormatter={(value, payload) => {
                        const item = payload?.[0]?.payload;
                        return item?.fullTime || value;
                      }}
                    />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="mileage" 
                      name="Пробег (км)" 
                      stroke="#3B82F6" 
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  Нет данных для отображения
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Children for maintenance section */}
      {children}
    </div>
  );
}

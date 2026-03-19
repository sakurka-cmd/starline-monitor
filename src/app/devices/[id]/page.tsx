'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import { useDeviceStore } from '@/store/devices';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DeviceChart } from '@/components/devices/DeviceChart';
import {
  Loader2,
  ArrowLeft,
  MapPin,
  Thermometer,
  Battery,
  Fuel,
  Gauge,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Clock,
  RefreshCw,
} from 'lucide-react';

export default function DeviceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const deviceId = params.id as string;
  
  const { isAuthenticated, isLoading: authLoading, fetchUser } = useAuthStore();
  const { 
    currentDevice, 
    history, 
    isLoading: deviceLoading, 
    isHistoryLoading,
    fetchDeviceState, 
    fetchDeviceHistory, 
    clearCurrentDevice,
    error 
  } = useDeviceStore();

  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h');

  const fetchHistoryForRange = (id: string, range: '24h' | '7d' | '30d') => {
    const end = new Date();
    const start = new Date();
    
    switch (range) {
      case '24h':
        start.setHours(start.getHours() - 24);
        break;
      case '7d':
        start.setDate(start.getDate() - 7);
        break;
      case '30d':
        start.setDate(start.getDate() - 30);
        break;
    }

    fetchDeviceHistory(id, start.toISOString(), end.toISOString());
  };

  const handleTimeRangeChange = (range: '24h' | '7d' | '30d') => {
    setTimeRange(range);
    if (deviceId) {
      fetchHistoryForRange(deviceId, range);
    }
  };

  const handleRefresh = () => {
    if (deviceId) {
      fetchDeviceState(deviceId);
      fetchHistoryForRange(deviceId, timeRange);
    }
  };

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && deviceId) {
      fetchDeviceState(deviceId);
      fetchHistoryForRange(deviceId, timeRange);
    }
  }, [isAuthenticated, deviceId, timeRange, fetchDeviceState]);

  useEffect(() => {
    return () => {
      clearCurrentDevice();
    };
  }, [clearCurrentDevice]);

  if (authLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (deviceLoading && !currentDevice) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!currentDevice) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="py-12 text-center">
            <p className="text-slate-400 mb-4">Устройство не найдено</p>
            <Button onClick={() => router.push('/dashboard')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Вернуться к устройствам
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const state = currentDevice.state;
  const gps = currentDevice.gps;

  const getAlarmBadge = () => {
    if (!state?.alarm_state) return null;
    
    const alarmState = state.alarm_state.toLowerCase();
    if (alarmState.includes('armed') || alarmState === 'on') {
      return (
        <Badge className="bg-green-600 text-white">
          <ShieldCheck className="w-4 h-4 mr-1" />
          Под охраной
        </Badge>
      );
    } else if (alarmState.includes('alarm') || alarmState.includes('triggered')) {
      return (
        <Badge variant="destructive">
          <ShieldAlert className="w-4 h-4 mr-1" />
          Тревога
        </Badge>
      );
    } else {
      return (
        <Badge variant="secondary">
          <Shield className="w-4 h-4 mr-1" />
          Снято с охраны
        </Badge>
      );
    }
  };

  const formatValue = (value: number | null | undefined, suffix: string = ''): string => {
    if (value === null || value === undefined) return '—';
    return `${value.toFixed(1)}${suffix}`;
  };

  const formatLastUpdate = (timestamp: string | null | undefined) => {
    if (!timestamp) return '—';
    return new Date(timestamp).toLocaleString('ru-RU');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 backdrop-blur-sm bg-slate-900/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => router.push('/dashboard')} className="text-slate-300">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Назад
            </Button>
            <div className="flex items-center gap-2">
              <svg className="h-8 w-8 text-primary" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
              </svg>
              <span className="text-xl font-bold text-white">StarLine Monitor</span>
            </div>
          </div>
          <Button variant="outline" onClick={handleRefresh} disabled={deviceLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${deviceLoading ? 'animate-spin' : ''}`} />
            Обновить
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Device Info */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-white">{currentDevice.name}</h1>
              {getAlarmBadge()}
            </div>
            <p className="text-slate-400">
              ID: {currentDevice.device_id_starline || 'Не синхронизирован'}
            </p>
            {state && (
              <p className="text-sm text-slate-500 flex items-center gap-1 mt-1">
                <Clock className="h-3 w-3" />
                Обновлено: {formatLastUpdate(state.timestamp)}
              </p>
            )}
          </div>
        </div>

        {error && (
          <Card className="mb-6 border-destructive bg-destructive/10">
            <CardContent className="py-4 text-destructive">
              {error}
            </CardContent>
          </Card>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Battery className="h-4 w-4 text-primary" />
                <span className="text-sm text-slate-400">Батарея</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {formatValue(state?.battery_voltage, ' В')}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Thermometer className="h-4 w-4 text-primary" />
                <span className="text-sm text-slate-400">Салон</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {formatValue(state?.interior_temp, '°C')}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Thermometer className="h-4 w-4 text-orange-500" />
                <span className="text-sm text-slate-400">Двигатель</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {formatValue(state?.engine_temp, '°C')}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Fuel className="h-4 w-4 text-primary" />
                <span className="text-sm text-slate-400">Топливо</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {state?.fuel_level !== null && state?.fuel_level !== undefined 
                  ? `${state.fuel_level}%` 
                  : '—'}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <Gauge className="h-4 w-4 text-primary" />
                <span className="text-sm text-slate-400">Пробег</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {state?.mileage !== null && state?.mileage !== undefined 
                  ? `${(state.mileage / 1000).toFixed(1)}k км` 
                  : '—'}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <MapPin className="h-4 w-4 text-primary" />
                <span className="text-sm text-slate-400">Скорость</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {gps?.speed !== null && gps?.speed !== undefined 
                  ? `${gps.speed} км/ч` 
                  : '0 км/ч'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* GPS Location */}
        {gps && (
          <Card className="bg-slate-800/50 border-slate-700 mb-8">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <MapPin className="h-5 w-5 text-primary" />
                GPS координаты
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-slate-400">Широта</p>
                  <p className="text-lg font-medium text-white">{gps.latitude.toFixed(6)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Долгота</p>
                  <p className="text-lg font-medium text-white">{gps.longitude.toFixed(6)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Высота</p>
                  <p className="text-lg font-medium text-white">
                    {gps.altitude !== null ? `${gps.altitude} м` : '—'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Charts */}
        <Tabs defaultValue="state" className="space-y-4">
          <TabsList>
            <TabsTrigger value="state">Состояние</TabsTrigger>
            <TabsTrigger value="gps">GPS история</TabsTrigger>
          </TabsList>

          <TabsContent value="state">
            <div className="flex gap-2 mb-4">
              <Button 
                variant={timeRange === '24h' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => handleTimeRangeChange('24h')}
              >
                24 часа
              </Button>
              <Button 
                variant={timeRange === '7d' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => handleTimeRangeChange('7d')}
              >
                7 дней
              </Button>
              <Button 
                variant={timeRange === '30d' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => handleTimeRangeChange('30d')}
              >
                30 дней
              </Button>
            </div>

            {isHistoryLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : (
              <DeviceChart 
                states={history?.states || []} 
                gpsPositions={history?.gps_positions}
                title="История показателей"
                description={`Данные за ${timeRange === '24h' ? '24 часа' : timeRange === '7d' ? '7 дней' : '30 дней'}`}
              />
            )}
          </TabsContent>

          <TabsContent value="gps">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">История перемещений</CardTitle>
                <CardDescription className="text-slate-400">
                  Последние GPS координаты устройства
                </CardDescription>
              </CardHeader>
              <CardContent>
                {history?.gps_positions && history.gps_positions.length > 0 ? (
                  <div className="max-h-96 overflow-y-auto space-y-2">
                    {history.gps_positions.slice().reverse().map((pos, index) => (
                      <div 
                        key={pos.id || index}
                        className="flex items-center justify-between p-3 rounded-lg bg-slate-700/50"
                      >
                        <div className="flex items-center gap-4">
                          <MapPin className="h-4 w-4 text-primary" />
                          <div>
                            <p className="text-white font-medium">
                              {pos.latitude.toFixed(6)}, {pos.longitude.toFixed(6)}
                            </p>
                            <p className="text-sm text-slate-400">
                              {new Date(pos.timestamp).toLocaleString('ru-RU')}
                            </p>
                          </div>
                        </div>
                        {pos.speed !== null && (
                          <Badge variant="outline">{pos.speed} км/ч</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-center py-8">
                    Нет данных о перемещениях
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

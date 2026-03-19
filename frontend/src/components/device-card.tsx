'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Device } from '@/lib/types';
import { 
  Shield, 
  Key, 
  Thermometer, 
  Fuel, 
  Gauge, 
  Battery, 
  Clock,
  Trash2,
  Eye,
  Ruble
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';

interface DeviceCardProps {
  device: Device;
  onDelete: (id: string) => void;
  onView: (id: string) => void;
}

export function DeviceCard({ device, onDelete, onView }: DeviceCardProps) {
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

  return (
    <Card className="bg-slate-800/50 border-slate-700 hover:border-blue-500/50 transition-all duration-200 group">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <div className="p-2 rounded-lg bg-blue-600/20 border border-blue-500/30">
              <Gauge className="w-5 h-5 text-blue-400" />
            </div>
            {device.name}
          </CardTitle>
          <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => onView(device.id)}
              className="text-slate-400 hover:text-blue-400 hover:bg-blue-600/20"
            >
              <Eye className="w-4 h-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => onDelete(device.id)}
              className="text-slate-400 hover:text-red-400 hover:bg-red-600/20"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Badges */}
        <div className="flex flex-wrap gap-2">
          <Badge 
            variant={state?.arm_state ? "default" : "secondary"}
            className={state?.arm_state 
              ? "bg-green-600/80 text-white hover:bg-green-700/80" 
              : "bg-slate-700 text-slate-300"}
          >
            <Shield className="w-3 h-3 mr-1" />
            Охрана {state?.arm_state ? 'ВКЛ' : 'ВЫКЛ'}
          </Badge>
          <Badge 
            variant={state?.ign_state ? "default" : "secondary"}
            className={state?.ign_state 
              ? "bg-orange-600/80 text-white hover:bg-orange-700/80" 
              : "bg-slate-700 text-slate-300"}
          >
            <Key className="w-3 h-3 mr-1" />
            Зажигание {state?.ign_state ? 'ВКЛ' : 'ВЫКЛ'}
          </Badge>
        </div>

        {/* Temperature Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
              <Thermometer className="w-3 h-3" />
              Салон
            </div>
            <div className="text-white font-medium">
              {formatValue(state?.temp_inner, '°C')}
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
              <Thermometer className="w-3 h-3 text-orange-400" />
              Двигатель
            </div>
            <div className="text-white font-medium">
              {formatValue(state?.temp_engine, '°C')}
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
          <div className="flex items-center gap-2 text-slate-300">
            <Ruble className="w-4 h-4 text-green-400" />
            <span className="text-slate-400">Баланс:</span>
            <span className="text-white">{formatValue(state?.balance, ' ₽')}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Gauge className="w-4 h-4 text-blue-400" />
            <span className="text-slate-400">Пробег:</span>
            <span className="text-white">{formatValue(state?.mileage, ' км')}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Fuel className="w-4 h-4 text-yellow-400" />
            <span className="text-slate-400">Топливо:</span>
            <span className="text-white">{formatValue(state?.fuel_litres, ' л')}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Clock className="w-4 h-4 text-purple-400" />
            <span className="text-slate-400">Моточасы:</span>
            <span className="text-white">{state?.motohrs?.toFixed(1) || '—'}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Gauge className="w-4 h-4 text-cyan-400" />
            <span className="text-slate-400">Скорость:</span>
            <span className="text-white">{formatValue(state?.speed, ' км/ч')}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Battery className="w-4 h-4 text-green-400" />
            <span className="text-slate-400">АКБ:</span>
            <span className="text-white">{formatValue(state?.battery_voltage, ' В')}</span>
          </div>
        </div>

        {/* Last Update */}
        <div className="pt-2 border-t border-slate-700/50 flex items-center gap-2 text-xs text-slate-500">
          <Clock className="w-3 h-3" />
          Обновлено: {formatTime(state?.timestamp)}
        </div>
      </CardContent>
    </Card>
  );
}

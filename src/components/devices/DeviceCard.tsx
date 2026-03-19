'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { StarLineDevice, DeviceWithState } from '@/lib/types';
import {
  Car,
  MapPin,
  Thermometer,
  Battery,
  Fuel,
  Gauge,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Eye,
  Clock,
} from 'lucide-react';

interface DeviceCardProps {
  device: StarLineDevice | DeviceWithState;
  onDelete?: (id: string) => void;
  onView?: (id: string) => void;
  isDeleting?: boolean;
}

export function DeviceCard({ device, onDelete, onView, isDeleting }: DeviceCardProps) {
  const hasState = 'state' in device && device.state;
  const hasGps = 'gps' in device && device.gps;
  const state = hasState ? (device as DeviceWithState).state : null;
  const gps = hasGps ? (device as DeviceWithState).gps : null;

  const getAlarmBadge = () => {
    if (!state?.alarm_state) return null;
    
    const alarmState = state.alarm_state.toLowerCase();
    if (alarmState.includes('armed') || alarmState === 'on') {
      return (
        <Badge variant="default" className="bg-green-600">
          <ShieldCheck className="w-3 h-3 mr-1" />
          Под охраной
        </Badge>
      );
    } else if (alarmState.includes('alarm') || alarmState.includes('triggered')) {
      return (
        <Badge variant="destructive">
          <ShieldAlert className="w-3 h-3 mr-1" />
          Тревога
        </Badge>
      );
    } else {
      return (
        <Badge variant="secondary">
          <Shield className="w-3 h-3 mr-1" />
          Снято с охраны
        </Badge>
      );
    }
  };

  const formatVoltage = (voltage: number | null | undefined) => {
    if (voltage === null || voltage === undefined) return '—';
    return `${voltage.toFixed(1)} В`;
  };

  const formatTemp = (temp: number | null | undefined) => {
    if (temp === null || temp === undefined) return '—';
    return `${temp.toFixed(1)}°C`;
  };

  const formatLastUpdate = (timestamp: string | null | undefined) => {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    return date.toLocaleString('ru-RU');
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Car className="w-5 h-5 text-primary" />
              {device.name}
            </CardTitle>
            <CardDescription className="mt-1">
              ID: {device.device_id_starline || 'Не синхронизирован'}
            </CardDescription>
          </div>
          {getAlarmBadge()}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="flex items-center gap-2">
            <Battery className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Батарея</p>
              <p className="font-medium">{formatVoltage(state?.battery_voltage)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Thermometer className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Температура</p>
              <p className="font-medium">{formatTemp(state?.interior_temp)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Fuel className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Топливо</p>
              <p className="font-medium">
                {state?.fuel_level !== null && state?.fuel_level !== undefined 
                  ? `${state.fuel_level}%` 
                  : '—'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Gauge className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Пробег</p>
              <p className="font-medium">
                {state?.mileage !== null && state?.mileage !== undefined 
                  ? `${state.mileage.toLocaleString()} км` 
                  : '—'}
              </p>
            </div>
          </div>
        </div>

        {gps && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
            <MapPin className="w-4 h-4" />
            <span>
              {gps.latitude.toFixed(6)}, {gps.longitude.toFixed(6)}
            </span>
            {gps.speed !== null && gps.speed !== undefined && (
              <Badge variant="outline" className="ml-2">
                {gps.speed} км/ч
              </Badge>
            )}
          </div>
        )}

        {state && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
            <Clock className="w-3 h-3" />
            <span>Обновлено: {formatLastUpdate(state.timestamp)}</span>
          </div>
        )}

        <div className="flex gap-2">
          {onView && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => onView(device.id)}
              className="flex items-center gap-1"
            >
              <Eye className="w-4 h-4" />
              Подробнее
            </Button>
          )}
          {onDelete && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button 
                  variant="outline" 
                  size="sm" 
                  disabled={isDeleting}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Удалить устройство?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Вы уверены, что хотите удалить устройство &quot;{device.name}&quot;? 
                    Это действие нельзя отменить.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Отмена</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => onDelete(device.id)}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Удалить
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

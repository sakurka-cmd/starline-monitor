'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import { useDeviceStore } from '@/store/devices';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DeviceCard } from '@/components/devices/DeviceCard';
import {
  Loader2,
  Plus,
  LogOut,
  Car,
  User,
} from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, logout, fetchUser } = useAuthStore();
  const { devices, isLoading: devicesLoading, fetchDevices, deleteDevice, error } = useDeviceStore();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchDevices();
    }
  }, [isAuthenticated, fetchDevices]);

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const handleViewDevice = (deviceId: string) => {
    router.push(`/devices/${deviceId}`);
  };

  const handleDeleteDevice = async (deviceId: string) => {
    try {
      await deleteDevice(deviceId);
    } catch (err) {
      console.error('Failed to delete device:', err);
    }
  };

  if (authLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 backdrop-blur-sm bg-slate-900/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="h-8 w-8 text-primary" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
            </svg>
            <span className="text-xl font-bold text-white">StarLine Monitor</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-slate-300">
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">{user?.name || user?.email}</span>
            </div>
            <Button variant="ghost" onClick={handleLogout} className="text-slate-300 hover:text-white">
              <LogOut className="h-4 w-4 mr-2" />
              Выход
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Мои устройства</h1>
            <p className="text-slate-400 mt-1">
              Управляйте вашими устройствами StarLine
            </p>
          </div>
          <Button onClick={() => router.push('/devices/add')} className="gap-2">
            <Plus className="h-4 w-4" />
            Добавить устройство
          </Button>
        </div>

        {error && (
          <Card className="mb-6 border-destructive bg-destructive/10">
            <CardContent className="py-4 text-destructive">
              {error}
            </CardContent>
          </Card>
        )}

        {devicesLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : devices.length === 0 ? (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="py-12 text-center">
              <Car className="h-16 w-16 text-slate-600 mx-auto mb-4" />
              <CardTitle className="text-white mb-2">Нет устройств</CardTitle>
              <CardDescription className="text-slate-400 mb-4">
                Добавьте ваше первое устройство StarLine для начала работы
              </CardDescription>
              <Button onClick={() => router.push('/devices/add')}>
                <Plus className="h-4 w-4 mr-2" />
                Добавить устройство
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {devices.map((device) => (
              <DeviceCard
                key={device.id}
                device={device}
                onView={handleViewDevice}
                onDelete={handleDeleteDevice}
                isDeleting={devicesLoading}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

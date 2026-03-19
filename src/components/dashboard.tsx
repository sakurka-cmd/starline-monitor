'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { DeviceCard } from '@/components/device-card';
import { DeviceModal } from '@/components/device-modal';
import { DeleteDialog } from '@/components/delete-dialog';
import { Plus, Car, Loader2, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import type { Device, CreateDeviceRequest } from '@/lib/types';

interface DashboardProps {
  onViewDevice: (id: string) => void;
}

export function Dashboard({ onViewDevice }: DashboardProps) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deleteDeviceId, setDeleteDeviceId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchDevices = async (isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    
    try {
      const data = await api.getDevices();
      setDevices(data);
    } catch (error) {
      console.error('Error fetching devices:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handleAddDevice = async (data: CreateDeviceRequest) => {
    setIsSubmitting(true);
    try {
      await api.createDevice(data);
      setIsModalOpen(false);
      fetchDevices();
    } catch (error) {
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteDevice = async () => {
    if (!deleteDeviceId) return;
    
    setIsDeleting(true);
    try {
      await api.deleteDevice(deleteDeviceId);
      setDeleteDeviceId(null);
      fetchDevices();
    } catch (error) {
      console.error('Error deleting device:', error);
      alert('Ошибка при удалении устройства');
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-64 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Мои устройства</h1>
          <p className="text-slate-400 text-sm mt-1">
            {devices.length === 0 
              ? 'Добавьте первое устройство для мониторинга' 
              : `${devices.length} устройств`}
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => fetchDevices(true)}
            disabled={isRefreshing}
            className="border-slate-600 text-slate-300 hover:bg-slate-800"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Обновить
          </Button>
          <Button 
            onClick={() => setIsModalOpen(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Plus className="w-4 h-4 mr-2" />
            Добавить устройство
          </Button>
        </div>
      </div>

      {/* Devices Grid */}
      {devices.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
          <div className="p-4 rounded-full bg-slate-800 mb-4">
            <Car className="w-12 h-12 opacity-50" />
          </div>
          <p className="text-lg mb-2">Устройств пока нет</p>
          <p className="text-sm mb-6">Добавьте устройство для начала мониторинга</p>
          <Button 
            onClick={() => setIsModalOpen(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Plus className="w-4 h-4 mr-2" />
            Добавить устройство
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {devices.map((device) => (
            <DeviceCard
              key={device.id}
              device={device}
              onDelete={(id) => setDeleteDeviceId(id)}
              onView={onViewDevice}
            />
          ))}
        </div>
      )}

      {/* Add Device Modal */}
      <DeviceModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        onSubmit={handleAddDevice}
        isLoading={isSubmitting}
      />

      {/* Delete Confirmation */}
      <DeleteDialog
        open={!!deleteDeviceId}
        onOpenChange={(open) => !open && setDeleteDeviceId(null)}
        onConfirm={handleDeleteDevice}
        title="Удалить устройство?"
        description="Это действие необратимо. Устройство и все связанные данные будут удалены."
        isLoading={isDeleting}
      />
    </div>
  );
}

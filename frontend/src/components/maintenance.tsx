'use client';

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { 
  Wrench, 
  Plus, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  Trash2,
  Pencil,
  Loader2,
  Calendar
} from 'lucide-react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import type { 
  MaintenanceRecord, 
  ServiceType, 
  UpcomingMaintenance,
  CreateMaintenanceRequest 
} from '@/lib/types';
import { api } from '@/lib/api';

interface MaintenanceSectionProps {
  deviceId: string;
  currentMileage: number | null;
  currentMotohrs: number | null;
}

export function MaintenanceSection({ 
  deviceId, 
  currentMileage, 
  currentMotohrs 
}: MaintenanceSectionProps) {
  const [records, setRecords] = useState<MaintenanceRecord[]>([]);
  const [upcoming, setUpcoming] = useState<UpcomingMaintenance[]>([]);
  const [serviceTypes, setServiceTypes] = useState<ServiceType[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<MaintenanceRecord | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [recordsData, upcomingData, typesData] = await Promise.all([
        api.getMaintenance(deviceId),
        api.getUpcomingMaintenance(deviceId),
        api.getServiceTypes(),
      ]);
      setRecords(recordsData);
      setUpcoming(upcomingData);
      setServiceTypes(typesData);
    } catch (error) {
      console.error('Error fetching maintenance data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [deviceId]);

  const handleAddRecord = () => {
    setEditingRecord(null);
    setIsModalOpen(true);
  };

  const handleEditRecord = (record: MaintenanceRecord) => {
    setEditingRecord(record);
    setIsModalOpen(true);
  };

  const handleDeleteRecord = async (recordId: string) => {
    if (!confirm('Вы уверены, что хотите удалить эту запись?')) return;
    
    try {
      await api.deleteMaintenance(deviceId, recordId);
      fetchData();
    } catch (error) {
      console.error('Error deleting record:', error);
      alert('Ошибка при удалении записи');
    }
  };

  const handleSubmit = async (data: CreateMaintenanceRequest) => {
    setIsSubmitting(true);
    try {
      if (editingRecord) {
        await api.updateMaintenance(deviceId, editingRecord.id, data);
      } else {
        await api.createMaintenance(deviceId, data);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (error) {
      console.error('Error saving record:', error);
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ok':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'warning':
        return <Clock className="w-4 h-4 text-yellow-400" />;
      case 'overdue':
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok':
        return 'bg-green-900/30 border-green-700';
      case 'warning':
        return 'bg-yellow-900/30 border-yellow-700';
      case 'overdue':
        return 'bg-red-900/30 border-red-700';
      default:
        return 'bg-slate-800/50 border-slate-700';
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 mt-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6 mt-8">
      {/* Upcoming Maintenance Alerts */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
            Предстоящее обслуживание
          </CardTitle>
        </CardHeader>
        <CardContent>
          {upcoming.length === 0 ? (
            <p className="text-slate-400 text-sm">Нет предстоящих обслуживаний</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {upcoming.map((item) => (
                <div
                  key={item.id}
                  className={`p-3 rounded-lg border ${getStatusColor(item.status)}`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {getStatusIcon(item.status)}
                    <span className="font-medium text-white">
                      {item.service_type.name}
                    </span>
                  </div>
                  {item.mileage_remaining !== null && (
                    <p className="text-sm text-slate-300">
                      Осталось: {item.mileage_remaining.toFixed(0)} км
                    </p>
                  )}
                  {item.motohrs_remaining !== null && (
                    <p className="text-sm text-slate-300">
                      Осталось: {item.motohrs_remaining.toFixed(1)} моточасов
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Maintenance Records */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Wrench className="w-5 h-5 text-blue-400" />
              История обслуживания
            </CardTitle>
            <Button 
              onClick={handleAddRecord}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              Добавить
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {records.length === 0 ? (
            <div className="text-center py-8 text-slate-400">
              <Wrench className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Записей об обслуживании пока нет</p>
              <Button 
                variant="outline" 
                onClick={handleAddRecord}
                className="mt-4 border-slate-600 text-slate-300"
              >
                <Plus className="w-4 h-4 mr-2" />
                Добавить первую запись
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-700 hover:bg-slate-800/50">
                    <TableHead className="text-slate-400">Тип сервиса</TableHead>
                    <TableHead className="text-slate-400">Описание</TableHead>
                    <TableHead className="text-slate-400">Дата</TableHead>
                    <TableHead className="text-slate-400">Пробег</TableHead>
                    <TableHead className="text-slate-400">Моточасы</TableHead>
                    <TableHead className="text-slate-400">Стоимость</TableHead>
                    <TableHead className="text-slate-400 text-right">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {records.map((record) => (
                    <TableRow key={record.id} className="border-slate-700 hover:bg-slate-800/50">
                      <TableCell className="text-white">
                        {record.service_type?.name || '—'}
                      </TableCell>
                      <TableCell className="text-slate-300 max-w-[200px] truncate">
                        {record.description || '—'}
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {format(new Date(record.service_date), 'dd.MM.yyyy', { locale: ru })}
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {record.mileage_at_service?.toLocaleString('ru-RU')} км
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {record.motohrs_at_service?.toFixed(1)} ч
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {record.cost ? `${record.cost.toLocaleString('ru-RU')} ₽` : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEditRecord(record)}
                            className="text-slate-400 hover:text-blue-400 hover:bg-blue-600/20"
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteRecord(record.id)}
                            className="text-slate-400 hover:text-red-400 hover:bg-red-600/20"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Modal */}
      <MaintenanceModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        onSubmit={handleSubmit}
        serviceTypes={serviceTypes}
        currentMileage={currentMileage}
        currentMotohrs={currentMotohrs}
        editingRecord={editingRecord}
        isLoading={isSubmitting}
      />
    </div>
  );
}

interface MaintenanceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CreateMaintenanceRequest) => Promise<void>;
  serviceTypes: ServiceType[];
  currentMileage: number | null;
  currentMotohrs: number | null;
  editingRecord: MaintenanceRecord | null;
  isLoading: boolean;
}

function MaintenanceModal({
  open,
  onOpenChange,
  onSubmit,
  serviceTypes,
  currentMileage,
  currentMotohrs,
  editingRecord,
  isLoading,
}: MaintenanceModalProps) {
  // Compute initial values based on editingRecord
  const initialValues = {
    serviceTypeId: editingRecord?.service_type_id || '',
    description: editingRecord?.description || '',
    mileageAtService: editingRecord?.mileage_at_service?.toString() || currentMileage?.toString() || '',
    motohrsAtService: editingRecord?.motohrs_at_service?.toString() || currentMotohrs?.toString() || '',
    serviceDate: editingRecord 
      ? format(new Date(editingRecord.service_date), 'yyyy-MM-dd')
      : format(new Date(), 'yyyy-MM-dd'),
    cost: editingRecord?.cost?.toString() || '',
    notes: editingRecord?.notes || '',
  };

  const [serviceTypeId, setServiceTypeId] = useState(initialValues.serviceTypeId);
  const [description, setDescription] = useState(initialValues.description);
  const [mileageAtService, setMileageAtService] = useState(initialValues.mileageAtService);
  const [motohrsAtService, setMotohrsAtService] = useState(initialValues.motohrsAtService);
  const [serviceDate, setServiceDate] = useState(initialValues.serviceDate);
  const [cost, setCost] = useState(initialValues.cost);
  const [notes, setNotes] = useState(initialValues.notes);
  const [error, setError] = useState<string | null>(null);

  const selectedServiceType = serviceTypes.find(st => st.id === serviceTypeId);

  // Reset form when modal opens with new data
  const resetForm = () => {
    setServiceTypeId(initialValues.serviceTypeId);
    setDescription(initialValues.description);
    setMileageAtService(initialValues.mileageAtService);
    setMotohrsAtService(initialValues.motohrsAtService);
    setServiceDate(initialValues.serviceDate);
    setCost(initialValues.cost);
    setNotes(initialValues.notes);
    setError(null);
  };

  // Use a separate effect that only runs when the modal opens
  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (open) {
      resetForm();
    }
  }

  // Also reset when editingRecord changes while modal is open
  const [prevEditingRecord, setPrevEditingRecord] = useState(editingRecord?.id);
  if (editingRecord?.id !== prevEditingRecord && open) {
    setPrevEditingRecord(editingRecord?.id);
    resetForm();
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!serviceTypeId) {
      setError('Выберите тип сервиса');
      return;
    }

    if (!mileageAtService || !motohrsAtService) {
      setError('Укажите пробег и моточасы на момент обслуживания');
      return;
    }

    try {
      await onSubmit({
        service_type_id: serviceTypeId,
        description: description.trim() || undefined,
        mileage_at_service: parseFloat(mileageAtService),
        motohrs_at_service: parseFloat(motohrsAtService),
        service_date: serviceDate,
        next_service_mileage: selectedServiceType?.interval_mileage 
          ? parseFloat(mileageAtService) + selectedServiceType.interval_mileage 
          : undefined,
        next_service_motohrs: selectedServiceType?.interval_motohrs
          ? parseFloat(motohrsAtService) + selectedServiceType.interval_motohrs
          : undefined,
        cost: cost ? parseFloat(cost) : undefined,
        notes: notes.trim() || undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сохранения');
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-slate-900 border-slate-700 text-white sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl">
            {editingRecord ? 'Редактировать запись' : 'Добавить запись обслуживания'}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            Заполните информацию о проведенном обслуживании
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-900/50 border border-red-700 text-red-200 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label className="text-slate-300">Тип сервиса</Label>
            <Select value={serviceTypeId} onValueChange={setServiceTypeId}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                <SelectValue placeholder="Выберите тип сервиса" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-600">
                {serviceTypes.map((type) => (
                  <SelectItem 
                    key={type.id} 
                    value={type.id}
                    className="text-white hover:bg-slate-700 focus:bg-slate-700"
                  >
                    {type.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedServiceType && (
              <p className="text-xs text-slate-400">
                Интервал: {selectedServiceType.interval_mileage?.toLocaleString() || '—'} км,{' '}
                {selectedServiceType.interval_motohrs?.toFixed(0) || '—'} моточасов
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description" className="text-slate-300">Описание</Label>
            <Input
              id="description"
              type="text"
              placeholder="Краткое описание работ"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="mileage" className="text-slate-300">Пробег (км)</Label>
              <Input
                id="mileage"
                type="number"
                placeholder="0"
                value={mileageAtService}
                onChange={(e) => setMileageAtService(e.target.value)}
                className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="motohrs" className="text-slate-300">Моточасы</Label>
              <Input
                id="motohrs"
                type="number"
                step="0.1"
                placeholder="0"
                value={motohrsAtService}
                onChange={(e) => setMotohrsAtService(e.target.value)}
                className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="service-date" className="text-slate-300 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Дата обслуживания
            </Label>
            <Input
              id="service-date"
              type="date"
              value={serviceDate}
              onChange={(e) => setServiceDate(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="cost" className="text-slate-300">Стоимость (₽)</Label>
            <Input
              id="cost"
              type="number"
              placeholder="0"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes" className="text-slate-300">Заметки</Label>
            <Textarea
              id="notes"
              placeholder="Дополнительные заметки"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 min-h-[80px]"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isLoading}
              className="flex-1 bg-transparent border-slate-600 text-slate-300 hover:bg-slate-800"
            >
              Отмена
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Сохранение...
                </>
              ) : (
                'Сохранить'
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2 } from 'lucide-react';
import type { CreateDeviceRequest } from '@/lib/types';

interface DeviceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CreateDeviceRequest) => Promise<void>;
  isLoading: boolean;
}

export function DeviceModal({ open, onOpenChange, onSubmit, isLoading }: DeviceModalProps) {
  const [name, setName] = useState('');
  const [appId, setAppId] = useState('');
  const [appSecret, setAppSecret] = useState('');
  const [starlineLogin, setStarlineLogin] = useState('');
  const [starlinePassword, setStarlinePassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Введите название устройства');
      return;
    }
    if (!appId.trim()) {
      setError('Введите App ID');
      return;
    }
    if (!appSecret.trim()) {
      setError('Введите App Secret');
      return;
    }
    if (!starlineLogin.trim()) {
      setError('Введите логин StarLine');
      return;
    }
    if (!starlinePassword.trim()) {
      setError('Введите пароль StarLine');
      return;
    }

    try {
      await onSubmit({
        name: name.trim(),
        app_id: appId.trim(),
        app_secret: appSecret.trim(),
        starline_login: starlineLogin.trim(),
        starline_password: starlinePassword.trim(),
      });
      
      // Reset form
      setName('');
      setAppId('');
      setAppSecret('');
      setStarlineLogin('');
      setStarlinePassword('');
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка добавления устройства');
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setError(null);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-slate-900 border-slate-700 text-white sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl">Добавить устройство</DialogTitle>
          <DialogDescription className="text-slate-400">
            Введите данные для подключения к StarLine API
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-900/50 border border-red-700 text-red-200 text-sm">
              {error}
            </div>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="device-name" className="text-slate-300">
              Название устройства
            </Label>
            <Input
              id="device-name"
              type="text"
              placeholder="Мой автомобиль"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="app-id" className="text-slate-300">
              App ID
            </Label>
            <Input
              id="app-id"
              type="text"
              placeholder="Ваш App ID"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="app-secret" className="text-slate-300">
              App Secret
            </Label>
            <Input
              id="app-secret"
              type="password"
              placeholder="Ваш App Secret"
              value={appSecret}
              onChange={(e) => setAppSecret(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="starline-login" className="text-slate-300">
              Логин StarLine
            </Label>
            <Input
              id="starline-login"
              type="text"
              placeholder="Логин или email"
              value={starlineLogin}
              onChange={(e) => setStarlineLogin(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="starline-password" className="text-slate-300">
              Пароль StarLine
            </Label>
            <Input
              id="starline-password"
              type="password"
              placeholder="Пароль"
              value={starlinePassword}
              onChange={(e) => setStarlinePassword(e.target.value)}
              className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500"
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
                  Добавление...
                </>
              ) : (
                'Добавить'
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

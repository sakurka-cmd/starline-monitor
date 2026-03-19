'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useDeviceStore } from '@/store/devices';
import { Loader2, Info } from 'lucide-react';

const deviceSchema = z.object({
  name: z.string().min(2, 'Название должно содержать минимум 2 символа'),
  app_id: z.string().min(1, 'App ID обязателен'),
  app_secret: z.string().min(1, 'App Secret обязателен'),
  user_login: z.string().min(1, 'Логин StarLine обязателен'),
  user_password: z.string().min(1, 'Пароль StarLine обязателен'),
});

type DeviceFormData = z.infer<typeof deviceSchema>;

export function DeviceForm() {
  const router = useRouter();
  const { addDevice, isLoading, error, clearError } = useDeviceStore();
  const [localError, setLocalError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<DeviceFormData>({
    resolver: zodResolver(deviceSchema),
  });

  const onSubmit = async (data: DeviceFormData) => {
    try {
      clearError();
      setLocalError(null);
      await addDevice(data);
      router.push('/dashboard');
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Ошибка добавления устройства');
    }
  };

  const displayError = localError || error;

  return (
    <Card className="w-full max-w-lg mx-auto">
      <CardHeader>
        <CardTitle>Добавить устройство StarLine</CardTitle>
        <CardDescription>
          Введите данные вашего устройства для подключения к StarLine API
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {displayError && (
            <Alert variant="destructive">
              <AlertDescription>{displayError}</AlertDescription>
            </Alert>
          )}
          
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-sm">
              Для получения App ID и App Secret необходимо зарегистрировать приложение 
              на <a href="https://developer.starline.ru" target="_blank" rel="noopener noreferrer" className="underline">developer.starline.ru</a>
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <Label htmlFor="name">Название устройства</Label>
            <Input
              id="name"
              type="text"
              placeholder="Мой автомобиль"
              {...register('name')}
              disabled={isLoading}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="app_id">App ID</Label>
            <Input
              id="app_id"
              type="text"
              placeholder="Ваш App ID"
              {...register('app_id')}
              disabled={isLoading}
            />
            {errors.app_id && (
              <p className="text-sm text-destructive">{errors.app_id.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="app_secret">App Secret</Label>
            <Input
              id="app_secret"
              type="password"
              placeholder="Ваш App Secret"
              {...register('app_secret')}
              disabled={isLoading}
            />
            {errors.app_secret && (
              <p className="text-sm text-destructive">{errors.app_secret.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="user_login">Логин StarLine</Label>
            <Input
              id="user_login"
              type="text"
              placeholder="Ваш логин StarLine"
              {...register('user_login')}
              disabled={isLoading}
            />
            {errors.user_login && (
              <p className="text-sm text-destructive">{errors.user_login.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="user_password">Пароль StarLine</Label>
            <Input
              id="user_password"
              type="password"
              placeholder="Ваш пароль StarLine"
              {...register('user_password')}
              disabled={isLoading}
            />
            {errors.user_password && (
              <p className="text-sm text-destructive">{errors.user_password.message}</p>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
            disabled={isLoading}
          >
            Отмена
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Добавить
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}

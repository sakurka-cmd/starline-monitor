import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getCurrentUser } from '@/lib/auth';

// GET - получить все устройства пользователя
export async function GET() {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Не авторизован' },
        { status: 401 }
      );
    }
    
    const devices = await db.device.findMany({
      where: { userId: user.id },
      include: {
        states: {
          orderBy: { timestamp: 'desc' },
          take: 1,
        },
      },
      orderBy: { createdAt: 'desc' },
    });
    
    return NextResponse.json({ devices });
  } catch (error) {
    console.error('Get devices error:', error);
    return NextResponse.json(
      { error: 'Ошибка при получении устройств' },
      { status: 500 }
    );
  }
}

// POST - добавить новое устройство
export async function POST(request: NextRequest) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Не авторизован' },
        { status: 401 }
      );
    }
    
    const body = await request.json();
    const { deviceId, name, alias, deviceType, firmwareVersion } = body;
    
    if (!deviceId) {
      return NextResponse.json(
        { error: 'ID устройства обязателен' },
        { status: 400 }
      );
    }
    
    // Проверка на дубликат
    const existing = await db.device.findUnique({
      where: { deviceId },
    });
    
    if (existing) {
      return NextResponse.json(
        { error: 'Устройство уже добавлено' },
        { status: 400 }
      );
    }
    
    const device = await db.device.create({
      data: {
        userId: user.id,
        deviceId,
        name,
        alias,
        deviceType,
        firmwareVersion,
      },
    });
    
    return NextResponse.json({ device });
  } catch (error) {
    console.error('Create device error:', error);
    return NextResponse.json(
      { error: 'Ошибка при создании устройства' },
      { status: 500 }
    );
  }
}

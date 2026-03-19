import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getCurrentUser } from '@/lib/auth';

// GET - получить историю состояний устройства
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Не авторизован' },
        { status: 401 }
      );
    }
    
    const { id } = await params;
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '100');
    const from = searchParams.get('from');
    const to = searchParams.get('to');
    
    // Проверка владения устройством
    const device = await db.device.findFirst({
      where: { id, userId: user.id },
    });
    
    if (!device) {
      return NextResponse.json(
        { error: 'Устройство не найдено' },
        { status: 404 }
      );
    }
    
    // Фильтр по дате
    const dateFilter: { timestamp: { gte?: Date; lte?: Date } } = {};
    if (from) dateFilter.timestamp.gte = new Date(from);
    if (to) dateFilter.timestamp.lte = new Date(to);
    
    const states = await db.deviceState.findMany({
      where: {
        deviceId: id,
        ...dateFilter,
      },
      orderBy: { timestamp: 'desc' },
      take: limit,
    });
    
    return NextResponse.json({ states });
  } catch (error) {
    console.error('Get states error:', error);
    return NextResponse.json(
      { error: 'Ошибка при получении состояний' },
      { status: 500 }
    );
  }
}

// POST - добавить новое состояние (для Worker)
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Не авторизован' },
        { status: 401 }
      );
    }
    
    const { id } = await params;
    const body = await request.json();
    
    // Проверка владения устройством
    const device = await db.device.findFirst({
      where: { id, userId: user.id },
    });
    
    if (!device) {
      return NextResponse.json(
        { error: 'Устройство не найдено' },
        { status: 404 }
      );
    }
    
    const state = await db.deviceState.create({
      data: {
        deviceId: id,
        timestamp: body.timestamp ? new Date(body.timestamp) : new Date(),
        armState: body.armState ?? 0,
        armDatetime: body.armDatetime ? new Date(body.armDatetime) : null,
        ignState: body.ignState ?? 0,
        ignDatetime: body.ignDatetime ? new Date(body.ignDatetime) : null,
        runTime: body.runTime ?? 0,
        tempInner: body.tempInner,
        tempEngine: body.tempEngine,
        tempOutdoor: body.tempOutdoor,
        balance: body.balance,
        balanceCurrency: body.balanceCurrency,
        doorDriver: body.doorDriver,
        doorPassenger: body.doorPassenger,
        doorRearLeft: body.doorRearLeft,
        doorRearRight: body.doorRearRight,
        hood: body.hood,
        trunk: body.trunk,
        handbrake: body.handbrake,
        brake: body.brake,
        gsmLevel: body.gsmLevel,
        gpsLevel: body.gpsLevel,
        batteryVoltage: body.batteryVoltage,
        rawData: body.rawData ? JSON.stringify(body.rawData) : null,
      },
    });
    
    return NextResponse.json({ state });
  } catch (error) {
    console.error('Create state error:', error);
    return NextResponse.json(
      { error: 'Ошибка при создании состояния' },
      { status: 500 }
    );
  }
}

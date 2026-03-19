import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getCurrentUser } from '@/lib/auth';

// GET - получить устройство по ID
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
    
    const device = await db.device.findFirst({
      where: { id, userId: user.id },
      include: {
        states: {
          orderBy: { timestamp: 'desc' },
          take: 100,
        },
        positions: {
          orderBy: { timestamp: 'desc' },
          take: 100,
        },
      },
    });
    
    if (!device) {
      return NextResponse.json(
        { error: 'Устройство не найдено' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({ device });
  } catch (error) {
    console.error('Get device error:', error);
    return NextResponse.json(
      { error: 'Ошибка при получении устройства' },
      { status: 500 }
    );
  }
}

// DELETE - удалить устройство
export async function DELETE(
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
    
    // Проверка владения
    const device = await db.device.findFirst({
      where: { id, userId: user.id },
    });
    
    if (!device) {
      return NextResponse.json(
        { error: 'Устройство не найдено' },
        { status: 404 }
      );
    }
    
    await db.device.delete({
      where: { id },
    });
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Delete device error:', error);
    return NextResponse.json(
      { error: 'Ошибка при удалении устройства' },
      { status: 500 }
    );
  }
}

// PUT - обновить устройство
export async function PUT(
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
    
    // Проверка владения
    const device = await db.device.findFirst({
      where: { id, userId: user.id },
    });
    
    if (!device) {
      return NextResponse.json(
        { error: 'Устройство не найдено' },
        { status: 404 }
      );
    }
    
    const updated = await db.device.update({
      where: { id },
      data: {
        name: body.name,
        alias: body.alias,
        deviceType: body.deviceType,
        firmwareVersion: body.firmwareVersion,
      },
    });
    
    return NextResponse.json({ device: updated });
  } catch (error) {
    console.error('Update device error:', error);
    return NextResponse.json(
      { error: 'Ошибка при обновлении устройства' },
      { status: 500 }
    );
  }
}

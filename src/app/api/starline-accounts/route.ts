import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getCurrentUser } from '@/lib/auth';

// GET - получить все StarLine аккаунты пользователя
export async function GET() {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json({ error: 'Не авторизован' }, { status: 401 });
    }
    
    const accounts = await db.$queryRaw`
      SELECT id, name, login, starline_user_id, is_active, last_sync, created_at
      FROM starline_accounts
      WHERE user_id = ${user.id}
      ORDER BY created_at DESC
    `;
    
    return NextResponse.json({ accounts });
  } catch (error) {
    console.error('Get accounts error:', error);
    return NextResponse.json({ error: 'Ошибка получения аккаунтов' }, { status: 500 });
  }
}

// POST - добавить новый StarLine аккаунт
export async function POST(request: NextRequest) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json({ error: 'Не авторизован' }, { status: 401 });
    }
    
    const body = await request.json();
    const { name, app_id, app_secret, login, password } = body;
    
    if (!app_id || !app_secret || !login || !password) {
      return NextResponse.json({ 
        error: 'Все поля обязательны: app_id, app_secret, login, password' 
      }, { status: 400 });
    }
    
    await db.$executeRaw`
      INSERT INTO starline_accounts (user_id, name, app_id, app_secret, login, password)
      VALUES (${user.id}, ${name || 'StarLine аккаунт'}, ${app_id}, ${app_secret}, ${login}, ${password})
    `;
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Create account error:', error);
    return NextResponse.json({ error: 'Ошибка создания аккаунта' }, { status: 500 });
  }
}

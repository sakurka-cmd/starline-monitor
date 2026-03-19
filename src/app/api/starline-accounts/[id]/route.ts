import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getCurrentUser } from '@/lib/auth';

// DELETE - удалить аккаунт
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json({ error: 'Не авторизован' }, { status: 401 });
    }
    
    const { id } = await params;
    
    await db.$executeRaw`
      DELETE FROM starline_accounts 
      WHERE id = ${parseInt(id)} AND user_id = ${user.id}
    `;
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Delete account error:', error);
    return NextResponse.json({ error: 'Ошибка удаления' }, { status: 500 });
  }
}

// PUT - обновить аккаунт
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json({ error: 'Не авторизован' }, { status: 401 });
    }
    
    const { id } = await params;
    const body = await request.json();
    const { name, app_id, app_secret, login, password, is_active } = body;
    
    await db.$executeRaw`
      UPDATE starline_accounts SET
        name = ${name},
        app_id = ${app_id},
        app_secret = ${app_secret},
        login = ${login},
        password = ${password},
        is_active = ${is_active ?? 1}
      WHERE id = ${parseInt(id)} AND user_id = ${user.id}
    `;
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Update account error:', error);
    return NextResponse.json({ error: 'Ошибка обновления' }, { status: 500 });
  }
}

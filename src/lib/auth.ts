import { db } from './db';
import { User, Session } from '@prisma/client';
import { cookies } from 'next/headers';
import { randomBytes, createHash } from 'crypto';

// Хэширование пароля
export function hashPassword(password: string): string {
  return createHash('sha256').update(password).digest('hex');
}

// Проверка пароля
export function verifyPassword(password: string, hash: string): boolean {
  return hashPassword(password) === hash;
}

// Генерация токена сессии
export function generateToken(): string {
  return randomBytes(32).toString('hex');
}

// Создание сессии
export async function createSession(userId: string): Promise<Session> {
  const token = generateToken();
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 дней
  
  const session = await db.session.create({
    data: {
      userId,
      token,
      expiresAt,
    },
  });
  
  return session;
}

// Получение текущего пользователя
export async function getCurrentUser(): Promise<User | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get('session_token')?.value;
  
  if (!token) {
    return null;
  }
  
  const session = await db.session.findUnique({
    where: { token },
    include: { user: true },
  });
  
  if (!session || session.expiresAt < new Date()) {
    return null;
  }
  
  return session.user;
}

// Удаление сессии
export async function deleteSession(token: string): Promise<void> {
  await db.session.deleteMany({
    where: { token },
  });
}

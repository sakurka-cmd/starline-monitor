import { NextRequest, NextResponse } from 'next/server';
import { proxyToBackend } from '@/lib/proxy';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const authHeader = request.headers.get('Authorization');
    
    const response = await proxyToBackend(`/devices/${id}/state`, {
      method: 'GET',
      headers: authHeader ? { Authorization: authHeader } : {},
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Get device state proxy error:', error);
    return NextResponse.json(
      { detail: 'Ошибка соединения с сервером' },
      { status: 500 }
    );
  }
}

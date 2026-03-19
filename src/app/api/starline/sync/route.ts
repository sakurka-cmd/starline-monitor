import { NextRequest, NextResponse } from 'next/server';
import { getCurrentUser } from '@/lib/auth';
import { db } from '@/lib/db';
import { createHash } from 'crypto';

// StarLine API endpoints
const SLID_URL = 'https://id.starline.ru';
const WEBAPI_URL = 'https://developer.starline.ru';

// POST - синхронизация устройств с StarLine
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
    const { appId, appSecret, userLogin, userPassword } = body;
    
    if (!appId || !appSecret || !userLogin || !userPassword) {
      return NextResponse.json(
        { error: 'Все поля обязательны' },
        { status: 400 }
      );
    }
    
    let appToken: string | null = null;
    let userToken: string | null = null;
    let slnetToken: string | null = null;
    let userId: string | null = null;
    
    // Шаг 1: Получение кода приложения
    const codeUrl = `${SLID_URL}/apiV3/application/getCode`;
    const secretMd5 = createHash('md5').update(appSecret).digest('hex');
    
    const codeResponse = await fetch(`${codeUrl}?appId=${appId}&secret=${secretMd5}`);
    const codeData = await codeResponse.json();
    
    if (codeData.state !== 1) {
      return NextResponse.json({ error: 'Ошибка получения кода', details: codeData });
    }
    
    const code = codeData.desc.code;
    
    // Шаг 2: Получение токена приложения
    const tokenUrl = `${SLID_URL}/apiV3/application/getToken`;
    const secretCombined = appSecret + code;
    const tokenSecretMd5 = createHash('md5').update(secretCombined).digest('hex');
    
    const tokenResponse = await fetch(`${tokenUrl}?appId=${appId}&secret=${tokenSecretMd5}`);
    const tokenData = await tokenResponse.json();
    
    if (tokenData.state !== 1) {
      return NextResponse.json({ error: 'Ошибка получения токена', details: tokenData });
    }
    
    appToken = tokenData.desc.token;
    
    // Шаг 3: Аутентификация пользователя
    const loginUrl = `${SLID_URL}/apiV3/user/login`;
    const passwordSha1 = createHash('sha1').update(userPassword).digest('hex');
    
    const loginResponse = await fetch(loginUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'token': appToken,
      },
      body: `login=${encodeURIComponent(userLogin)}&pass=${passwordSha1}`,
    });
    
    const loginData = await loginResponse.json();
    
    if (loginData.state !== 1) {
      return NextResponse.json({ error: 'Ошибка аутентификации', details: loginData });
    }
    
    userToken = loginData.desc.user_token;
    userId = loginData.desc.id;
    
    // Шаг 4: Авторизация в WebAPI
    const webapiUrl = `${WEBAPI_URL}/json/v2/auth.slid`;
    
    const webapiResponse = await fetch(webapiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ slid_token: userToken }),
    });
    
    const setCookie = webapiResponse.headers.get('set-cookie');
    if (setCookie) {
      const cookieMatches = setCookie.match(/slnet=([^;]+)/);
      if (cookieMatches) {
        slnetToken = cookieMatches[1];
      }
    }
    
    if (!slnetToken) {
      return NextResponse.json({ error: 'Не удалось получить slnet token' });
    }
    
    // Шаг 5: Получение списка устройств
    const devicesUrl = `${WEBAPI_URL}/json/v1/user/${userId}/devices`;
    
    const devicesResponse = await fetch(devicesUrl, {
      headers: {
        'Cookie': `slnet=${slnetToken}`,
      },
    });
    
    const devicesData = await devicesResponse.json();
    
    // Парсинг устройств
    let devices: Array<{
      device_id?: string;
      id?: string;
      name?: string;
      alias?: string;
      device_type?: string;
      firmware_version?: string;
      type?: string;
    }> = [];
    
    if (Array.isArray(devicesData.devices)) {
      devices = devicesData.devices;
    } else if (Array.isArray(devicesData.desc)) {
      devices = devicesData.desc;
    }
    
    // Сохранение устройств в базу
    const syncedDevices = [];
    
    for (const device of devices) {
      const deviceId = device.device_id || device.id;
      
      if (!deviceId) continue;
      
      // Проверка существования
      const existing = await db.device.findUnique({
        where: { deviceId },
      });
      
      if (existing) {
        // Обновление
        const updated = await db.device.update({
          where: { deviceId },
          data: {
            name: device.name || device.alias,
            alias: device.alias,
            deviceType: device.device_type || device.type,
            firmwareVersion: device.firmware_version,
          },
        });
        syncedDevices.push(updated);
      } else {
        // Создание
        const created = await db.device.create({
          data: {
            userId: user.id,
            deviceId,
            name: device.name || device.alias,
            alias: device.alias,
            deviceType: device.device_type || device.type,
            firmwareVersion: device.firmware_version,
          },
        });
        syncedDevices.push(created);
      }
      
      // Получение состояния устройства
      if (slnetToken) {
        try {
          const stateUrl = `${WEBAPI_URL}/json/v3/device/${deviceId}/data`;
          const stateResponse = await fetch(stateUrl, {
            headers: {
              'Cookie': `slnet=${slnetToken}`,
            },
          });
          
          const stateData = await stateResponse.json();
          
          if (stateData.state === 1 && stateData.desc) {
            const desc = stateData.desc;
            
            // Сохранение состояния
            await db.deviceState.create({
              data: {
                deviceId: syncedDevices[syncedDevices.length - 1].id,
                timestamp: new Date(),
                armState: desc.arm ?? 0,
                ignState: desc.ign ?? 0,
                runTime: desc.run_time ?? 0,
                tempInner: desc.temp?.inner,
                tempEngine: desc.temp?.engine,
                tempOutdoor: desc.temp?.outdoor,
                balance: desc.balance,
                balanceCurrency: desc.balance_currency,
                gsmLevel: desc.gsm?.level,
                gpsLevel: desc.gps?.level,
                batteryVoltage: desc.battery_voltage,
                rawData: JSON.stringify(desc),
              },
            });
          }
        } catch (e) {
          console.error(`Error fetching state for ${deviceId}:`, e);
        }
      }
    }
    
    // Обновление StarLine ID пользователя
    await db.user.update({
      where: { id: user.id },
      data: { starlineId: userId },
    });
    
    return NextResponse.json({
      success: true,
      deviceCount: syncedDevices.length,
      devices: syncedDevices,
    });
  } catch (error) {
    console.error('Sync error:', error);
    return NextResponse.json(
      { error: 'Ошибка при синхронизации', details: String(error) },
      { status: 500 }
    );
  }
}

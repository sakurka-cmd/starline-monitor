'use client';

import { useMemo } from 'react';
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DeviceState, GpsPosition } from '@/lib/types';
import { formatDate } from '@/lib/utils';

interface DeviceChartProps {
  states: DeviceState[];
  gpsPositions?: GpsPosition[];
  title?: string;
  description?: string;
}

const chartConfig = {
  battery_voltage: {
    label: 'Напряжение батареи',
    color: 'hsl(var(--chart-1))',
  },
  interior_temp: {
    label: 'Температура салона',
    color: 'hsl(var(--chart-2))',
  },
  engine_temp: {
    label: 'Температура двигателя',
    color: 'hsl(var(--chart-3))',
  },
  fuel_level: {
    label: 'Уровень топлива',
    color: 'hsl(var(--chart-4))',
  },
  speed: {
    label: 'Скорость',
    color: 'hsl(var(--chart-5))',
  },
} satisfies ChartConfig;

export function DeviceChart({ 
  states, 
  gpsPositions, 
  title = 'История показателей',
  description = 'Графики изменения параметров устройства'
}: DeviceChartProps) {
  const chartData = useMemo(() => {
    return states.map((state) => ({
      timestamp: new Date(state.timestamp).getTime(),
      time: formatDate(new Date(state.timestamp), 'HH:mm'),
      date: formatDate(new Date(state.timestamp), 'dd.MM.yyyy HH:mm'),
      battery_voltage: state.battery_voltage,
      interior_temp: state.interior_temp,
      engine_temp: state.engine_temp,
      fuel_level: state.fuel_level,
    })).sort((a, b) => a.timestamp - b.timestamp);
  }, [states]);

  const gpsData = useMemo(() => {
    if (!gpsPositions) return [];
    return gpsPositions.map((pos) => ({
      timestamp: new Date(pos.timestamp).getTime(),
      time: formatDate(new Date(pos.timestamp), 'HH:mm'),
      date: formatDate(new Date(pos.timestamp), 'dd.MM.yyyy HH:mm'),
      speed: pos.speed,
      latitude: pos.latitude,
      longitude: pos.longitude,
    })).sort((a, b) => a.timestamp - b.timestamp);
  }, [gpsPositions]);

  if (states.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            Нет данных для отображения
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="temperature">
          <TabsList className="mb-4">
            <TabsTrigger value="temperature">Температура</TabsTrigger>
            <TabsTrigger value="battery">Батарея</TabsTrigger>
            <TabsTrigger value="fuel">Топливо</TabsTrigger>
            {gpsData.length > 0 && (
              <TabsTrigger value="speed">Скорость</TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="temperature">
            <ChartContainer config={chartConfig} className="h-[300px] w-full">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => value}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  label={{ value: '°C', angle: -90, position: 'insideLeft' }}
                />
                <ChartTooltip
                  content={<ChartTooltipContent />}
                  labelFormatter={(value, payload) => {
                    if (payload && payload[0]) {
                      return payload[0].payload.date;
                    }
                    return value;
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="interior_temp"
                  stroke={chartConfig.interior_temp.color}
                  name="Темп. салона"
                  dot={false}
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="engine_temp"
                  stroke={chartConfig.engine_temp.color}
                  name="Темп. двигателя"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ChartContainer>
          </TabsContent>

          <TabsContent value="battery">
            <ChartContainer config={chartConfig} className="h-[300px] w-full">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  label={{ value: 'В', angle: -90, position: 'insideLeft' }}
                  domain={['auto', 'auto']}
                />
                <ChartTooltip
                  content={<ChartTooltipContent />}
                  labelFormatter={(value, payload) => {
                    if (payload && payload[0]) {
                      return payload[0].payload.date;
                    }
                    return value;
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="battery_voltage"
                  stroke={chartConfig.battery_voltage.color}
                  name="Напряжение"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ChartContainer>
          </TabsContent>

          <TabsContent value="fuel">
            <ChartContainer config={chartConfig} className="h-[300px] w-full">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  label={{ value: '%', angle: -90, position: 'insideLeft' }}
                  domain={[0, 100]}
                />
                <ChartTooltip
                  content={<ChartTooltipContent />}
                  labelFormatter={(value, payload) => {
                    if (payload && payload[0]) {
                      return payload[0].payload.date;
                    }
                    return value;
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="fuel_level"
                  stroke={chartConfig.fuel_level.color}
                  name="Уровень топлива"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ChartContainer>
          </TabsContent>

          {gpsData.length > 0 && (
            <TabsContent value="speed">
              <ChartContainer config={chartConfig} className="h-[300px] w-full">
                <LineChart data={gpsData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="time" 
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                    label={{ value: 'км/ч', angle: -90, position: 'insideLeft' }}
                  />
                  <ChartTooltip
                    content={<ChartTooltipContent />}
                    labelFormatter={(value, payload) => {
                      if (payload && payload[0]) {
                        return payload[0].payload.date;
                      }
                      return value;
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="speed"
                    stroke={chartConfig.speed.color}
                    name="Скорость"
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ChartContainer>
            </TabsContent>
          )}
        </Tabs>
      </CardContent>
    </Card>
  );
}

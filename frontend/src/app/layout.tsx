import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "StarLine Мониторинг - Система контроля транспорта",
  description: "Профессиональная система мониторинга транспорта StarLine. Контролируйте местоположение, состояние охраны, температуру, топливо и другие параметры вашего автомобиля в реальном времени.",
  keywords: ["StarLine", "мониторинг", "GPS", "охрана", "автомобиль", "транспорт", "контроль", "телематика"],
  authors: [{ name: "StarLine Team" }],
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233B82F6' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/><polygon points='16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76'/></svg>",
  },
  openGraph: {
    title: "StarLine Мониторинг",
    description: "Система контроля транспорта в реальном времени",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "StarLine Мониторинг",
    description: "Система контроля транспорта в реальном времени",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className="dark" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}

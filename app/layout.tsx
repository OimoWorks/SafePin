import type { Metadata } from "next";
import "./globals.css";
import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";

export const metadata: Metadata = {
  title: "SafePin",
  description: "松山市内の避難所・AED・マンホールトイレ・給水拠点をオフラインでも確認できる防災マップアプリ",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <meta name="theme-color" content="#E53E3E" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="SafePin" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <meta property="og:title" content="SafePin - 松山市防災マップ" />
        <meta property="og:description" content="松山市内の避難所・AED・マンホールトイレ・給水拠点をオフラインでも確認できる防災マップアプリ" />
        <meta property="og:type" content="website" />
        {/* TODO: OGP画像（1200x630推奨）を用意後、下記URLを差し替えてください */}
        <meta property="og:image" content="/icons/icon-512.png" />
      </head>
      <body className="antialiased">
        <ServiceWorkerRegister />
        {children}
      </body>
    </html>
  );
}

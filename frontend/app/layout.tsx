import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: "Lincoln's net - WiFi Access",
  description: 'Fast, Reliable WiFi Access',
  viewport: 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no',
  themeColor: '#667eea',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
      </head>
      <body>{children}</body>
    </html>
  );
}

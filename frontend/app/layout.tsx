import type { Metadata, Viewport } from 'next';
import './globals.css';

// Separate viewport export (Next.js 14+ requirement)
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1.0,
  maximumScale: 1.0,
  userScalable: false,
  themeColor: '#667eea',
};

export const metadata: Metadata = {
  title: "Lincoln's net - WiFi Access",
  description: 'Fast, Reliable WiFi Access',
  applicationName: "Lincoln's net",
  authors: [{ name: "Lincoln's net" }],
  keywords: ['WiFi', 'Hotspot', 'Internet', 'M-Pesa', 'Kenya'],
  manifest: '/manifest.json',
  icons: {
    icon: [
      {
        url: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="%23667eea"/><text x="50" y="65" font-size="50" text-anchor="middle" fill="white">📶</text></svg>',
        type: 'image/svg+xml',
      },
    ],
    apple: [
      {
        url: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="%23667eea"/><text x="50" y="65" font-size="50" text-anchor="middle" fill="white">📶</text></svg>',
        type: 'image/svg+xml',
      },
    ],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: "Lincoln's net",
  },
  formatDetection: {
    telephone: true,
  },
  openGraph: {
    title: "Lincoln's net - WiFi Access",
    description: 'Fast, Reliable WiFi Access',
    type: 'website',
    siteName: "Lincoln's net",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* Basic Meta Tags */}
        <meta charSet="utf-8" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Lincoln's net" />
        
        {/* Theme Color */}
        <meta name="theme-color" content="#667eea" />
        
        {/* Inline Favicon to prevent 404 */}
        <link
          rel="icon"
          href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%23667eea'/><text x='50' y='65' font-size='50' text-anchor='middle' fill='white'>📶</text></svg>"
          type="image/svg+xml"
        />
        
        {/* Apple Touch Icon */}
        <link
          rel="apple-touch-icon"
          href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%23667eea'/><text x='50' y='65' font-size='50' text-anchor='middle' fill='white'>📶</text></svg>"
        />
      </head>
      <body style={{ margin: 0, padding: 0, minHeight: '100vh' }}>
        {children}
      </body>
    </html>
  );
}

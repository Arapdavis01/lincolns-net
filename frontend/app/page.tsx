'use client';

import { useEffect, useState } from 'react';

// Define TypeScript interfaces
interface WiFiPackage {
  id: number;
  name: string;
  price: number;
  duration: string;
  download: string;
  upload: string;
}

export default function Home() {
  const [packages, setPackages] = useState<WiFiPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPackage, setSelectedPackage] = useState<number | null>(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [macAddress, setMacAddress] = useState('');
  const [ipAddress, setIpAddress] = useState('');
  const [linkLoginOnly, setLinkLoginOnly] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // Get URL parameters from MikroTik router
    const urlParams = new URLSearchParams(window.location.search);
    setMacAddress(urlParams.get('mac') || '');
    setIpAddress(urlParams.get('ip') || '');
    setLinkLoginOnly(urlParams.get('link_login_only') || '');

    // Load packages
    loadPackages();
  }, []);

  async function loadPackages() {
    try {
      // Try to fetch from Supabase
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
      const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

      if (supabaseUrl && supabaseKey) {
        const response = await fetch(
          `${supabaseUrl}/rest/v1/internet_packages?is_active=eq.true&order=price.asc`,
          {
            headers: {
              'apikey': supabaseKey,
              'Authorization': `Bearer ${supabaseKey}`,
              'Content-Type': 'application/json',
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            const mappedPackages = data.map((pkg: any) => ({
              id: pkg.id,
              name: pkg.name,
              price: pkg.price,
              duration: formatDuration(pkg.duration_seconds),
              download: pkg.download_rate_limit,
              upload: pkg.upload_rate_limit,
            }));
            setPackages(mappedPackages);
            setLoading(false);
            return;
          }
        }
      }
    } catch (error) {
      console.error('Error fetching packages from Supabase:', error);
    }

    // Fallback to static packages
    setPackages([
      {
        id: 1,
        name: 'Hourly Pass',
        price: 1.00,
        duration: '1 hour',
        download: '5M',
        upload: '2M',
      },
      {
        id: 2,
        name: 'Daily Pass',
        price: 3.00,
        duration: '24 hours',
        download: '10M',
        upload: '5M',
      },
      {
        id: 3,
        name: 'Weekly Pass',
        price: 15.00,
        duration: '7 days',
        download: '20M',
        upload: '10M',
      },
      {
        id: 4,
        name: 'Monthly Pass',
        price: 50.00,
        duration: '30 days',
        download: '50M',
        upload: '25M',
      },
    ]);
    setLoading(false);
  }

  function formatDuration(seconds: number): string {
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days`;
    return `${Math.floor(seconds / 2592000)} months`;
  }

  async function handlePayment(e: React.FormEvent) {
    e.preventDefault();

    if (!selectedPackage) {
      alert('Please select a package');
      return;
    }

    if (!phoneNumber || phoneNumber.length < 10) {
      alert('Please enter a valid phone number');
      return;
    }

    setIsSubmitting(true);

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://lincolns-net-backend.onrender.com';

    try {
      const response = await fetch(`${backendUrl}/pay`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          package_id: selectedPackage,
          phone_number: phoneNumber,
          mac: macAddress,
          ip: ipAddress,
          link_login_only: linkLoginOnly,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Redirect to success page or payment gateway
        if (data.redirect_url) {
          window.location.href = data.redirect_url;
        } else {
          alert('Payment initiated! Check your phone for M-Pesa prompt.');
        }
      } else {
        alert(data.detail || 'Payment initiation failed. Please try again.');
      }
    } catch (error) {
      console.error('Error initiating payment:', error);
      alert('Error connecting to payment service. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.spinner}></div>
        <p style={{ color: 'white', fontSize: '16px' }}>Loading packages...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.logo}>📶</div>
          <h1 style={styles.title}>Lincoln&apos;s net</h1>
          <p style={styles.subtitle}>Fast, Reliable WiFi Access</p>
        </div>

        {/* Packages */}
        <div style={styles.packagesList}>
          {packages.map((pkg) => (
            <div
              key={pkg.id}
              onClick={() => setSelectedPackage(pkg.id)}
              style={{
                ...styles.packageCard,
                border: `2px solid ${selectedPackage === pkg.id ? '#667eea' : '#e2e8f0'}`,
                background: selectedPackage === pkg.id ? '#f7fafc' : '#ffffff',
              }}
            >
              {selectedPackage === pkg.id && (
                <div style={styles.checkmark}>✓</div>
              )}
              <div style={styles.packageName}>{pkg.name}</div>
              <div style={styles.packagePrice}>${pkg.price.toFixed(2)}</div>
              <div style={styles.packageDetails}>
                <span style={styles.badge}>⏱ {pkg.duration}</span>
                <span style={styles.badge}>📥 {pkg.download}</span>
                <span style={styles.badge}>📤 {pkg.upload}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Payment Form */}
        <form onSubmit={handlePayment}>
          <div style={styles.formGroup}>
            <label style={styles.label}>Phone Number (M-Pesa)</label>
            <input
              type="tel"
              placeholder="e.g., 0712345678"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value.replace(/[^0-9]/g, ''))}
              maxLength={10}
              style={styles.input}
              required
            />
          </div>

          <button
            type="submit"
            disabled={!selectedPackage || isSubmitting}
            style={{
              ...styles.button,
              background: selectedPackage && !isSubmitting 
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
                : '#cbd5e0',
              cursor: selectedPackage && !isSubmitting ? 'pointer' : 'not-allowed',
            }}
          >
            {isSubmitting ? 'Processing...' : 'Connect Now'}
          </button>
        </form>

        {/* Footer */}
        <div style={styles.footer}>
          Secure payment via M-Pesa | Powered by Lincoln&apos;s net
        </div>
      </div>
    </div>
  );
}

// Styles
const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '20px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  card: {
    width: '100%',
    maxWidth: '480px',
    background: 'rgba(255, 255, 255, 0.95)',
    borderRadius: '24px',
    padding: '32px 24px',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '32px',
  },
  logo: {
    width: '80px',
    height: '80px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderRadius: '20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
    fontSize: '36px',
    boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#2d3748',
    marginBottom: '8px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#718096',
  },
  packagesList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
    marginBottom: '32px',
  },
  packageCard: {
    borderRadius: '16px',
    padding: '20px',
    cursor: 'pointer',
    transition: 'all 0.3s',
    position: 'relative' as const,
    userSelect: 'none' as const,
  },
  checkmark: {
    position: 'absolute' as const,
    top: '12px',
    right: '12px',
    width: '24px',
    height: '24px',
    background: '#667eea',
    color: 'white',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    fontWeight: 'bold',
  },
  packageName: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#2d3748',
    marginBottom: '8px',
  },
  packagePrice: {
    fontSize: '24px',
    fontWeight: 700,
    color: '#667eea',
    marginBottom: '12px',
  },
  packageDetails: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap' as const,
  },
  badge: {
    background: '#edf2f7',
    color: '#4a5568',
    padding: '4px 8px',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 500,
  },
  formGroup: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
    color: '#4a5568',
    marginBottom: '8px',
  },
  input: {
    width: '100%',
    padding: '16px',
    border: '2px solid #e2e8f0',
    borderRadius: '12px',
    fontSize: '16px',
    color: '#2d3748',
    outline: 'none',
    transition: 'all 0.3s',
    boxSizing: 'border-box' as const,
  },
  button: {
    width: '100%',
    padding: '16px',
    color: 'white',
    border: 'none',
    borderRadius: '12px',
    fontSize: '18px',
    fontWeight: 600,
    transition: 'all 0.3s',
    boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
  },
  footer: {
    textAlign: 'center' as const,
    marginTop: '24px',
    fontSize: '12px',
    color: '#a0aec0',
  },
  loadingContainer: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid rgba(255, 255, 255, 0.3)',
    borderTopColor: 'white',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
};

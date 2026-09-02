'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/utils/supabase/client';

interface Package {
  id: number;
  name: string;
  description: string | null;
  price: number;
  duration_seconds: number;
  download_rate_limit: string;
  upload_rate_limit: string;
  is_active: boolean;
}

export default function Home() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPackage, setSelectedPackage] = useState<number | null>(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [macAddress, setMacAddress] = useState('');
  const [ipAddress, setIpAddress] = useState('');
  const [linkLoginOnly, setLinkLoginOnly] = useState('');
  const supabase = createClient();

  useEffect(() => {
    // Get URL parameters from MikroTik
    const urlParams = new URLSearchParams(window.location.search);
    setMacAddress(urlParams.get('mac') || '');
    setIpAddress(urlParams.get('ip') || '');
    setLinkLoginOnly(urlParams.get('link_login_only') || '');

    // Fetch packages
    fetchPackages();
  }, []);

  async function fetchPackages() {
    try {
      const { data, error } = await supabase
        .from('internet_packages')
        .select('*')
        .eq('is_active', true)
        .order('price', { ascending: true });

      if (error) throw error;
      setPackages(data || []);
    } catch (error) {
      console.error('Error fetching packages:', error);
    } finally {
      setLoading(false);
    }
  }

  function formatDuration(seconds: number): string {
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days`;
    return `${Math.floor(seconds / 2592000)} months`;
  }

  function handlePackageSelect(packageId: number) {
    setSelectedPackage(packageId);
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

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    
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

      if (response.ok) {
        const data = await response.json();
        // Redirect to payment or success page
        window.location.href = data.redirect_url || `${backendUrl}/success`;
      } else {
        alert('Payment initiation failed. Please try again.');
      }
    } catch (error) {
      console.error('Error initiating payment:', error);
      alert('Error connecting to payment service');
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading packages...</p>
      </div>
    );
  }

  return (
    <div className="portal-container">
      <div className="portal-card">
        <div className="portal-header">
          <div className="portal-logo">📶</div>
          <h1>Lincoln&apos;s net</h1>
          <p>Fast, Reliable WiFi Access</p>
        </div>

        <div className="packages-list">
          {packages.map((pkg) => (
            <div
              key={pkg.id}
              className={`package-card ${selectedPackage === pkg.id ? 'selected' : ''}`}
              onClick={() => handlePackageSelect(pkg.id)}
            >
              <div className="package-name">{pkg.name}</div>
              {pkg.description && (
                <div className="package-description">{pkg.description}</div>
              )}
              <div className="package-price">${pkg.price.toFixed(2)}</div>
              <div className="package-details">
                <span className="package-badge">⏱ {formatDuration(pkg.duration_seconds)}</span>
                <span className="package-badge">📥 {pkg.download_rate_limit}</span>
                <span className="package-badge">📤 {pkg.upload_rate_limit}</span>
              </div>
            </div>
          ))}
        </div>

        <form onSubmit={handlePayment}>
          <div className="form-group">
            <label htmlFor="phone">Phone Number (M-Pesa)</label>
            <input
              type="tel"
              id="phone"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value.replace(/[^0-9]/g, ''))}
              placeholder="e.g., 0712345678"
              pattern="[0-9]{10}"
              maxLength={10}
              required
            />
          </div>

          <button type="submit" className="submit-button" disabled={!selectedPackage}>
            Connect Now
          </button>
        </form>

        <div className="portal-footer">
          Secure payment via M-Pesa | Powered by Lincoln&apos;s net
        </div>
      </div>
    </div>
  );
}

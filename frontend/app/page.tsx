'use client';

import { useEffect, useState } from 'react';

export default function Home() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');

  useEffect(() => {
    // For now, just show static packages
    // Later you can connect to Supabase
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
    ]);
    setLoading(false);
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial' }}>
      <h1>Lincoln&apos;s net</h1>
      <p>Fast, Reliable WiFi Access</p>
      
      {packages.map((pkg) => (
        <div
          key={pkg.id}
          onClick={() => setSelectedPackage(pkg.id)}
          style={{
            border: `2px solid ${selectedPackage === pkg.id ? 'blue' : 'gray'}`,
            padding: '20px',
            margin: '10px 0',
            borderRadius: '10px',
            cursor: 'pointer',
          }}
        >
          <h3>{pkg.name}</h3>
          <div>${pkg.price.toFixed(2)}</div>
          <div>Duration: {pkg.duration}</div>
          <div>Download: {pkg.download} | Upload: {pkg.upload}</div>
        </div>
      ))}

      <input
        type="tel"
        placeholder="Phone Number"
        value={phoneNumber}
        onChange={(e) => setPhoneNumber(e.target.value)}
        style={{ width: '100%', padding: '12px', margin: '10px 0' }}
      />

      <button
        style={{
          width: '100%',
          padding: '16px',
          background: 'blue',
          color: 'white',
          border: 'none',
          borderRadius: '10px',
        }}
      >
        Connect Now
      </button>
    </div>
  );
}

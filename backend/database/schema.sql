-- Lincoln's net - Application Database Schema
-- PostgreSQL Schema for WiFi Billing System

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- System Settings Table
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Internet Packages Table
CREATE TABLE IF NOT EXISTS internet_packages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    duration_seconds INTEGER NOT NULL,
    download_rate_limit VARCHAR(50) NOT NULL DEFAULT '1M',
    upload_rate_limit VARCHAR(50) NOT NULL DEFAULT '1M',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Billing Transactions Table
CREATE TABLE IF NOT EXISTS billing_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    mac_address VARCHAR(17) NOT NULL,
    package_id INTEGER REFERENCES internet_packages(id),
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, SUCCESS, FAILED, EXPIRED
    payment_reference VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better query performance
CREATE INDEX idx_billing_transactions_mac ON billing_transactions(mac_address);
CREATE INDEX idx_billing_transactions_status ON billing_transactions(status);
CREATE INDEX idx_billing_transactions_phone ON billing_transactions(phone_number);
CREATE INDEX idx_internet_packages_active ON internet_packages(is_active);

-- Insert default packages
INSERT INTO internet_packages (name, description, price, duration_seconds, download_rate_limit, upload_rate_limit)
VALUES 
    ('Hourly Pass', '1 hour of high-speed internet', 1.00, 3600, '5M', '2M'),
    ('Daily Pass', '24 hours of unlimited internet', 3.00, 86400, '10M', '5M'),
    ('Weekly Pass', '7 days of premium internet', 15.00, 604800, '20M', '10M'),
    ('Monthly Pass', '30 days of unlimited internet', 50.00, 2592000, '50M', '25M')
ON CONFLICT DO NOTHING;

-- Insert default settings
INSERT INTO system_settings (setting_key, setting_value, description, is_secret)
VALUES 
    ('gateway_name', 'Lincoln''s net', 'WiFi Gateway Name', FALSE),
    ('radius_secret', 'change-this-secret', 'RADIUS Server Secret', TRUE),
    ('payment_gateway_url', 'https://payment-gateway.example.com', 'Payment Gateway URL', FALSE)
ON CONFLICT (setting_key) DO NOTHING;

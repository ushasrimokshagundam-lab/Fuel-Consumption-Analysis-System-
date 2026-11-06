CREATE DATABASE IF NOT EXISTS fuel_db;
USE fuel_db;

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id    INT PRIMARY KEY AUTO_INCREMENT,
    vehicle_code  VARCHAR(20) NOT NULL UNIQUE,
    vehicle_type  VARCHAR(30) NOT NULL,
    fuel_type     VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS fuel_records (
    record_id       INT PRIMARY KEY AUTO_INCREMENT,
    vehicle_id      INT NOT NULL,
    fill_date       DATE NOT NULL,
    odometer_km     INT NOT NULL,
    litres          DECIMAL(8,2) NOT NULL,
    total_cost      DECIMAL(10,2) NOT NULL,
    full_tank_flag  TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE
);

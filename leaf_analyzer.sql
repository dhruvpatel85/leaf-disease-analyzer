-- ============================================
-- Leaf Analyzer Database Setup
-- Run this in phpMyAdmin or MySQL CLI:
--   mysql -u root -p < leaf_analyzer.sql
-- ============================================

CREATE DATABASE IF NOT EXISTS leaf_analyzer
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE leaf_analyzer;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id         INT          AUTO_INCREMENT PRIMARY KEY,
    full_name  VARCHAR(100) NOT NULL,
    email      VARCHAR(150) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Analysis History Table
CREATE TABLE IF NOT EXISTS analysis_history (
    id            INT              AUTO_INCREMENT PRIMARY KEY,
    user_id       INT              NOT NULL,
    image_path    VARCHAR(255)     NOT NULL,
    result_status ENUM('healthy','unhealthy') NOT NULL,
    disease_name  VARCHAR(100)     DEFAULT NULL,
    confidence    DECIMAL(5,2)     DEFAULT NULL,
    solution      TEXT             DEFAULT NULL,
    analyzed_at   TIMESTAMP        DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

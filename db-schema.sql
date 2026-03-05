-- MySQL schema for Telegram local sync project

CREATE TABLE IF NOT EXISTS channels (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  telegram_id BIGINT NOT NULL UNIQUE,
  username VARCHAR(255) NULL UNIQUE,
  title VARCHAR(512) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  channel_id BIGINT UNSIGNED NOT NULL,
  message_id BIGINT NOT NULL,
  text MEDIUMTEXT NULL,
  media_url VARCHAR(1024) NULL,
  published_at DATETIME NOT NULL,
  synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_channel_message (channel_id, message_id),
  KEY idx_channel_published (channel_id, published_at DESC),
  CONSTRAINT fk_messages_channel
    FOREIGN KEY (channel_id) REFERENCES channels(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Attachments: .npvt files linked to messages (channel_id + message_id = same as messages table)
CREATE TABLE IF NOT EXISTS message_files (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  channel_id BIGINT UNSIGNED NOT NULL,
  message_id BIGINT NOT NULL,
  filename VARCHAR(255) NOT NULL,
  content LONGBLOB NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_channel_message_file (channel_id, message_id),
  CONSTRAINT fk_message_files_message
    FOREIGN KEY (channel_id, message_id) REFERENCES messages(channel_id, message_id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sync_logs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  started_at DATETIME NOT NULL,
  finished_at DATETIME NULL,
  status ENUM('success', 'partial', 'error') NOT NULL,
  error_message TEXT NULL,
  channels_processed INT NOT NULL DEFAULT 0,
  messages_inserted INT NOT NULL DEFAULT 0,
  messages_skipped INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


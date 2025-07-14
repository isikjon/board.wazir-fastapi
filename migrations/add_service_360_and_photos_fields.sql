-- Добавление полей для 360° панорам и системы фотографий в таблицу service_cards
-- Выполнить на MySQL базе данных

ALTER TABLE service_cards 
ADD COLUMN tour_360_url VARCHAR(255) NULL COMMENT 'URL для старой совместимости',
ADD COLUMN tour_360_file_id VARCHAR(100) NULL COMMENT 'ID файла панорамы',  
ADD COLUMN tour_360_original_url VARCHAR(255) NULL COMMENT 'Путь к оригинальному файлу',
ADD COLUMN tour_360_optimized_url VARCHAR(255) NULL COMMENT 'Путь к оптимизированному файлу',
ADD COLUMN tour_360_preview_url VARCHAR(255) NULL COMMENT 'Путь к превью',
ADD COLUMN tour_360_thumbnail_url VARCHAR(255) NULL COMMENT 'Путь к миниатюре',
ADD COLUMN tour_360_metadata TEXT NULL COMMENT 'JSON с метаданными панорамы',
ADD COLUMN tour_360_uploaded_at DATETIME NULL COMMENT 'Дата загрузки панорамы',
ADD COLUMN photos_uploaded_at DATETIME NULL COMMENT 'Дата последней загрузки фотографий';

-- Создание индексов для оптимизации поиска
CREATE INDEX idx_service_cards_360_file_id ON service_cards(tour_360_file_id);
CREATE INDEX idx_service_cards_360_uploaded ON service_cards(tour_360_uploaded_at);
CREATE INDEX idx_service_cards_photos_uploaded ON service_cards(photos_uploaded_at); 
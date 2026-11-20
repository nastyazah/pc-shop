-- Маленький стартовий набір для розробки. Справжній каталог (5-20 тис.) додамо окремим імпортом.
INSERT INTO categories (id, parent_id, slug, name, position) VALUES
 (1, NULL, 'components',   'Комплектуючі', 0),
 (2, 1, 'motherboards', 'Материнські плати', 1),
 (3, 1, 'cpu',          'Процесори', 2),
 (4, 1, 'gpu',          'Відеокарти', 3),
 (5, 1, 'ram',          'Оперативна памʼять', 4),
 (6, 1, 'ssd',          'SSD-накопичувачі', 5),
 (7, 1, 'psu',          'Блоки живлення', 6),
 (8, 1, 'cases',        'Корпуси', 7),
 (9, 1, 'coolers',      'Охолодження', 8);
SELECT setval(pg_get_serial_sequence('categories', 'id'), 9);

INSERT INTO brands (slug, name) VALUES
 ('asus','ASUS'),('msi','MSI'),('gigabyte','Gigabyte'),('amd','AMD'),('intel','Intel'),
 ('sapphire','Sapphire'),('kingston','Kingston'),('corsair','Corsair'),('samsung','Samsung'),
 ('seasonic','Seasonic'),('lian-li','Lian Li'),('deepcool','DeepCool');

INSERT INTO products (sku, name, brand_id, category_id, description, price, old_price, in_stock, specs, popularity)
SELECT v.sku, v.name, b.id, c.id, v.descr, v.price, v.old, v.stock, v.specs, v.pop
FROM (VALUES
 ('MB-ASU-B650TUF', 'ASUS TUF GAMING B650-PLUS WIFI', 'asus', 'motherboards',
  'Материнська плата для процесорів Ryzen 7000 з Wi-Fi 6, підтримкою DDR5 та PCIe 5.0.',
  9499::numeric, 10299::numeric, true, '{"socket":"AM5","chipset":"B650","ram_type":"DDR5","form_factor":"ATX"}'::jsonb, 90),
 ('MB-MSI-B550TOM', 'MSI MAG B550 TOMAHAWK', 'msi', 'motherboards',
  'Надійна плата на AM4 з DDR4, посиленим живленням і двома слотами M.2.',
  6999, NULL, true, '{"socket":"AM4","chipset":"B550","ram_type":"DDR4","form_factor":"ATX"}', 70),
 ('MB-GIG-Z790AE', 'Gigabyte Z790 AORUS ELITE AX', 'gigabyte', 'motherboards',
  'Плата для Intel 12-14 покоління з DDR5, Wi-Fi 6E та потужною системою живлення.',
  11999, NULL, true, '{"socket":"LGA1700","chipset":"Z790","ram_type":"DDR5","form_factor":"ATX"}', 55),
 ('CPU-AMD-R57600X', 'AMD Ryzen 5 7600X', 'amd', 'cpu',
  'Шестиядерний процесор на архітектурі Zen 4 для ігор та роботи.',
  8499, 9299, true, '{"socket":"AM5","cores":6,"threads":12}', 95),
 ('CPU-INT-I512400F', 'Intel Core i5-12400F', 'intel', 'cpu',
  'Доступний шестиядерний процесор для ігрового ПК, без вбудованої графіки.',
  4899, NULL, true, '{"socket":"LGA1700","cores":6,"threads":12}', 85),
 ('GPU-MSI-4060V2X', 'MSI GeForce RTX 4060 VENTUS 2X BLACK 8G', 'msi', 'gpu',
  'Відеокарта для Full HD і QHD з DLSS 3 та тихою системою охолодження.',
  15499, NULL, true, '{"vram_gb":8,"vendor":"NVIDIA"}', 100),
 ('GPU-SAP-7800XT', 'Sapphire PULSE Radeon RX 7800 XT 16GB', 'sapphire', 'gpu',
  'Відеокарта з 16 ГБ памʼяті для ігор у QHD та 4K.',
  27999, 29499, false, '{"vram_gb":16,"vendor":"AMD"}', 60),
 ('RAM-KNG-FB32D5', 'Kingston FURY Beast 32GB (2x16GB) DDR5-6000', 'kingston', 'ram',
  'Комплект оперативної памʼяті DDR5 з профілем EXPO/XMP.',
  5799, NULL, true, '{"ram_type":"DDR5","capacity_gb":32,"speed_mhz":6000}', 80),
 ('RAM-CRS-V16D4', 'Corsair Vengeance LPX 16GB (2x8GB) DDR4-3200', 'corsair', 'ram',
  'Перевірена часом оперативна памʼять DDR4 з низькопрофільним радіатором.',
  1899, NULL, true, '{"ram_type":"DDR4","capacity_gb":16,"speed_mhz":3200}', 75),
 ('SSD-SAM-980P1T', 'Samsung 980 PRO 1TB NVMe', 'samsung', 'ssd',
  'Швидкий NVMe SSD з інтерфейсом PCIe 4.0 до 7000 МБ/с.',
  5199, 5699, true, '{"capacity_gb":1000,"interface":"NVMe PCIe 4.0"}', 88),
 ('SSD-KNG-NV2-500', 'Kingston NV2 500GB NVMe', 'kingston', 'ssd',
  'Бюджетний NVMe SSD для системи та програм.',
  1599, NULL, true, '{"capacity_gb":500,"interface":"NVMe PCIe 4.0"}', 65),
 ('PSU-SEA-FOCUS750', 'Seasonic FOCUS GX-750', 'seasonic', 'psu',
  'Повністю модульний блок живлення 750 Вт із сертифікатом 80+ Gold.',
  4799, NULL, true, '{"wattage":750,"efficiency":"80+ Gold"}', 50),
 ('CASE-LIA-LAN216', 'Lian Li LANCOOL 216', 'lian-li', 'cases',
  'Корпус із чудовим повітряним потоком і місцем під великі відеокарти.',
  4999, NULL, true, '{"form_factor":"ATX"}', 45),
 ('COOL-DEE-AK620', 'DeepCool AK620', 'deepcool', 'coolers',
  'Двобаштовий кулер для процесора, розсіює до 260 Вт.',
  2799, NULL, true, '{"type":"Повітряний","tdp_w":260}', 52)
) AS v(sku, name, brand, cat, descr, price, old, stock, specs, pop)
JOIN brands b ON b.slug = v.brand
JOIN categories c ON c.slug = v.cat;

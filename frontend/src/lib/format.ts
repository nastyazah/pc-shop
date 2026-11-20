export const formatPrice = (n: number) => `${new Intl.NumberFormat("uk-UA").format(Math.round(n))} ₴`;

export function plural(n: number, one: string, few: string, many: string) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

export function formatSpec(key: string, value: string | number): string {
  const v = Number(value);
  switch (key) {
    case "vram_gb": return `${value} ГБ`;
    case "capacity_gb": return v >= 1000 ? `${v / 1000} ТБ` : `${value} ГБ`;
    case "wattage":
    case "tdp_w": return `${value} Вт`;
    case "speed_mhz": return `${value} МГц`;
    case "boost_ghz": return `${value} ГГц`;
    case "cores": return `${value} ядер`;
    case "read_mbps": return `${value} МБ/с`;
    case "rpm": return `${value} об/хв`;
    case "cache_mb": return `${value} МБ`;
    case "size_mm":
    case "radiator_mm": return `${value} мм`;
    case "quantity": return `${value} шт.`;
    default: return String(value);
  }
}

export const SPEC_LABELS: Record<string, string> = {
  socket: "Сокет", chipset: "Чипсет", ram_type: "Тип памʼяті", form_factor: "Форм-фактор", wifi: "Wi-Fi",
  cores: "Ядра", threads: "Потоки", boost_ghz: "Частота до", tdp_w: "TDP", vendor: "Виробник чипа",
  chip: "Графічний чип", vram_gb: "Відеопамʼять", memory_type: "Тип памʼяті", capacity_gb: "Обсяг",
  speed_mhz: "Частота", modules: "Комплект", interface: "Інтерфейс", read_mbps: "Читання", rpm: "Оберти",
  cache_mb: "Кеш", wattage: "Потужність", efficiency: "Сертифікат", modularity: "Кабелі", color: "Колір",
  side_panel: "Бокова панель", type: "Тип", radiator_mm: "Радіатор", size_mm: "Розмір", quantity: "У комплекті",
  connector: "Підключення",
};

// які характеристики показувати на картці для кожної категорії
export const CARD_SPECS: Record<string, string[]> = {
  motherboards: ["socket", "chipset", "ram_type", "form_factor"],
  cpu: ["socket", "cores", "boost_ghz", "tdp_w"],
  gpu: ["chip", "vram_gb", "memory_type"],
  ram: ["ram_type", "capacity_gb", "speed_mhz", "modules"],
  ssd: ["capacity_gb", "interface", "read_mbps", "form_factor"],
  hdd: ["capacity_gb", "rpm", "cache_mb", "form_factor"],
  psu: ["wattage", "efficiency", "modularity"],
  cases: ["form_factor", "color", "side_panel"],
  coolers: ["type", "tdp_w", "radiator_mm"],
  fans: ["size_mm", "quantity", "connector"],
};

export const discountPercent = (price: number, old?: number | null) =>
  old && old > price ? Math.round((1 - price / old) * 100) : 0;

export const CATEGORIES = [
  { slug: "motherboards", label: "Материнські плати", hint: "сокет, чипсет, тип памʼяті" },
  { slug: "cpu", label: "Процесори", hint: "Ryzen, Core, кількість ядер" },
  { slug: "gpu", label: "Відеокарти", hint: "GeForce, Radeon, обсяг памʼяті" },
  { slug: "ram", label: "Оперативна памʼять", hint: "DDR4, DDR5, комплекти" },
  { slug: "ssd", label: "SSD-накопичувачі", hint: "NVMe, SATA, обсяг" },
  { slug: "hdd", label: "Жорсткі диски", hint: "для архівів і медіатеки" },
  { slug: "psu", label: "Блоки живлення", hint: "потужність, сертифікат 80+" },
  { slug: "cases", label: "Корпуси", hint: "форм-фактор, колір" },
  { slug: "coolers", label: "Охолодження процесора", hint: "повітряні та рідинні" },
  { slug: "fans", label: "Вентилятори", hint: "120 і 140 мм" },
];

export const categoryLabel = (slug?: string | null) => CATEGORIES.find((c) => c.slug === slug)?.label;

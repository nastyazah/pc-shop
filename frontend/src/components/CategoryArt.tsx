// Лінійні ілюстрації категорій: показуються, поки в товару немає фото.
const ART: Record<string, React.ReactNode> = {
  motherboards: (<><rect x="10" y="8" width="100" height="74" rx="6" /><rect x="26" y="22" width="28" height="28" rx="3" /><path d="M68 18v36M78 18v36M88 18v36M98 18v36M20 66h58" /><circle cx="18" cy="16" r="2" /><circle cx="102" cy="74" r="2" /></>),
  cpu: (<><rect x="30" y="20" width="60" height="50" rx="6" /><rect x="42" y="32" width="36" height="26" rx="3" /><path d="M40 12v8M52 12v8M64 12v8M76 12v8M40 70v8M52 70v8M64 70v8M76 70v8M22 32h8M22 45h8M22 58h8M90 32h8M90 45h8M90 58h8" /></>),
  gpu: (<><rect x="8" y="22" width="104" height="46" rx="6" /><circle cx="38" cy="45" r="14" /><circle cx="82" cy="45" r="14" /><circle cx="38" cy="45" r="4" /><circle cx="82" cy="45" r="4" /><path d="M20 68v6h50v-6" /></>),
  ram: (<><rect x="8" y="26" width="104" height="34" rx="3" /><rect x="18" y="34" width="14" height="18" rx="2" /><rect x="38" y="34" width="14" height="18" rx="2" /><rect x="58" y="34" width="14" height="18" rx="2" /><rect x="78" y="34" width="14" height="18" rx="2" /><path d="M14 66h92" strokeDasharray="3 4" /></>),
  ssd: (<><rect x="14" y="24" width="86" height="42" rx="6" /><rect x="26" y="34" width="20" height="22" rx="2" /><rect x="54" y="34" width="20" height="22" rx="2" /><path d="M100 36v18M106 40v10" /></>),
  hdd: (<><rect x="22" y="12" width="76" height="66" rx="6" /><circle cx="56" cy="45" r="21" /><circle cx="56" cy="45" r="5" /><path d="M86 20L66 40" /></>),
  psu: (<><rect x="14" y="18" width="92" height="54" rx="6" /><circle cx="46" cy="45" r="18" /><path d="M46 27v36M28 45h36M78 32h20M78 40h20M78 48h20M78 56h20" /></>),
  cases: (<><rect x="34" y="8" width="52" height="74" rx="6" /><rect x="41" y="16" width="30" height="42" rx="3" /><circle cx="56" cy="70" r="5" /><path d="M78 18v10" /></>),
  coolers: (<><rect x="36" y="14" width="48" height="52" rx="4" /><path d="M36 26h48M36 36h48M36 46h48M36 56h48M46 66V14M60 66V14M74 66V14" /><rect x="30" y="66" width="60" height="9" rx="2" /></>),
  fans: (<><circle cx="60" cy="45" r="34" /><circle cx="60" cy="45" r="7" /><ellipse cx="60" cy="27" rx="7" ry="12" /><ellipse cx="78" cy="45" rx="12" ry="7" /><ellipse cx="60" cy="63" rx="7" ry="12" /><ellipse cx="42" cy="45" rx="12" ry="7" /></>),
};

export default function CategoryArt({ category, className = "h-3/5 text-navy/30" }: { category: string; className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 120 90"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ART[category] ?? ART.cpu}
    </svg>
  );
}

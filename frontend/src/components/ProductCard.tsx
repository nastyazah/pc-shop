import type { Product } from "@/lib/api";
import { CARD_SPECS, SPEC_LABELS, discountPercent, formatPrice, formatSpec } from "@/lib/format";
import ProductImage from "./ProductImage";

// Світла панель під фото (як знімки на білому в магазинах), решта на темному.
export default function ProductCard({ p, showDescription = true }: { p: Product; showDescription?: boolean }) {
  const keys = (CARD_SPECS[p.category] ?? Object.keys(p.specs)).filter((k) => p.specs[k] !== undefined).slice(0, 3);
  const off = discountPercent(p.price, p.old_price);
  return (
    <article className="group relative isolate flex h-full flex-col">
      {/* при наведенні картка підсвічується бордовим напівпрозорим градієнтом */}
      <span
        aria-hidden
        className="pointer-events-none absolute -inset-3 -z-10 rounded-3xl bg-[linear-gradient(160deg,rgba(120,0,0,0.62),rgba(193,18,31,0.18)_62%,rgba(120,0,0,0.06))] opacity-0 ring-1 ring-inset ring-red/25 transition-opacity duration-200 group-hover:opacity-100"
      />
      <div className="relative overflow-hidden rounded-2xl bg-cream">
        <ProductImage src={p.image_url} alt={p.name} category={p.category} />
        {off > 0 && <span className="absolute left-3 top-3 bg-red px-2 py-0.5 text-xs font-semibold text-cream">−{off}%</span>}
        {!p.in_stock && <span className="absolute right-3 top-3 text-xs font-medium text-navy/60">Немає в наявності</span>}
      </div>

      <p className="mt-4 flex items-baseline gap-2.5">
        <span className="text-xl font-semibold tabular-nums">{formatPrice(p.price)}</span>
        {p.old_price ? <span className="text-sm tabular-nums text-cream/40 line-through">{formatPrice(p.old_price)}</span> : null}
      </p>
      <h3 className="mt-1.5 line-clamp-3 text-[15px] font-medium leading-snug">{p.name}</h3>
      {showDescription && p.description && <p className="mt-2 line-clamp-2 text-sm leading-snug text-cream/60">{p.description}</p>}

      <dl className="mt-3 text-sm">
        {keys.map((k) => (
          <div key={k} className="flex justify-between gap-3 border-t border-cream/10 py-1.5">
            <dt className="text-cream/45">{SPEC_LABELS[k] ?? k}</dt>
            <dd className="text-right tabular-nums">{formatSpec(k, p.specs[k])}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

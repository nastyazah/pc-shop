"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { Bucket, SearchResponse } from "@/lib/api";
import { formatSpec } from "@/lib/format";

type Props = { facets: SearchResponse["facets"]; category?: string | null };

export default function Facets({ facets, category }: Props) {
  const router = useRouter();
  const params = useSearchParams();

  function update(mutate: (p: URLSearchParams) => void) {
    const p = new URLSearchParams(params.toString());
    mutate(p);
    p.delete("page");
    router.push(`/search?${p.toString()}`, { scroll: false });
  }

  function toggle(name: string, value: string | number) {
    update((p) => {
      const current = p.getAll(name);
      const v = String(value);
      p.delete(name);
      (current.includes(v) ? current.filter((x) => x !== v) : [...current, v]).forEach((x) => p.append(name, x));
    });
  }

  function pickCategory(slug: string) {
    update((p) => {
      if (p.get("category") === slug) p.delete("category");
      else p.set("category", slug);
      [...p.keys()].filter((k) => k.startsWith("spec.")).forEach((k) => p.delete(k)); // фільтри іншої категорії не мають сенсу
    });
  }

  const checked = (name: string, v: string | number) => params.getAll(name).includes(String(v));

  const Group = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <fieldset className="border-t border-cream/10 py-5 first:border-t-0 first:pt-0">
      <legend className="mb-3 text-sm font-semibold">{title}</legend>
      <div className="space-y-2">{children}</div>
    </fieldset>
  );

  const Check = ({ name, b, fmt }: { name: string; b: Bucket; fmt?: (v: string | number) => string }) => (
    <label className="flex cursor-pointer items-center gap-2.5 text-sm">
      <input type="checkbox" className="size-4 accent-red" checked={checked(name, b.value)} onChange={() => toggle(name, b.value)} />
      <span className="flex-1">{fmt ? fmt(b.value) : String(b.value)}</span>
      <span className="tabular-nums text-cream/40">{b.count}</span>
    </label>
  );

  return (
    <div>
      {facets.categories.length > 1 || category ? (
        <Group title="Категорія">
          {facets.categories.map((c) => (
            <label key={String(c.value)} className="flex cursor-pointer items-center gap-2.5 text-sm">
              <input type="radio" name="category" className="size-4 accent-red" checked={category === c.value} onChange={() => pickCategory(String(c.value))} onClick={() => category === c.value && pickCategory(String(c.value))} />
              <span className="flex-1">{c.label ?? c.value}</span>
              <span className="tabular-nums text-cream/40">{c.count}</span>
            </label>
          ))}
        </Group>
      ) : null}

      {facets.brands.length > 0 && (
        <Group title="Бренд">
          {facets.brands.map((b) => <Check key={String(b.value)} name="brand" b={b} />)}
        </Group>
      )}

      <Group title="Ціна, ₴">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            update((p) => {
              for (const k of ["price_min", "price_max"]) {
                const v = String(f.get(k) ?? "").trim();
                if (v) p.set(k, v); else p.delete(k);
              }
            });
          }}
          className="flex items-center gap-2"
        >
          <input name="price_min" inputMode="numeric" aria-label="Ціна від" placeholder={facets.price.min ? String(Math.floor(facets.price.min)) : "від"} defaultValue={params.get("price_min") ?? ""} className="w-full rounded-md border border-cream/20 bg-transparent px-3 py-1.5 text-sm tabular-nums placeholder:text-cream/35" />
          <span className="text-cream/40">–</span>
          <input name="price_max" inputMode="numeric" aria-label="Ціна до" placeholder={facets.price.max ? String(Math.ceil(facets.price.max)) : "до"} defaultValue={params.get("price_max") ?? ""} className="w-full rounded-md border border-cream/20 bg-transparent px-3 py-1.5 text-sm tabular-nums placeholder:text-cream/35" />
          <button type="submit" className="btn-red rounded-lg px-3 py-1.5 text-sm font-medium">Ок</button>
        </form>
      </Group>

      {Object.entries(facets.specs).map(([key, f]) =>
        f.buckets.length > 0 ? (
          <Group key={key} title={f.label}>
            {f.buckets.map((b) => (
              <Check key={String(b.value)} name={`spec.${key}`} b={b} fmt={(v) => formatSpec(key, v)} />
            ))}
          </Group>
        ) : null,
      )}

      <Group title="Наявність">
        <label className="flex cursor-pointer items-center gap-2.5 text-sm">
          <input type="checkbox" className="size-4 accent-red" checked={params.get("in_stock") === "true"} onChange={(e) => update((p) => (e.target.checked ? p.set("in_stock", "true") : p.delete("in_stock")))} />
          Тільки в наявності
        </label>
      </Group>
    </div>
  );
}

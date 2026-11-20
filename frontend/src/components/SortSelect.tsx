"use client";

import { useRouter, useSearchParams } from "next/navigation";

const OPTIONS = [
  ["relevance", "За релевантністю"],
  ["popular", "Найпопулярніші"],
  ["price_asc", "Спочатку дешевші"],
  ["price_desc", "Спочатку дорожчі"],
];

export default function SortSelect() {
  const router = useRouter();
  const params = useSearchParams();
  return (
    <label className="flex items-center gap-3 text-sm text-cream/60">
      Сортування
      <select
        value={params.get("sort") ?? "relevance"}
        onChange={(e) => {
          const p = new URLSearchParams(params.toString());
          p.set("sort", e.target.value);
          p.delete("page");
          router.push(`/search?${p.toString()}`, { scroll: false });
        }}
        className="cursor-pointer border-b-2 border-red bg-transparent py-1 pr-1 font-medium text-cream"
      >
        {OPTIONS.map(([v, l]) => (
          <option key={v} value={v} className="bg-ink">{l}</option>
        ))}
      </select>
    </label>
  );
}

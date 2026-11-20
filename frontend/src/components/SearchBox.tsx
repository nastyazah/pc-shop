"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { suggest, type SuggestResponse } from "@/lib/api";
import { formatPrice } from "@/lib/format";

// Викликати всередині <Suspense>: компонент читає ?q= з адреси.
export default function SearchBox({ variant = "hero" }: { variant?: "hero" | "header" }) {
  const hero = variant === "hero";
  const router = useRouter();
  const params = useSearchParams();
  const listId = useId();
  const boxRef = useRef<HTMLDivElement>(null);
  const [value, setValue] = useState(params.get("q") ?? "");
  const [data, setData] = useState<SuggestResponse | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  useEffect(() => setValue(params.get("q") ?? ""), [params]);

  // підказки з невеликою затримкою; попередній запит скасовується
  useEffect(() => {
    const q = value.trim();
    if (q.length < 2) {
      setData(null);
      return;
    }
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      suggest(q, ctrl.signal).then(setData).catch(() => {});
    }, 180);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [value]);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  const products = data?.products ?? [];
  const chips = data?.chips ?? [];
  const showList = open && (products.length > 0 || chips.length > 0);

  function go(q: string) {
    setOpen(false);
    const trimmed = q.trim();
    router.push(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : "/search");
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, products.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, -1));
    } else if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "Enter" && active >= 0 && products[active]) {
      e.preventDefault();
      go(products[active].name);
    }
  }

  return (
    <div ref={boxRef} className="relative">
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          go(value);
        }}
        className={
          hero
            ? "flex h-16 items-center gap-3 rounded-2xl bg-paper pl-5 pr-2.5 text-navy shadow-[0_24px_60px_-24px_rgba(5,14,22,0.75)] ring-1 ring-navy/10 focus-within:ring-2 focus-within:ring-red"
            : "flex h-10 items-center gap-2 rounded-xl bg-cream/10 pl-3 pr-1.5 text-cream ring-1 ring-cream/20 focus-within:ring-2 focus-within:ring-steel"
        }
      >
        <svg aria-hidden viewBox="0 0 24 24" className="size-5 shrink-0 opacity-50" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-label="Пошук товарів"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={hero ? "Наприклад: материнка asus am5 до 8000" : "Пошук товарів"}
          autoComplete="off"
          className={`min-w-0 flex-1 bg-transparent outline-none ${hero ? "text-lg placeholder:text-navy/40" : "text-sm placeholder:text-cream/45"}`}
        />
        <button type="submit" className={`btn-red font-medium ${hero ? "h-12 rounded-xl px-7" : "h-7 rounded-lg px-3 text-sm"}`}>
          Знайти
        </button>
      </form>

      {showList && (
        <div
          id={listId}
          role="listbox"
          className={`absolute top-full z-40 mt-2 overflow-hidden rounded-2xl bg-paper text-navy shadow-2xl ring-1 ring-navy/10 ${hero ? "inset-x-0" : "right-0 w-[26rem] max-w-[90vw]"}`}
        >
          {chips.length > 0 && (
            <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-navy/10 px-4 py-3 text-sm">
              <li className="text-navy/55">Розуміємо як:</li>
              {chips.map((c, i) => (
                <li key={i} className="flex items-center gap-1.5 font-medium">
                  <span aria-hidden className="size-1.5 rounded-full bg-red" />
                  {c.label}
                </li>
              ))}
            </ul>
          )}
          {products.map((p, i) => (
            <div
              key={p.id}
              role="option"
              aria-selected={i === active}
              onMouseEnter={() => setActive(i)}
              onClick={() => go(p.name)}
              className={`flex cursor-pointer items-baseline justify-between gap-4 px-4 py-2.5 text-sm ${i === active ? "bg-navy/5" : ""}`}
            >
              <span className="truncate">{p.name}</span>
              <span className="shrink-0 tabular-nums text-navy/55">{formatPrice(p.price)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

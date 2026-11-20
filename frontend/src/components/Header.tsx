"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import SearchBox from "./SearchBox";
import { CATEGORIES } from "@/lib/categories";

// На головній шапка лежить поверх банера, на інших сторінках - напівпрозора темна.
export default function Header() {
  const pathname = usePathname();
  const home = pathname === "/";
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  return (
    <header className={`z-30 w-full text-cream ${home ? "absolute inset-x-0 top-0" : "relative border-b border-cream/10 bg-ink/70 backdrop-blur"}`}>
      <div className="mx-auto flex h-[76px] max-w-7xl items-center gap-8 px-5">
        <Link href="/" className="flex shrink-0 items-center gap-2.5 text-xl font-semibold tracking-tight">
          <span aria-hidden className="grid size-7 place-items-center rounded-full bg-red">
            <span className="size-2.5 rounded-full bg-ink" />
          </span>
          Ядро
        </Link>

        <nav aria-label="Основна навігація" className="flex items-center gap-7 text-sm text-cream/75">
          <div ref={menuRef} className="relative">
            <button
              type="button"
              aria-expanded={open}
              aria-controls="catalog-menu"
              onClick={() => setOpen((v) => !v)}
              className={`flex items-center gap-2 rounded-xl px-3.5 py-2 font-medium text-cream transition-colors hover:bg-cream/10 ${open ? "bg-cream/10" : ""}`}
            >
              Каталог
              <svg aria-hidden viewBox="0 0 12 12" className={`size-3 transition-transform ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="m2 4 4 4 4-4" />
              </svg>
            </button>
            {open && (
              <div id="catalog-menu" className="absolute left-0 top-full z-50 mt-3 w-[min(34rem,90vw)] rounded-2xl bg-paper p-3 text-navy shadow-2xl ring-1 ring-navy/10">
                <Link href="/search" onClick={() => setOpen(false)} className="block rounded-xl px-4 py-3 font-semibold hover:bg-navy/5">
                  Усі товари
                </Link>
                <ul className="grid gap-x-2 sm:grid-cols-2">
                  {CATEGORIES.map((c) => (
                    <li key={c.slug}>
                      <Link href={`/search?category=${c.slug}`} onClick={() => setOpen(false)} className="block rounded-xl px-4 py-2.5 hover:bg-navy/5">
                        <span className="block font-medium">{c.label}</span>
                        <span className="block text-sm text-navy/55">{c.hint}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

        </nav>

        {!home && (
          <div className="ml-auto w-full max-w-xs">
            <Suspense fallback={null}>
              <SearchBox variant="header" />
            </Suspense>
          </div>
        )}
      </div>
    </header>
  );
}

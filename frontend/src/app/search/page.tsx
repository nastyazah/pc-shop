import Link from "next/link";
import Facets from "@/components/Facets";
import ProductCard from "@/components/ProductCard";
import SortSelect from "@/components/SortSelect";
import { search, type SearchResponse } from "@/lib/api";
import { CATEGORIES, categoryLabel } from "@/lib/categories";
import { plural } from "@/lib/format";
import { BANNER_PHOTO } from "@/lib/photos";

const PAGE_SIZE = 24;

// посилання на той самий запит із вибраною категорією
function suggestionQuery(qs: URLSearchParams, category: string) {
  const p = new URLSearchParams(qs.toString());
  p.set("category", category);
  p.delete("page");
  return p.toString();
}
type SP = Promise<Record<string, string | string[] | undefined>>;

export default async function SearchPage({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) {
    if (v === undefined) continue;
    (Array.isArray(v) ? v : [v]).forEach((x) => qs.append(k, x));
  }
  const q = typeof sp.q === "string" ? sp.q : "";
  const page = Math.max(1, Number(sp.page) || 1);

  let data: SearchResponse | null = null;
  try {
    data = await search(qs);
  } catch {
    data = null;
  }

  const pageHref = (n: number) => {
    const p = new URLSearchParams(qs.toString());
    p.set("page", String(n));
    return `/search?${p.toString()}`;
  };

  const state = data?.state ?? "ok";
  const empty = state !== "ok"; // "не продаємо" або "не зрозуміли": без лічильника, фільтрів і чипів
  const u = empty ? undefined : data?.understood;
  const title = q ? `«${q}»` : (categoryLabel(typeof sp.category === "string" ? sp.category : null) ?? "Каталог");
  const hasFixes = !!u && (!!u.corrected_from || (u.typos?.length ?? 0) > 0 || (u.splits?.length ?? 0) > 0 || !!u.llm);
  const hasNotes = !!u && (u.chips.length > 0 || hasFixes);

  return (
    <main>
      <section className="relative isolate overflow-hidden bg-ink text-cream">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={BANNER_PHOTO} alt="" className="absolute inset-0 -z-20 size-full object-cover object-[50%_30%] opacity-70" />
        <div aria-hidden className="absolute inset-0 -z-10 bg-[linear-gradient(90deg,rgba(5,14,22,0.96)_0%,rgba(5,14,22,0.85)_55%,rgba(5,14,22,0.35)_100%)]" />
        <div aria-hidden className="absolute inset-0 -z-10 bg-[radial-gradient(45%_120%_at_95%_100%,rgba(193,18,31,0.45),transparent_70%)]" />
        <div className="mx-auto max-w-7xl px-5 py-12">
          <h1 className="text-4xl font-semibold tracking-[-0.03em] sm:text-5xl">
            {q ? <><span className="text-cream/60">{empty ? "Пошук " : "Результати за "}</span>{title}</> : title}
          </h1>
          {data && !empty && (
            <p className="mt-3 text-cream/65">
              {data.total} {plural(data.total, "товар", "товари", "товарів")}
            </p>
          )}
          {hasNotes && u && (
            <div className="mt-5 text-sm">
              {u.chips.length > 0 && (
                <ul className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
                  <li className="text-cream/55">Ми зрозуміли:</li>
                  {u.chips.map((c, i) => (
                    <li key={i} className="flex items-center gap-1.5 font-medium">
                      <span aria-hidden className="size-1.5 rounded-full bg-red" />
                      {c.label}
                    </li>
                  ))}
                </ul>
              )}
              {hasFixes && (
                <p className="mt-2 text-cream/55">
                  {u.corrected_from && <>Виправили розкладку: «{u.corrected_from}». </>}
                  {u.typos?.map((t) => <span key={t.from}>Виправили «{t.from}» на «{t.to}». </span>)}
                  {u.splits?.map((t) => <span key={t.from}>Розділили «{t.from}» на «{t.to}». </span>)}
                  {u.llm && <span>Частину запиту розібрав ШІ-помічник.</span>}
                </p>
              )}
            </div>
          )}
          {u?.suggestion && (
            <p className="mt-3 text-sm text-cream/70">
              Можливо, ви шукаєте:{" "}
              <Link
                href={`/search?${suggestionQuery(qs, u.suggestion.category)}`}
                className="font-medium text-cream underline decoration-cream/40 underline-offset-4"
              >
                {u.suggestion.label}
              </Link>
            </p>
          )}
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-5 pb-28 pt-12">
        {!data ? (
          <p className="border-l-2 border-red pl-5 text-lg">
            Пошук тимчасово недоступний. Перевірте, що API запущено (uvicorn app.main:app --port 8000).
          </p>
        ) : state === "not_sold" && data.not_sold ? (
          <div>
            <div className="max-w-2xl">
              <h2 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
                {data.not_sold.certain ? "На жаль, ми не продаємо" : "Схоже, ми не продаємо"} {data.not_sold.product}.
              </h2>
              <p className="mt-4 text-lg text-cream/65">У нашому каталозі комплектуючі для ПК. Ось що в нас є:</p>
              <ul className="mt-5 flex flex-wrap gap-x-6 gap-y-2.5">
                {CATEGORIES.map((c) => (
                  <li key={c.slug}>
                    <Link href={`/search?category=${c.slug}`} className="underline decoration-cream/40 underline-offset-4 hover:text-steel">{c.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
            {data.related && data.related.items.length > 0 && (
              <section className="mt-20">
                <h2 className="text-2xl font-semibold tracking-tight">{data.related.title}</h2>
                <ul className="mt-8 grid grid-cols-2 gap-x-6 gap-y-12 md:grid-cols-3 xl:grid-cols-4">
                  {data.related.items.map((p) => (
                    <li key={p.id}>
                      <ProductCard p={p} showDescription={false} />
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        ) : state === "unknown" ? (
          <div className="max-w-2xl">
            <h2 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">Ми не зовсім зрозуміли запит.</h2>
            {data.variants && data.variants.length > 0 ? (
              <>
                <p className="mt-4 text-lg text-cream/65">Можливо, ви шукали:</p>
                <ul className="mt-5 flex flex-wrap gap-x-6 gap-y-3 text-lg">
                  {data.variants.map((v) => (
                    <li key={v.label}>
                      <Link
                        href={`/search?q=${encodeURIComponent(v.q)}${v.category ? `&category=${v.category}` : ""}`}
                        className="font-medium underline decoration-cream/40 underline-offset-4 hover:text-steel"
                      >
                        {v.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="mt-4 text-lg text-cream/65">Спробуйте інше формулювання, наприклад «відеокарта 8 гб» або «материнка asus am5».</p>
            )}
            <p className="mt-10 text-cream/65">Або перегляньте категорії:</p>
            <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-2.5">
              {CATEGORIES.map((c) => (
                <li key={c.slug}>
                  <Link href={`/search?category=${c.slug}`} className="underline decoration-cream/30 underline-offset-4 hover:decoration-cream">{c.label}</Link>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="grid gap-12 lg:grid-cols-[240px_minmax(0,1fr)]">
            <aside aria-label="Фільтри" className="self-start rounded-2xl bg-navy/30 p-6 ring-1 ring-cream/10 lg:sticky lg:top-6">
              <Facets facets={data.facets} category={data.applied.category} />
            </aside>

            <section aria-live="polite">
              <div className="mb-8 flex flex-wrap items-center justify-between gap-3 border-b border-cream/15 pb-4">
                <p className="font-medium">
                  {data.total} {plural(data.total, "товар", "товари", "товарів")}
                </p>
                <SortSelect />
              </div>

              {data.items.length === 0 ? (
                <div className="max-w-xl">
                  <p className="text-2xl font-semibold tracking-tight">Нічого не знайшли{q ? ` за запитом «${q}»` : ""}</p>
                  <p className="mt-3 text-cream/65">Приберіть частину фільтрів або сформулюйте простіше, наприклад «відеокарта 8 гб». Або перегляньте категорії:</p>
                  <ul className="mt-5 flex flex-wrap gap-x-5 gap-y-2">
                    {CATEGORIES.slice(0, 6).map((c) => (
                      <li key={c.slug}>
                        <Link href={`/search?category=${c.slug}`} className="underline decoration-cream/40 underline-offset-4 hover:text-steel">{c.label}</Link>
                      </li>
                    ))}
                  </ul>
                  <Link href="/search" className="btn-red mt-8 inline-block rounded-xl px-6 py-3 font-medium">Скинути пошук</Link>
                </div>
              ) : (
                <ul className="grid grid-cols-2 gap-x-6 gap-y-12 md:grid-cols-3 xl:grid-cols-4">
                  {data.items.map((p) => (
                    <li key={p.id}>
                      <ProductCard p={p} />
                    </li>
                  ))}
                </ul>
              )}

              {data.total > PAGE_SIZE && (
                <nav aria-label="Сторінки" className="mt-14 flex items-center justify-between border-t border-cream/15 pt-5 text-sm">
                  {page > 1 ? <Link href={pageHref(page - 1)} className="border-b-2 border-red pb-0.5 font-medium">Назад</Link> : <span />}
                  <span className="text-cream/55">Сторінка {page} з {Math.ceil(data.total / PAGE_SIZE)}</span>
                  {page * PAGE_SIZE < data.total ? <Link href={pageHref(page + 1)} className="border-b-2 border-red pb-0.5 font-medium">Далі</Link> : <span />}
                </nav>
              )}
            </section>
          </div>
        )}
      </div>
    </main>
  );
}

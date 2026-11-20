import { Suspense } from "react";
import Link from "next/link";
import Banner from "@/components/Banner";
import CategoryArt from "@/components/CategoryArt";
import ProductCard from "@/components/ProductCard";
import SearchBox from "@/components/SearchBox";
import { search, type SearchResponse } from "@/lib/api";
import { CATEGORIES, categoryLabel } from "@/lib/categories";
import { SECTION_PHOTO } from "@/lib/photos";

const ROWS = ["gpu", "motherboards", "cpu", "ssd"];
const EXAMPLES = ["мамка під ам5 ддр5 асус до 10000", "плта", "відеокрта 8 гб", "хард 4 тб", "ртх 4060"];

const DEMO_ROWS: [string, string][] = [
  ["Категорія", "Материнські плати"],
  ["Бренд", "ASUS"],
  ["Сокет", "AM5"],
  ["Памʼять", "DDR5"],
  ["Ціна", "до 10 000 ₴"],
];
const FIXES: [string, string][] = [
  ["плта", "Материнські плати"],
  ["dsltjrfhn 8 u,", "Відеокарти, 8 ГБ"],
  ["материнкаасус", "Материнські плати, ASUS"],
];

async function row(slug: string): Promise<SearchResponse | null> {
  try {
    return await search(new URLSearchParams({ category: slug, sort: "popular", size: "5" }));
  } catch {
    return null; // API ще не запущено: рядок просто не показуємо
  }
}

export default async function Home() {
  const rows = await Promise.all(ROWS.map(row));

  return (
    <main>
      <Banner />

      <div className="relative z-10 mx-auto -mt-8 max-w-3xl px-5">
        <Suspense fallback={null}>
          <SearchBox variant="hero" />
        </Suspense>
        <p className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-cream/65">
          <span>Спробуйте:</span>
          {EXAMPLES.map((q) => (
            <Link key={q} href={`/search?q=${encodeURIComponent(q)}`} className="underline decoration-cream/40 underline-offset-4 transition-colors hover:text-cream hover:decoration-cream">
              {q}
            </Link>
          ))}
        </p>
      </div>

      <section className="mx-auto mt-20 max-w-7xl px-5">
        <h2 className="text-2xl font-semibold tracking-tight">Категорії</h2>
        <ul className="mt-8 grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:grid-cols-5">
          {CATEGORIES.map((c) => (
            <li key={c.slug}>
              <Link href={`/search?category=${c.slug}`} className="group block">
                <div className="grid h-24 place-items-center">
                  <CategoryArt category={c.slug} className="h-full text-steel/55 transition-colors group-hover:text-red" />
                </div>
                <span className="mt-3 block font-medium underline-offset-4">{c.label}</span>
                <span className="mt-0.5 block text-sm text-cream/50">{c.hint}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {ROWS.map((slug, i) => {
        const data = rows[i];
        if (!data || data.items.length === 0) return null;
        return (
          <section key={slug} className="mx-auto mt-24 max-w-7xl px-5">
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="text-2xl font-semibold tracking-tight">
                {categoryLabel(slug)}
                <sup className="ml-1.5 text-sm font-semibold text-red">{data.total}</sup>
              </h2>
              <Link href={`/search?category=${slug}`} className="text-sm underline decoration-cream/40 underline-offset-4 hover:text-steel">
                Дивитись усі
              </Link>
            </div>
            <ul className="mt-8 grid grid-cols-2 gap-x-6 gap-y-12 md:grid-cols-3 lg:grid-cols-5">
              {data.items.map((p) => (
                <li key={p.id}>
                  <ProductCard p={p} showDescription={false} />
                </li>
              ))}
            </ul>
          </section>
        );
      })}

      <section className="relative isolate mt-28 overflow-hidden bg-cream text-navy">
        {/* фото під кремовою плівкою: ліворуч щільніше (текст), праворуч проглядає більше */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={SECTION_PHOTO} alt="" loading="lazy" className="absolute inset-0 -z-20 size-full object-cover" />
        <div aria-hidden className="absolute inset-0 -z-10 bg-[linear-gradient(90deg,rgba(253,240,213,0.97)_0%,rgba(253,240,213,0.9)_42%,rgba(253,240,213,0.66)_100%)]" />
        <div className="mx-auto grid max-w-7xl gap-14 px-5 py-20 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="text-4xl font-semibold leading-[1.05] tracking-[-0.03em] sm:text-5xl">Пишіть, як думаєте. Ми зрозуміємо.</h2>
            <p className="mt-6 max-w-lg text-lg leading-relaxed text-navy/70">
              Материнка, мамка чи motherboard для нас одне й те саме. Діалекти, одруківки, злитне написання та неправильну розкладку теж розуміємо.
            </p>
          </div>
          <div className="border-l-2 border-red pl-8">
            <p className="text-sm font-medium text-red">Так ми розуміємо запит</p>
            <p className="mt-3 text-2xl font-medium tracking-tight">«мамка під ам5 ддр5 асус до 10000»</p>
            <dl className="mt-5 divide-y divide-navy/15">
              {DEMO_ROWS.map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between py-2.5">
                  <dt className="text-navy/70">{k}</dt>
                  <dd className="font-medium tabular-nums">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-8 text-sm font-medium text-red">А ще помилки, злите написання й не та розкладка</p>
            <dl className="mt-2 divide-y divide-navy/15">
              {FIXES.map(([q, r]) => (
                <div key={q} className="flex items-baseline justify-between gap-6 py-2.5">
                  <dt className="text-navy/70">«{q}»</dt>
                  <dd className="text-right font-medium">{r}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>
    </main>
  );
}

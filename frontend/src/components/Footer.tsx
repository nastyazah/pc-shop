import Link from "next/link";
import { CATEGORIES } from "@/lib/categories";
import { PHOTO_CREDITS } from "@/lib/photos";

export default function Footer() {
  return (
    <footer className="bg-ink text-cream/70">
      <div className="mx-auto grid max-w-7xl gap-10 border-t border-cream/10 px-5 py-14 md:grid-cols-[1.2fr_2fr]">
        <div>
          <p className="flex items-center gap-2.5 text-xl font-semibold text-cream">
            <span aria-hidden className="grid size-7 place-items-center rounded-full bg-red">
              <span className="size-2.5 rounded-full bg-ink" />
            </span>
            Ядро
          </p>
          <p className="mt-4 max-w-xs text-sm leading-relaxed">
            Комплектуючі для ПК та пошук, який розуміє, що ви маєте на увазі.
          </p>
        </div>
        <ul className="grid grid-cols-2 gap-x-6 gap-y-2.5 text-sm sm:grid-cols-3">
          {CATEGORIES.map((c) => (
            <li key={c.slug}>
              <Link href={`/search?category=${c.slug}`} className="hover:text-cream hover:underline hover:decoration-cream hover:underline-offset-4">
                {c.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <p className="mx-auto max-w-7xl border-t border-cream/10 px-5 py-5 text-xs text-cream/45">
        Фото:{" "}
        {PHOTO_CREDITS.map((c, i) => (
          <span key={c.name}>
            {i > 0 && ", "}
            <a href={c.href} className="underline underline-offset-2 hover:text-cream">{c.name}</a>
          </span>
        ))}
        , Unsplash
      </p>
    </footer>
  );
}

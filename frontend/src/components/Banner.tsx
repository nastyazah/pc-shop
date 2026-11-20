import Link from "next/link";
import { BANNER_PHOTO } from "@/lib/photos";

// Банер головної. Текст і ціна задані вручну: це рекламний слот, а не дані з каталогу.
export default function Banner() {
  return (
    <section className="relative isolate overflow-hidden bg-ink text-cream">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={BANNER_PHOTO} alt="" fetchPriority="high" className="absolute inset-0 -z-20 size-full object-cover object-[65%_50%]" />
      <div aria-hidden className="absolute inset-0 -z-10 bg-[linear-gradient(90deg,rgba(5,14,22,0.95)_0%,rgba(5,14,22,0.8)_40%,rgba(5,14,22,0.2)_100%)]" />
      <div aria-hidden className="absolute inset-0 -z-10 bg-[radial-gradient(55%_90%_at_90%_100%,rgba(193,18,31,0.5),transparent_70%)]" />
      <div className="mx-auto max-w-7xl px-5 pb-32 pt-40">
        <p className="text-lg text-steel">Відеокарта</p>
        <h1 className="mt-2 max-w-2xl text-5xl font-semibold leading-[1.02] tracking-[-0.035em] sm:text-6xl lg:text-7xl">
          MSI GeForce RTX 4060 VENTUS 2X
        </h1>
        <p className="mt-5 max-w-md text-lg text-cream/70">Для ігор у Full HD та QHD з підтримкою DLSS 3.</p>
        <div className="mt-9 flex flex-wrap items-center gap-6">
          <Link href="/search?q=rtx%204060" className="btn-red rounded-xl px-7 py-3.5 font-medium">Дивитись</Link>
          <p className="text-3xl font-semibold tabular-nums">15 499 ₴</p>
        </div>
      </div>
    </section>
  );
}

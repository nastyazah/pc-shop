"use client";

import { useEffect, useRef, useState } from "react";
import CategoryArt from "./CategoryArt";

type Props = { src?: string | null; alt: string; category: string };

// Фото накладається на кремовий фон через multiply (білий фон знімка зникає).
// Без фото - ілюстрація категорії.
export default function ProductImage({ src, alt, category }: Props) {
  const [failed, setFailed] = useState(false);
  const ref = useRef<HTMLImageElement>(null);

  useEffect(() => {
    // якщо файл не завантажився ще до гідрації, onError вже не спрацює
    if (ref.current?.complete && ref.current.naturalWidth === 0) setFailed(true);
  }, []);

  if (!src || failed) {
    return (
      <div className="grid aspect-[4/3] place-items-center bg-[radial-gradient(closest-side,rgba(0,48,73,0.1),transparent)]">
        <CategoryArt category={category} />
      </div>
    );
  }
  return (
    <div className="grid aspect-[4/3] place-items-center">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img ref={ref} src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} className="size-full object-contain mix-blend-multiply" />
    </div>
  );
}

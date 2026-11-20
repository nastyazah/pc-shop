export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Chip = { kind: string; label: string };
export type Product = {
  id: number; sku: string; name: string; description?: string; brand?: string | null; category: string; category_name?: string;
  price: number; old_price?: number | null; in_stock: boolean; image_url?: string | null;
  specs: Record<string, string | number>;
};
export type Bucket = { value: string | number; label?: string | null; count: number };
export type Variant = { label: string; q: string; category?: string };
export type SearchResponse = {
  state?: "ok" | "not_sold" | "unknown";
  not_sold?: { product: string; certain: boolean } | null;
  variants?: Variant[];
  related?: { title: string; items: Product[] } | null;
  total: number; took_ms: number; hybrid: boolean; items: Product[];
  understood: { chips: Chip[]; corrected_from?: string | null; typos?: { from: string; to: string }[]; splits?: { from: string; to: string }[]; llm?: boolean; suggestion?: { category: string; label: string } | null };
  applied: { category?: string | null; brands: string[] };
  facets: {
    categories: Bucket[]; brands: Bucket[];
    price: { min: number | null; max: number | null };
    specs: Record<string, { label: string; buckets: Bucket[] }>;
  };
};
export type SuggestResponse = { chips: Chip[]; products: Pick<Product, "id" | "name" | "brand" | "price" | "category">[] };

export async function search(qs: URLSearchParams): Promise<SearchResponse> {
  const res = await fetch(`${API}/api/search?${qs.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`search ${res.status}`);
  return res.json();
}

export async function suggest(q: string, signal?: AbortSignal): Promise<SuggestResponse> {
  const res = await fetch(`${API}/api/suggest?q=${encodeURIComponent(q)}`, { signal });
  if (!res.ok) throw new Error(`suggest ${res.status}`);
  return res.json();
}

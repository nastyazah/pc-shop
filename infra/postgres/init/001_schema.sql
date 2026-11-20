CREATE TABLE categories (
  id        serial PRIMARY KEY,
  parent_id int REFERENCES categories(id) ON DELETE RESTRICT,
  slug      text NOT NULL UNIQUE,
  name      text NOT NULL,
  position  int  NOT NULL DEFAULT 0
);

CREATE TABLE brands (
  id   serial PRIMARY KEY,
  slug text NOT NULL UNIQUE,
  name text NOT NULL
);

CREATE TABLE products (
  id          bigserial PRIMARY KEY,
  sku         text NOT NULL UNIQUE,
  name        text NOT NULL,
  brand_id    int REFERENCES brands(id),
  category_id int NOT NULL REFERENCES categories(id),
  description text NOT NULL DEFAULT '',
  price       numeric(12,2) NOT NULL CHECK (price >= 0),
  old_price   numeric(12,2),
  in_stock    boolean NOT NULL DEFAULT true,
  is_active   boolean NOT NULL DEFAULT true,
  specs       jsonb   NOT NULL DEFAULT '{}',
  image_url   text,
  popularity  int     NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX products_category_idx ON products (category_id);
CREATE INDEX products_specs_gin ON products USING gin (specs);

-- шлях категорії від кореня: ['components','motherboards']
CREATE VIEW category_paths AS
WITH RECURSIVE t AS (
  SELECT id, ARRAY[slug] AS path FROM categories WHERE parent_id IS NULL
  UNION ALL
  SELECT c.id, t.path || c.slug FROM categories c JOIN t ON c.parent_id = t.id
)
SELECT id, path FROM t;

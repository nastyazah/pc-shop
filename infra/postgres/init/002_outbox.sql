-- Transactional Outbox: подія пишеться в ТІЙ САМІЙ транзакції, що й зміна товару.
-- Воркер читає чергу, будує документ із поточного стану БД і індексує його в OpenSearch.
CREATE TABLE outbox_events (
  id             bigserial PRIMARY KEY,
  aggregate_type text   NOT NULL,
  aggregate_id   bigint NOT NULL,
  event_type     text   NOT NULL CHECK (event_type IN ('upsert', 'delete')),
  created_at     timestamptz NOT NULL DEFAULT now(),
  processed_at   timestamptz,
  attempts       int  NOT NULL DEFAULT 0,
  last_error     text
);
CREATE INDEX outbox_pending_idx ON outbox_events (id) WHERE processed_at IS NULL;

CREATE FUNCTION touch_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END $$;
CREATE TRIGGER products_touch BEFORE UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE FUNCTION products_to_outbox() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type) VALUES ('product', OLD.id, 'delete');
    RETURN OLD;
  END IF;
  INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type) VALUES ('product', NEW.id, 'upsert');
  RETURN NEW;
END $$;
CREATE TRIGGER products_outbox AFTER INSERT OR UPDATE OR DELETE ON products
  FOR EACH ROW EXECUTE FUNCTION products_to_outbox();

-- перейменували бренд/категорію -> переіндексувати їхні товари
CREATE FUNCTION brand_category_to_outbox() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME = 'brands' THEN
    INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type)
      SELECT 'product', id, 'upsert' FROM products WHERE brand_id = NEW.id;
  ELSE
    INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type)
      SELECT 'product', id, 'upsert' FROM products WHERE category_id = NEW.id;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER brands_outbox AFTER UPDATE OF name ON brands
  FOR EACH ROW EXECUTE FUNCTION brand_category_to_outbox();
CREATE TRIGGER categories_outbox AFTER UPDATE OF name, slug ON categories
  FOR EACH ROW EXECUTE FUNCTION brand_category_to_outbox();

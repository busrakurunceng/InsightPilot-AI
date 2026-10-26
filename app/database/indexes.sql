-- InsightPilot AI
-- Module 1: Database Indexes

-- Experiment 1: Customer order lookup
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
ON public.orders (customer_id);

-- Experiment 2: Order purchase date filtering

CREATE INDEX IF NOT EXISTS idx_orders_purchase_timestamp
ON public.orders (order_purchase_timestamp);

-- Experiment 3: Product-based order item lookup

CREATE INDEX IF NOT EXISTS idx_order_items_product_id
ON public.order_items (product_id);

-- Experiment 4: Seller-based order item lookup

CREATE INDEX IF NOT EXISTS idx_order_items_seller_id
ON public.order_items (seller_id);

-- Experiment 5: Order review lookup

CREATE INDEX IF NOT EXISTS idx_order_reviews_order_id
ON public.order_reviews (order_id);
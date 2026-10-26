-- InsightPilot AI
-- Module 1: Database Indexes

-- Experiment 1: Customer order lookup
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
ON orders (customer_id);
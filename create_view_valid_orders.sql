-- 创建视图：筛选有效订单
-- 筛选条件：
-- 1. source_order_id 为空（表示这是原始订单，不是退款订单）
-- 2. pay_time 不为空（表示已支付）

CREATE OR REPLACE VIEW valid_orders AS
SELECT 
    order_id,
    order_status,
    sku_id,
    sku_name,
    pay_amount,
    count,
    pay_time,
    create_time,
    update_time,
    source_order_id,
    phone,
    raw_data,
    sync_time
FROM orders
WHERE source_order_id IS NULL
  AND pay_time IS NOT NULL;

-- 添加视图注释
COMMENT ON VIEW valid_orders IS '有效订单视图：source_order_id为空且pay_time不为空的订单（原始已支付订单）';

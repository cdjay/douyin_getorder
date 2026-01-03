-- 创建视图：筛选有效订单
-- 筛选条件：
-- 1. source_order_id 为空或空字符串（表示这是原始订单，不是退款订单）
-- 2. pay_time 不为空（表示已支付）

CREATE OR REPLACE VIEW valid_orders AS
SELECT 
    order_id,
    count,
    pay_time,
    order_status,
    sku_id,
    sku_name
FROM orders
WHERE (source_order_id IS NULL OR source_order_id = '')
  AND pay_time IS NOT NULL;

-- 添加视图注释
COMMENT ON VIEW valid_orders IS '有效订单视图：source_order_id为空或空字符串且pay_time不为空的订单（原始已支付订单）';

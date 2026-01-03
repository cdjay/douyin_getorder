-- 创建视图：有效订单（关联orders、orders_excel、travel_bookings）
-- 筛选条件：
-- 1. source_order_id 为空或空字符串（表示这是原始订单，不是退款订单）
-- 2. pay_time 不为空（表示已支付）
--
-- 聚合逻辑：
-- 1. 关联orders_excel表：数值字段求和，字符串字段去重合并（逗号分隔）
-- 2. 关联travel_bookings表：获取出行日期
-- 3. 按order_id分组：每个订单一条记录

CREATE OR REPLACE VIEW valid_orders AS
SELECT 
    -- ========== orders表字段 ==========
    o.order_id,
    o.count,
    o.pay_time,
    o.order_status,
    o.sku_id,
    o.sku_name,
    
    -- ========== orders_excel数值字段（求和）==========
    SUM(oe.actual_receipt) as actual_receipt,
    SUM(oe.sale_amount) as sale_amount,
    SUM(oe.merchant_subsidy) as merchant_subsidy,
    SUM(oe.product_payment) as product_payment,
    SUM(oe.platform_subsidy) as platform_subsidy,
    SUM(oe.software_fee) as software_fee,
    SUM(oe.talent_commission) as talent_commission,
    SUM(oe.increment_commission) as increment_commission,
    SUM(oe.preset_price) as preset_price,
    SUM(oe.booking_surcharge) as booking_surcharge,
    
    -- ========== orders_excel字符串字段（去重合并，逗号分隔）==========
    STRING_AGG(DISTINCT oe.platform_discount_detail, ',') as platform_discount_detail,
    STRING_AGG(DISTINCT oe.software_fee_rate, ',') as software_fee_rate,
    STRING_AGG(DISTINCT oe.sales_role, ',') as sales_role,
    STRING_AGG(DISTINCT oe.deal_channel, ',') as deal_channel,
    STRING_AGG(DISTINCT oe.owner_nickname, ',') as owner_nickname,
    STRING_AGG(DISTINCT oe.owner_uid, ',') as owner_uid,
    
    -- ========== travel_bookings表字段 ==========
    tb.travel_date

FROM orders o

LEFT JOIN orders_excel oe ON o.order_id = oe.order_id
LEFT JOIN travel_bookings tb ON o.order_id = tb.order_number

WHERE (o.source_order_id IS NULL OR o.source_order_id = '')
  AND o.pay_time IS NOT NULL

GROUP BY o.order_id, o.count, o.pay_time, o.order_status, o.sku_id, o.sku_name, tb.travel_date

ORDER BY o.pay_time DESC;

-- 添加视图注释
COMMENT ON VIEW valid_orders IS '有效订单视图：关联orders、orders_excel、travel_bookings三个表，数值字段求和，字符串字段去重合并（逗号分隔）';

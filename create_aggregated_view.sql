-- 创建视图：订单聚合视图
-- 关联orders、orders_excel、travel_bookings三个表
-- 以orders.order_id为准

CREATE OR REPLACE VIEW order_details_aggregated AS
SELECT 
    -- ========== orders表字段 ==========
    o.order_id,
    o.count,
    o.pay_time,
    o.order_status,
    o.sku_id,
    o.sku_name,
    
    -- ========== orders_excel表字段 ==========
    oe.actual_receipt,
    oe.sale_amount,
    oe.merchant_subsidy,
    oe.product_payment,
    oe.platform_subsidy,
    oe.platform_discount_detail,
    oe.software_fee,
    oe.talent_commission,
    oe.increment_commission,
    oe.preset_price,
    oe.booking_surcharge,
    oe.software_fee_rate,
    oe.sales_role,
    oe.deal_channel,
    oe.owner_nickname,
    oe.owner_uid,
    
    -- ========== travel_bookings表字段 ==========
    tb.travel_date

FROM orders o

-- LEFT JOIN orders_excel（保留所有orders记录）
LEFT JOIN orders_excel oe ON o.order_id = oe.order_id

-- LEFT JOIN travel_bookings（使用order_number关联）
LEFT JOIN travel_bookings tb ON o.order_id = tb.order_number

-- 筛选有效订单：source_order_id为空或空字符串 且 pay_time不为空
WHERE (o.source_order_id IS NULL OR o.source_order_id = '')
  AND o.pay_time IS NOT NULL

-- 按pay_time降序排序（最新在第一条）
ORDER BY o.pay_time DESC;

-- 添加视图注释
COMMENT ON VIEW order_details_aggregated IS '订单聚合视图：关联orders、orders_excel、travel_bookings三个表，以orders.order_id为准';

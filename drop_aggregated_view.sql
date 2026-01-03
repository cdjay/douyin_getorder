-- 删除order_details_aggregated视图

DROP VIEW IF EXISTS order_details_aggregated;

SELECT 'order_details_aggregated视图已删除' as status;

-- 验证视图列表
SELECT 
    schemaname,
    viewname
FROM pg_views
WHERE schemaname = 'public'
  AND viewname LIKE '%order%'
ORDER BY viewname;

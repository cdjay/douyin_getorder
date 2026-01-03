-- orders_excel表迁移脚本
-- 目的：添加唯一约束(order_id, sub_order_id)并清空数据

-- ==========================================
-- 第一步：清空orders_excel表
-- ==========================================
TRUNCATE TABLE orders_excel CASCADE;

SELECT 'orders_excel表已清空' as status;

-- ==========================================
-- 第二步：检查并删除旧约束（如果存在）
-- ==========================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'orders_excel_unique_order_sub'
    ) THEN
        ALTER TABLE orders_excel 
        DROP CONSTRAINT IF EXISTS orders_excel_unique_order_sub;
        RAISE NOTICE '旧唯一约束已删除';
    END IF;
END $$;

-- ==========================================
-- 第三步：添加唯一约束
-- ==========================================
ALTER TABLE orders_excel 
ADD CONSTRAINT orders_excel_unique_order_sub 
UNIQUE (order_id, sub_order_id);

SELECT '唯一约束已添加：orders_excel_unique_order_sub' as status;

-- ==========================================
-- 第四步：验证约束
-- ==========================================
SELECT 
    conname as constraint_name,
    contype as constraint_type
FROM pg_constraint
WHERE conrelid = 'orders_excel'::regclass
  AND conname = 'orders_excel_unique_order_sub';

-- ==========================================
-- 第五步：验证表结构
-- ==========================================
SELECT COUNT(*) as current_count FROM orders_excel;

-- ==========================================
-- 完成
-- ==========================================
SELECT 'orders_excel表迁移完成！可以重新导入Excel数据了。' as status;

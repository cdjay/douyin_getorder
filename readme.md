# 抖音来客订单同步系统 (Douyin Life Order Sync)

自动从抖音开放平台拉取本地生活订单数据并存储到PostgreSQL数据库，支持Excel文件导入。

## ✨ 功能特性

### API订单同步
- 🔁 **自动同步** - 定期拉取订单数据，无需人工干预
- 📱 **手机号解密** - 自动解密订单中的加密手机号
- 📄 **智能分页** - 按天切分，支持断点续传，避免数据丢失
- ⏰ **灵活配置** - 支持天数、日期、时间戳三种时间范围配置
- 🐳 **Docker支持** - 完整的容器化部署方案
- 💾 **数据安全** - Upsert机制避免重复，JSONB存储原始数据

### Excel导入
- 📊 **售卖明细导入** - 支持售卖明细Excel文件自动导入
- 🎫 **旅行社预约明细导入** - 支持多sheet旅行社预约明细导入
- 🔄 **自动监控** - 实时监控data文件夹，自动导入新文件
- 🗑️ **自动清理** - 导入成功后自动删除Excel文件
- 📈 **进度显示** - 详细的导入进度和调试信息
- ⚙️ **智能过滤** - 自动跳过"说明"类sheet和空行

### 监控管理
- 💓 **心跳监控** - 实时监控程序运行状态
- 🎮 **远程控制** - 支持通过数据库发送STOP/START指令
- 📊 **状态记录** - 记录任务状态、心跳时间、错误信息

## 📋 技术栈

- **Python 3.7+** - 核心语言
- **PostgreSQL** - 数据存储
- **SQLAlchemy** - ORM框架
- **Requests** - HTTP请求
- **Cryptography** - AES加密解密

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/cdjay/douyin_getorder.git
cd douyin_getorder
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入真实配置
# Windows: notepad .env
# Linux/Mac: nano .env
```

**必要配置项：**

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| `DB_URL` | 数据库连接字符串 | 自行配置PostgreSQL |
| `APPID` | 抖音应用ID | [抖音开放平台](https://open.douyin.com/) |
| `AppSecret` | 抖音应用密钥 | [抖音开放平台](https://open.douyin.com/) |
| `ACCOUNT_ID` | 抖音账号ID | [抖音开放平台](https://open.douyin.com/) / [life.douyin.com](https://life.douyin.com/) |

### 5. 运行程序

```bash
python main.py
```

程序会自动开始拉取订单数据，默认每小时同步一次。

## 📊 Excel导入

### 功能说明

支持两种Excel文件类型的自动导入：

1. **售卖明细** - 文件名格式：`售卖明细_*.xlsx`
2. **旅行社预约明细** - 文件名格式：`旅行社预约明细_*.xlsx`

### 使用方法

#### 1. 运行Excel导入程序

```bash
# 终端1：运行Excel导入监控
python excel_import.py
```

程序会自动监控`data`文件夹，每10秒扫描一次。

#### 2. 放入Excel文件

将Excel文件放入`data`文件夹：

```bash
data/
├── 售卖明细_2024-12-27_2025-12-07.xlsx
└── 旅行社预约明细_2025-12-07.xlsx
```

#### 3. 自动导入

程序会自动：
- 识别Excel文件类型
- 解析数据内容
- 保存到数据库
- 导入成功后删除文件

### Excel文件格式

#### 售卖明细Excel

**文件名：** `售卖明细_YYYY-MM-DD_YYYY-MM-DD.xlsx`

**必选字段：**
- 所属订单ID
- 子订单ID
- 券码状态
- 核销时间
- 订单实收
- 售卖金额
- 商家货款出资补贴
- 商品实付
- 平台补贴
- 平台补贴优惠明细
- 软件服务费
- 达人佣金
- 增量宝佣金
- 预售价(只针对酒旅商家)
- 预约加价(只针对酒旅商家)
- 软件服务费率
- 带货角色
- 成交渠道
- 订单归属人昵称
- 订单归属人uid

#### 旅行社预约明细Excel

**文件名：** `旅行社预约明细_YYYY-MM-DD.xlsx`

**工作表：**
- 未预约-1
- 待接单-1
- 已预约-1
- 已完成-1
- 已拒单-1

**必选字段：**
- 订单编号
- 商品名称
- 商品品类
- 商品类型
- 购买份数

### 导入日志示例

```
2026-01-03 00:05:46 - 启动Excel导入程序
2026-01-03 00:05:46 - 开始新一轮扫描
2026-01-03 00:05:46 - 开始导入售卖明细: 售卖明细_2024-12-27_2025-12-07.xlsx
  打开工作表: 售卖明细
  总行数: 11668
  表头: ['所属订单ID', '子单ID', '订单标签', '支付时间', '商品名称']...
  已读取 1000 行...
  ...
  读取完成: 11667 行有效数据 (跳过 0 行空数据)
解析完成: 11667 条记录
✅ 售卖明细导入完成: 11667 条记录
✅ 已删除已导入文件: 售卖明细_2024-12-27_2025-12-07.xlsx

开始导入旅行社预约明细: 旅行社预约明细_2025-12-07.xlsx
  发现 6 个工作表
  检查工作表: 未预约-1
  读取完成: 113 行有效数据
  ...
✅ 旅行社预约明细导入完成: 9903 条记录
✅ 已删除已导入文件: 旅行社预约明细_2025-12-07.xlsx

✅ 导入完成: 21570 条记录
```

### 数据库表结构

#### orders_excel（售卖明细）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `order_id` | VARCHAR | 所属订单ID |
| `sub_order_id` | VARCHAR | 子订单ID |
| `coupon_status` | VARCHAR | 券码状态 |
| `verification_time` | TIMESTAMP | 核销时间 |
| `actual_receipt` | FLOAT | 订单实收 |
| `sale_amount` | FLOAT | 售卖金额 |
| `merchant_subsidy` | FLOAT | 商家货款出资补贴 |
| `product_payment` | FLOAT | 商品实付 |
| `platform_subsidy` | FLOAT | 平台补贴 |
| `platform_discount_detail` | VARCHAR | 平台补贴优惠明细 |
| `software_fee` | FLOAT | 软件服务费 |
| `talent_commission` | FLOAT | 达人佣金 |
| `increment_commission` | FLOAT | 增量宝佣金 |
| `preset_price` | FLOAT | 预售价 |
| `booking_surcharge` | FLOAT | 预约加价 |
| `software_fee_rate` | VARCHAR | 软件服务费率 |
| `sales_role` | VARCHAR | 带货角色 |
| `deal_channel` | VARCHAR | 成交渠道 |
| `owner_nickname` | VARCHAR | 订单归属人昵称 |
| `owner_uid` | VARCHAR | 订单归属人uid |
| `raw_excel` | JSONB | 原始Excel数据 |
| `file_name` | VARCHAR | 文件名 |
| `import_time` | TIMESTAMP | 导入时间 |

#### travel_bookings（旅行社预约明细）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `order_number` | VARCHAR | 订单编号 |
| `travel_date` | DATE | 出行日期 |
| `booking_status` | VARCHAR | 预约状态 |
| `raw_excel` | JSONB | 原始Excel数据 |
| `file_name` | VARCHAR | 文件名 |
| `sheet_name` | VARCHAR | 工作表名 |
| `import_time` | TIMESTAMP | 导入时间 |

### 查询示例

#### 查询售卖明细

```sql
SELECT 
    file_name,
    COUNT(*) as count,
    SUM(actual_receipt) as total_amount
FROM orders_excel
GROUP BY file_name
ORDER BY file_name DESC;
```

#### 查询旅行社预约明细

```sql
SELECT 
    sheet_name,
    booking_status,
    COUNT(*) as count
FROM travel_bookings
GROUP BY sheet_name, booking_status
ORDER BY sheet_name;
```

#### 按预约状态统计

```sql
SELECT 
    booking_status,
    COUNT(*) as count
FROM travel_bookings
GROUP BY booking_status;
```

## ⚙️ 配置说明

### 时间范围配置

**方式1：指定日期范围（推荐）**

```env
START_DATE=2024-01-01
END_DATE=2024-12-31
```

或指定具体时间：

```env
START_DATE=2024-01-01 10:00:00
END_DATE=2024-01-31 18:00:00
```

**方式2：指定时间戳**

```env
START_TIME=1704067200
END_TIME=1735660799
```

**方式3：指定天数（默认）**

```env
SYNC_DAYS=7
```
表示同步最近7天的订单数据。

### 订单状态筛选

```env
ORDER_STATUS=2
```

常用状态值：
- 不配置：拉取所有状态
- `2`：已完成
- `3`：退款中
- `4`：已退款

### 其他配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SYNC_INTERVAL` | 3600 | 同步间隔（秒） |
| `PAGE_SIZE` | 50 | 每页订单数量（1-100） |
| `GET_SECRET_NUMBER` | false | 是否查询配送信息 |
| `USE_CREATE_TIME` | true | 是否使用创单时间而非修改时间 |

## 📊 数据库字段说明

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `order_id` | VARCHAR | 订单ID（主键） | 1077940305329948933 |
| `order_status` | VARCHAR | 订单状态 | 1（已完成） |
| `sku_id` | VARCHAR | 商品SKU ID | 1760543044430907 |
| `sku_name` | VARCHAR | 商品名称 | 三星堆+熊猫基地精品团 |
| `pay_amount` | FLOAT | 支付金额 | 429.00 |
| `count` | INTEGER | 订单数量 | 1 |
| `pay_time` | TIMESTAMP | 支付时间 | 2024-01-25 14:31:54 |
| `create_time` | TIMESTAMP | 订单创建时间 | 2024-01-25 14:31:52 |
| `update_time` | TIMESTAMP | 订单更新时间 | 2024-02-25 10:30:33 |
| `source_order_id` | VARCHAR | 来源订单ID | 1078263594007388830 |
| `phone` | VARCHAR | 手机号（已解密） | 138****0000 |
| `raw_data` | JSONB | 完整原始数据 | API响应的完整JSON |

## 💻 查询示例

### 查询最新订单

```sql
SELECT 
    order_id, 
    order_status,
    sku_name, 
    pay_amount, 
    pay_time, 
    phone 
FROM orders 
ORDER BY pay_time DESC 
LIMIT 10;
```

### 按手机号查询

```sql
SELECT * FROM orders WHERE phone = '138****0000';
```

### 按日期统计

```sql
SELECT 
    DATE(pay_time) as date,
    COUNT(*) as order_count,
    SUM(pay_amount) as total_amount
FROM orders
GROUP BY DATE(pay_time)
ORDER BY date DESC;
```

### 按商品统计

```sql
SELECT 
    sku_id,
    sku_name,
    COUNT(*) as order_count,
    SUM(pay_amount) as total_amount
FROM orders
GROUP BY sku_id, sku_name
ORDER BY order_count DESC;
```

## 🐳 Docker部署

### 1. 构建镜像

```bash
docker build -t douyin-order-sync .
```

### 2. 运行容器

```bash
docker run -d \
  --name douyin-sync \
  --restart unless-stopped \
  -e DB_URL=postgresql://user:pass@host:5432/dbname \
  -e APPID=your_app_id \
  -e AppSecret=your_secret \
  -e ACCOUNT_ID=your_account_id \
  douyin-order-sync
```

### 3. 查看日志

```bash
docker logs -f douyin-sync
```

### 4. 停止容器

```bash
docker stop douyin-sync
```

## ❓ 常见问题

### 1. 如何获取抖音应用ID和密钥？

访问 [抖音开放平台](https://open.douyin.com/)，创建应用后即可获取。

### 2. 手机号显示乱码或解密失败？

请检查`.env`文件中的`AppSecret`是否正确。密钥用于解密手机号，错误会导致解密失败。

### 3. 数据库连接失败？

请检查：
- PostgreSQL服务是否运行
- 数据库连接字符串格式是否正确
- 数据库用户权限是否足够

### 4. 订单数据不完整？

程序采用智能分页，支持断点续传。如果发现数据不完整：
- 检查日志是否有错误信息
- 确认时间范围配置是否正确
- 考虑分批次拉取历史数据

### 5. 如何停止程序？

```bash
# 方法1：Ctrl+C
# 方法2：Docker环境
docker stop douyin-sync
```

## 📁 项目结构

```
douyin_getorder/
├── main.py              # API订单同步主程序
├── excel_import.py       # Excel导入主程序
├── excel_importer.py    # Excel导入器
├── config.py            # 配置管理
├── database.py          # 数据库操作
├── douyin_api.py       # 抖音API客户端
├── task_manager.py     # 任务监控
├── requirements.txt    # Python依赖
├── .env.example       # 环境变量模板
├── README.md          # 项目说明
├── CHANGELOG.md       # 版本更新记录
└── data/              # Excel文件存放目录
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📮 联系方式

如有问题或建议，欢迎提交Issue。

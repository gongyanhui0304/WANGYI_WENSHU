SELECT 
     CASE WHEN 部门 = '软件开发部' THEN '可诺特软件' ELSE 部门 END AS 部门  , 
     年份月份, 各部门总数, 总数, 天数, 登录次数, 账户占比, 访问率
FROM express_dw.dbo.DWD_BI_DEPMENT_REPORT 
where 年份月份 = ${年月} -- '202510'
      AND 部门 <> '信息中心'
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

SELECT 
     CASE WHEN 部门 = '软件开发部' THEN '可诺特软件' ELSE 部门 END AS 部门  , 
     年份月份, 各部门总数, 总数, 天数, 登录次数, 账户占比, 访问率
FROM DWD_BI_DEPMENT_REPORT 
where 年份月份 = :dynamic_param -- '202510'
      AND 部门 <> '信息中心'
-- ===== 通用参考SQL结束 =====

 SELECT
       ZMONTH , 
       v.模块 , 
       v.占比 / 100 AS 占比 
FROM   express_ods.dbo.ODS_SAP_ZTBASIS02_02  
CROSS APPLY (
    VALUES
     ( '成本核算', [A1PERC]),   
     ( '财务管理', [A2PERC]),
     ( '报价平台', [A3PERC]),
     ( '产供销', [A4PERC]),
     ( '其他(进销存)', [A5PERC]) 
) AS v(模块, 占比 ) 
WHERE  ZMONTH = ${年月} -- '202510'
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

 SELECT
       ZMONTH , 
       v.模块 , 
       v.占比 / 100 AS 占比 
FROM   ODS_SAP_ZTBASIS02_02  
CROSS APPLY (
    VALUES
     ( '成本核算', [A1PERC]),   
     ( '财务管理', [A2PERC]),
     ( '报价平台', [A3PERC]),
     ( '产供销', [A4PERC]),
     ( '其他(进销存)', [A5PERC]) 
) AS v(模块, 占比 ) 
WHERE  ZMONTH = :dynamic_param -- '202510'
-- ===== 通用参考SQL结束 =====

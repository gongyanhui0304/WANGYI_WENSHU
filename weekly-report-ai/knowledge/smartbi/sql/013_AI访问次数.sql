SELECT 
     FORMAT(CONVERT(DATE,created_at,120),'yyyy-MM-dd') AS FDATE 
     , LEFT(created_at , 4) + '年' + REPLACE(DATEPART(WEEK, FORMAT(CONVERT(DATE,created_at,120),'yyyy-MM-dd') ) , '-', '') + '周' AS "年周"  
       , COUNT(id) AS 访问次数  
  FROM ODS_AI_messages_export 
  WHERE -- FORMAT(CONVERT(DATE,created_at,120),'yyyyMM') <= ${年月} 
        -- AND 
        FORMAT(CONVERT(DATE,created_at,120),'yyyy') = LEFT(${年月} , 4)           
  GROUP BY FORMAT(CONVERT(DATE,created_at,120),'yyyy-MM-dd') 
           , LEFT(created_at , 4) + '年' + REPLACE(DATEPART(WEEK, FORMAT(CONVERT(DATE,created_at,120),'yyyy-MM-dd') ) , '-', '') + '周'
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

SELECT 
     FORMAT(CONVERT(DATE,created_at,120),'yyyy-MM-dd') AS FDATE 
     , LEFT(created_at , 4) + '年' + REPLACE(DATEPART(WEEK, FORMAT(CONVERT(DATE,created_at,120),'yyyy-MM-dd') ) , '-', '') + '周' AS "年周"  
       , COUNT(id) AS 访问次数  
  FROM ODS_AI_messages_export 
  WHERE -- FORMAT(CONVERT(DATE,created_at,120),'yyyyMM') <= :dynamic_param 
        -- AND 
        FORMAT(CONVERT(DATE,created_at,120),'yyyy') = LEFT(:dynamic_param , 4)           
  GROUP BY FORMAT(CONVERT(DATE,created_at,120),'yyyy-MM-dd') 
           , LEFT(created_at , 4) + '年' + REPLACE(DATEPART(WEEK, FORMAT(CONVERT(DATE,created_at,120),'yyyy-MM-dd') ) , '-', '') + '周'
-- ===== 通用参考SQL结束 =====

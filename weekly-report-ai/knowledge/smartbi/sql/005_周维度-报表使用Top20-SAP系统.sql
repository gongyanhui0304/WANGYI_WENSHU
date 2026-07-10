SELECT  
   A."报表编码", A."报表编码"+'-'+A."报表名称" AS "报表名称" , A."访问次数" , B."总次数"  , C.KOSTL
  , ROUND(CAST(A.访问次数 AS FLOAT) / CAST(B.总次数 AS FLOAT) , 4) AS 占比  
 FROM (  
 SELECT TOP 20 
       SLGTC AS "报表编码",
       TTEXT AS "报表名称", 
       COUNT(SLGUSER) AS "访问次数" 
FROM   express_ods.dbo.ODS_SAP_ZVS_TCODE_LOG
WHERE  {[LEFT(SLGDATTIM,4) + '年' + REPLACE(DATEPART(WEEK, CONVERT(varchar(8), LEFT(SLGDATTIM, 8), 112) ) , '-', '') + '周'  = ${年周}]}  --   '2026年15周'  
       AND SLGTC <> 'SEU_INT' 
       AND SLGTC LIKE 'Z%' 
       AND LEFT(SLGTC,6) <> 'ZTBASI'  
GROUP BY  SLGTC, TTEXT
ORDER BY 访问次数 DESC  ) AS A  
LEFT JOIN (
  SELECT 
  COUNT(SLGUSER) AS "总次数"   
 FROM express_ods.dbo.ODS_SAP_ZVS_TCODE_LOG  
 WHERE {[LEFT(SLGDATTIM,4) + '年' + REPLACE(DATEPART(WEEK, CONVERT(varchar(8), LEFT(SLGDATTIM, 8), 112) ) , '-', '') + '周'  = ${年周}]}  --   '2026年15周'     
   ) AS B ON 1 = 1  
 LEFT JOIN (  
   SELECT 
    distinct  TCODE , KOSTL     
  FROM express_ods.dbo.ODS_SAP_ZVS_TCODE_DATE  WHERE KOSTL is not null 
       ) AS C ON A."报表编码" = C.TCODE
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

SELECT  
   A."报表编码", A."报表编码"+'-'+A."报表名称" AS "报表名称" , A."访问次数" , B."总次数"  , C.KOSTL
  , ROUND(CAST(A.访问次数 AS FLOAT) / CAST(B.总次数 AS FLOAT) , 4) AS 占比  
 FROM (  
 SELECT SLGTC AS "报表编码",
       TTEXT AS "报表名称", 
       COUNT(SLGUSER) AS "访问次数" 
FROM   ODS_SAP_ZVS_TCODE_LOG
WHERE /* SmartBI filter macro removed */ 1=1
       AND SLGTC <> 'SEU_INT' 
       AND SLGTC LIKE 'Z%' 
       AND LEFT(SLGTC,6) <> 'ZTBASI'  
GROUP BY  SLGTC, TTEXT
ORDER BY 访问次数 DESC  ) AS A  
LEFT JOIN (
  SELECT 
  COUNT(SLGUSER) AS "总次数"   
 FROM ODS_SAP_ZVS_TCODE_LOG  
WHERE /* SmartBI filter macro removed */ 1=1
   ) AS B ON 1 = 1  
 LEFT JOIN (  
   SELECT 
    distinct  TCODE , KOSTL     
  FROM ODS_SAP_ZVS_TCODE_DATE  WHERE KOSTL is not null 
       ) AS C ON A."报表编码" = C.TCODE
-- ===== 通用参考SQL结束 =====

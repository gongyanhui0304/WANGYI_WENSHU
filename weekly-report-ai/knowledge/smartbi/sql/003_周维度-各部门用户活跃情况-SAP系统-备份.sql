SELECT   
    A.* , B.平均访问率  
  FROM (   
SELECT 
  A.部门    -- , A.年份月份 
  , A.各部门总数 , B.总数 , C.天数 , A.登录次数  
  , ROUND(CAST(A.各部门总数 AS FLOAT) / CAST(B.总数 AS FLOAT) , 2) AS 账户占比   
  , ROUND(CAST(A.登录次数 AS FLOAT) / (CAST(A.各部门总数 AS FLOAT) * CAST(C.天数 AS FLOAT) ) , 2) AS 访问率   
 FROM ( 
SELECT CASE WHEN KOSTL = '软件开发部' THEN '研发中心'ELSE KOSTL END AS "部门" -- , LEFT(SAL_DATE,6) AS "年份月份"  
       , SUM(USERNUMBER_KY) AS "各部门总数"   
       , SUM(LOGNUMBER) AS "登录次数"        
FROM express_ods.dbo.ODS_SAP_LOG_BM_WEEK  
WHERE FWEEK = ${年周}   
      AND KOSTL IS NOT NULL AND KOSTL <> '' AND KOSTL <> '信息中心'   AND KOSTL <> '管理中心' 
GROUP BY  CASE WHEN KOSTL = '软件开发部' THEN '研发中心'ELSE KOSTL END  -- , LEFT(SAL_DATE,6) 
    ) AS A  
  LEFT JOIN ( 
SELECT SUM(USERNUMBER_KY) AS "总数"                -- USERNUMBER, USERNUMBER_KY, LOGNUMBER
FROM express_ods.dbo.ODS_SAP_LOG_BM_WEEK  
WHERE FWEEK = ${年周}   
      AND KOSTL IS NOT NULL AND KOSTL <> '' AND KOSTL <> '信息中心'   AND KOSTL <> '管理中心' 
    ) AS B ON 1 = 1     
  LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  -- , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH    
  , REPLACE(C_WEEK, 'W', '') C_WEEK   
FROM express_dw.[dbo].[DIM_DATE] 
where {[LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周'  = ${年周}]} 
     -- AND REPLACE(C_YEAR_MONTH, '-', '') = FORMAT(GETDATE()-7,'yyyyMM') 
GROUP BY -- C_YEAR_MONTH  , 
         REPLACE(C_WEEK, 'W', '')  
     ) AS C ON 1 = 1   
       ) AS A 
   LEFT JOIN (  
   SELECT 
  -- A.部门 -- , A.年份月份 
  -- , A.各部门总数 , B.总数 , C.天数 , A.登录次数  
  -- , ROUND(CAST(A.各部门总数 AS FLOAT) / CAST(B.总数 AS FLOAT) , 2) AS 账户占比   
  -- , 
  AVG(ROUND(CAST(A.登录次数 AS FLOAT) / (CAST(A.各部门总数 AS FLOAT) * CAST(C.天数 AS FLOAT) ) , 2) )  AS 平均访问率   
 FROM ( 
SELECT CASE WHEN KOSTL = '软件开发部' THEN '研发中心'ELSE KOSTL END  AS "部门" -- , LEFT(SAL_DATE,6) AS "年份月份"  
       , SUM(USERNUMBER_KY) AS "各部门总数"   
       , SUM(LOGNUMBER) AS "登录次数"        
FROM express_ods.dbo.ODS_SAP_LOG_BM_WEEK  
WHERE FWEEK = ${年周}   
      AND KOSTL IS NOT NULL AND KOSTL <> '' AND KOSTL <> '信息中心'   AND KOSTL <> '管理中心' 
GROUP BY  CASE WHEN KOSTL = '软件开发部' THEN '研发中心'ELSE KOSTL END  -- , LEFT(SAL_DATE,6) 
    ) AS A  
  LEFT JOIN ( 
SELECT SUM(USERNUMBER_KY) AS "总数"                -- USERNUMBER, USERNUMBER_KY, LOGNUMBER
FROM express_ods.dbo.ODS_SAP_LOG_BM_WEEK  
WHERE FWEEK = ${年周}   
      AND KOSTL IS NOT NULL AND KOSTL <> '' AND KOSTL <> '信息中心'   AND KOSTL <> '管理中心' 
    ) AS B ON 1 = 1     
  LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  -- , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH    
  , REPLACE(C_WEEK, 'W', '') C_WEEK   
FROM express_dw.[dbo].[DIM_DATE] 
where {[LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周'  = ${年周}]} 
     -- AND REPLACE(C_YEAR_MONTH, '-', '') = FORMAT(GETDATE()-7,'yyyyMM') 
GROUP BY -- C_YEAR_MONTH  , 
         REPLACE(C_WEEK, 'W', '')  
     ) AS C ON 1 = 1   
       ) AS B ON 1 = 1
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

SELECT   
    A.* , B.平均访问率  
  FROM (   
SELECT 
  A.部门    -- , A.年份月份 
  , A.各部门总数 , B.总数 , C.天数 , A.登录次数  
  , ROUND(CAST(A.各部门总数 AS FLOAT) / CAST(B.总数 AS FLOAT) , 2) AS 账户占比   
  , ROUND(CAST(A.登录次数 AS FLOAT) / (CAST(A.各部门总数 AS FLOAT) * CAST(C.天数 AS FLOAT) ) , 2) AS 访问率   
 FROM ( 
SELECT CASE WHEN KOSTL = '软件开发部' THEN '研发中心'ELSE KOSTL END AS "部门" -- , LEFT(SAL_DATE,6) AS "年份月份"  
       , SUM(USERNUMBER_KY) AS "各部门总数"   
       , SUM(LOGNUMBER) AS "登录次数"        
FROM ODS_SAP_LOG_BM_WEEK  
WHERE FWEEK = :dynamic_param   
      AND KOSTL IS NOT NULL AND KOSTL <> '' AND KOSTL <> '信息中心'   AND KOSTL <> '管理中心' 
GROUP BY  CASE WHEN KOSTL = '软件开发部' THEN '研发中心'ELSE KOSTL END  -- , LEFT(SAL_DATE,6) 
    ) AS A  
  LEFT JOIN ( 
SELECT SUM(USERNUMBER_KY) AS "总数"                -- USERNUMBER, USERNUMBER_KY, LOGNUMBER
FROM ODS_SAP_LOG_BM_WEEK  
WHERE FWEEK = :dynamic_param   
      AND KOSTL IS NOT NULL AND KOSTL <> '' AND KOSTL <> '信息中心'   AND KOSTL <> '管理中心' 
    ) AS B ON 1 = 1     
  LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  -- , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH    
  , REPLACE(C_WEEK, 'W', '') C_WEEK   
FROM [DIM_DATE] 
WHERE /* SmartBI filter macro removed */ 1=1
     -- AND REPLACE(C_YEAR_MONTH, '-', '') = FORMAT(GETDATE()-7,'yyyyMM') 
GROUP BY -- C_YEAR_MONTH  , 
         REPLACE(C_WEEK, 'W', '')  
     ) AS C ON 1 = 1   
       ) AS A 
   LEFT JOIN (  
   SELECT 
  -- A.部门 -- , A.年份月份 
  -- , A.各部门总数 , B.总数 , C.天数 , A.登录次数  
  -- , ROUND(CAST(A.各部门总数 AS FLOAT) / CAST(B.总数 AS FLOAT) , 2) AS 账户占比   
  -- , 
  AVG(ROUND(CAST(A.登录次数 AS FLOAT) / (CAST(A.各部门总数 AS FLOAT) * CAST(C.天数 AS FLOAT) ) , 2) )  AS 平均访问率   
 FROM ( 
SELECT CASE WHEN KOSTL = '软件开发部' THEN '研发中心'ELSE KOSTL END  AS "部门" -- , LEFT(SAL_DATE,6) AS "年份月份"  
       , SUM(USERNUMBER_KY) AS "各部门总数"   
       , SUM(LOGNUMBER) AS "登录次数"        
FROM ODS_SAP_LOG_BM_WEEK  
WHERE FWEEK = :dynamic_param   
      AND KOSTL IS NOT NULL AND KOSTL <> '' AND KOSTL <> '信息中心'   AND KOSTL <> '管理中心' 
GROUP BY  CASE WHEN KOSTL = '软件开发部' THEN '研发中心'ELSE KOSTL END  -- , LEFT(SAL_DATE,6) 
    ) AS A  
  LEFT JOIN ( 
SELECT SUM(USERNUMBER_KY) AS "总数"                -- USERNUMBER, USERNUMBER_KY, LOGNUMBER
FROM ODS_SAP_LOG_BM_WEEK  
WHERE FWEEK = :dynamic_param   
      AND KOSTL IS NOT NULL AND KOSTL <> '' AND KOSTL <> '信息中心'   AND KOSTL <> '管理中心' 
    ) AS B ON 1 = 1     
  LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  -- , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH    
  , REPLACE(C_WEEK, 'W', '') C_WEEK   
FROM [DIM_DATE] 
WHERE /* SmartBI filter macro removed */ 1=1
     -- AND REPLACE(C_YEAR_MONTH, '-', '') = FORMAT(GETDATE()-7,'yyyyMM') 
GROUP BY -- C_YEAR_MONTH  , 
         REPLACE(C_WEEK, 'W', '')  
     ) AS C ON 1 = 1   
       ) AS B ON 1 = 1
-- ===== 通用参考SQL结束 =====

SELECT  
    A.FTYPE , A.用户每月累计访问次数  
    ,  B.每个模块的每个Tcode应访问次数 
    ,  C.天数  
    , A.用户每月累计访问次数 / (B.每个模块的每个Tcode应访问次数 * C.天数 ) AS 模块使用率 
 FROM ( 
SELECT   
    LEFT(A.SLGDATTIM, 6) AS SLGDATTIM , A.FTYPE , COUNT(A.SLGUSER) AS "用户每月累计访问次数"  
  FROM ( 
 SELECT distinct
     SLGUSER , NAME_TEXT , SLGTC , LEFT(SLGDATTIM, 8) AS SLGDATTIM  
     , [TYPE] AS FTYPE 
 FROM ODS_SAP_ZVS_TCODE_LOG  
 WHERE LEFT(SLGDATTIM, 6) = ${年月} -- '202510' 
       ) AS A 
   GROUP BY LEFT(A.SLGDATTIM, 6) , A.FTYPE  ) AS A  

  LEFT JOIN (   
 SELECT  
    A.FTYPE , COUNT(A.UNAME) AS "每个模块的每个Tcode应访问次数"   
   FROM (  
 SELECT 
   distinct  UNAME,  TCODE,  FTYPE 
FROM express_ods.dbo.ODS_SAP_ZVS_USER_TCODE  
 WHERE TCODE LIKE 'Z%' AND YM_BANBEN = ${年月} -- '202510' 
      ) AS A  
   GROUP BY A.FTYPE  ) AS B ON A.FTYPE = B.FTYPE        
   
   LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH   
FROM express_dw.[dbo].[DIM_DATE] 
where REPLACE(C_YEAR_MONTH, '-', '') = ${年月} -- '202510'
GROUP BY C_YEAR_MONTH   ) AS C ON A.SLGDATTIM = C.C_YEAR_MONTH
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

SELECT  
    A.FTYPE , A.用户每月累计访问次数  
    ,  B.每个模块的每个Tcode应访问次数 
    ,  C.天数  
    , A.用户每月累计访问次数 / (B.每个模块的每个Tcode应访问次数 * C.天数 ) AS 模块使用率 
 FROM ( 
SELECT   
    LEFT(A.SLGDATTIM, 6) AS SLGDATTIM , A.FTYPE , COUNT(A.SLGUSER) AS "用户每月累计访问次数"  
  FROM ( 
 SELECT distinct
     SLGUSER , NAME_TEXT , SLGTC , LEFT(SLGDATTIM, 8) AS SLGDATTIM  
     , [TYPE] AS FTYPE 
 FROM ODS_SAP_ZVS_TCODE_LOG  
 WHERE LEFT(SLGDATTIM, 6) = :dynamic_param -- '202510' 
       ) AS A 
   GROUP BY LEFT(A.SLGDATTIM, 6) , A.FTYPE  ) AS A  

  LEFT JOIN (   
 SELECT  
    A.FTYPE , COUNT(A.UNAME) AS "每个模块的每个Tcode应访问次数"   
   FROM (  
 SELECT 
   distinct  UNAME,  TCODE,  FTYPE 
FROM ODS_SAP_ZVS_USER_TCODE  
 WHERE TCODE LIKE 'Z%' AND YM_BANBEN = :dynamic_param -- '202510' 
      ) AS A  
   GROUP BY A.FTYPE  ) AS B ON A.FTYPE = B.FTYPE        
   
   LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH   
FROM [DIM_DATE] 
where REPLACE(C_YEAR_MONTH, '-', '') = :dynamic_param -- '202510'
GROUP BY C_YEAR_MONTH   ) AS C ON A.SLGDATTIM = C.C_YEAR_MONTH
-- ===== 通用参考SQL结束 =====

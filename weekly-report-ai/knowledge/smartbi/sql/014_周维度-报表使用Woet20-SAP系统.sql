SELECT A.* , C.KOSTL
 FROM (  
 SELECT -- TOP 20 
        A.TCODE AS "报表编码" , 
        A.TCODE+'-'+C.TTEXT AS "报表名称" , 
        COUNT(B.报表编码) AS "访问次数" 
 FROM express_ods.dbo.ODS_SAP_ZVS_TCODE_DATE AS A 
 LEFT JOIN ODS_SAP_TSTCT AS C ON A.TCODE = C.TCODE
 LEFT JOIN (SELECT SLGTC AS "报表编码", 
       SLGTC+'-'+TTEXT AS "报表名称"  
FROM   express_ods.dbo.ODS_SAP_ZVS_TCODE_LOG
WHERE  LEFT(SLGDATTIM, 8) <= (SELECT MAX(CONVERT(varchar(8),C_DATE, 112))  as C_DATE   
                               FROM express_dw.[dbo].[DIM_DATE] 
                               where LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周' =  ${年周} -- '2026年17周'  
                                  )   
       AND LEFT(SLGDATTIM, 8) >= (SELECT MAX(CONVERT(varchar(8), DATEADD(day, -90, C_DATE ) , 112) )  as C_DATE   
                               FROM express_dw.[dbo].[DIM_DATE] 
                               where LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周' = ${年周} --'2026年17周'  
                                  )      
       AND SLGTC <> 'SEU_INT' 
       AND LEFT(SLGTC,6) <> 'ZTBASI' 
            ) AS B ON A.TCODE = B.报表编码   
  WHERE A.TCODE LIKE 'Z%'    
       AND A.TCODE+'-'+C.TTEXT IS NOT NULL  
       AND A.TCODE NOT LIKE 'ZMOM%' AND A.TCODE NOT LIKE 'ZTBASIS%'   
       AND A.TCODE IN ( SELECT distinct TCODE  FROM  express_ods.dbo.ODS_SAP_ZVS_TCODE_DATE  
                           WHERE 1 = 1 -- TCODE = 'ZM083' 
                                 AND LEFT(CDAT, 8) >= (SELECT MAX(CONVERT(varchar(8), DATEADD(day, -90, C_DATE ) , 112) )  as C_DATE   
                               FROM express_dw.[dbo].[DIM_DATE] 
                               where LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周' = ${年周} --'2026年17周'  
                                  )  
           )  
 GROUP BY A.TCODE , A.TCODE+'-'+C.TTEXT   
-- ORDER BY 访问次数 ASC  
    ) AS A  
 LEFT JOIN (  
   SELECT 
    distinct  TCODE , KOSTL     
  FROM express_ods.dbo.ODS_SAP_ZVS_TCODE_DATE  WHERE KOSTL is not null 
       ) AS C ON A."报表编码" = C.TCODE     
   WHERE 访问次数 = 0     
   -- ORDER BY 访问次数 ASC
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

SELECT A.* , C.KOSTL
 FROM (  
 SELECT -- TOP 20 
        A.TCODE AS "报表编码" , 
        A.TCODE+'-'+C.TTEXT AS "报表名称" , 
        COUNT(B.报表编码) AS "访问次数" 
 FROM ODS_SAP_ZVS_TCODE_DATE AS A 
 LEFT JOIN ODS_SAP_TSTCT AS C ON A.TCODE = C.TCODE
 LEFT JOIN (SELECT SLGTC AS "报表编码", 
       SLGTC+'-'+TTEXT AS "报表名称"  
FROM   ODS_SAP_ZVS_TCODE_LOG
WHERE  LEFT(SLGDATTIM, 8) <= (SELECT MAX(CONVERT(varchar(8),C_DATE, 112))  as C_DATE   
                               FROM [DIM_DATE] 
                               where LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周' =  :dynamic_param -- '2026年17周'  
                                  )   
       AND LEFT(SLGDATTIM, 8) >= (SELECT MAX(CONVERT(varchar(8), DATEADD(day, -90, C_DATE ) , 112) )  as C_DATE   
                               FROM [DIM_DATE] 
                               where LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周' = :dynamic_param --'2026年17周'  
                                  )      
       AND SLGTC <> 'SEU_INT' 
       AND LEFT(SLGTC,6) <> 'ZTBASI' 
            ) AS B ON A.TCODE = B.报表编码   
  WHERE A.TCODE LIKE 'Z%'    
       AND A.TCODE+'-'+C.TTEXT IS NOT NULL  
       AND A.TCODE NOT LIKE 'ZMOM%' AND A.TCODE NOT LIKE 'ZTBASIS%'   
       AND A.TCODE IN ( SELECT distinct TCODE  FROM  ODS_SAP_ZVS_TCODE_DATE  
                           WHERE 1 = 1 -- TCODE = 'ZM083' 
                                 AND LEFT(CDAT, 8) >= (SELECT MAX(CONVERT(varchar(8), DATEADD(day, -90, C_DATE ) , 112) )  as C_DATE   
                               FROM [DIM_DATE] 
                               where LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周' = :dynamic_param --'2026年17周'  
                                  )  
           )  
 GROUP BY A.TCODE , A.TCODE+'-'+C.TTEXT   
-- ORDER BY 访问次数 ASC  
    ) AS A  
 LEFT JOIN (  
   SELECT 
    distinct  TCODE , KOSTL     
  FROM ODS_SAP_ZVS_TCODE_DATE  WHERE KOSTL is not null 
       ) AS C ON A."报表编码" = C.TCODE     
   WHERE 访问次数 = 0     
   -- ORDER BY 访问次数 ASC
-- ===== 通用参考SQL结束 =====

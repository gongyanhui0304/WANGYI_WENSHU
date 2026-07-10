SELECT  
   A.* , B.平均访问率  
  FROM ( 
SELECT 
  A.部门 , A.年份月份 , C.C_WEEK AS 周 , A.各部门总数 , B.总数 , C.天数 , ISNULL(D.登录次数,0) 登录次数   
 -- , ROUND(CAST(A.各部门总数 AS FLOAT) / CAST(B.总数 AS FLOAT) , 2) AS 账户占比   
 -- , ROUND(ISNULL(CAST(D.登录次数 AS FLOAT),0) / (CAST(A.各部门总数 AS FLOAT) * CAST(C.天数 AS FLOAT) ) , 2) AS 访问率   
FROM ( 
SELECT 
      CASE WHEN A.deptname2 = '软件开发部' THEN '研发中心'ELSE A.deptname2 END AS "部门", A.VERSION_MONTH AS "年份月份"  
      , COUNT(A.empcode) AS "各部门总数"   
from ( SELECT distinct deptname2 , empcode , VERSION_MONTH FROM express_dw.dbo.DWD_BIUSER_MINGXI 
            WHERE VERSION_MONTH >= '202510' AND deptname2 <> '信息中心'  AND deptname2 <> '管理中心'  ) AS A 
 GROUP BY CASE WHEN A.deptname2 = '软件开发部' THEN '研发中心'ELSE A.deptname2 END  , A.VERSION_MONTH  ) AS A 
 LEFT JOIN ( 
 SELECT 
      A.VERSION_MONTH AS "年份月份"  
      , COUNT(A.empcode) AS "总数"   
 from ( SELECT distinct deptname2 , empcode , VERSION_MONTH FROM express_dw.dbo.DWD_BIUSER_MINGXI 
            WHERE VERSION_MONTH >= '202510' AND deptname2 <> '信息中心'  AND deptname2 <> '管理中心'  ) AS A 
 GROUP BY A.VERSION_MONTH  ) AS B ON A.年份月份 = B.年份月份  
  LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH   , REPLACE(C_WEEK, 'W', '') C_WEEK 
FROM express_dw.[dbo].[DIM_DATE] 
where {[LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周' = ${年周}]}  --   = '2026年15周' 
     -- AND REPLACE(C_YEAR_MONTH, '-', '') = FORMAT(GETDATE()-7,'yyyyMM') 
GROUP BY REPLACE(C_YEAR_MONTH, '-', '') , REPLACE(C_WEEK, 'W', '')   ) AS C ON A.年份月份 = C.C_YEAR_MONTH  
 LEFT JOIN ( 
   SELECT   
  LEFT(A."年份月份",6) AS "年份月份"  
  , A.FWEEK
  , A."部门" 
  , COUNT(A.c_username) AS "登录次数" 
  FROM ( 
  SELECT distinct 
  CONVERT(varchar(8), A.c_time, 112) AS "年份月份"  
  , REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') AS FWEEK  
  , B.deptname2 AS "部门" 
  , A.c_username   
FROM SmartbiRep.dbo.t_operationlog AS A
LEFT JOIN 
    express_ods.dbo.ODS_EHR_VPS_EMPINFO AS B ON A.c_username = B.empcode
WHERE {[FORMAT(A.c_time,'yyyy') + '年' + REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') + '周' = ${年周}]}  --   = '2026年15周' 
 -- AND FORMAT(A.c_time,'yyyyMM') = FORMAT(GETDATE()-7,'yyyyMM')     
 -- AND REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') = '15' 
  AND A.c_detail NOT LIKE '%系统内部使用本地客户端连接器切换登录用户%'
 -- AND A.c_type = '登录'
  AND A.c_type like'%浏览%'   AND A.c_type  <>'私有查询'      
 -- AND A.c_username = '022279' 
  AND B.deptname2 IS NOT NULL ) AS A     
 GROUP BY LEFT(A."年份月份",6) , A."部门" , A.FWEEK      
   ) AS D ON A.年份月份 = D.年份月份 AND A.部门 = D.部门 AND C.C_WEEK = D.FWEEK   
  where {[LEFT(A.年份月份,4) + '年' + C.C_WEEK + '周' = ${年周}]}  --  = '2026年15周'  
      --  AND A.年份月份 = FORMAT(GETDATE()-7,'yyyyMM')   
        ) AS A 
   LEFT JOIN (  
   SELECT 
 -- A.部门 , A.年份月份 , C.C_WEEK AS 周 , A.各部门总数 , B.总数 , C.天数 , ISNULL(D.登录次数,0) 登录次数   
 -- , ROUND(CAST(A.各部门总数 AS FLOAT) / CAST(B.总数 AS FLOAT) , 2) AS 账户占比   
 -- , 
      AVG(ROUND(ISNULL(CAST(D.登录次数 AS FLOAT),0) / (CAST(A.各部门总数 AS FLOAT) * CAST(C.天数 AS FLOAT) ) , 2) )  AS 平均访问率   
FROM ( 
SELECT 
      A.deptname2 AS "部门", A.VERSION_MONTH AS "年份月份"  
      , COUNT(A.empcode) AS "各部门总数"   
from ( SELECT distinct deptname2 , empcode , VERSION_MONTH FROM express_dw.dbo.DWD_BIUSER_MINGXI 
            WHERE VERSION_MONTH >= '202510' AND deptname2 <> '信息中心'  AND deptname2 <> '管理中心'  ) AS A 
 GROUP BY A.deptname2 , A.VERSION_MONTH  ) AS A 
 LEFT JOIN ( 
 SELECT 
      A.VERSION_MONTH AS "年份月份"  
      , COUNT(A.empcode) AS "总数"   
 from ( SELECT distinct deptname2 , empcode , VERSION_MONTH FROM express_dw.dbo.DWD_BIUSER_MINGXI 
            WHERE VERSION_MONTH >= '202510' AND deptname2 <> '信息中心'  AND deptname2 <> '管理中心'  ) AS A 
 GROUP BY A.VERSION_MONTH  ) AS B ON A.年份月份 = B.年份月份  
  LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH   , REPLACE(C_WEEK, 'W', '') C_WEEK 
FROM express_dw.[dbo].[DIM_DATE] 
where {[LEFT(REPLACE(C_YEAR_MONTH, '-', ''),4) + '年' + REPLACE(C_WEEK, 'W', '') + '周' = ${年周}]}  --   = '2026年15周' 
     -- AND REPLACE(C_YEAR_MONTH, '-', '') = FORMAT(GETDATE()-7,'yyyyMM') 
GROUP BY REPLACE(C_YEAR_MONTH, '-', '') , REPLACE(C_WEEK, 'W', '')   ) AS C ON A.年份月份 = C.C_YEAR_MONTH  
 LEFT JOIN ( 
   SELECT   
  LEFT(A."年份月份",6) AS "年份月份"  
  , A.FWEEK
  , CASE WHEN A."部门" = '软件开发部' THEN '研发中心'ELSE A."部门" END AS "部门" 
  , COUNT(A.c_username) AS "登录次数" 
  FROM ( 
  SELECT distinct 
  CONVERT(varchar(8), A.c_time, 112) AS "年份月份"  
  , REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') AS FWEEK  
  , B.deptname2 AS "部门" 
  , A.c_username   
FROM SmartbiRep.dbo.t_operationlog AS A
LEFT JOIN 
    express_ods.dbo.ODS_EHR_VPS_EMPINFO AS B ON A.c_username = B.empcode
WHERE {[FORMAT(A.c_time,'yyyy') + '年' + REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') + '周' = ${年周}]}  --   = '2026年15周' 
 -- AND FORMAT(A.c_time,'yyyyMM') = FORMAT(GETDATE()-7,'yyyyMM')     
 -- AND REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') = '15' 
  AND A.c_detail NOT LIKE '%系统内部使用本地客户端连接器切换登录用户%'
 -- AND A.c_type = '登录'
  AND A.c_type like'%浏览%'   AND A.c_type  <>'私有查询'      
 -- AND A.c_username = '022279' 
  AND B.deptname2 IS NOT NULL ) AS A     
 GROUP BY LEFT(A."年份月份",6) , CASE WHEN A."部门" = '软件开发部' THEN '研发中心'ELSE A."部门" END  , A.FWEEK      
   ) AS D ON A.年份月份 = D.年份月份 AND A.部门 = D.部门 AND C.C_WEEK = D.FWEEK   
  where {[LEFT(A.年份月份,4) + '年' + C.C_WEEK + '周' = ${年周}]}  --  = '2026年15周'  
       -- AND A.年份月份 = FORMAT(GETDATE()-7,'yyyyMM')   
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
  A.部门 , A.年份月份 , C.C_WEEK AS 周 , A.各部门总数 , B.总数 , C.天数 , ISNULL(D.登录次数,0) 登录次数   
 -- , ROUND(CAST(A.各部门总数 AS FLOAT) / CAST(B.总数 AS FLOAT) , 2) AS 账户占比   
 -- , ROUND(ISNULL(CAST(D.登录次数 AS FLOAT),0) / (CAST(A.各部门总数 AS FLOAT) * CAST(C.天数 AS FLOAT) ) , 2) AS 访问率   
FROM ( 
SELECT 
      CASE WHEN A.deptname2 = '软件开发部' THEN '研发中心'ELSE A.deptname2 END AS "部门", A.VERSION_MONTH AS "年份月份"  
      , COUNT(A.empcode) AS "各部门总数"   
from ( SELECT distinct deptname2 , empcode , VERSION_MONTH FROM DWD_BIUSER_MINGXI 
            WHERE VERSION_MONTH >= '202510' AND deptname2 <> '信息中心'  AND deptname2 <> '管理中心'  ) AS A 
 GROUP BY CASE WHEN A.deptname2 = '软件开发部' THEN '研发中心'ELSE A.deptname2 END  , A.VERSION_MONTH  ) AS A 
 LEFT JOIN ( 
 SELECT 
      A.VERSION_MONTH AS "年份月份"  
      , COUNT(A.empcode) AS "总数"   
 from ( SELECT distinct deptname2 , empcode , VERSION_MONTH FROM DWD_BIUSER_MINGXI 
            WHERE VERSION_MONTH >= '202510' AND deptname2 <> '信息中心'  AND deptname2 <> '管理中心'  ) AS A 
 GROUP BY A.VERSION_MONTH  ) AS B ON A.年份月份 = B.年份月份  
  LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH   , REPLACE(C_WEEK, 'W', '') C_WEEK 
FROM [DIM_DATE] 
WHERE /* SmartBI filter macro removed */ 1=1
     -- AND REPLACE(C_YEAR_MONTH, '-', '') = FORMAT(GETDATE()-7,'yyyyMM') 
GROUP BY REPLACE(C_YEAR_MONTH, '-', '') , REPLACE(C_WEEK, 'W', '')   ) AS C ON A.年份月份 = C.C_YEAR_MONTH  
 LEFT JOIN ( 
   SELECT   
  LEFT(A."年份月份",6) AS "年份月份"  
  , A.FWEEK
  , A."部门" 
  , COUNT(A.c_username) AS "登录次数" 
  FROM ( 
  SELECT distinct 
  CONVERT(varchar(8), A.c_time, 112) AS "年份月份"  
  , REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') AS FWEEK  
  , B.deptname2 AS "部门" 
  , A.c_username   
FROM t_operationlog AS A
LEFT JOIN 
    ODS_EHR_VPS_EMPINFO AS B ON A.c_username = B.empcode
WHERE /* SmartBI filter macro removed */ 1=1
 -- AND FORMAT(A.c_time,'yyyyMM') = FORMAT(GETDATE()-7,'yyyyMM')     
 -- AND REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') = '15' 
  AND A.c_detail NOT LIKE '%系统内部使用本地客户端连接器切换登录用户%'
 -- AND A.c_type = '登录'
  AND A.c_type like'%浏览%'   AND A.c_type  <>'私有查询'      
 -- AND A.c_username = '022279' 
  AND B.deptname2 IS NOT NULL ) AS A     
 GROUP BY LEFT(A."年份月份",6) , A."部门" , A.FWEEK      
   ) AS D ON A.年份月份 = D.年份月份 AND A.部门 = D.部门 AND C.C_WEEK = D.FWEEK   
WHERE /* SmartBI filter macro removed */ 1=1
      --  AND A.年份月份 = FORMAT(GETDATE()-7,'yyyyMM')   
        ) AS A 
   LEFT JOIN (  
   SELECT 
 -- A.部门 , A.年份月份 , C.C_WEEK AS 周 , A.各部门总数 , B.总数 , C.天数 , ISNULL(D.登录次数,0) 登录次数   
 -- , ROUND(CAST(A.各部门总数 AS FLOAT) / CAST(B.总数 AS FLOAT) , 2) AS 账户占比   
 -- , 
      AVG(ROUND(ISNULL(CAST(D.登录次数 AS FLOAT),0) / (CAST(A.各部门总数 AS FLOAT) * CAST(C.天数 AS FLOAT) ) , 2) )  AS 平均访问率   
FROM ( 
SELECT 
      A.deptname2 AS "部门", A.VERSION_MONTH AS "年份月份"  
      , COUNT(A.empcode) AS "各部门总数"   
from ( SELECT distinct deptname2 , empcode , VERSION_MONTH FROM DWD_BIUSER_MINGXI 
            WHERE VERSION_MONTH >= '202510' AND deptname2 <> '信息中心'  AND deptname2 <> '管理中心'  ) AS A 
 GROUP BY A.deptname2 , A.VERSION_MONTH  ) AS A 
 LEFT JOIN ( 
 SELECT 
      A.VERSION_MONTH AS "年份月份"  
      , COUNT(A.empcode) AS "总数"   
 from ( SELECT distinct deptname2 , empcode , VERSION_MONTH FROM DWD_BIUSER_MINGXI 
            WHERE VERSION_MONTH >= '202510' AND deptname2 <> '信息中心'  AND deptname2 <> '管理中心'  ) AS A 
 GROUP BY A.VERSION_MONTH  ) AS B ON A.年份月份 = B.年份月份  
  LEFT JOIN (
  SELECT 
  count(*) - SUM( CASE WHEN HOLIDAY_TYPE = 1 THEN 1 ELSE 0 END ) - SUM( CASE WHEN WEEK = 6 THEN 0.5 ELSE 0 END ) AS "天数" 
  , REPLACE(C_YEAR_MONTH, '-', '') AS C_YEAR_MONTH   , REPLACE(C_WEEK, 'W', '') C_WEEK 
FROM [DIM_DATE] 
WHERE /* SmartBI filter macro removed */ 1=1
     -- AND REPLACE(C_YEAR_MONTH, '-', '') = FORMAT(GETDATE()-7,'yyyyMM') 
GROUP BY REPLACE(C_YEAR_MONTH, '-', '') , REPLACE(C_WEEK, 'W', '')   ) AS C ON A.年份月份 = C.C_YEAR_MONTH  
 LEFT JOIN ( 
   SELECT   
  LEFT(A."年份月份",6) AS "年份月份"  
  , A.FWEEK
  , CASE WHEN A."部门" = '软件开发部' THEN '研发中心'ELSE A."部门" END AS "部门" 
  , COUNT(A.c_username) AS "登录次数" 
  FROM ( 
  SELECT distinct 
  CONVERT(varchar(8), A.c_time, 112) AS "年份月份"  
  , REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') AS FWEEK  
  , B.deptname2 AS "部门" 
  , A.c_username   
FROM t_operationlog AS A
LEFT JOIN 
    ODS_EHR_VPS_EMPINFO AS B ON A.c_username = B.empcode
WHERE /* SmartBI filter macro removed */ 1=1
 -- AND FORMAT(A.c_time,'yyyyMM') = FORMAT(GETDATE()-7,'yyyyMM')     
 -- AND REPLACE(DATEPART(WEEK, A.c_time ) , '-', '') = '15' 
  AND A.c_detail NOT LIKE '%系统内部使用本地客户端连接器切换登录用户%'
 -- AND A.c_type = '登录'
  AND A.c_type like'%浏览%'   AND A.c_type  <>'私有查询'      
 -- AND A.c_username = '022279' 
  AND B.deptname2 IS NOT NULL ) AS A     
 GROUP BY LEFT(A."年份月份",6) , CASE WHEN A."部门" = '软件开发部' THEN '研发中心'ELSE A."部门" END  , A.FWEEK      
   ) AS D ON A.年份月份 = D.年份月份 AND A.部门 = D.部门 AND C.C_WEEK = D.FWEEK   
WHERE /* SmartBI filter macro removed */ 1=1
       -- AND A.年份月份 = FORMAT(GETDATE()-7,'yyyyMM')   
        ) AS B ON 1 = 1
-- ===== 通用参考SQL结束 =====

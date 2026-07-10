SELECT 
   C.dep , A."报表名称" , A."访问次数" , B."总次数" 
  , ROUND(CAST(A.访问次数 AS FLOAT) / CAST(B.总次数 AS FLOAT) , 4) AS 占比  
 FROM (  
    SELECT TOP 20 
       -- CONVERT(varchar(6), c_time, 112) AS 年月,
        c_detailname                     AS 报表名称,
        c_detailid  ,  
        COUNT(*)                         AS 访问次数
    FROM SmartbiRep.dbo.t_operationlog
    WHERE {[FORMAT(c_time,'yyyy') + '年' + REPLACE(DATEPART(WEEK, c_time ) , '-', '') + '周' = ${年周}]}  -- '2026年14周'  
      AND c_detail NOT LIKE '%系统内部使用本地客户端连接器切换登录用户%'
      AND c_type like'%浏览%'   AND c_type NOT like '%私有查询%'      
      AND c_detailname IS NOT NULL
      AND c_detailname NOT LIKE '%填报%'
      AND c_detailname NOT LIKE '%导入%'
      AND c_source_type IS NOT NULL
      AND c_username LIKE '0%' 
      AND c_detailid IN (  SELECT  distinct a.c_resid
           FROM  SmartbiRep. [dbo].[t_restree] a 
           left join express_ods.[dbo].[ODS_DEP_BAOBIAO_CID]  b on a.c_pid=b.c_pid
             WHERE a.c_pid  in  (  SELECT   c_pid from   express_ods.[dbo].[ODS_DEP_BAOBIAO_CID]    )  
                   and c_restype not  in ('DEFAULT_TREENODE')  AND a.c_resname NOT IN ('1','11')     )
    GROUP BY -- CONVERT(varchar(6), c_time, 112), 
             c_detailname , c_detailid  
     ORDER BY 访问次数 DESC           
) AS A  
 LEFT JOIN (  
  SELECT 
   --  CONVERT(varchar(6), c_time, 112) AS "年月" 	,    
      count(*) AS "总次数" 
FROM SmartbiRep.[dbo].[t_operationlog] 
where  {[FORMAT(c_time,'yyyy') + '年' + REPLACE(DATEPART(WEEK, c_time ) , '-', '') + '周' = ${年周}]}  -- '2026年14周'  
 and  c_detail not like '%系统内部使用本地客户端连接器切换登录用户%' --
--and  c_type ='登录' 
AND c_type like'%浏览%'   AND c_type  NOT like '%私有查询%'    
and  c_detailname is  not null
and  c_detailname NOT like '%填报%'  and  c_detailname NOT like '%导入%' 
and c_source_type is  not null
 --and c_username='000065' 
 and c_username like '0%'  
 -- GROUP BY CONVERT(varchar(6), c_time, 112) 
   ) AS B ON 1 = 1       
  LEFT JOIN (SELECT  b.dep,   a.c_resname , a.c_resid
           FROM  SmartbiRep. [dbo].[t_restree] a 
           left join express_ods.[dbo].[ODS_DEP_BAOBIAO_CID]  b on a.c_pid=b.c_pid
             WHERE a.c_pid  in  (  SELECT   c_pid from   express_ods.[dbo].[ODS_DEP_BAOBIAO_CID]    )  
                   and c_restype not  in ('DEFAULT_TREENODE')  AND a.c_resname NOT IN ('1','11')   ) AS C ON A.c_detailid = C.c_resid
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

SELECT 
   C.dep , A."报表名称" , A."访问次数" , B."总次数" 
  , ROUND(CAST(A.访问次数 AS FLOAT) / CAST(B.总次数 AS FLOAT) , 4) AS 占比  
 FROM (  
    SELECT -- CONVERT(varchar(6), c_time, 112) AS 年月,
        c_detailname                     AS 报表名称,
        c_detailid  ,  
        COUNT(*)                         AS 访问次数
    FROM t_operationlog
WHERE /* SmartBI filter macro removed */ 1=1
      AND c_detail NOT LIKE '%系统内部使用本地客户端连接器切换登录用户%'
      AND c_type like'%浏览%'   AND c_type NOT like '%私有查询%'      
      AND c_detailname IS NOT NULL
      AND c_detailname NOT LIKE '%填报%'
      AND c_detailname NOT LIKE '%导入%'
      AND c_source_type IS NOT NULL
      AND c_username LIKE '0%' 
      AND c_detailid IN (  SELECT  distinct a.c_resid
           FROM  [t_restree] a 
           left join [ODS_DEP_BAOBIAO_CID]  b on a.c_pid=b.c_pid
             WHERE a.c_pid  in  (  SELECT   c_pid from   [ODS_DEP_BAOBIAO_CID]    )  
                   and c_restype not  in ('DEFAULT_TREENODE')  AND a.c_resname NOT IN ('1','11')     )
    GROUP BY -- CONVERT(varchar(6), c_time, 112), 
             c_detailname , c_detailid  
     ORDER BY 访问次数 DESC           
) AS A  
 LEFT JOIN (  
  SELECT 
   --  CONVERT(varchar(6), c_time, 112) AS "年月" 	,    
      count(*) AS "总次数" 
FROM [t_operationlog] 
WHERE /* SmartBI filter macro removed */ 1=1
 and  c_detail not like '%系统内部使用本地客户端连接器切换登录用户%' --
--and  c_type ='登录' 
AND c_type like'%浏览%'   AND c_type  NOT like '%私有查询%'    
and  c_detailname is  not null
and  c_detailname NOT like '%填报%'  and  c_detailname NOT like '%导入%' 
and c_source_type is  not null
 --and c_username='000065' 
 and c_username like '0%'  
 -- GROUP BY CONVERT(varchar(6), c_time, 112) 
   ) AS B ON 1 = 1       
  LEFT JOIN (SELECT  b.dep,   a.c_resname , a.c_resid
           FROM  [t_restree] a 
           left join [ODS_DEP_BAOBIAO_CID]  b on a.c_pid=b.c_pid
             WHERE a.c_pid  in  (  SELECT   c_pid from   [ODS_DEP_BAOBIAO_CID]    )  
                   and c_restype not  in ('DEFAULT_TREENODE')  AND a.c_resname NOT IN ('1','11')   ) AS C ON A.c_detailid = C.c_resid
-- ===== 通用参考SQL结束 =====

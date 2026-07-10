SELECT 
  CONVERT(varchar(6), A.PLMDBD, 112) AS "年份月份"  
  , CASE WHEN B.deptname2 = '软件开发部' THEN '可诺特软件' ELSE B.deptname2 END AS "部门" 
  , COUNT(A.PLMUSER) AS "登录次数"    
FROM express_ods.dbo.ODS_PLM_PLMLOGGER AS A 
LEFT JOIN 
    express_ods.dbo.ODS_EHR_VPS_EMPINFO AS B ON A.PLMUSER = B.empcode
WHERE CONVERT(varchar(6), A.PLMDBD, 112) = ${年月} -- '202510' 
  AND B.deptname2 IS NOT NULL  
 GROUP BY CONVERT(varchar(6), A.PLMDBD, 112) , CASE WHEN B.deptname2 = '软件开发部' THEN '可诺特软件' ELSE B.deptname2 END
-- ===== 通用参考SQL（去SQL Server库名前缀/去固定模板变量，仅供口径理解） =====
-- 说明：
-- 1. 本段不替代上方原始 SQL，上方原始 SQL 作为 SmartBI 口径参考保留。
-- 2. 本段去掉 SQL Server 库名前缀，例如 express_ods.dbo / express_dw.dbo / SmartbiRep.dbo。
-- 3. 本段把固定模板变量改为 :dynamic_param，实际执行时必须由页面 config.json 的 metric_queries 按指标场景传入时间、系统、部门等参数。
-- 4. TOP / 周期 / 月份 / 系统维度不得固定死，正式执行 SQL 应在 knowledge/smartbi/sql/metrics/ 中按 Metric 单独维护。
-- 5. 本段只供大模型理解统计口径和字段关系，不作为固定执行 SQL。

SELECT 
  CONVERT(varchar(6), A.PLMDBD, 112) AS "年份月份"  
  , CASE WHEN B.deptname2 = '软件开发部' THEN '可诺特软件' ELSE B.deptname2 END AS "部门" 
  , COUNT(A.PLMUSER) AS "登录次数"    
FROM ODS_PLM_PLMLOGGER AS A 
LEFT JOIN 
    ODS_EHR_VPS_EMPINFO AS B ON A.PLMUSER = B.empcode
WHERE CONVERT(varchar(6), A.PLMDBD, 112) = :dynamic_param -- '202510' 
  AND B.deptname2 IS NOT NULL  
 GROUP BY CONVERT(varchar(6), A.PLMDBD, 112) , CASE WHEN B.deptname2 = '软件开发部' THEN '可诺特软件' ELSE B.deptname2 END
-- ===== 通用参考SQL结束 =====

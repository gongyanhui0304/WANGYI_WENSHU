WITH reports AS (
  SELECT a.c_resid AS report_id, a.c_resname AS report_name, b.dep AS system_name
  FROM SmartbiRep.dbo.t_restree a
  LEFT JOIN express_ods.dbo.ODS_DEP_BAOBIAO_CID b ON a.c_pid = b.c_pid
  WHERE a.c_pid IN (SELECT c_pid FROM express_ods.dbo.ODS_DEP_BAOBIAO_CID)
    AND a.c_restype NOT IN (''DEFAULT_TREENODE'')
    AND a.c_resname NOT IN (''1'', ''11'')
), visit_30 AS (
  SELECT c_detailid AS report_id, COUNT(*) AS visit_30d, MAX(c_time) AS last_visit_time
  FROM SmartbiRep.dbo.t_operationlog
  WHERE c_time >= DATEADD(day, -30, GETDATE())
    AND c_type LIKE N''%浏览%''
    AND c_type NOT LIKE N''%私有查询%''
    AND c_detailname IS NOT NULL
    AND c_source_type IS NOT NULL
    AND c_username LIKE ''0%''
  GROUP BY c_detailid
), visit_7 AS (
  SELECT c_detailid AS report_id, COUNT(*) AS visit_7d
  FROM SmartbiRep.dbo.t_operationlog
  WHERE c_time >= DATEADD(day, -7, GETDATE())
    AND c_type LIKE N''%浏览%''
    AND c_type NOT LIKE N''%私有查询%''
    AND c_detailname IS NOT NULL
    AND c_source_type IS NOT NULL
    AND c_username LIKE ''0%''
  GROUP BY c_detailid
)
SELECT TOP 20
       ROW_NUMBER() OVER (ORDER BY COALESCE(v30.visit_30d, 0) ASC, r.report_name ASC) AS rank_no,
       COALESCE(r.system_name, N''其它'') AS system_name,
       r.report_id,
       r.report_name,
       COALESCE(v7.visit_7d, 0) AS visit_7d,
       COALESCE(v30.visit_30d, 0) AS visit_30d,
       v30.last_visit_time,
       CASE
         WHEN COALESCE(v30.visit_30d, 0) = 0 THEN N''建议下线''
         WHEN COALESCE(v30.visit_30d, 0) <= 2 THEN N''建议优化''
         WHEN COALESCE(v30.visit_30d, 0) <= 5 THEN N''建议推广''
         ELSE N''建议合并''
       END AS governance_action
FROM reports r
LEFT JOIN visit_30 v30 ON r.report_id = v30.report_id
LEFT JOIN visit_7 v7 ON r.report_id = v7.report_id
WHERE COALESCE(v30.visit_30d, 0) <= 5
ORDER BY COALESCE(v30.visit_30d, 0) ASC, r.report_name ASC;

WITH low_activity AS (
  SELECT r.report_id, r.report_name, COALESCE(r.system_name, N''其它'') AS system_name, COALESCE(v.visit_30d, 0) AS visit_30d
  FROM (
    SELECT a.c_resid AS report_id, a.c_resname AS report_name, b.dep AS system_name
    FROM SmartbiRep.dbo.t_restree a
    LEFT JOIN express_ods.dbo.ODS_DEP_BAOBIAO_CID b ON a.c_pid = b.c_pid
    WHERE a.c_pid IN (SELECT c_pid FROM express_ods.dbo.ODS_DEP_BAOBIAO_CID)
      AND a.c_restype NOT IN (''DEFAULT_TREENODE'')
      AND a.c_resname NOT IN (''1'', ''11'')
  ) r
  LEFT JOIN (
    SELECT c_detailid AS report_id, COUNT(*) AS visit_30d
    FROM SmartbiRep.dbo.t_operationlog
    WHERE c_time >= DATEADD(day, -30, GETDATE())
      AND c_type LIKE N''%浏览%''
      AND c_type NOT LIKE N''%私有查询%''
      AND c_detailname IS NOT NULL
      AND c_source_type IS NOT NULL
      AND c_username LIKE ''0%''
    GROUP BY c_detailid
  ) v ON r.report_id = v.report_id
  WHERE COALESCE(v.visit_30d, 0) <= 5
)
SELECT system_name, COUNT(*) AS low_activity_count
FROM low_activity
GROUP BY system_name
ORDER BY low_activity_count DESC;

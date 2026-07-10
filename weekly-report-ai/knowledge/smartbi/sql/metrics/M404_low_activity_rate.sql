WITH reports AS (
  SELECT a.c_resid AS report_id
  FROM SmartbiRep.dbo.t_restree a
  WHERE a.c_pid IN (SELECT c_pid FROM express_ods.dbo.ODS_DEP_BAOBIAO_CID)
    AND a.c_restype NOT IN (''DEFAULT_TREENODE'')
    AND a.c_resname NOT IN (''1'', ''11'')
), visits AS (
  SELECT c_detailid AS report_id, COUNT(*) AS visit_30d
  FROM SmartbiRep.dbo.t_operationlog
  WHERE c_time >= DATEADD(day, -30, GETDATE())
    AND c_type LIKE N''%浏览%''
    AND c_type NOT LIKE N''%私有查询%''
    AND c_detailname IS NOT NULL
    AND c_source_type IS NOT NULL
    AND c_username LIKE ''0%''
  GROUP BY c_detailid
), summary AS (
  SELECT COUNT(*) AS report_total,
         SUM(CASE WHEN COALESCE(v.visit_30d, 0) <= 5 THEN 1 ELSE 0 END) AS low_activity_count
  FROM reports r
  LEFT JOIN visits v ON r.report_id = v.report_id
)
SELECT report_total, low_activity_count,
       CASE WHEN report_total = 0 THEN 0 ELSE CAST(low_activity_count AS float) / CAST(report_total AS float) END AS low_activity_rate
FROM summary;

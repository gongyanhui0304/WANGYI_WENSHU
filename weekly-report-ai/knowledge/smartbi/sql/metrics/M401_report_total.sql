SELECT a.c_resid AS report_id, a.c_resname AS report_name, b.dep AS system_name
FROM SmartbiRep.dbo.t_restree a
LEFT JOIN express_ods.dbo.ODS_DEP_BAOBIAO_CID b ON a.c_pid = b.c_pid
WHERE a.c_pid IN (SELECT c_pid FROM express_ods.dbo.ODS_DEP_BAOBIAO_CID)
  AND a.c_restype NOT IN (''DEFAULT_TREENODE'')
  AND a.c_resname NOT IN (''1'', ''11'');

-- ==============================================================
-- Redmine Sprint 进度明细
-- 参数: 版本名称（如 'Sprint1'）
-- ==============================================================

SELECT i.id, i.subject, s.name as status, p.name as priority,
       u.firstname || ' ' || u.lastname as assignee,
       i.done_ratio as progress_pct, i.due_date,
       i.created_on::date, i.closed_on::date,
       i.updated_on::date as last_update
FROM issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN enumerations p ON i.priority_id = p.id AND p.type='IssuePriority'
LEFT JOIN users u ON i.assigned_to_id = u.id
LEFT JOIN versions v ON i.fixed_version_id = v.id
WHERE v.name = :sprint_name    -- 如 'Sprint1'
ORDER BY i.status_id, i.id

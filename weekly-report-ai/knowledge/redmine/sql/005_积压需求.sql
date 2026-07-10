-- ==============================================================
-- Redmine 积压需求（长时间未更新）
-- 参数: stale_days（默认 14 天）
-- ==============================================================

SELECT i.id, i.subject, p.name as project, s.name as status,
       u.firstname || ' ' || u.lastname as assignee,
       i.created_on::date, i.updated_on::date as last_update,
       CURRENT_DATE - i.updated_on::date as days_stale
FROM issues i
LEFT JOIN projects p ON i.project_id = p.id
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN users u ON i.assigned_to_id = u.id
WHERE i.status_id IN (SELECT id FROM issue_statuses WHERE name IN ('新建','进行中'))
  AND i.updated_on::date < CURRENT_DATE - :stale_days
ORDER BY i.updated_on

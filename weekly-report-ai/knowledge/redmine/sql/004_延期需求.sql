-- ==============================================================
-- Redmine 延期需求清单
-- 到期日已过但未关闭的需求
-- ==============================================================

SELECT i.id, i.subject, p.name as project, s.name as status,
       u.firstname || ' ' || u.lastname as assignee,
       i.due_date, i.done_ratio as progress_pct,
       i.updated_on::date as last_update,
       CURRENT_DATE - i.due_date::date as days_overdue
FROM issues i
LEFT JOIN projects p ON i.project_id = p.id
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN users u ON i.assigned_to_id = u.id
WHERE i.due_date IS NOT NULL
  AND i.due_date < CURRENT_DATE
  AND i.status_id NOT IN (
      SELECT id FROM issue_statuses WHERE name IN ('已关闭','已解决','已拒绝')
  )
ORDER BY i.due_date

SELECT i.id, i.subject, p.name AS project, s.name AS status,
       u.firstname || '' '' || u.lastname AS assignee,
       i.due_date, i.done_ratio AS progress_pct,
       i.updated_on::date AS last_update,
       CURRENT_DATE - i.due_date::date AS days_overdue
FROM issues i
LEFT JOIN projects p ON i.project_id = p.id
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN users u ON i.assigned_to_id = u.id
WHERE i.due_date IS NOT NULL
  AND i.due_date < CURRENT_DATE
  AND COALESCE(s.is_closed, false) = false
ORDER BY i.due_date;

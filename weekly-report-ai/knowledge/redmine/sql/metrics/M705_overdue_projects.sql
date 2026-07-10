SELECT DISTINCT p.*
FROM projects p
JOIN issues i ON i.project_id = p.id
LEFT JOIN issue_statuses s ON i.status_id = s.id
WHERE i.due_date IS NOT NULL
  AND i.due_date < CURRENT_DATE
  AND COALESCE(s.is_closed, false) = false;

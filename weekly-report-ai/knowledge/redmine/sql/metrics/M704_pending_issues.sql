SELECT i.*
FROM issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
WHERE COALESCE(s.is_closed, false) = false;

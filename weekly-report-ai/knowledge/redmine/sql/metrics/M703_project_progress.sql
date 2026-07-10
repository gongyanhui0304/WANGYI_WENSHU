SELECT p.id AS project_id, p.name AS project_name,
       COUNT(i.id) AS issue_total,
       COUNT(i.id) FILTER (WHERE COALESCE(s.is_closed, false) = true) AS closed_total,
       COUNT(i.id) FILTER (WHERE COALESCE(s.is_closed, false) = false) AS open_total,
       COUNT(i.id) FILTER (WHERE i.updated_on::date BETWEEN :week_start AND :week_end) AS updated_this_week
FROM projects p
LEFT JOIN issues i ON i.project_id = p.id
LEFT JOIN issue_statuses s ON i.status_id = s.id
GROUP BY p.id, p.name
ORDER BY updated_this_week DESC, issue_total DESC;

SELECT DISTINCT p.*
FROM projects p
JOIN issues i ON i.project_id = p.id
WHERE i.updated_on::date BETWEEN :week_start AND :week_end;

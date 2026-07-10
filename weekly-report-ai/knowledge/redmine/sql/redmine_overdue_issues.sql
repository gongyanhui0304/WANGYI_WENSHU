-- ==============================================================
-- Redmine 延期/超期需求查询
-- 说明：查询截止日期已过但未关闭的需求
-- ==============================================================

SELECT
    i.id AS issue_id,
    i.subject AS issue_subject,
    i.due_date,
    i.created_on AS created_time,
    i.updated_on AS updated_time,
    i.done_ratio AS progress_percent,

    -- 延期天数
    CAST(julianday('now') - julianday(i.due_date) AS INTEGER) AS overdue_days,

    s.name AS status_name,
    p.name AS priority_name,
    pr.name AS project_name,

    u_assigned.login AS assigned_to_login,
    u_assigned.firstname || ' ' || u_assigned.lastname AS assigned_to_name

FROM issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN enumerations p ON i.priority_id = p.id AND p.type = 'IssuePriority'
LEFT JOIN projects pr ON i.project_id = pr.id
LEFT JOIN users u_assigned ON i.assigned_to_id = u_assigned.id

WHERE
    i.due_date IS NOT NULL
    AND i.due_date < date('now')
    AND s.is_closed = FALSE

ORDER BY overdue_days DESC, p.position ASC

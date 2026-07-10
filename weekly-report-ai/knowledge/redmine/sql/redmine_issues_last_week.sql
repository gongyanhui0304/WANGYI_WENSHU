-- ==============================================================
-- Redmine 需求情况 - 上周查询
-- 说明：查询上周的需求数据，用于周环比计算
-- ==============================================================

SELECT
    i.id AS issue_id,
    i.subject AS issue_subject,
    i.created_on AS created_time,
    i.closed_on AS closed_time,
    i.due_date AS due_date,

    s.name AS status_name,
    p.name AS priority_name,
    t.name AS tracker_name,
    pr.name AS project_name,
    pr.id AS project_id,

    u_assigned.login AS assigned_to_login,
    u_assigned.firstname || ' ' || u_assigned.lastname AS assigned_to_name,

    c.name AS category_name

FROM issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN enumerations p ON i.priority_id = p.id AND p.type = 'IssuePriority'
LEFT JOIN trackers t ON i.tracker_id = t.id
LEFT JOIN projects pr ON i.project_id = pr.id
LEFT JOIN users u_assigned ON i.assigned_to_id = u_assigned.id
LEFT JOIN issue_categories c ON i.category_id = c.id

WHERE
    (i.created_on >= :last_week_start AND i.created_on < :last_week_end)
    OR (i.updated_on >= :last_week_start AND i.updated_on < :last_week_end)

ORDER BY i.created_on DESC

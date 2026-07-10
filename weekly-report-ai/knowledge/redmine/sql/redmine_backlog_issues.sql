-- ==============================================================
-- Redmine 积压需求查询
-- 说明：查询状态为打开、处理中但长时间未更新的需求
--       可根据业务定义调整"积压"的时间阈值（如下面的 14 天）
-- ==============================================================

SELECT
    i.id AS issue_id,
    i.subject AS issue_subject,
    i.created_on AS created_time,
    i.updated_on AS updated_time,
    i.due_date,

    -- 自上次更新以来的天数
    CAST(julianday('now') - julianday(i.updated_on) AS INTEGER) AS days_since_update,
    -- 创建以来的天数
    CAST(julianday('now') - julianday(i.created_on) AS INTEGER) AS days_since_create,

    i.done_ratio AS progress_percent,
    i.estimated_hours,

    s.name AS status_name,
    p.name AS priority_name,
    t.name AS tracker_name,
    pr.name AS project_name,

    u_assigned.login AS assigned_to_login,
    u_assigned.firstname || ' ' || u_assigned.lastname AS assigned_to_name

FROM issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN enumerations p ON i.priority_id = p.id AND p.type = 'IssuePriority'
LEFT JOIN trackers t ON i.tracker_id = t.id
LEFT JOIN projects pr ON i.project_id = pr.id
LEFT JOIN users u_assigned ON i.assigned_to_id = u_assigned.id

WHERE
    s.is_closed = FALSE
    AND CAST(julianday('now') - julianday(i.updated_on) AS INTEGER) > :stale_days   -- 如 14

ORDER BY days_since_update DESC

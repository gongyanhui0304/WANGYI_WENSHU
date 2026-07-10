-- ==============================================================
-- Redmine 需求情况 - 本周查询
-- 说明：查询本周的需求创建、完成、状态分布
-- 请根据实际 Redmine PostgreSQL 表结构调整
-- ==============================================================

SELECT
    -- 需求基本信息
    i.id AS issue_id,
    i.subject AS issue_subject,
    i.description AS issue_description,
    i.created_on AS created_time,
    i.updated_on AS updated_time,
    i.closed_on AS closed_time,
    i.due_date AS due_date,
    i.start_date AS start_date,
    i.estimated_hours,
    i.done_ratio AS progress_percent,

    -- 状态
    s.name AS status_name,

    -- 优先级
    p.name AS priority_name,

    -- 跟踪类型（需求/缺陷/任务）
    t.name AS tracker_name,

    -- 项目
    pr.name AS project_name,
    pr.id AS project_id,

    -- 指派人
    u_assigned.login AS assigned_to_login,
    u_assigned.firstname || ' ' || u_assigned.lastname AS assigned_to_name,

    -- 作者
    u_author.login AS author_login,
    u_author.firstname || ' ' || u_author.lastname AS author_name,

    -- 分类/模块
    c.name AS category_name

FROM issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN enumerations p ON i.priority_id = p.id AND p.type = 'IssuePriority'
LEFT JOIN trackers t ON i.tracker_id = t.id
LEFT JOIN projects pr ON i.project_id = pr.id
LEFT JOIN users u_assigned ON i.assigned_to_id = u_assigned.id
LEFT JOIN users u_author ON i.author_id = u_author.id
LEFT JOIN issue_categories c ON i.category_id = c.id

WHERE
    -- 本周创建或更新的需求
    (i.created_on >= :week_start AND i.created_on < :week_end)
    OR (i.updated_on >= :week_start AND i.updated_on < :week_end)

ORDER BY i.created_on DESC

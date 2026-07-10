-- ==============================================================
-- Redmine 本周整体情况（新建/关闭/更新 + 各项目活跃度 + 待处理堆积）
-- ==============================================================

-- 本周范围
-- week_start = date_trunc('week', CURRENT_DATE)::date
-- week_end   = week_start + 6 days

-- 3a. 本周新建 vs 关闭
SELECT
    COUNT(*) FILTER (WHERE created_on::date BETWEEN :week_start AND :week_end) as new_this_week,
    COUNT(*) FILTER (WHERE closed_on::date BETWEEN :week_start AND :week_end) as closed_this_week,
    COUNT(*) FILTER (WHERE updated_on::date BETWEEN :week_start AND :week_end) as updated_this_week
FROM issues;

-- 3b. 各项目本周动态
SELECT p.name as project,
       COUNT(*) FILTER (WHERE i.created_on::date BETWEEN :week_start AND :week_end) as new_cnt,
       COUNT(*) FILTER (WHERE i.closed_on::date BETWEEN :week_start AND :week_end) as closed_cnt,
       COUNT(*) as total_active
FROM issues i
LEFT JOIN projects p ON i.project_id = p.id
WHERE i.updated_on::date BETWEEN :week_start AND :week_end
GROUP BY p.name
ORDER BY total_active DESC;

-- 3c. 待处理堆积 TOP N
SELECT p.name, COUNT(*) as open_cnt
FROM issues i LEFT JOIN projects p ON i.project_id = p.id
WHERE i.status_id IN (SELECT id FROM issue_statuses WHERE name IN ('新建','进行中'))
GROUP BY p.name ORDER BY open_cnt DESC;

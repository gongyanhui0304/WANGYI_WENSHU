-- ==============================================================
-- Redmine 各模块（跟踪类型）问题处理情况
-- 按 tracker 类型 + 状态 交叉统计
-- ==============================================================

SELECT t.name as tracker_type, s.name as status, COUNT(*) as cnt
FROM issues i
LEFT JOIN trackers t ON i.tracker_id = t.id
LEFT JOIN issue_statuses s ON i.status_id = s.id
GROUP BY t.name, s.name
ORDER BY t.name, s.name

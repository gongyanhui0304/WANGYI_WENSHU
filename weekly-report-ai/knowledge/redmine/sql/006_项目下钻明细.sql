-- ==============================================================
-- Redmine 单项目下钻明细
-- 当某个项目"慢"时，下钻看具体卡在哪
-- 参数: project_name（项目名称）
-- ==============================================================

-- 6a. 项目概况
SELECT COUNT(*) as total,
       COUNT(*) FILTER (WHERE s.name IN ('新建','进行中')) as open_cnt,
       COUNT(*) FILTER (WHERE s.name IN ('已解决','已关闭','已拒绝')) as closed_cnt
FROM issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN projects p ON i.project_id = p.id
WHERE p.name = :project_name;

-- 6b. 按负责人分布（谁手上最多）
SELECT u.firstname || ' ' || u.lastname as assignee,
       s.name as status, COUNT(*) as cnt
FROM issues i
LEFT JOIN users u ON i.assigned_to_id = u.id
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN projects p ON i.project_id = p.id
WHERE p.name = :project_name AND s.name IN ('新建','进行中')
GROUP BY u.firstname, u.lastname, s.name
ORDER BY cnt DESC;

-- 6c. 待处理需求明细（最久未更新的排前面）
SELECT i.id, i.subject, s.name as status,
       u.firstname || ' ' || u.lastname as assignee,
       pri.name as priority, i.done_ratio as progress,
       i.created_on::date, i.updated_on::date,
       CURRENT_DATE - i.updated_on::date as days_stale,
       i.due_date, CURRENT_DATE - i.due_date::date as days_overdue
FROM issues i
LEFT JOIN issue_statuses s ON i.status_id = s.id
LEFT JOIN users u ON i.assigned_to_id = u.id
LEFT JOIN enumerations pri ON i.priority_id = pri.id AND pri.type='IssuePriority'
LEFT JOIN projects p ON i.project_id = p.id
WHERE p.name = :project_name
  AND s.name IN ('新建','进行中')
ORDER BY i.updated_on

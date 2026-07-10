SELECT
  CASE WHEN COUNT(*) = 0 THEN 0
       ELSE ROUND((COUNT(*) FILTER (WHERE closed_on::date BETWEEN :week_start AND :week_end))::numeric / COUNT(*)::numeric, 4)
  END AS completion_rate
FROM issues
WHERE created_on::date <= :week_end;

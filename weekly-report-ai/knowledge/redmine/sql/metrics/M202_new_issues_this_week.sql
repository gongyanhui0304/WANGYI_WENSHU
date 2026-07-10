SELECT * FROM issues WHERE created_on::date BETWEEN :week_start AND :week_end;

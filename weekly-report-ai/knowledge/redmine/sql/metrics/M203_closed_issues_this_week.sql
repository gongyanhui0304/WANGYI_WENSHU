SELECT * FROM issues WHERE closed_on::date BETWEEN :week_start AND :week_end;

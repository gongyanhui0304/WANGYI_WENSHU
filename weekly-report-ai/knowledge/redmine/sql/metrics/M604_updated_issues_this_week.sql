SELECT * FROM issues WHERE updated_on::date BETWEEN :week_start AND :week_end;

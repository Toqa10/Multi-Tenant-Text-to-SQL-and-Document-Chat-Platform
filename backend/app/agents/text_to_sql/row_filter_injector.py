"""Row Filter Injector module."""

from __future__ import annotations

import sqlglot
import sqlglot.expressions as exp
from app.agents.text_to_sql.sql_validator import SQLValidator


class RowFilterInjector:
    """Injects mandatory row-level WHERE conditions into SQL AST."""

    @staticmethod
    def inject_row_filters(
        sql: str, row_filters: dict[str, str], dialect: str = "postgres"
    ) -> str:
        """
        Inject row filters per table into the SQL query.
        row_filters is a dict mapping table_name -> filter_expression (e.g. {"orders": "tenant_id = 't1'"}).
        """
        if not row_filters:
            return sql

        ast = SQLValidator.validate_sql(sql, dialect=dialect)

        # For every select statement in AST, append filter expressions to WHERE
        for select_stmt in ast.find_all(exp.Select):
            for table in select_stmt.find_all(exp.Table):
                table_name = table.name.lower()
                if table_name in row_filters:
                    filter_str = row_filters[table_name]
                    filter_ast = sqlglot.parse_one(filter_str, read=dialect)
                    if select_stmt.args.get("where"):
                        select_stmt.where(filter_ast, append=True)
                    else:
                        select_stmt.where(filter_ast)

        return ast.sql(dialect=dialect)

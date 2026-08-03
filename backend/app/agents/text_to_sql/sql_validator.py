"""SQLGlot-powered SQL Security Validator."""

from __future__ import annotations

import sqlglot
import sqlglot.expressions as exp
from app.core.exceptions import SQLSecurityError, SQLValidationError

FORBIDDEN_STATEMENTS = (
    exp.Drop,
    exp.Delete,
    exp.Update,
    exp.Alter,
    exp.Create,
    exp.Insert,
    exp.TruncateTable,
    exp.Command,
)

FORBIDDEN_FUNCTIONS = {
    "pg_read_file", "pg_read_binary_file", "xp_cmdshell", "load_file",
    "openrowset", "opendatasource", "exec", "eval", "system"
}

FORBIDDEN_SCHEMAS = {
    "pg_catalog", "information_schema", "sys", "mysql", "performance_schema"
}


class SQLValidator:
    """Strict security validator enforcing read-only SELECT queries with zero administrative side-effects."""

    @staticmethod
    def validate_sql(sql: str, dialect: str = "postgres") -> exp.Expression:
        """
        Validate raw SQL string against strict security policies.
        Returns parsed SQLGlot AST if safe.
        Raises SQLSecurityError or SQLValidationError if unsafe.
        """
        clean_sql = sql.strip()

        # Reject SQL comments
        if "--" in clean_sql or "/*" in clean_sql:
            raise SQLSecurityError(message="SQL comments are strictly forbidden.")

        # Reject multiple statements
        if clean_sql.count(";") > 1 or (clean_sql.endswith(";") and ";" in clean_sql[:-1]):
            raise SQLSecurityError(message="Multiple SQL statements are not permitted.")

        # Parse AST using SQLGlot
        try:
            parsed_list = sqlglot.parse(clean_sql, read=dialect)
        except Exception as exc:
            raise SQLValidationError(message=f"Failed to parse SQL query: {exc}") from exc

        if not parsed_list or len(parsed_list) != 1:
            raise SQLSecurityError(message="Expected exactly one SQL statement.")

        expression = parsed_list[0]
        if expression is None:
            raise SQLValidationError(message="Empty SQL statement.")

        # Must be a SELECT or Union of SELECTs
        if not isinstance(expression, (exp.Select, exp.Union)):
            raise SQLSecurityError(
                message=f"Forbidden statement type: {expression.key.upper()}. Only SELECT is allowed."
            )

        # Check for forbidden statement types in AST
        for node in expression.walk():
            if isinstance(node, FORBIDDEN_STATEMENTS):
                raise SQLSecurityError(message=f"Forbidden operation detected: {node.key.upper()}.")

            # Check forbidden functions
            if isinstance(node, exp.Func):
                func_name = node.name.lower() if hasattr(node, "name") else ""
                if func_name in FORBIDDEN_FUNCTIONS:
                    raise SQLSecurityError(message=f"Forbidden function call: {func_name}.")

            # Check forbidden schemas
            if isinstance(node, exp.Table):
                schema_name = node.db.lower() if node.db else ""
                if schema_name in FORBIDDEN_SCHEMAS:
                    raise SQLSecurityError(message=f"Access to administrative schema '{schema_name}' is blocked.")

        return expression

"""Unit tests for SQLGlot Security Validator."""

from __future__ import annotations

import pytest
from app.agents.text_to_sql.sql_validator import SQLValidator
from app.core.exceptions import SQLSecurityError, SQLValidationError


def test_valid_select_query():
    """Verify clean SELECT statements pass validation."""
    sql = "SELECT id, name, email FROM users WHERE is_active = true"
    ast = SQLValidator.validate_sql(sql)
    assert ast is not None


def test_reject_drop_table():
    """Verify DROP TABLE is rejected."""
    sql = "DROP TABLE users;"
    with pytest.raises(SQLSecurityError):
        SQLValidator.validate_sql(sql)


def test_reject_delete():
    """Verify DELETE is rejected."""
    sql = "DELETE FROM orders WHERE id = 1"
    with pytest.raises(SQLSecurityError):
        SQLValidator.validate_sql(sql)


def test_reject_sql_comment():
    """Verify comments (-- and /* */) are rejected."""
    sql = "SELECT * FROM users -- inline comment"
    with pytest.raises(SQLSecurityError):
        SQLValidator.validate_sql(sql)


def test_reject_admin_schema():
    """Verify access to pg_catalog is rejected."""
    sql = "SELECT * FROM pg_catalog.pg_tables"
    with pytest.raises(SQLSecurityError):
        SQLValidator.validate_sql(sql)

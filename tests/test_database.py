import pytest

from database import Database


class FakeCursor:
    def __init__(self, pool):
        self.pool = pool
        self.description = None
        self.rowcount = 0
        self.closed = False
        self.params = None

    def execute(self, query, params=()):
        self.pool.statements.append(str(query))
        self.params = params
        self.pool.last_params = params
        if str(query).lstrip().upper().startswith('SELECT'):
            self.description = (object(),)
            self.rowcount = 1

    def executemany(self, query, params):
        self.pool.statements.append(str(query))

    def fetchone(self):
        if self.pool.fetchone_rows:
            return self.pool.fetchone_rows.pop(0)
        return None

    def fetchall(self):
        return self.pool.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, pool):
        self.pool = pool
        self.closed = 0
        self.autocommit = False
        self.commits = 0
        self.rollbacks = 0
        self.cursors = []

    def cursor(self):
        cursor = FakeCursor(self.pool)
        self.cursors.append(cursor)
        return cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakePool:
    def __init__(self):
        self.statements = []
        self.last_params = None
        self.rows = [{'id': 42}]
        self.fetchone_rows = []
        self.connection = FakeConnection(self)
        self.returned = []

    def getconn(self):
        return self.connection

    def putconn(self, connection, close=False):
        self.returned.append((connection, close))

    def closeall(self):
        pass


def make_database():
    db = Database.__new__(Database)
    db._pool = FakePool()
    return db


def test_execute_buffers_rows_and_closes_cursor_before_pool_return():
    db = make_database()

    result = db.execute('SELECT id FROM products WHERE id = %s', (42,))

    assert result.fetchone() == {'id': 42}
    assert result.fetchone() is None
    assert db._pool.connection.commits == 1
    assert db._pool.connection.cursors[0].closed
    assert db._pool.returned == [(db._pool.connection, False)]


def test_connection_rolls_back_and_returns_connection_after_failure():
    db = make_database()

    with pytest.raises(RuntimeError, match='query failed'):
        with db.get_connection() as connection:
            connection.cursor()
            raise RuntimeError('query failed')

    assert db._pool.connection.rollbacks == 1
    assert db._pool.connection.commits == 0
    assert db._pool.connection.cursors[0].closed
    assert db._pool.returned == [(db._pool.connection, False)]


def test_schema_uses_postgresql_types_and_native_sql():
    db = make_database()
    db.init_database()
    sql = '\n'.join(db._pool.statements).upper()

    assert 'ID SERIAL PRIMARY KEY' in sql
    assert 'USER_ID BIGINT' in sql
    assert 'PRICE NUMERIC(12,2)' in sql
    assert 'IMAGES JSONB' in sql
    assert "STATUS TEXT DEFAULT 'IN STOCK'" in sql
    assert "STATUS TEXT DEFAULT 'PENDING'" in sql
    assert 'AUTOINCREMENT' not in sql
    assert 'INSERT OR REPLACE' not in sql
    assert 'GROUP_CONCAT' not in sql
    assert '?' not in sql


def test_payment_status_default_migration_runs_after_type_migration():
    db = make_database()
    cursor = db._pool.connection.cursor()
    db._pool.fetchone_rows = [(1,), None]

    db._migrate_postgres_schema(cursor)

    statements = '\n'.join(db._pool.statements).upper()
    assert "ALTER TABLE PAYMENTS ALTER COLUMN STATUS SET DEFAULT 'PENDING'" in statements
    assert db._pool.statements[-1] == "INSERT INTO schema_migrations (version) VALUES (%s)"


@pytest.mark.parametrize(
    ('status', 'expected_statuses'),
    [
        ('Pending', ['pending']),
        ('pending', ['pending']),
        ('Completed', ['completed', 'delivered']),
    ],
)
def test_admin_order_query_filters_status_case_insensitively(status, expected_statuses):
    db = make_database()
    db._pool.rows = [{'id': 42, 'status': status, 'items': []}]

    orders = db.get_orders_by_status(status)

    sql = '\n'.join(db._pool.statements).lower()
    assert 'lower(btrim(o.status)) = any(%s)' in sql
    assert db._pool.last_params == (expected_statuses, 50)
    assert orders[0]['id'] == 42


def test_admin_order_query_all_statuses_includes_customer_and_items():
    db = make_database()
    db._pool.rows = []

    assert db.get_orders_by_status() == []

    sql = '\n'.join(db._pool.statements).lower()
    assert 'left join users u on u.user_id = o.user_id' in sql
    assert 'jsonb_agg' in sql
    assert 'order_status' not in sql
    assert db._pool.last_params == (50,)
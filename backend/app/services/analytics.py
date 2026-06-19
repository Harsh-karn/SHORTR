from clickhouse_driver import Client
import os

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "default")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

kwargs = {
    "host": CLICKHOUSE_HOST, 
    "port": CLICKHOUSE_PORT,
    "database": CLICKHOUSE_DB,
    "user": CLICKHOUSE_USER,
}
if CLICKHOUSE_PASSWORD:
    kwargs["password"] = CLICKHOUSE_PASSWORD

clickhouse_client = Client(**kwargs)

def init_clickhouse():
    try:
        # Create the table if it doesn't exist
        clickhouse_client.execute('''
            CREATE TABLE IF NOT EXISTS click_events (
                event_id UUID,
                link_id UUID,
                user_id UUID,
                slug String,
                clicked_at DateTime,
                ip_hash String,
                country String,
                region String,
                city String,
                device_type String,
                os String,
                browser String,
                referrer String,
                user_agent String
            ) ENGINE = MergeTree()
            ORDER BY (link_id, clicked_at)
            PARTITION BY toYYYYMM(clicked_at)
        ''')
        print("ClickHouse initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize ClickHouse: {e}")

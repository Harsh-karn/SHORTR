from datetime import datetime
import hashlib
import uuid
from app.workers.celery_app import celery_app
from app.services.analytics import clickhouse_client

# TODO: integrate with MaxMind GeoIP for real country/city parsing
def resolve_geoip(ip: str):
    # Mocking for now
    class Geo:
        country = "Unknown"
        city = "Unknown"
        region = "Unknown"
    return Geo()

# TODO: integrate user_agent parsing
def parse_user_agent(ua: str):
    class Device:
        type = "desktop"
        os = "Unknown"
        browser = "Unknown"
    return Device()

@celery_app.task(name="app.workers.tasks.record_click")
def record_click(link_id: str, slug: str, user_id: str, request_metadata: dict):
    ip = request_metadata.get("ip", "0.0.0.0")
    geo = resolve_geoip(ip)
    device = parse_user_agent(request_metadata.get("user_agent", ""))
    
    clickhouse_client.execute(
        "INSERT INTO click_events VALUES",
        [{
            "event_id": uuid.uuid4(),
            "link_id": uuid.UUID(link_id),
            "user_id": uuid.UUID(user_id) if user_id else uuid.UUID(int=0), # UUID required
            "slug": slug,
            "clicked_at": datetime.utcnow(),
            "ip_hash": hashlib.sha256(ip.encode('utf-8')).hexdigest(),
            "country": geo.country,
            "region": geo.region,
            "city": geo.city,
            "device_type": device.type,
            "os": device.os,
            "browser": device.browser,
            "referrer": request_metadata.get("referrer", ""),
            "user_agent": request_metadata.get("user_agent", "")
        }]
    )

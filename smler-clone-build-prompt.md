# Build Prompt: URL Shortener SaaS Platform (like app.smler.io)

## Overview

Build a production-grade, monetizable URL shortener SaaS platform with deep linking, analytics, custom domains, bulk shortening, QR code generation, and a public REST API. The platform targets developers, marketers, and businesses who need intelligent link management at scale.

The reference product is **app.smler.io** — a professional URL shortener with TRAI compliance, deep link support, and enterprise analytics. Build a functionally equivalent platform that can be deployed independently and monetized via tiered subscriptions.

---

## Tech Stack

### Frontend
- **Framework**: Next.js 14 (App Router) with TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **Auth**: Clerk (or NextAuth v5 with credentials + OAuth)
- **State**: Zustand for client state; React Query (TanStack) for server state
- **Charts**: Recharts for analytics dashboards
- **Animations**: Framer Motion for micro-interactions

### Backend
- **API Server**: FastAPI (Python 3.11+)
- **Task Queue**: Celery + Redis (bulk jobs, async analytics writes)
- **Cache**: Redis (slug → URL lookups, rate limiting)
- **Primary DB**: PostgreSQL (via SQLAlchemy + Alembic migrations)
- **Analytics DB**: ClickHouse (high-write time-series click events)
- **Object Storage**: Cloudflare R2 or AWS S3 (QR code images, CSV exports)

### Infrastructure
- **DNS + CDN**: Cloudflare (wildcard DNS for custom domains, edge caching)
- **Frontend Deploy**: Vercel
- **Backend Deploy**: Railway or a VPS (Ubuntu) with Docker Compose
- **Payments**: Razorpay (India-first) with webhook handling
- **Email**: Resend (transactional emails)
- **GeoIP**: MaxMind GeoLite2 or ip-api.com for click location data

---

## Project Structure

```
/
├── frontend/                  # Next.js 14 app
│   ├── app/
│   │   ├── (marketing)/       # Landing page, pricing, blog, docs
│   │   ├── (dashboard)/       # Authenticated app shell
│   │   │   ├── links/         # Link list, create, edit
│   │   │   ├── analytics/     # Click analytics per link
│   │   │   ├── domains/       # Custom domain management
│   │   │   ├── qr/            # QR code generation
│   │   │   ├── bulk/          # Bulk shortening UI
│   │   │   ├── api-keys/      # API key management
│   │   │   └── billing/       # Plan + payment management
│   │   └── api/               # Next.js API routes (auth callbacks, webhooks)
│   ├── components/
│   └── lib/
│
├── backend/                   # FastAPI app
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── redirect.py    # Core redirect engine (most critical)
│   │   │   ├── links.py       # CRUD for links
│   │   │   ├── analytics.py   # Analytics query endpoints
│   │   │   ├── domains.py     # Custom domain management
│   │   │   ├── bulk.py        # Bulk shortening jobs
│   │   │   ├── qr.py          # QR code generation
│   │   │   └── api_keys.py    # API key issuance + validation
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/
│   │   │   ├── slug.py        # Slug generation (nanoid)
│   │   │   ├── cache.py       # Redis operations
│   │   │   ├── analytics.py   # ClickHouse write/read
│   │   │   ├── geoip.py       # IP → location resolution
│   │   │   └── deeplink.py    # Deep link + AASA/assetlinks logic
│   │   ├── workers/           # Celery tasks
│   │   └── middleware/
│   │       ├── rate_limit.py
│   │       └── domain.py      # Custom domain resolution middleware
│   └── alembic/               # DB migrations
│
└── docker-compose.yml
```

---

## Database Schema

### PostgreSQL Tables

```sql
-- Users (managed by Clerk, mirrored here for relational integrity)
users (
  id UUID PRIMARY KEY,
  clerk_id TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL,
  plan TEXT DEFAULT 'free',       -- free | pro | business
  api_calls_today INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- Short links
links (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  slug TEXT UNIQUE NOT NULL,             -- e.g. "abc123"
  destination_url TEXT NOT NULL,
  title TEXT,
  domain_id UUID REFERENCES domains(id), -- NULL = default domain
  is_active BOOLEAN DEFAULT TRUE,
  has_analytics BOOLEAN DEFAULT FALSE,
  expires_at TIMESTAMPTZ,
  password_hash TEXT,                    -- optional password protection
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
)

-- Custom domains
domains (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  domain TEXT UNIQUE NOT NULL,           -- e.g. "go.mybrand.com"
  is_verified BOOLEAN DEFAULT FALSE,
  verification_token TEXT,
  ssl_provisioned BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- API keys
api_keys (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  key_hash TEXT UNIQUE NOT NULL,         -- store hash, not raw key
  name TEXT,
  last_used_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- Bulk jobs
bulk_jobs (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  status TEXT DEFAULT 'pending',         -- pending | processing | done | failed
  total_rows INT,
  processed_rows INT DEFAULT 0,
  result_file_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- Deep link configurations
deep_links (
  id UUID PRIMARY KEY,
  link_id UUID REFERENCES links(id),
  ios_scheme TEXT,                       -- e.g. "myapp://"
  ios_app_store_url TEXT,
  android_scheme TEXT,
  android_package TEXT,
  android_play_store_url TEXT,
  fallback_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- Subscription plans
subscriptions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  razorpay_subscription_id TEXT,
  plan TEXT NOT NULL,
  status TEXT,                           -- active | cancelled | past_due
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
)
```

### ClickHouse Table (Analytics)

```sql
CREATE TABLE click_events (
  event_id UUID,
  link_id UUID,
  user_id UUID,
  slug String,
  clicked_at DateTime,
  ip_hash String,                        -- hashed for privacy
  country String,
  region String,
  city String,
  device_type String,                    -- mobile | desktop | tablet
  os String,
  browser String,
  referrer String,
  user_agent String
) ENGINE = MergeTree()
ORDER BY (link_id, clicked_at)
PARTITION BY toYYYYMM(clicked_at);
```

---

## Feature Implementation Details

### 1. Core Redirect Engine (`/routers/redirect.py`)

This is the most performance-critical component. Every millisecond matters.

```
GET /{slug}  →  resolve to destination  →  302 redirect
```

**Logic:**
1. Extract slug from path (or subdomain for custom domains)
2. Check Redis cache: `GET link:{slug}` → returns JSON with destination + metadata
3. On cache miss: query PostgreSQL, warm Redis cache with 24h TTL
4. Check if link is active, not expired, not password-protected
5. If `has_analytics=True`: push click event to Celery queue (non-blocking)
6. Return `302 Found` with `Location` header

**Redis key structure:**
```
link:{slug}          → { destination, is_active, has_analytics, link_id, deep_link_config }
domain:{hostname}    → { user_id, domain_id }
ratelimit:{api_key}  → counter with TTL
```

**Deep link redirect flow:**
1. Parse `User-Agent` header to detect iOS / Android / desktop
2. On iOS: redirect to `ios_scheme://` or App Store URL
3. On Android: redirect to `android_scheme://` or Play Store URL
4. On desktop: redirect to `fallback_url` or `destination_url`
5. Serve an intermediate HTML page with `<meta>` deep link tags for App Links / Universal Links

### 2. Slug Generation (`/services/slug.py`)

```python
import nanoid

def generate_slug(length: int = 7) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return nanoid.generate(alphabet, length)

def generate_unique_slug(db, redis, length=7) -> str:
    for _ in range(10):
        slug = generate_slug(length)
        if not redis.exists(f"link:{slug}") and not db.query(Link).filter_by(slug=slug).first():
            return slug
    return generate_slug(length + 1)  # fallback to longer slug
```

Custom alias: validate regex `^[a-zA-Z0-9_-]{3,50}$`, check uniqueness, reserve system slugs (api, docs, dashboard, etc.).

### 3. Analytics Pipeline

**Write path (async via Celery):**
```python
@celery_app.task
def record_click(link_id, slug, user_id, request_metadata):
    ip = request_metadata["ip"]
    geo = resolve_geoip(ip)            # MaxMind lookup
    device = parse_user_agent(request_metadata["user_agent"])
    
    clickhouse_client.execute(
        "INSERT INTO click_events VALUES",
        [{
            "event_id": uuid4(),
            "link_id": link_id,
            "slug": slug,
            "clicked_at": datetime.utcnow(),
            "ip_hash": sha256(ip).hexdigest(),
            "country": geo.country,
            "city": geo.city,
            "device_type": device.type,
            "os": device.os,
            "browser": device.browser,
            "referrer": request_metadata.get("referrer", "")
        }]
    )
```

**Read path (analytics dashboard API):**
```
GET /analytics/{link_id}?period=7d
→ total clicks, unique clicks, clicks by country, by device, by day
```

Query ClickHouse with `GROUP BY` on `clicked_at`, `country`, `device_type`.

### 4. Custom Domains

**Setup flow:**
1. User adds domain (e.g. `go.mybrand.com`) in dashboard
2. System generates a DNS verification token (TXT record)
3. User adds TXT record `_smler-verify.go.mybrand.com → {token}` at their DNS provider
4. Background Celery task polls DNS every 5 min to confirm TXT record
5. Once verified, user adds CNAME `go.mybrand.com → redirect.yourplatform.com`
6. Cloudflare handles SSL via full proxy mode

**Routing in FastAPI:**
```python
@app.middleware("http")
async def domain_routing_middleware(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0]
    if host != "yourplatform.com":
        # Custom domain — resolve to user context
        domain_config = await redis.get(f"domain:{host}")
        if domain_config:
            request.state.domain_config = json.loads(domain_config)
    return await call_next(request)
```

### 5. QR Code Generation (`/routers/qr.py`)

```python
import qrcode
from qrcode.image.styledpil import StyledPilImage
from io import BytesIO

def generate_qr(url: str, color: str = "#000000", bg: str = "#ffffff") -> bytes:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=color, back_color=bg)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
```

Endpoint: `POST /qr/generate` → returns PNG image or uploads to R2 and returns CDN URL.
Support formats: PNG, SVG, PDF. Support logo overlay for branded QR codes.

### 6. Bulk Shortening (`/routers/bulk.py`)

**Flow:**
1. `POST /bulk/upload` → accept CSV/XLSX (columns: `long_url`, `custom_alias`, `title`)
2. Validate file, create `bulk_job` record, push to Celery
3. Celery worker processes rows in batches of 100, creates links, updates `processed_rows`
4. On completion, generate result CSV, upload to R2, update `result_file_url`
5. Frontend polls `GET /bulk/jobs/{job_id}` for status + progress
6. User downloads result CSV with added `short_url` column

### 7. API Key System

- Generate: `POST /api-keys` → returns raw key once (store hash in DB)
- Validate: middleware extracts `Authorization: Bearer {key}`, SHA-256 hashes it, looks up in Redis
- Rate limit: plan-based limits enforced via `slowapi` + Redis counters
- Scopes: read (analytics only) vs write (create/manage links) vs admin

### 8. Deep Link Serving (AASA + assetlinks.json)

For Universal Links (iOS), your redirect domain must serve:
```
GET /.well-known/apple-app-site-association
Content-Type: application/json (no .json extension)
```

For App Links (Android):
```
GET /.well-known/assetlinks.json
```

Store these configs per domain in PostgreSQL. Serve dynamically via FastAPI based on `Host` header. Cache aggressively — Apple and Google crawl these on app install.

---

## Frontend Pages

### Marketing (`/`)
- Hero with live demo (shorten a URL without signup)
- Feature cards: deep links, analytics, custom domains, bulk, API, QR
- Pricing table (Free / Pro / Business)
- Trusted companies logo strip
- Blog section

### Dashboard (`/dashboard`)
- **Links**: searchable table with slug, destination, clicks, status, actions (copy, QR, analytics, edit, delete)
- **Create Link**: drawer/modal with fields: destination URL, custom alias, title, expiry, password, deep link config, analytics toggle
- **Analytics**: per-link dashboard — total clicks graph (7d/30d/90d), top countries (map), device breakdown (donut chart), top referrers (table), hourly heatmap
- **Custom Domains**: add domain → DNS instructions → verification status → active domains list
- **QR Generator**: pick link → customize color, size, logo → preview → download PNG/SVG
- **Bulk**: drag-and-drop CSV upload → progress bar → download results
- **API Keys**: generate key (shown once) → list active keys → revoke
- **Billing**: current plan → usage meters → upgrade CTA → Razorpay checkout

---

## API Design (Public REST API)

Base URL: `https://api.yourplatform.com/v1`

```
POST   /links                    Create short link
GET    /links                    List user's links (paginated)
GET    /links/{id}               Get link details
PATCH  /links/{id}               Update link
DELETE /links/{id}               Delete link

GET    /links/{id}/analytics     Get click analytics
GET    /links/{id}/qr            Generate QR code

POST   /bulk                     Create bulk shortening job
GET    /bulk/{job_id}            Get job status + download URL

GET    /domains                  List custom domains
POST   /domains                  Add custom domain
DELETE /domains/{id}             Remove domain
```

All endpoints require `Authorization: Bearer {api_key}` header.
Return standard JSON: `{ success: bool, data: {}, error: string | null }`.
Rate limits in response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

---

## Subscription Plans & Limits

| Limit | Free | Pro | Business |
|---|---|---|---|
| Links | 100 | Unlimited | Unlimited |
| Clicks/month tracked | 10,000 | 500,000 | Unlimited |
| Custom domains | 0 | 1 | 5 |
| Bulk rows/job | 0 | 1,000 | 10,000 |
| API calls/day | 0 | 5,000 | 50,000 |
| Team seats | 1 | 1 | 5 |
| Analytics retention | 30 days | 1 year | Forever |
| QR code downloads | 5/day | Unlimited | Unlimited |
| Deep linking | No | Yes | Yes |

Enforce limits in FastAPI middleware: check `user.plan` + Redis counters on each request.

---

## Razorpay Integration

1. Create plans in Razorpay dashboard (monthly/annual per tier)
2. `POST /billing/subscribe` → create Razorpay subscription → return checkout URL
3. Webhook `POST /webhooks/razorpay` → handle `subscription.activated`, `subscription.charged`, `subscription.cancelled`
4. On activation: update `users.plan` and create `subscriptions` record
5. On cancellation: downgrade plan at period end (don't cut off immediately)
6. Send Resend emails on: signup, plan upgrade, invoice, cancellation

---

## Performance Targets

| Metric | Target |
|---|---|
| Redirect latency (cache hit) | < 10ms |
| Redirect latency (cache miss) | < 80ms |
| API response time (p95) | < 200ms |
| Analytics query (7 days) | < 500ms |
| Bulk job (1000 rows) | < 30 seconds |
| Uptime | 99.9% |

**Achieving this:**
- Redis for all redirect lookups (never hit Postgres on the hot path)
- Cloudflare cache for static assets + edge redirect rules
- ClickHouse columnar storage for fast analytics aggregation
- Async click recording (never block the redirect on DB write)
- Connection pooling via `asyncpg` for Postgres, `aioredis` for Redis

---

## Security Checklist

- [ ] API keys stored as SHA-256 hashes only (never raw)
- [ ] User IP hashed before storing in ClickHouse (GDPR)
- [ ] Rate limiting on all public endpoints (slowapi)
- [ ] Input validation on all URLs (reject `javascript:`, `data:`, local IPs)
- [ ] SSRF protection: block redirects to private IP ranges (10.x, 192.168.x, 127.x)
- [ ] Slug collision detection with retry logic
- [ ] CSRF protection on dashboard API routes
- [ ] Custom domain ownership verification before activation
- [ ] Password-protected links use bcrypt hashing
- [ ] Webhook signatures verified (Razorpay HMAC)

---

## Docker Compose (Local Dev)

```yaml
version: "3.9"
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://user:pass@db:5432/urlshortener
      REDIS_URL: redis://redis:6379
      CLICKHOUSE_HOST: clickhouse
    depends_on: [db, redis, clickhouse]

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker --loglevel=info
    depends_on: [redis]

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: urlshortener
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    volumes: [redisdata:/data]

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports: ["8123:8123", "9000:9000"]
    volumes: [chdata:/var/lib/clickhouse]

volumes:
  pgdata:
  redisdata:
  chdata:
```

---

## Build Order (Ship in This Sequence)

1. **Week 1–2**: Redirect engine + slug generation + Redis caching. This is the core. Get it fast first.
2. **Week 3**: Auth (Clerk) + PostgreSQL schema + basic link CRUD API
3. **Week 4**: Next.js dashboard — link list, create link, copy short URL
4. **Week 5**: Analytics pipeline — ClickHouse setup + Celery click recording + dashboard charts
5. **Week 6**: QR code generation + custom domain setup flow
6. **Week 7**: Deep linking — AASA/assetlinks serving + user-agent routing
7. **Week 8**: Bulk shortening — CSV upload + Celery job + progress polling
8. **Week 9**: Public API + API key system + rate limiting
9. **Week 10**: Razorpay billing + plan enforcement + usage meters
10. **Week 11**: Landing page + pricing page + docs
11. **Week 12**: Security audit, load testing, production deploy

---

## Environment Variables

```env
# Backend
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
CLICKHOUSE_HOST=...
CLICKHOUSE_DB=analytics
SECRET_KEY=...                         # JWT signing
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
RESEND_API_KEY=...
MAXMIND_DB_PATH=./GeoLite2-City.mmdb
R2_BUCKET=...
R2_ACCESS_KEY=...
R2_SECRET_KEY=...
R2_ENDPOINT=...

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourplatform.com
NEXT_PUBLIC_DEFAULT_DOMAIN=yourplatform.com
NEXT_PUBLIC_RAZORPAY_KEY_ID=...
CLERK_SECRET_KEY=...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...
```

---

## Key Decisions & Rationale

| Decision | Rationale |
|---|---|
| Redis for redirect cache | Slug lookups must be O(1) at < 10ms — Redis is non-negotiable |
| ClickHouse for analytics | Postgres can't handle billions of click rows efficiently; ClickHouse is purpose-built for this |
| Celery for async tasks | Redirect must never wait on DB writes — decouple with a queue |
| Cloudflare for custom domains | Wildcard SSL + DNS proxying handled out-of-the-box |
| nanoid for slugs | URL-safe, shorter than UUID, collision-resistant at scale |
| Razorpay over Stripe | Indian GST billing, UPI support, better INR experience |
| Clerk for auth | Handles email, Google, GitHub OAuth + session management with minimal code |

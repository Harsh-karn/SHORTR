<div align="center">
  <img src="https://raw.githubusercontent.com/Harsh-karn/SHORTR/main/frontend/public/next.svg" width="120" alt="SHORTR Logo" />
  <h1 align="center">SHORTR ⚡</h1>
  <p align="center">
    <strong>A high-performance, developer-first URL shortener SaaS platform.</strong>
  </p>
  <p align="center">
    Built for speed and massive scale using Next.js, FastAPI, PostgreSQL, Redis, and ClickHouse.
  </p>
  <br />
</div>

## ✨ Features

- **🚀 Lightning Fast Redirects**: Redis edge caching guarantees sub-millisecond redirect lookups.
- **📊 Real-time Analytics**: Billions of events ingested seamlessly using ClickHouse for unparalleled analytical performance.
- **🔐 Developer API Keys**: Robust programmatic access via secure, hashed API keys managed right from your dashboard.
- **🛡️ Secure Authentication**: Modern and seamless user sign-ups/sign-ins powered by Clerk.
- **💅 Beautiful UI**: A highly polished, accessible dashboard built with Next.js 14 App Router, Tailwind CSS, and shadcn/ui.

---

## 🏗️ Architecture

SHORTR is separated into a modern frontend app and a high-performance backend, orchestrated by Docker.

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS & shadcn/ui
- **Authentication**: Clerk `@clerk/nextjs`
- **Data Fetching**: Native `fetch` with React hooks

### Backend
- **API**: FastAPI (Python)
- **Relational Data**: PostgreSQL + SQLAlchemy + Alembic (Links, Users, API Keys)
- **Caching & Rate Limiting**: Redis
- **Analytics Engine**: ClickHouse (High-throughput click event ingestion)
- **Containerization**: Docker Compose

---

## 🚦 Workflows & Usage

### 1. Link Management
1. Authenticate securely via **Clerk** on the frontend dashboard.
2. Generate shortened URLs customized with aliases or domains.
3. Share your `sho.rt/your-alias` links anywhere. 
4. Every time a link is visited, a background task asynchronously logs the event to **ClickHouse** without blocking the redirect.

### 2. API Key Generation
1. Navigate to the **API Keys** section in your dashboard.
2. Create a new key with a custom name.
3. Securely copy the raw key (shown only once). The backend hashes this key via `SHA-256` before storing it in **PostgreSQL**.
4. Use this key as a `Bearer` token to programmatically create and manage links from your own scripts or applications!

### 3. Developer Authentication Flow
The FastAPI backend uses dual-authentication middleware. Requests to `/v1/*` are authorized by checking for either:
- A valid **Clerk JWT Token** (Dashboard UI)
- A valid **Hashed API Key** (Programmatic access)

---

## 💻 Getting Started Locally

### Prerequisites
- Node.js 18+
- Python 3.10+
- Docker & Docker Compose
- A [Clerk](https://clerk.com) account

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/Harsh-karn/SHORTR.git
   cd SHORTR
   ```

2. **Start the Backend Services**
   The backend environment runs entirely in Docker.
   ```bash
   docker-compose up -d --build
   ```

3. **Configure Frontend Environment**
   Navigate to the `frontend` directory and create a `.env.local` file:
   ```bash
   cd frontend
   ```
   Add your Clerk keys to `.env.local`:
   ```env
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   CLERK_SECRET_KEY=sk_test_...
   ```

4. **Install Frontend Dependencies & Run**
   ```bash
   npm install
   npm run dev
   ```

5. **Visit the app**
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request and make this app more useful.

<div align="center">
  <br />
  <p>Built with ❤️ by Harsh-Karn </p>
</div>

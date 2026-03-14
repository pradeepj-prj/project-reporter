# Component Inventory

The table below provides a detailed inventory of each deployable component, including the framework, database dependency, deployment target, and default port.

| Component | Repository | Language | Framework | Database | Deploy Target | Default Port |
|:----------|:-----------|:---------|:----------|:---------|:--------------|:-------------|
| HR Data Generator | HR-Data-Generator | Python 3.10 | -- (library) | -- | `pip install` | -- |
| TM Skills API | talent-management-app | Python 3.10 | FastAPI + uvicorn | PostgreSQL (asyncpg) | CF on BTP ap10 | 8000 |
| TM MCP Server | tm-mcp-server | Python 3.10 | FastMCP + uvicorn | SQLite WAL (audit.db) | CF on BTP ap10 | 8080 |
| HR Dashboard | hr-data-dashboard | Python 3.10 | Streamlit | In-memory (pandas) | Local | 8501 |
| MCP Audit Dashboard | mcp-audit-dashboard | TypeScript 5.9 | React 19 + Vite 7.3 | -- (REST consumer) | Local / static host | 5173 |

**Notes on the inventory:**

- The HR Data Generator is not a running service. It is a pip-installable Python library that produces pandas DataFrames. Other components either import it directly (the HR Dashboard) or consume its output after it has been loaded into PostgreSQL.
- The TM Skills API and TM MCP Server are deployed as **separate Cloud Foundry applications**, each with their own `manifest.yml`. They share no runtime resources. The MCP server calls the API over HTTPS using the CF-assigned route.
- On Cloud Foundry, the `PORT` environment variable is injected by the platform and overrides the default. Both applications bind to `0.0.0.0:$PORT` in production.
- The MCP Audit Dashboard is a static SPA. In production, it can be served from any static host (S3, Vercel, CF static buildpack). During development and demos, `npm run dev` serves it on `localhost:5173`.

---

Back to [Architecture Overview](index.md).

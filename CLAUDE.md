# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Recipe Vault** is a Python FastAPI backend for an AI-powered recipe management and discovery application. It is a RAG (Retrieval-Augmented Generation) system combining hybrid search (keyword + semantic vector) with Claude-powered chat agents.

## Commands

All commands run from `backend/`:

```bash
# Run dev server
uvicorn app.main:app --reload

# Run full local stack (Postgres + Qdrant + API)
docker-compose up

# Run tests
pytest tests/unit/                    # unit tests (no DB required)
pytest tests/integration/             # integration tests (requires test DB)
python tests/eval/run_eval.py         # recall@k / MRR evaluation

# Run a single test
pytest tests/unit/test_hybrid_search.py::test_rrf_fusion -v

# Lint / format
ruff check .
ruff format .

# Database migrations
alembic upgrade head

# Reindex vectors (after embedding model change, etc.)
python scripts/reindex_qdrant.py
```

## Required Environment Variables

See `backend/.env.example`. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Auth signing secret |
| `ANTHROPIC_API_KEY` | Claude API |
| `VOYAGE_API_KEY` | Voyage AI embeddings |
| `COHERE_API_KEY` | Cohere reranking (if `RERANKER_PROVIDER=cohere`) |
| `RERANKER_PROVIDER` | `cohere` or `cross_encoder` |
| `EMBEDDING_MODEL` | Which Voyage model to use |
| `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_NAME` | Vector store |

## Architecture

### Data Storage Split

Postgres stores all relational data (recipes, users, chat, memory). Qdrant stores raw vectors. The `recipe_embeddings` table in Postgres is a **marker-only table** — it tracks embedding state (which recipes have been embedded, with what model/version) but stores no vectors. Qdrant is the single source of truth for vectors, keyed by `recipe_id`.

### Key Component Interactions

**Recipe Ingestion:**
`api/recipes.py` → `recipes/service.py` (validates, writes DB) → triggers `ingestion/pipeline.py` → `chunking/recipe_chunker.py` builds `embedding_text` → `ingestion/embedding.py` calls Voyage → upserts to Qdrant → updates `recipe_embeddings` marker row.

**Search:**
`api/search.py` → `retrieval/pipeline.py`:
1. `query_rewriter.py` calls Claude (cheap model) to expand/rewrite query
2. `hybrid_search.py` runs two arms in parallel:
   - **Keyword arm:** `recipes/repository.py` (PostgreSQL `tsvector` + trigram on ingredients)
   - **Vector arm:** Qdrant via `providers/vectorstore/qdrant.py`
3. RRF (Reciprocal Rank Fusion) merges both result lists in `hybrid_search.py`
4. `reranker.py` re-ranks via Cohere or self-hosted cross-encoder
5. `context_builder.py` assembles final context (recipes + user memory + history)

**Chat:**
`api/chat.py` → creates session in Postgres → `chat/agent.py` runs Claude tool-use loop with tools defined in `chat/tools.py` (`search_recipes`, `get_recipe`, `update_memory`) → `memory/extractor.py` learns preferences from conversation → response streamed to client.

### Provider Abstraction

All external services are behind Protocol-based interfaces in `providers/`:
- `providers/llm/` — LLM (Anthropic impl)
- `providers/embeddings/` — Embeddings (Voyage impl)
- `providers/rerankers/` — Reranking (Cohere or cross-encoder impl)
- `providers/vectorstore/` — Vector DB (Qdrant impl)

Each subdirectory has `base.py` (Protocol) and one or more concrete implementations. Swap implementations via environment config, not code changes.

### Repository Pattern

`recipes/repository.py` owns **all SQL queries** — raw keyword search, ingredient matching, full-text search. The service layer (`recipes/service.py`) calls into the repository and orchestrates multi-step operations. API handlers call services, not repositories directly.

### User Memory

`memory/store.py` — CRUD on `user_memories` table (persistent user preferences/facts)
`memory/retriever.py` — loads relevant memories into chat context
`memory/extractor.py` — extracts new facts from chat history via LLM

Memory is injected into every chat system prompt so Claude personalizes responses per user.

## Schema Reference

`RV_schema.txt` at the repo root contains the full PostgreSQL schema with design rationale. Read this before touching data models or migrations.

## Test Strategy

| Type | Location | Notes |
|---|---|---|
| Unit | `tests/unit/` | No DB or external services; tests RRF fusion logic, chunking, etc. |
| Integration | `tests/integration/` | Requires a running test DB; tests full API endpoints |
| Eval | `tests/eval/run_eval.py` | Measures recall@k and MRR against a golden query set |

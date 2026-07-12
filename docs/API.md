# ResearchAI — API Reference

Base URL: `http://localhost:8000`
Interactive docs: `http://localhost:8000/api/docs`

---

## System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check + watsonx status |
| GET | `/api/info` | App info, model, active modules |

---

## Search (`/api/search`)

### `POST /api/search`
Execute a multi-source literature search.

**Request body:**
```json
{
  "query": "Federated Learning for healthcare",
  "max_results": 10,
  "sources": ["arxiv", "semantic_scholar", "crossref"],
  "year_from": 2018,
  "year_to": 2024,
  "sort_by": "relevance"
}
```
`sort_by`: `relevance` | `date` | `citations`

**Response:** `SearchResult` with ranked `papers[]`, keywords, related concepts, timing.

---

### `GET /api/search/analyze?q=<query>`
AI-powered query analysis without executing a search.

**Response:** `QueryAnalysis` with topic, domain, keywords, intent, expansions.

---

### `GET /api/search/history?limit=20`
Return recent search history.

---

## Papers (`/api/papers`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/papers?limit=50` | List all indexed papers |
| GET | `/api/papers/{id}` | Get a paper by ID |
| POST | `/api/papers/process` | Download + index a PDF |
| POST | `/api/papers/upload` | Upload a local PDF file |
| GET | `/api/papers/{id}/chunks` | Get text chunks for a paper |
| GET | `/api/papers/{id}/knowledge-base/count` | Vector count |
| DELETE | `/api/papers/{id}` | Delete a paper and all data |

### `POST /api/papers/process`
```json
{ "paper_id": "arxiv:2303.12528", "pdf_url": "https://arxiv.org/pdf/2303.12528" }
```

---

## Summarization (`/api/summarize`)

### `POST /api/summarize`
```json
{ "paper_id": "arxiv:001", "level": "detailed" }
```
`level`: `short` | `medium` | `detailed`

**Response:** `PaperSummary` with problem, methodology, results, contributions, limitations, future work.

---

## Comparison (`/api/compare`)

### `POST /api/compare`
```json
{
  "paper_ids": ["arxiv:001", "s2:abc123"],
  "aspects": ["method", "dataset", "results", "limitations"]
}
```
Min 2, max 10 papers.

**Response:** `ComparisonResult` with table rows, narrative, key differences, recommendation.

---

## Literature Review (`/api/review`)

### `POST /api/review`
```json
{
  "topic": "Vision Transformers",
  "paper_ids": [],
  "use_all_papers": true
}
```
**Response:** `LiteratureReview` with sections, trends, strengths, challenges, references.

---

## Gap Analysis (`/api/gaps`)

### `POST /api/gaps/analyze`
Identify research gaps from literature.

### `POST /api/gaps/hypotheses`
Generate AI research hypotheses.

Both accept:
```json
{ "topic": "AI Safety", "paper_ids": [], "use_all_papers": true }
```

---

## Citations (`/api/citations`)

### `POST /api/citations/generate`
```json
{ "paper_ids": ["arxiv:001", "s2:abc"], "format": "apa" }
```
`format`: `apa` | `ieee` | `mla` | `chicago` | `bibtex`

### `GET /api/citations/formats`
Returns list of supported citation formats.

---

## Reports (`/api/reports`)

### `POST /api/reports/generate`
```json
{
  "topic": "AI in Cybersecurity",
  "paper_ids": [],
  "include_sections": ["title","abstract","introduction","literature_review","research_gap","references"],
  "citation_format": "apa"
}
```

### `GET /api/reports`
List previously generated reports.

---

## Chat (`/api/chat`)

### `POST /api/chat/session`
Create a new chat session.
```json
{ "paper_ids": ["arxiv:001"] }
```
Returns `{ "session_id": "uuid" }`

### `POST /api/chat/message`
Send a message to an active session.
```json
{
  "session_id": "uuid",
  "message": "What is the main contribution of this paper?",
  "paper_ids": []
}
```
**Response:** `ChatResponse` with answer, sources, retrieved chunks, confidence, reasoning.

### `GET /api/chat/{session_id}`
Get session history.

---

## Timeline (`/api/timeline`)

### `POST /api/timeline/generate`
```json
{ "topic": "Transformer evolution", "paper_ids": [], "use_all_papers": true }
```
**Response:** `ResearchTimeline` with sorted `events[]` and narrative.

---

## Trends (`/api/trends`)

### `POST /api/trends/analyze`
```json
{ "topic": "Large Language Models", "paper_ids": [], "use_all_papers": true }
```
**Response:** `TrendAnalysis` with publication trends, top keywords, top authors, venues, growth rate.

---

## Error Responses

All errors follow this schema:
```json
{ "error": "Error Type", "detail": "Human-readable description" }
```

| Status | Error Type |
|--------|-----------|
| 404 | Resource not found |
| 422 | Validation Error |
| 503 | Search Error / AI Generation Error / Vector Store Error |
| 500 | Internal Error |

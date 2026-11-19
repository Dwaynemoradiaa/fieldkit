# Understand and demonstrate FieldKit

## A five minute demo

1. Start offline mode and upload the samples. Explain that this mode tests plumbing without paid model calls.
2. Ask a P1 response question. Show the source and the retrieve/answer/review timings.
3. Ask an unrelated question to show abstention, then explain that lexical-threshold rejection is imperfect.
4. Show the CSV source locator, API documentation and a workspace-isolation test.
5. Walk through the conditional graph in `app/core.py`. Describe separate Gemini answer/reviewer calls and one bounded retry. Do not present mocked tests as real model evaluations.

After enabling Gemini, repeat the demo and show an actual semantic query, live token usage and failure behavior. Read the logs without exposing your credentials.

## Questions you should be ready to answer

**Why Qdrant?** It provides vector similarity search, metadata filters and a local development mode. Every retrieval and deletion includes the workspace filter. A collection fingerprint separates incompatible embedding modes.

**Why two agent roles?** Drafting and evaluation have different instructions. A reviewer can identify unsupported claims and send feedback for one repair. Since both use the same model, their errors may correlate; review does not establish ground truth.

**Why LangGraph?** The graph explicitly represents shared request state, branching, retry limits and abstention. It avoids an open-ended autonomous loop. This version has no durable checkpointer.

**How do you prevent hallucination?** Retrieved evidence, citation-ID validation, model-based review and abstention reduce risk. None guarantees correctness. Next steps are a human-labelled evaluation set and claim-level evidence checks.

**What do the metrics mean?** Request latency covers retrieval, drafting and review. Per-node spans explain where time goes. Output throughput averages all model calls. Generation cost is only an estimate based on configured token prices; embeddings and infrastructure are excluded.

**What happens when an upload is repeated?** Deterministic IDs derived from workspace, filename, content and chunk index make identical uploads idempotent. Changed content is a new document. An old version needs explicit deletion.

**How would you scale?** External Qdrant; queued ingestion workers; shared rate limits; durable trace storage; OAuth/SSO; per-document access control; batching/caching; load tests and a real evaluation dataset. There is no claim these are already implemented.

**What DSA can you discuss?** Chunking is linear in extracted text length. Hash maps group chunks by document. Deques expire request timestamps. UUID-derived point IDs provide stable addressing. Database retrieval is delegated to Qdrant; do not claim to have implemented its indexing algorithm.

## Technical discovery worksheet

Use this to practice a customer conversation; it is not evidence that you have led one.

- Which decisions should this assistant support, and what mistakes are unacceptable?
- What documents/tables exist, who owns them, and how often do they change?
- Which users may see which documents? Must data stay in a specific region?
- Which systems need integration? Is outbound provider processing permitted?
- What volume, latency target and cost ceiling define success?
- Who will label evaluation examples, approve the pilot and own operations?

## Your next engineering contributions

Run the app yourself, inspect the tests and explain each module. Then add one independently understood improvement: background ingestion, a real held-out evaluation set, hybrid retrieval, or durable trace storage. Document the before/after behavior with reproducible measurements. Be candid about AI assistance when asked.

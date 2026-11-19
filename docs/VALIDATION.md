# Validation record

Environment: Python 3.12; dependency versions pinned in requirements files.

- 16 automated tests passed locally. These cover real embedded Qdrant and real LangGraph execution, API authentication/isolation, ingestion, persistence, deletion, CSV/PDF parsing, request limits, trace privacy, and mocked Gemini adapter/reviewer paths.
- 8 of 8 synthetic offline evaluation cases passed. Full per-case results are in `evaluation_results.json`. These are smoke cases, not an enterprise quality benchmark.
- Python compilation, JavaScript syntax and deployment shell syntax checks passed.
- FastAPI startup succeeded; the browser HTML and OpenAPI schema were checked through the test client.
- Visual/browser interaction testing could not run because Chromium process startup was blocked by the execution environment. Desktop/mobile visual layout and browser click paths need checking on your machine.
- Live Gemini API calls, Docker builds, external Qdrant and Google Cloud deployment were not executed. No credentials or paid resources were used.

The test run emitted an environment-plugin warning about a future pytest API removal; all tests completed successfully.

# satsyil_lakemeterplus

This project merges code from two upstream repositories, originally released
under two different licenses. Per project decision, the merged/derivative
work in this repository (`satsyil_lakemeterplus`) is distributed under the
**Elastic License 2.0** (see `LICENSE`) — the more permissive of the two
upstream licenses, since it does not tie use to being a customer of a
specific vendor's paid service. This file preserves the upstream attribution
and notices required by both original licenses.

**This is a good-faith technical reading of both license texts, not legal
advice.** If this project is ever distributed beyond internal/scaffold use,
get the license choice reviewed by whoever has authority over each upstream
repository (see `docs/TODO.md` task #1) — a permissive re-license of the
merged work does not by itself waive the upstream licensors' own terms for
the code they contributed.

## Upstream sources

### `lakemeter-oss` (ported into `src/backend/app/*` excluding `observability/`, and `src/frontend/`)

Copyright (2026) Databricks, Inc.

This software includes software developed at Databricks
(https://www.databricks.com/), originally distributed under the
**Databricks License** (full text below), which requires:
give recipients a copy of the license; mark modified files; retain
copyright/patent/trademark/attribution notices in derivative works; and
carry forward the contents of any NOTICE file. All of those are satisfied
by this file plus `LICENSE`.

<details>
<summary>Databricks License (original, full text)</summary>

```
Databricks License
Copyright (2026) Databricks, Inc.

Definitions.

Agreement: The agreement between Databricks, Inc., and you governing
the use of the Databricks Services, as that term is defined in
the Master Cloud Services Agreement (MCSA) located at
www.databricks.com/legal/mcsa.

Licensed Materials: The source code, object code, data, and/or other
works to which this license applies.

Scope of Use. You may not use the Licensed Materials except in
connection with your use of the Databricks Services pursuant to
the Agreement. Your use of the Licensed Materials must comply at all
times with any restrictions applicable to the Databricks Services,
generally, and must be used in accordance with any applicable
documentation. You may view, use, copy, modify, publish, and/or
distribute the Licensed Materials solely for the purposes of using
the Licensed Materials within or connecting to the Databricks Services.
If you do not agree to these terms, you may not view, use, copy,
modify, publish, and/or distribute the Licensed Materials.

Redistribution. You may redistribute and sublicense the Licensed
Materials so long as all use is in compliance with these terms. ...

[See lakemeter-oss-main/LICENSE.md in the source repository for the
complete, unabridged text, including Redistribution, Termination, and
Disclaimer/Limitation-of-Liability sections.]
```

</details>

Original `lakemeter-oss` dependency attribution (reproduced from its own
NOTICE.md, since all of it still applies to the merged codebase):

| Package | Purpose | License | Source |
| --- | --- | --- | --- |
| fastapi | Web framework for building APIs | MIT | github.com/fastapi/fastapi |
| uvicorn | ASGI server for FastAPI | BSD-3-Clause | github.com/encode/uvicorn |
| sqlalchemy | SQL toolkit and ORM | MIT | github.com/sqlalchemy/sqlalchemy |
| psycopg2-binary | PostgreSQL database adapter | LGPL | github.com/psycopg/psycopg2 |
| pydantic | Data validation using Python type hints | MIT | github.com/pydantic/pydantic |
| pydantic-settings | Settings management for Pydantic | MIT | github.com/pydantic/pydantic-settings |
| python-multipart | Streaming multipart parser | Apache-2.0 | github.com/Kludex/python-multipart |
| xlsxwriter | Excel XLSX file creation | BSD-2-Clause | github.com/jmcnamara/XlsxWriter |
| python-jose | JOSE implementation (JWT) | MIT | github.com/mpdavis/python-jose |
| passlib | Password hashing framework | BSD-3-Clause | github.com/glic3rern/passlib |
| python-dotenv | Read `.env` files | BSD-3-Clause | github.com/theskumar/python-dotenv |
| cachetools | Extensible memoizing collections | MIT | github.com/tkem/cachetools |
| databricks-sdk | Databricks SDK for Python | Apache-2.0 | github.com/databricks/databricks-sdk-py |
| httpx | HTTP client | BSD-3-Clause | github.com/encode/httpx |
| aiofiles | Async file support | Apache-2.0 | github.com/Tinche/aiofiles |
| react / react-dom | UI component library | MIT | github.com/facebook/react |
| react-router-dom | Client-side routing | MIT | github.com/remix-run/react-router |
| axios | HTTP client | MIT | github.com/axios/axios |
| zustand | State management | MIT | github.com/pmndrs/zustand |
| framer-motion | Animation library | MIT | github.com/framer/motion |
| clsx, file-saver, react-hot-toast, react-markdown, remark-gfm | Various UI utilities | MIT | see respective GitHub repos |
| @headlessui/react, @heroicons/react | Unstyled/icon UI components | MIT | github.com/tailwindlabs |
| @dnd-kit/* | Drag and drop toolkit | MIT | github.com/clauderic/dnd-kit |
| typescript | TypeScript language | Apache-2.0 | github.com/microsoft/TypeScript |
| tailwindcss, vite | Build tooling | MIT | see respective GitHub repos |

**Modification notice** (required by the Databricks License's redistribution
terms): the `lakemeter-oss` source files ported into this repository have
been modified from their original form — see `docs/merge-tasks.md` and
`docs/TODO.md` for the specific changes (config unification, auth header
list extended, security middleware added, observability module mounted at
`/api/v1/observability/*`).

### `databricks-cost-observability` (ported into `src/backend/app/observability/`)

Copyright (c) 2026 vijayakunuri1

Originally distributed under the **Elastic License 2.0** — the same license
this merged repository now uses, so no re-licensing gap exists for this
portion of the code. Full original license text: see `LICENSE` in this
repository (identical terms), or `databricks-cost-observability-main/LICENSE`
in the source repository.

**Modification notice**: the `databricks-cost-observability` source files
ported into `src/backend/app/observability/` have been modified — import
paths were rewritten to the `app.observability.*` package namespace, the
`core/config.py` Settings class was replaced with a compatibility shim
backed by the unified `app.config.Settings`, and the hardcoded default
warehouse ID (`21f5bd20b7f44a51`) was removed from `scripts/*.py` in favor
of a required environment variable. See `docs/merge-tasks.md` and
`docs/TODO.md` for the full list of changes.

## Additional dependencies added during the merge

| Package | Purpose | License | Source |
| --- | --- | --- | --- |
| scikit-learn | Isolation Forest cost-anomaly detection (`observability/services/ml_service.py`) | BSD-3-Clause | github.com/scikit-learn/scikit-learn |
| numpy | Numerical computing, used by scikit-learn and anomaly baseline math | BSD-3-Clause | github.com/numpy/numpy |

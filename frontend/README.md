# Blending Master — Frontend (Phase 3)

Next.js 14 App Router + TypeScript + Tailwind 3 + custom shadcn-style components.

## Pages

| Route | PRD ID | Status |
|---|---|---|
| `/`         | S-001 메인 대시보드 | 백엔드 연동 (`GET /cases`, `/health`) |
| `/judge`    | S-002 신규 판단      | 백엔드 연동 (`POST /judge`) |
| `/interview`| S-003 베테랑 지식 추출 | Mock UI (Phase 4에서 `/interview/*` 연결) |
| `/consult`  | S-004 AI 상담         | 백엔드 연동 (`POST /consult`) |

## Quick start

```bash
# From project root
cd frontend
npm install
cp .env.local.example .env.local   # optional: change BACKEND_URL
npm run dev                         # http://localhost:3000
```

Make sure the backend is running on `http://localhost:8000`
(`uvicorn backend.main:app --reload --port 8000` from the project root).

The Next dev server proxies `/api/backend/*` -> `BACKEND_URL` to avoid CORS in
development. Production deployments can either keep the proxy or point to an
absolute backend URL.

## Architecture

```
frontend/
├── app/
│   ├── layout.tsx               Nav + shell
│   ├── globals.css              Tailwind base
│   ├── page.tsx                 S-001 dashboard
│   ├── judge/page.tsx           S-002 new judgment
│   ├── interview/page.tsx       S-003 veteran interview (mock)
│   └── consult/page.tsx         S-004 AI consult
├── components/
│   ├── nav.tsx                  Top navigation
│   └── ui/                      Button / Card / Input / Badge primitives
├── lib/
│   ├── api.ts                   Backend client (typed fetch wrapper)
│   ├── types.ts                 Shared response types
│   └── cn.ts                    clsx + tailwind-merge helper
├── next.config.mjs              /api/backend/* proxy rewrites
├── tailwind.config.ts
└── package.json
```

## Notes

- All four PRD screens (S-001 – S-004) are present; S-003 stores responses
  in component state only — the `/interview/*` API and Secondary RAG ingestion
  are scheduled for Phase 4.
- Korean labels throughout the UI per the PRD/BRD vocabulary.
- No third-party form library — minimal `useState` forms keep the bundle small.

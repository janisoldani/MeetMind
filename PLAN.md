# MeetMind — Implementierungsplan

> Stand: März 2025 | Basiert auf Projektplanung v2 + Planungsgespräch
> Ziel: Portfolio-Projekt + potenzielles Produkt | Stack: FastAPI · Next.js 14 · pgvector · Whisper · Ollama

---

## Architektur-Entscheidungen (final)

| Thema | Entscheidung | Begründung |
|---|---|---|
| Vektordatenbank | pgvector von Tag 1 | Kein ChromaDB — läuft im selben PostgreSQL-Container, keine spätere Datenmigration |
| LLM (MVP) | Ollama + LLaMA 3.1 8B | Kostenlos, lokal, ~8GB RAM |
| Transkription (MVP) | Whisper `base` lokal | Balance Speed/Qualität ohne GPU |
| Embeddings (MVP) | sentence-transformers `all-MiniLM-L6-v2` | 384 Dimensionen, läuft im FastAPI-Prozess |
| Auth | Clerk Free Tier | Fertige UI, 0€, Standard im Next.js-Ökosystem |
| Monitoring | Sentry Free + Python logging | 0€, ab Tag 1 aktiv |
| Job Queue | FastAPI BackgroundTasks (kein Redis/Celery) | MVP-Vereinfachung + Crash-Recovery implementiert |
| Timeline | 5 Milestones (variabel) | Kein fixer Tages-Plan |

### Production-Upgrade-Pfad (spätere Phase)
```
LLM_PROVIDER=ollama        → LLM_PROVIDER=openai
TRANSCRIPTION_MODE=local   → TRANSCRIPTION_MODE=api
EMBEDDING_MODE=local       → EMBEDDING_MODE=openai  (+ Re-Embedding aller Daten, Migration nötig)
OPENAI_API_KEY=sk-...
```

> ⚠️ Hinweis: Wechsel von sentence-transformers (384 dim) zu OpenAI text-embedding-3-small (1536 dim)
> erfordert eine Daten-Migration + Re-Embedding aller bestehenden Meetings — KEIN reiner Env-Var-Wechsel.

---

## Projektstruktur (Monorepo)

```
meetmind/
├── .github/
│   └── workflows/
│       └── ci.yml                    # pytest + Docker Build bei jedem Push
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI App, Startup-Events
│   │   ├── config.py                 # Settings via pydantic-settings + .env
│   │   ├── dependencies.py           # Clerk Auth, DB-Session, workspace_id Injection
│   │   ├── db/
│   │   │   ├── base.py               # SQLAlchemy Base
│   │   │   └── session.py            # AsyncSession Factory + RLS workspace_id setzen
│   │   ├── models/
│   │   │   ├── workspace.py
│   │   │   ├── user.py
│   │   │   ├── meeting.py            # MeetingStatus ENUM
│   │   │   ├── action_item.py
│   │   │   └── embedding.py          # pgvector Embedding-Tabelle
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── health.py         # GET /health
│   │   │       ├── meetings.py       # Upload, Liste, Detail, Delete, Retry
│   │   │       ├── chat.py           # POST /chat/query (RAG)
│   │   │       ├── search.py         # GET /search?q=
│   │   │       ├── actions.py        # Action Items CRUD
│   │   │       └── workspaces.py     # Workspace-Verwaltung
│   │   └── services/
│   │       ├── transcription.py      # Whisper lokal / OpenAI API (via Env)
│   │       ├── llm.py                # Ollama / OpenAI (via Env) + Prompts
│   │       ├── embeddings.py         # sentence-transformers / OpenAI (via Env)
│   │       ├── rag.py                # LangChain RAG-Chain + pgvector Search
│   │       ├── pipeline.py           # Orchestrierung: Upload → Whisper → LLM → Embeddings
│   │       └── llm_mock.py           # Mock-Provider für CI-Tests (kein API-Call)
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 001_init_schema.py    # workspaces, users, meetings, action_items
│   │       ├── 002_add_pgvector.py   # embeddings Tabelle + HNSW-Index
│   │       └── 003_add_rls.py        # Row Level Security Policies
│   ├── tests/
│   │   ├── conftest.py               # Fixtures: DB, Test-Workspace, Test-User, Mock-Provider
│   │   ├── test_api.py               # Alle Endpoints, Auth-Guards, Status-Codes
│   │   ├── test_transcription.py     # Whisper-Pipeline mit 30-Sek. Test-MP3
│   │   └── test_rag.py               # RAG-Chain + RLS-Sicherheitstest
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                      # Next.js App Router
│   │   │   ├── (auth)/               # Login/Signup via Clerk
│   │   │   ├── dashboard/            # Meeting-Liste
│   │   │   ├── meetings/[id]/        # Meeting-Detail + Transkript
│   │   │   └── chat/                 # RAG-Chat UI
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn/ui Komponenten
│   │   │   ├── meeting/              # MeetingCard, TranscriptViewer, UploadForm
│   │   │   ├── chat/                 # ChatInput, ChatMessage, SourceChip
│   │   │   └── upload/               # DropZone, ConsentBanner, ProgressBar
│   │   └── lib/
│   │       ├── api.ts                # fetch-Wrapper für alle Backend-Calls
│   │       ├── auth.ts               # Clerk Helpers
│   │       └── utils.ts
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml                # PostgreSQL + pgvector (nur DB in Docker)
├── Makefile                          # Alle wichtigen Befehle
├── .env.example
├── .gitignore
├── PLAN.md                           # Diese Datei
└── README.md                         # GitHub Landingpage (nach Milestone 5)
```

---

## Datenbankschema

### workspaces
| Spalte | Typ | Beschreibung |
|---|---|---|
| id | UUID PK | Primärschlüssel |
| name | VARCHAR(255) | Firmenname oder Abteilung |
| slug | VARCHAR(100) UNIQUE | URL-freundlicher Bezeichner |
| plan | ENUM free\|pro\|enterprise | Feature-Limits |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### users
| Spalte | Typ | Beschreibung |
|---|---|---|
| id | UUID PK | Entspricht Clerk User ID |
| email | VARCHAR(255) UNIQUE | E-Mail-Adresse |
| display_name | VARCHAR(100) | Anzeigename |
| workspace_id | UUID FK → workspaces | Aktiver Workspace (MVP: 1 Workspace pro User) |
| role | ENUM admin\|member\|viewer | Berechtigungen |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

> ⚠️ MVP-Limitation: Ein User gehört genau einem Workspace. Post-MVP: `user_workspace_memberships`-Tabelle.

### meetings
| Spalte | Typ | Beschreibung |
|---|---|---|
| id | UUID PK | Primärschlüssel |
| title | VARCHAR(255) | Meeting-Titel |
| date | TIMESTAMP | Meeting-Datum |
| duration_sec | INTEGER | Dauer in Sekunden |
| audio_path | TEXT | Lokaler Pfad (MVP) oder S3-URL (Production) |
| transcript | TEXT | Vollständiges Transkript |
| summary | TEXT | LLM-generierte Zusammenfassung (nullable) |
| status | ENUM | pending\|transcribing\|transcription_failed\|summarizing\|transcript_only\|indexing\|not_indexed\|done |
| llm_provider | VARCHAR(50) | 'ollama' oder 'openai' (Rückverfolgbarkeit) |
| workspace_id | UUID FK | Multi-Tenant Workspace-Referenz |
| consent_given | BOOLEAN | Consent des Uploaders |
| consent_timestamp | TIMESTAMP | Zeitpunkt der Zustimmung |
| consent_text_version | VARCHAR(20) | Version des Consent-Texts |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### action_items
| Spalte | Typ | Beschreibung |
|---|---|---|
| id | UUID PK | Primärschlüssel |
| meeting_id | UUID FK | Referenz auf Meeting |
| workspace_id | UUID FK | Direkte Workspace-Referenz (für effiziente RLS) |
| description | TEXT | Aufgabenbeschreibung |
| assignee_name | VARCHAR(100) | Zugewiesene Person (aus Transkript) |
| due_date | DATE | Fälligkeitsdatum (optional) |
| status | ENUM open\|in_progress\|done | Aufgabenstatus |
| timestamp_sec | FLOAT | Zeitpunkt im Meeting |
| confidence | FLOAT | LLM-Konfidenz (0.0–1.0) |
| source_quote | TEXT | Exaktes Zitat aus Transkript |

### embeddings
| Spalte | Typ | Beschreibung |
|---|---|---|
| id | UUID PK | Primärschlüssel |
| meeting_id | UUID FK (CASCADE DELETE) | Referenz auf Meeting |
| workspace_id | UUID FK (CASCADE DELETE) | Für RLS-Policy |
| chunk_index | INTEGER | Position im Transkript |
| chunk_text | TEXT | Transkript-Abschnitt |
| start_sec | FLOAT | Startzeit im Audio |
| end_sec | FLOAT | Endzeit im Audio |
| embedding | VECTOR(384) | sentence-transformers Vektor (MVP) |
| metadata | JSONB | Zusätzliche Metadaten |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

**Index:** `HNSW (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`

**RLS-Policy:**
```sql
CREATE POLICY workspace_isolation ON embeddings
USING (workspace_id = current_setting('app.workspace_id')::uuid);
-- Gleiche Policy für meetings und action_items
```

---

## API-Design

| Method | Endpoint | Beschreibung | Auth |
|---|---|---|---|
| GET | /health | Status aller Subsysteme | ✗ |
| POST | /api/v1/meetings/upload | Audio-Upload + Transkription starten | ✓ |
| POST | /api/v1/meetings/{id}/retry | Fehlgeschlagene Pipeline neu starten | ✓ |
| GET | /api/v1/meetings | Meetings des Workspaces (paginiert) | ✓ |
| GET | /api/v1/meetings/{id} | Meeting-Details + Transkript + Summary | ✓ |
| DELETE | /api/v1/meetings/{id} | Meeting + alle Daten löschen (Cascade) | ✓ |
| GET | /api/v1/meetings/{id}/action-items | Action Items eines Meetings | ✓ |
| PATCH | /api/v1/action-items/{id} | Action Item Status updaten | ✓ |
| POST | /api/v1/chat/query | RAG-Frage mit Quellenangaben | ✓ |
| GET | /api/v1/search?q={} | Semantische + Volltext-Suche | ✓ |
| GET | /api/v1/decisions | Alle Entscheidungen chronologisch | ✓ |

> WS /ws/transcribe/{id} — Live-Transkription: explizit Post-MVP (Whisper lokal zu langsam für Echtzeit)

---

## Umgebungsvariablen (.env.example)

```env
# Datenbank
DATABASE_URL=postgresql://meetmind:meetmind_dev@localhost:5432/meetmind

# KI-Provider (MVP: local | Production: openai)
LLM_PROVIDER=local
TRANSCRIPTION_MODE=local
EMBEDDING_MODE=local

# OpenAI (nur für Production)
OPENAI_API_KEY=

# Ollama (nur für MVP)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Whisper (MVP)
WHISPER_MODEL=base
WHISPER_LANGUAGE=de

# Embeddings (MVP)
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384

# Auth (Clerk)
CLERK_SECRET_KEY=
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=

# Monitoring
SENTRY_DSN=

# File Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=500
```

---

## RAG-Konfiguration (Startwerte)

```python
CHUNK_SIZE = 500          # Token pro Chunk
CHUNK_OVERLAP = 50        # Überlappung verhindert zerrissene Sätze
TOP_K = 5                 # Anzahl retrieved Chunks
SIMILARITY_THRESHOLD = 0.70  # Minimale Cosine-Similarity
EMBEDDING_DIM = 384       # all-MiniLM-L6-v2
```

---

## Graceful Degradation (Pipeline-Fehler)

| Pipeline-Schritt | Fehler | Verhalten | Status |
|---|---|---|---|
| Upload | Datei zu groß / falsches Format | HTTP 422, kein DB-Eintrag | — |
| Whisper | Absturz / OOM | `transcription_failed` + Retry-Button | error |
| LLM Summary | Ollama nicht erreichbar / JSON-Parse-Fehler | Summary = null, Meeting trotzdem sichtbar | transcript_only |
| Action Items | Ungültiges JSON | Leeres Array, manuell hinzufügbar | partial |
| Embedding | pgvector-Fehler | Meeting sichtbar, RAG nicht verfügbar | not_indexed |

**Crash-Recovery:** Beim App-Start alle Meetings mit `status=transcribing` → zurücksetzen auf `pending`.

---

## Milestone 1: Foundation

**Ziel:** App startet, Auth funktioniert, Datenbank läuft mit vollem Schema.

### Schritt 1 — Repository & Struktur
- [ ] Monorepo-Ordnerstruktur anlegen (exakt wie oben definiert)
- [ ] `.gitignore` (Python, Node, .env, uploads/)
- [ ] `.env.example` mit allen Variablen + Kommentaren
- [ ] `README.md` Skelett mit Badges-Platzhaltern

### Schritt 2 — Docker & Datenbank
- [ ] `docker-compose.yml` mit `pgvector/pgvector:pg16`
- [ ] Volumes für persistente Daten
- [ ] `make db-start` Befehl im Makefile
- [ ] Verbindung testen: `psql` Prompt + `pg_extension vector` vorhanden

### Schritt 3 — FastAPI Grundgerüst
- [ ] `requirements.txt` mit gepinnten Versionen
- [ ] `main.py` mit App-Instanz + Startup-Event (Crash-Recovery)
- [ ] `config.py` mit `pydantic-settings` (lädt `.env`)
- [ ] `db/session.py` mit AsyncSession + `SET LOCAL app.workspace_id` bei jedem Request
- [ ] Sentry SDK installieren + DSN konfigurieren

### Schritt 4 — Datenbankmigrationen
- [ ] Alembic initialisieren
- [ ] Migration 001: `workspaces`, `users`, `meetings`, `action_items`
- [ ] Migration 002: `embeddings` Tabelle + `VECTOR(384)` + HNSW-Index
- [ ] Migration 003: RLS-Policies für `embeddings`, `meetings`, `action_items`
- [ ] `make db-migrate` fehlerfrei durchlaufen

### Schritt 5 — Auth (Clerk)
- [ ] Clerk Free Account erstellen
- [ ] Next.js App (`npx create-next-app`) + Clerk SDK installieren
- [ ] Clerk Middleware: `/dashboard` nur für eingeloggte User
- [ ] `/sign-in` und `/sign-up` Routen
- [ ] Clerk Webhook → lokaler `/api/webhooks/clerk` Endpoint → User in DB anlegen/synchronisieren

### Schritt 6 — Health Endpoint & Monitoring
- [ ] `GET /health` → prüft DB-Verbindung, gibt JSON zurück
- [ ] Uptime Robot Free Account → Ping auf `/health` alle 5 Min.
- [ ] Test-Error an Sentry senden (manuell triggern)

### ✅ Milestone 1 fertig wenn:
- `make db-start` → PostgreSQL läuft
- `make db-migrate` → alle 3 Migrationen grün, Tabellen in `\dt` sichtbar
- Browser zeigt Clerk-Login
- Nach Login → Dashboard-Redirect funktioniert
- `GET /health` antwortet `{"db": "ok", "status": "healthy"}`
- Sentry empfängt einen Test-Error

---

## Milestone 2: Upload & Transkription

**Ziel:** Audiodatei hochladen → Whisper transkribiert → Ergebnis erscheint in der UI.

### Schritt 1 — Upload-Endpoint
- [ ] `POST /api/v1/meetings/upload`
  - Datei-Validierung via Magic Bytes (nicht nur Extension) — `python-magic`
  - Unterstützte Formate: `.mp3`, `.mp4`, `.wav`, `.m4a`
  - Max. Dateigröße aus Config (`MAX_FILE_SIZE_MB`)
  - Datei auf Filesystem speichern (`UPLOAD_DIR`)
  - DB-Eintrag anlegen: `status=pending`
  - HTTP 202 zurückgeben (nicht 200 — Verarbeitung läuft noch)
- [ ] `GET /api/v1/meetings/{id}` — Status-Polling

### Schritt 2 — Consent-Banner (DSGVO + §201 StGB)
- [ ] Modal erscheint vor Upload-Start
- [ ] Text: *"Ich bestätige, dass alle Teilnehmer dieser Aufzeichnung über die Aufnahme informiert wurden und ihre Zustimmung gegeben haben."*
- [ ] Checkbox + Bestätigen-Button — ohne Häkchen kein Upload möglich
- [ ] `consent_given`, `consent_timestamp`, `consent_text_version` in DB speichern

### Schritt 3 — Whisper-Pipeline
- [ ] `pip install openai-whisper`
- [ ] `services/transcription.py`:
  - Modell: `whisper.load_model("base")`
  - Sprache: `language="de"` (aus Config)
  - `word_timestamps=True` (für Confidence Scores später)
  - Transkript + `avg_confidence` zurückgeben
- [ ] FastAPI `BackgroundTask`:
  - `status=pending` → `status=transcribing` → Whisper → `status=summarizing`
  - Fehlerfall → `status=transcription_failed` + Fehlermeldung in DB

### Schritt 4 — Crash-Recovery
- [ ] In `main.py` Startup-Event:
  ```python
  # Alle "hängenden" Meetings beim Start zurücksetzen
  await reset_stuck_meetings()  # transcribing → pending
  ```
- [ ] Retry-Endpoint: `POST /api/v1/meetings/{id}/retry`

### Schritt 5 — Upload-UI
- [ ] `DropZone` Komponente (react-dropzone)
- [ ] Fortschrittsbalken via Polling alle 3 Sekunden auf `GET /meetings/{id}`
- [ ] Status-Anzeige: pending → transcribing → done / error
- [ ] Fehlerfall: verständliche Fehlermeldung + Retry-Button
- [ ] Upload-Guide Modal: Schritt-für-Schritt für Zoom / Google Meet / Teams

### ✅ Milestone 2 fertig wenn:
- MP3/MP4 hochladen → Transkript erscheint in UI
- Ohne Consent-Checkbox → Upload-Button disabled
- Falsches Dateiformat → HTTP 422 mit verständlicher Meldung
- App-Neustart während Transkription → Meeting bleibt nicht in `transcribing` hängen
- Whisper-Fehler → `transcription_failed` + Retry-Button sichtbar
- Sentry empfängt Fehler bei Whisper-Absturz

---

## Milestone 3: KI-Pipeline (LLM + Embeddings)

**Ziel:** Transkript → Zusammenfassung + Action Items + Vektoren in pgvector.

### Schritt 1 — Ollama Setup
- [ ] Ollama installieren: [ollama.ai](https://ollama.ai)
- [ ] Modell herunterladen: `ollama pull llama3.1` (~4-5 GB)
- [ ] Verbindung testen: `ollama run llama3.1 "Hallo"`
- [ ] LangChain Wrapper konfigurieren: `base_url=http://localhost:11434/v1`

### Schritt 2 — Zusammenfassung (LLM)
- [ ] `services/llm.py` mit `SUMMARY_PROMPT`:
  ```
  Antworte AUSSCHLIESSLICH mit JSON:
  {
    "summary": "3-5 Sätze",
    "key_decisions": ["..."],
    "topics": ["..."],
    "next_meeting_needed": true/false,
    "confidence": 0.0-1.0
  }
  ```
- [ ] JSON-Parse mit Fehlerbehandlung: Parse-Fehler → `status=transcript_only`, `summary=null`
- [ ] Graceful Degradation testen: Ollama stoppen → Upload → kein Crash, Meeting trotzdem sichtbar

### Schritt 3 — Action Items Extraktion
- [ ] `ACTION_ITEMS_PROMPT` in `llm.py`:
  ```
  Antworte AUSSCHLIESSLICH mit JSON-Array:
  [{
    "description": "...",
    "assignee": "Name oder null",
    "due_date": "YYYY-MM-DD oder null",
    "timestamp_sec": 120.5,
    "confidence": 0.0-1.0,
    "source_quote": "Exaktes Zitat (max 100 Zeichen)"
  }]
  ```
- [ ] `action_items` Tabelle befüllen (inkl. `workspace_id` direkt)
- [ ] Fehlerfall: Leeres Array `[]` — keine Action Items, aber kein Crash

### Schritt 4 — Embeddings + pgvector
- [ ] `pip install sentence-transformers`
- [ ] `services/embeddings.py`:
  - Modell: `all-MiniLM-L6-v2`
  - Transkript chunken via `RecursiveCharacterTextSplitter` (500 Token, 50 Overlap)
  - Chunks in `embeddings` Tabelle speichern: `chunk_text`, `VECTOR(384)`, `start_sec`/`end_sec`, `workspace_id`, `meeting_id`
- [ ] RLS testen: `EXPLAIN ANALYZE` zeigt Policy greift

### Schritt 5 — Pipeline-Orchestrierung
- [ ] `services/pipeline.py` verbindet alle Schritte:
  ```
  Upload → Whisper → Summary → Action Items → Embeddings → status=done
  ```
- [ ] JSON-Logging für jeden Schritt (Format aus Kap. 9.5)
- [ ] Ende-zu-Ende Test: reales Meeting komplett durchlaufen

### Schritt 6 — Meeting-Detail UI
- [ ] `/meetings/[id]` Seite:
  - Transkript-Viewer (scrollbar)
  - Summary-Panel: Zusammenfassung, Key Decisions, Topics als Badges
  - Action Items Liste mit Status, Assignee, Fälligkeitsdatum
  - LLM-Confidence als Farbindikator

### ✅ Milestone 3 fertig wenn:
- Komplette Pipeline läuft: Upload → Whisper → LLM → Embeddings → `status=done`
- Zusammenfassung + Action Items erscheinen in der UI
- LLM-Ausfall → App crasht nicht, Transkript bleibt sichtbar
- `embeddings` Tabelle hat Einträge nach Upload
- `EXPLAIN ANALYZE` zeigt RLS-Policy greift

---

## Milestone 4: RAG-Chat & Suche

**Ziel:** Fragen über Meetings stellen und Antworten mit klickbaren Quellenangaben erhalten.

### Schritt 1 — RAG-Chain
- [ ] `services/rag.py`:
  - Frage einbetten (sentence-transformers)
  - pgvector Cosine-Similarity Search (Top-K=5, Threshold=0.70)
  - `workspace_id` aus Request-Kontext (RLS greift automatisch)
  - Kontext aus Chunks bauen → LLaMA aufrufen
- [ ] `RAG_PROMPT`:
  ```
  Beantworte die Frage AUSSCHLIESSLICH basierend auf den Kontext-Abschnitten.
  Falls nicht im Kontext: "Diese Information ist in den verfügbaren Meetings nicht dokumentiert."
  Antworte mit JSON: { "answer": "...", "sources": [...], "confidence": 0.0-1.0, "found_in_context": true/false }
  ```

### Schritt 2 — Chat-Endpoint
- [ ] `POST /api/v1/chat/query`:
  - `workspace_id` aus Clerk-Token extrahieren
  - RAG-Chain aufrufen
  - Response mit `sources[]` (meeting_id, timestamp_sec, quote)
- [ ] Konversations-Kontext: letzte 3 Fragen/Antworten mitsenden

### Schritt 3 — Sicherheitstests (kritisch)
- [ ] **Cross-Workspace-Test:** 2 Workspaces anlegen, Embeddings in beiden
  - Query aus Workspace A darf 0 Ergebnisse aus Workspace B liefern
  - Fehler hier = kritischer Security-Bug
- [ ] Grenzfall: Unbekanntes Thema → korrekte "nicht dokumentiert"-Antwort
- [ ] Grenzfall: Leerer Workspace → keine Fehler

### Schritt 4 — Chat-UI
- [ ] Chat-Eingabefeld + Senden-Button
- [ ] Streaming-Anzeige (Server-Sent Events) + Typing-Indikator
- [ ] Quellenangaben als klickbare Chips unter jeder Antwort
- [ ] Klick auf Quelle → Meeting-Detail öffnen + Zeitstempel springen
- [ ] Similarity < 0.75: Warnung "Quellenbezug unsicher" anzeigen

### Schritt 5 — Semantische Suche
- [ ] `GET /api/v1/search?q=`:
  - Frage einbetten → pgvector Similarity Search
  - Ergebnisse: Meeting-Titel + Transkript-Snippet + Zeitstempel-Link
- [ ] Suche-UI: Suchfeld im Header, Ergebnisliste

### Schritt 6 — RAGAS-Evaluation
- [ ] 5 synthetische Test-Meetings erstellen (bekannter Inhalt: Entscheidungen, Action Items, Fakten)
- [ ] 10 Fragen pro Meeting = 50 Q&A-Paare
- [ ] `pip install ragas`
- [ ] Evaluation-Script ausführen: Faithfulness, Answer Relevancy, Context Recall, Context Precision
- [ ] Ergebnisse iterativ verbessern bis Zielwerte erreicht:

| Metrik | Zielwert MVP |
|---|---|
| Faithfulness | ≥ 0.75 |
| Answer Relevancy | ≥ 0.70 |
| Context Recall | ≥ 0.65 |
| Context Precision | ≥ 0.70 |

### ✅ Milestone 4 fertig wenn:
- RAG-Chat beantwortet Fragen mit klickbaren Quellenangaben
- Cross-Workspace-Test: 0 Datenlecks zwischen Workspaces
- RAGAS Faithfulness ≥ 0.75 dokumentiert
- Semantische Suche liefert Ergebnisse in < 2 Sek. lokal
- "Nicht dokumentiert"-Antwort bei unbekanntem Thema

---

## Milestone 5: Polish & Launch

**Ziel:** Portfolio-ready — README, Demo-Video, Tests, CI, DSGVO vollständig.

### Schritt 1 — Dashboard & UI-Polish
- [ ] Meeting-Liste: Filter (Datum, Status), Tags, Statusanzeige
- [ ] Action Items Board: Kanban (offen / in Bearbeitung / erledigt)
- [ ] Workspace-weiter Action Items View (Filter: Assignee, Status, Fälligkeit)
- [ ] Entscheidungs-Log: Key Decisions chronologisch durchsuchbar
- [ ] Empty States: Kein Dashboard-Rauschen beim ersten Login
- [ ] Loading States: Skeleton Loader, Typing-Indikator
- [ ] Responsive: Mobile (375px) nutzbar

### Schritt 2 — Whisper Confidence Scores
- [ ] `word_timestamps=True` in Whisper
- [ ] Wörter mit `probability < 0.6` → gelb unterstrichen im Transkript
- [ ] Wörter mit `probability < 0.5` → rot unterstrichen
- [ ] Hover zeigt numerischen Score
- [ ] Inline-Editierung möglich (Original bleibt erhalten)

### Schritt 3 — DSGVO-Vollständigkeit
- [ ] `DELETE /api/v1/meetings/{id}`:
  - Audio-Datei vom Filesystem
  - Transkript aus DB
  - Embeddings aus pgvector (CASCADE DELETE)
  - Action Items (CASCADE DELETE)
  - RAG-Query nach Löschung liefert leeres Ergebnis
- [ ] Soft-Delete mit 30-Tage-Frist (DSGVO Art. 17)
- [ ] Account-Löschung in Profil-Seite
- [ ] Export-Funktion: alle Daten als JSON (DSGVO Art. 15)

### Schritt 4 — Feature-Gate (Freemium)
- [ ] Free-User: RAG-Chat + Semantische Suche als gesperrte Buttons
- [ ] "Pro upgraden" CTA — Stripe-Webhook vorbereiten (inaktiv im MVP)

### Schritt 5 — Testing & CI
- [ ] `conftest.py`: Fixtures für DB-Session, Test-Workspace, Test-User, Mock-Provider
- [ ] Unit Tests `test_api.py`: alle Endpoints, Status-Codes, Auth-Guards (Ziel: ≥ 80% Coverage)
- [ ] Integration Tests `test_transcription.py`: 30-Sek. Test-MP3 Ende-zu-Ende
- [ ] RLS-Sicherheitstest: 2 Workspaces, 0 Cross-Workspace Leakage
- [ ] `.github/workflows/ci.yml`: pytest + Docker Build bei jedem Push
- [ ] pre-commit: ruff + black

### Schritt 6 — README & Demo
- [ ] Demo-Meeting aufnehmen (15-20 Min., klare Entscheidungen + Action Items)
- [ ] Demo-Video (2-3 Min., 1920×1080): Upload → Transkript → Summary → RAG-Frage → Quellenlink
- [ ] Demo-GIF (30 Sek.) für README
- [ ] README als Landingpage:
  - Hero + 1-Satz-Beschreibung + Badges (CI, License, Version)
  - Demo-GIF
  - 4-Punkte Feature-Liste
  - Tech-Stack Badges
  - Quick-Start (5 Befehle)
  - Mermaid Architecture-Diagram
  - Screenshots: Dashboard, Meeting-Detail, RAG-Chat
  - DSGVO & Privacy Abschnitt
  - Roadmap mit Checkboxen
- [ ] GitHub Repo public: Secrets prüfen (git-secrets), SECURITY.md, CONTRIBUTING.md

### ✅ Milestone 5 fertig wenn:
- `pytest` grün, CI-Badge im README sichtbar
- Meeting löschen entfernt alle Daten inkl. Vektoren
- README Quick-Start funktioniert auf einem fremden Rechner in 5 Befehlen
- Demo-Video zeigt alle Core-Features in < 3 Min.
- RAGAS-Scores im README dokumentiert

---

## Post-MVP (nach Launch)

- [ ] Sprecher-Diarisierung: `pyannote/speaker-diarization-3.1`
- [ ] Browser-Extension: Direktaufnahme aus Google Meet / Zoom
- [ ] Slack-Integration: Action Items direkt in Slack-Channels
- [ ] Stripe-Billing aktivieren
- [ ] Kalender-Anbindung: Auto-Reminder nach Meetings
- [ ] Production-Stack: OpenAI APIs + Railway Deployment
  - Inklusive Re-Embedding aller Daten (384 → 1536 Dimensionen)

---

## Makefile-Referenz

```makefile
db-start:     docker-compose up -d postgres
db-stop:      docker-compose down
db-migrate:   cd backend && alembic upgrade head
db-reset:     docker-compose down -v && docker-compose up -d postgres
backend:      cd backend && uvicorn app.main:app --reload --port 8000
frontend:     cd frontend && npm run dev
test:         cd backend && pytest tests/ -v
test-rag:     cd backend && pytest tests/test_rag.py -v
lint:         cd backend && ruff check . && black --check .
install:      pip install -r backend/requirements.txt && npm install --prefix frontend
```

---

## Definition of Done (MVP)

- [ ] Audio-Upload funktioniert, Whisper lokal transkribiert vollständig
- [ ] Consent-Banner implementiert, Timestamp in DB gespeichert
- [ ] Zusammenfassung und Action Items werden generiert
- [ ] Confidence Scores für unsichere Transkript-Stellen sichtbar
- [ ] RAG-Chat beantwortet Fragen mit Quellenangaben — RAGAS Faithfulness ≥ 0.75
- [ ] Cross-Workspace Data Leakage: 0 (RLS-Test grün)
- [ ] DSGVO: Datenlöschung entfernt alle zugehörigen Daten
- [ ] pytest-Suite grün, GitHub Actions CI läuft
- [ ] Demo-Video (2-3 Min.) zeigt alle Features
- [ ] README Quick-Start funktioniert auf fremdem Rechner
- [ ] Live-Transkription: explizit als Post-MVP markiert

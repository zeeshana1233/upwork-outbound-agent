# How to Build OpenCode Agents for Any Project

A universal guide for instructing an AI model to analyse a project and produce
ready-to-use `.opencode/agents/` files from scratch.

---

## What You Are Building

OpenCode agents live at:

```
<project-root>/
└── .opencode/
    └── agents/
        ├── scraper-dev.md
        ├── db-admin.md
        ├── deployer.md
        └── ...
```

Each file is a **Markdown document with a YAML front-matter header**.  
OpenCode reads these files and makes each agent available as a specialised persona
the main AI can adopt — or that it auto-routes to based on keywords.

---

## File Structure (Every Agent)

```markdown
---
name: Human Readable Name
description: One-line summary — what this agent does and when it is used
model: claude-sonnet-4.6
temperature: 0.1
verbosity: medium
tools:
  read: true
  write: true
  edit: true
  bash: true
  ask: true
---

## Identity
Who this agent is. One short paragraph. Role, seniority, what it owns.

## Key Files You Own
- `path/to/file.py` — what this file does, main functions/classes
- `path/to/other.py` — what this file does

## Domain Knowledge
Facts, constants, patterns, API details this agent must know cold.
The more specific and project-accurate, the better.

## Patterns to Follow
- Coding conventions, architectural rules, naming rules
- Things that must never be broken

## Common Issues You Debug
- Known failure modes + their root causes + fixes
```

---

## Configuration Options

### `temperature`
| Value | Use when |
|---|---|
| `0.1` | Code generation, debugging, DB migrations — needs to be exact |
| `0.2` | Code review, analysis with some nuance |
| `0.3` | Planning, architecture, design decisions |
| `0.5–0.7` | Creative writing, proposal drafts, brainstorming |

### `verbosity`
| Value | Use when |
|---|---|
| `low` | Simple confirmations, short answers |
| `medium` | Default — balanced responses |
| `high` | Audits, reviews, explanations that need full detail |
| `verbose` | Debugging sessions — show all reasoning steps |

### `tools`
| Tool | What it allows |
|---|---|
| `read` | Read files from the project |
| `write` | Create new files |
| `edit` | Modify existing files |
| `bash` | Run shell commands |
| `ask` | Ask the user clarifying questions |

**Rule of thumb:**
- Read-only auditors: `read: true`, everything else `false`
- Code writers: `read, write, edit, bash, ask` all `true`
- Analysts/planners: `read: true`, `ask: true`, writes `false`

---

## Step-by-Step Instructions for the AI Model

Give these instructions to the model you want to build the agents:

---

### Prompt to paste into your AI model

```
I want you to analyse this project and build a set of OpenCode agent files
for it. Here is what you need to do:

STEP 1 — EXPLORE THE PROJECT
Read these files to understand the project:
- README.md or any top-level docs
- The main entry point (main.py, index.js, app.py, server.ts, etc.)
- The folder/module structure (list all top-level directories)
- Any existing .opencode/ directory if present
- The deployment setup (Dockerfile, deploy.yml, .github/workflows/, etc.)
- The database models (models.py, schema.prisma, migrations/, etc.)
- Any config files (.env.example, config.py, config.ts, etc.)

STEP 2 — IDENTIFY THE MODULES
List every distinct subsystem in this project. Examples:
- Scraper / data ingestion layer
- API / backend routes
- Database / ORM layer
- Frontend / UI
- AI / ML pipeline
- Discord / Telegram / WhatsApp bot
- Deployment / CI/CD
- Auth / security
- Queue / worker / scheduler

Each distinct subsystem should get its own agent.

STEP 3 — DEFINE THE AGENTS
For each subsystem, define:
1. Agent name (short, kebab-case for filename, e.g. db-admin)
2. Description (one line — what it does + when to use it)
3. Temperature (0.1 for code, 0.3 for planning, 0.5–0.7 for creative)
4. Tools needed (read/write/edit/bash/ask — restrict as much as possible)
5. Key files it owns (exact paths + what each file does)
6. Domain knowledge (API facts, constants, patterns, env vars it cares about)
7. Patterns it must follow (project conventions it enforces)
8. Common issues it debugs (known failure modes + fixes)

Always include these standard agents regardless of project type:
- code-reviewer — read-only, temperature 0.1, verbosity high
- deployer — if there is any deployment setup

STEP 4 — WRITE THE FILES
Create each file at .opencode/agents/<agent-name>.md using this exact format:

---
name: <Name>
description: <one-line description>
model: claude-sonnet-4.6
temperature: <value>
verbosity: <low|medium|high>
tools:
  read: <true|false>
  write: <true|false>
  edit: <true|false>
  bash: <true|false>
  ask: <true|false>
---

## Identity
<Who this agent is — one paragraph>

## Key Files You Own
- `<path>` — <what it does>

## Domain Knowledge
<Bullet list of facts, constants, env vars, API details>

## Patterns to Follow
<Bullet list of conventions and rules>

## Common Issues You Debug
<Bullet list: symptom → root cause → fix>

STEP 5 — WRITE THE AGENTS.MD ROUTING TABLE
Create or update AGENTS.md in the project root.
It must contain:
1. A one-paragraph project summary
2. A module map table (Module | Status | Entry Point)
3. Critical conventions (things that must never be broken)
4. An auto-routing table: keyword triggers → agent name
5. Rule: "Never ask the user which agent to use — always decide and proceed"

The routing table format:
| Keywords in task | Agent to use |
|---|---|
| <comma-separated keywords> | [agent-name] |

STEP 6 — VERIFY
After writing all files, list them and confirm:
- Every major subsystem has an agent
- code-reviewer exists and is read-only (write: false, edit: false, bash: false)
- The routing table in AGENTS.md covers all agents
- Temperature values match the task type
- Tool permissions are as restrictive as possible
```

---

## Real Example: What Was Built for This Project

This project (Upwork Outbound Sales Agent) has 6 agents:

| File | Agent Name | Temperature | Write? | Bash? | Purpose |
|---|---|---|---|---|---|
| `scraper-dev.md` | Scraper Dev | 0.1 | ✅ | ✅ | GraphQL scraper, token rotation, job search |
| `db-admin.md` | DB Admin | 0.1 | ✅ | ✅ | PostgreSQL models, migrations, SQLAlchemy |
| `deployer.md` | Deployer | 0.1 | ✅ | ✅ | GitHub Actions, NSSM, Windows VPS |
| `meridian-tuner.md` | Meridian Tuner | 0.2 | ✅ | ✅ | AI scoring engine, prompts, corpus |
| `proposal-writer.md` | Proposal Writer | 0.5 | ✅ | ✅ | GPT proposal generation, WA delivery |
| `code-reviewer.md` | Code Reviewer | 0.1 | ❌ | ❌ | Read-only audit, finds bugs and anti-patterns |

The `AGENTS.md` file in the root ties them together with:
- Auto-routing keywords → agent
- Critical conventions that all agents must honour
- A module status map

---

## Tips for Writing Good Agent Files

**Be brutally specific about file paths.**  
Don't say "the scraper file" — say `scraper/job_search.py → fetch_jobs(), line 57`.

**Put the real constants in.**  
If the API endpoint is `https://api.example.com/graphql/v1`, put that exact URL
in the agent. If the env var is `UPWORK_OAUTH_TOKEN`, name it exactly.

**Write the failure modes from memory.**  
The most valuable part of an agent file is the "Common Issues" section.
It encodes debugging knowledge so the AI doesn't have to rediscover it every time.

**Restrict tools to the minimum needed.**  
A code reviewer that can't write files can't accidentally break things.
A planner that can't run bash can't accidentally restart a service.

**Keep descriptions short and keyword-rich.**  
The description field is used for auto-routing. Include the key technologies:
`"PostgreSQL + SQLAlchemy specialist — models, migrations, schema changes, query tuning"`
not just `"Database agent"`.

**One subsystem = one agent.**  
Don't create a mega-agent that does everything. Smaller, focused agents
route more accurately and produce better output.

---

## AGENTS.md Routing Rule (Critical)

Every `AGENTS.md` must contain this rule, verbatim or paraphrased:

> **You must ALWAYS auto-select the right agent before responding.**  
> Never wait for the user to choose.  
> Before every reply: read the task, match it to the routing table, adopt that
> agent's persona, and start your reply with the mode tag on its own line,
> e.g. `[scraper-dev]`.  
> If multiple keywords match, pick the most specific agent.  
> If nothing matches, default to `[build]` with full project context.  
> **Never ask the user which agent to use.**

---

## Quick Checklist

Before calling the agent setup complete, verify:

- [ ] `.opencode/agents/` directory exists in project root
- [ ] One `.md` file per major subsystem
- [ ] `code-reviewer.md` exists with `write: false`, `edit: false`, `bash: false`
- [ ] Every agent has real file paths (not placeholders)
- [ ] Every agent has a "Common Issues" section with at least 3 entries
- [ ] `AGENTS.md` exists in project root with routing table
- [ ] Routing table covers every agent file
- [ ] Temperature values are appropriate for each agent's task type
- [ ] No agent has more tool permissions than it needs

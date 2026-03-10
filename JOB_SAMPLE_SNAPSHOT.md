# Upwork Job Sample Snapshot

> Generated: 2026-03-04 22:43:37  
> Source: Live PostgreSQL DB — 3 most recent jobs with full description & skills  
> Purpose: Verification that all fields (description, skills, budget, client) are persisted correctly  

---

## Job 1: AI Developer Needed to Build an AI Agent with RAG for a Web Chatbot (MVP)

| Field | Value |
|---|---|
| **DB ID** | `155155` |
| **Job ID** | `~022029224825647302212` |
| **Budget** | `15.0` |
| **Client** | `Unknown` |
| **Posted At** | `2026-03-04 17:40:52.176481` |
| **Skills Count** | `10` |
| **Description Length** | `706 chars` |

### Skills

`Python`, `AI App Development`, `Natural Language Processing`, `Computer Vision`, `TensorFlow`, `Artificial Intelligence`, `Machine Learning`, `Chatbot Development`, `Web Application`, `Web Development`

### Full Description

Description:
We are looking to build an AI-powered internal assistant that can:
• Answer questions based on internal documents
• Retrieve relevant knowledge from PDFs, Google Drive, or structured data
• Provide contextual responses using RAG (Retrieval-Augmented Generation)
• Be deployed as a web-based internal tool
The goal is to create a production-ready AI MVP that can later scale into a broader automation system.
Scope includes:
• Document ingestion pipeline
• Vector database setup
• RAG architecture
• LLM integration
• Simple web interface
• Deployment guidance
Timeline: Start with Discovery & Architecture phase.
Please share examples of AI agents, RAG systems, or MVP builds you’ve developed.

---

## Job 2: Senior AWS Backend Engineer (Python) – Build Asset Management Platform Integrations

| Field | Value |
|---|---|
| **DB ID** | `155154` |
| **Job ID** | `~022029228876575672011` |
| **Budget** | `30.0` |
| **Client** | `Unknown` |
| **Posted At** | `2026-03-04 17:40:52.176471` |
| **Skills Count** | `7` |
| **Description Length** | `2594 chars` |

### Skills

`Amazon DynamoDB`, `Python`, `Amazon Web Services`, `Amazon S3`, `AWS Lambda`, `API Development`, `Amazon Cognito`

### Full Description

We are building a cloud-based asset and portfolio management platform that integrates financial reporting data, property management systems, and workflow automation tools.

We are looking for an experienced AWS backend engineer to help implement and extend the backend services and integrations.

The system architecture is already defined and includes:
- AWS-based backend services
- ETL pipelines for financial and property management reports
- API layer for a web application
- integrations with external systems such as Monday.com, lenders/banks reports, and property management systems

You will be responsible for implementing scalable backend services, ETL jobs, and integrations according to the provided architecture.

System Overview
The platform consists of several components:

Client Layer
- Web Application / Portal used by internal teams
- Displays KPIs and dashboards
- Authenticated access through the backend API

Backend API (AWS)
Main service layer responsible for:
- User authentication (AWS Cognito / IAM)
- Core business API for the web application
- File uploads/downloads to S3
- Reading and writing core structured data in DynamoDB
- Creating and updating tasks in Monday.com

Integration Layer

Monday Integration Service
Responsibilities:
- send tasks and updates to Monday.com
- receive webhook updates
- synchronise task status back to the platform

ETL / Data Processing
Event-driven and batch jobs are responsible for:
- importing reports from lenders/banks
- importing reports from property manager systems (Yardi, Excel, etc.)
- parsing financial data
- storing raw files in S3
- writing structured data into DynamoDB

Data Layer
Source of truth:
- S3 – raw uploaded reports
- DynamoDB (single table design) – normalised structured data

Responsibilities
- Implement and extend backend services on AWS
- Build REST APIs used by the web application
- Develop ETL pipelines to process financial and property management reports
- Implement integrations with Monday.com
- Design scalable DynamoDB data models
- Implement Lambda / Batch processing jobs
- Manage file workflows in S3
- Ensure secure authentication using Cognito/IAM
- Implement logging, monitoring, and error handling

Required Skills
Strong experience with:
- Python
- AWS (Lambda, S3, DynamoDB, IAM, Cognito)
- API development (FastAPI / Flask / similar)
- ETL pipelines
- REST API design
- data parsing (Excel / financial reports)
- serverless architecture

Nice to have:
- Monday.com API
- financial data pipelines
- property management systems (Yardi)
- infrastructure as code (Terraform / CDK)

---

## Job 3: Polymarket Arbitraze Bot

| Field | Value |
|---|---|
| **DB ID** | `155148` |
| **Job ID** | `~022029105422059379789` |
| **Budget** | `100.0` |
| **Client** | `Unknown` |
| **Posted At** | `2026-03-04 17:40:49.471358` |
| **Skills Count** | `4` |
| **Description Length** | `6541 chars` |

### Skills

`Bot Development`, `Python`, `API`, `Automation`

### Full Description

# Technical Specification

## Project: Crypto True Arbitrage Bot for Polymarket New Python Project

## 1. Objective

Develop a new Python project from scratch, separate repository, implementing an automated trading bot for Polymarket CLOB, focused exclusively on:

* Crypto Up/Down markets
* Time intervals: 15 minutes, 1 hour, 4 hours
* Guaranteed-profit arbitrage only, True-Arb Full Set strategy
* Configurable trade size in shares
* Automatic redeem or claim after market resolution
* Structured logging to console and files
* Fully configurable via .env.true_arb_bot

This must be a completely new project, not modifying any existing file.

---

## 2. Strategy Guaranteed Arbitrage Only

### 2.1 True-Arb Full Set BUY

For a market with two mutually exclusive outcomes UP and DOWN or YES and NO:

* a_up equals best ask price for UP
* a_down equals best ask price for DOWN
* edge equals 1 minus the sum of a_up and a_down

Trade is allowed only if:

a_up plus a_down is less than or equal to 1 minus EDGE_MIN

Execution:

* Buy equal shares S of both outcomes
* Profit is locked because payout equals 1 per full set
* Estimated profit equals edge multiplied by S

No speculative trading allowed.
No directional trading allowed.
Only deterministic guaranteed-profit arbitrage.

---

## 3. Markets to Trade

The bot must:

* Trade only crypto markets such as BTC, ETH, SOL
* Filter by intervals:

  * 15m
  * 1h
  * 4h
* Filter by asset list from ASSETS environment variable
* Trade only active and tradable markets

Market filtering must use Gamma API metadata such as slug, title, tags, or attributes.

---

## 4. Trade Size Configuration

Environment variable:

TRADE_SHARES_FIXED

Sizing logic:

S equals the minimum of q_up_top, q_down_top, and TRADE_SHARES_FIXED

Conditions:

* S must be greater than or equal to MIN_SHARES_PER_TRADE
* q_up_top must be greater than or equal to MIN_TOP_LIQ_SHARES
* q_down_top must be greater than or equal to MIN_TOP_LIQ_SHARES

No trade if liquidity is insufficient.

---

## 5. Execution Engine

### 5.1 Ticket State Machine

Each trade attempt must follow a strict state machine:

SCAN
then CANDIDATE
then PLACE_BOTH
then WAIT_FILL
then either FILLED_BOTH or PARTIAL then RECOVER or NONE then CANCEL
then DONE

### 5.2 Order Placement

Use limit orders with slight price improvement:

p_up equals the minimum of a_up plus TICK_IMPROVE and a_up plus MAX_ENTRY_SLIPPAGE
p_down equals the minimum of a_down plus TICK_IMPROVE and a_down plus MAX_ENTRY_SLIPPAGE

Orders must be placed nearly simultaneously.

If the second leg fails to place, immediately cancel the first leg.

---

## 6. Partial Fill Handling Mandatory

If only one leg fills:

### Step 1 Attempt Recovery

Try completing the second leg within MAX_RECOVER_SLIPPAGE

Only if still profitable:

filled_leg_price plus recover_leg_price must be less than or equal to 1 minus EDGE_RECOVER_MIN

### Step 2 If Recovery Fails

Immediately exit the filled leg:

* Sell at best bid or aggressive limit near bid
* Log realized loss
* Never leave unhedged exposure

---

## 7. Waiting for Market Resolution and Redeem

After a full set is successfully acquired:

* Store the position in a local registry such as JSON or SQLite
* Periodically check market status every REDEEM_POLL_SEC
* When status equals resolved:

  * Execute redeem or claim via SDK or REST
  * Log redeem.request, redeem.success, redeem.error

Redeem errors must not crash the bot.

---

## 8. Configuration File

All configuration must be loaded from:

.env.true_arb_bot

### Required Variables

#### API and Authentication

CLOB_REST_URL
GAMMA_REST_URL
POLY_ADDRESS
POLY_API_KEY
POLY_PASSPHRASE
POLY_PRIVATE_KEY or POLY_API_SECRET
USER_AGENT

#### Market Filters

ASSETS equals BTC, ETH, SOL
INTERVALS equals 15m, 1h, 4h
NO_TRADE_TTL_SEC equals 180

#### Trading

EDGE_MIN equals 0.004 and may be set to 0.0
EDGE_RECOVER_MIN equals 0.001
TRADE_SHARES_FIXED equals 10
MIN_SHARES_PER_TRADE equals 5
MIN_TOP_LIQ_SHARES equals 10
MAX_ENTRY_SLIPPAGE equals 0.002
MAX_RECOVER_SLIPPAGE equals 0.004
TICK_IMPROVE equals 0.001

#### Timing and Concurrency

SCAN_INTERVAL_MS equals 300
FILL_TIMEOUT_MS equals 600
RECOVER_TIMEOUT_MS equals 800
COOLDOWN_SEC equals 20
MAX_ACTIVE_TICKETS equals 10
MAX_OPEN_ORDERS equals 50
REDEEM_POLL_SEC equals 30

#### Reliability

HTTP_TIMEOUT_SEC equals 10
RETRY_MAX equals 3
RETRY_BACKOFF_BASE equals 0.5
FAIL_FAST_COUNT equals 8
FAIL_FAST_WINDOW_SEC equals 60
SAFE_PAUSE_SEC equals 30
DRY_RUN equals false

---

## 9. Logging Requirements

### Console

All logs must be JSON lines including:

* ts in ISO8601 format
* level
* event
* message
* run_id generated as UUID4 at startup
* context object

### Files

1. trades.jsonl
   Must include:

   * market_id
   * slug
   * asset
   * interval
   * prices
   * size
   * edge
   * state transitions
   * pnl_est
   * pnl_realized if recovery exit

2. errors.jsonl

   * Critical errors only
   * Include stack trace and context

---

## 10. Project Structure

crypto_true_arb_bot
pyproject.toml or requirements.txt
README.md
.env.true_arb_bot.example
src
main.py
config.py
logger.py
gamma_client.py
clob_client.py
scanner.py
execution.py
recovery.py
positions.py
redeem.py
health.py
data
trades.jsonl
errors.jsonl
positions.jsonl or sqlite

Run command:

python -m src.main

---

## 11. Required Modes

### DRY_RUN equals true

* No real order placement
* Full simulation with logging

### LIVE mode

* Real trading
* Full recovery logic active

---

## 12. Reliability Requirements

The bot must:

* Never crash on:

  * empty orderbooks
  * None or NaN prices
  * HTTP 4xx or 5xx
  * temporary network failures
* Use retry with exponential backoff
* Implement circuit breaker:

  * If FAIL_FAST_COUNT errors within FAIL_FAST_WINDOW_SEC
  * Pause trading for SAFE_PAUSE_SEC
* Graceful shutdown on SIGINT or SIGTERM:

  * Cancel open orders if possible
  * Flush logs

---

## 13. Acceptance Criteria

The project is accepted when:

* Runs successfully from scratch following README
* In DRY_RUN:

  * Scans crypto markets correctly
  * Identifies valid arbitrage opportunities
  * Logs tickets properly
* In LIVE:

  * Places both legs correctly
  * Handles partial fills properly
  * Does not leave unhedged exposure
  * Does not duplicate entries on the same market due to cooldown and in-flight control
* After resolution:

  * Executes redeem or logs ready-to-redeem correctly
* trades.jsonl and errors.jsonl are correctly written
* All configuration is loaded only from .env.true_arb_bot

---

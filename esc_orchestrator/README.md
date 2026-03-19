# ESC Orchestrator

A YAML-driven AI task queue for contract-first development.
Part of the ESC Software Solutions platform.

---

## Philosophy

Specifications are the source of truth. Code is generated from them, never
the reverse. The orchestrator processes one task at a time, giving you a
natural review point after every output. You design. The AI types.

---

## Installation

```bash
pip install -r esc_orchestrator/requirements.txt
```

---

## Project Structure

```
your_project/
├── esc_orchestrator/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── orchestrator.py
│   └── requirements.txt
├── build/
│   ├── queue.yaml           ← your task list
│   └── output/              ← generated code awaiting review
├── schema/
│   ├── tables/              ← table YAML specs
│   └── hasura/
│       ├── actions/         ← hasura action YAML specs
│       ├── permissions/     ← hasura permission YAML specs
│       └── relationships/   ← hasura relationship YAML specs
├── api/
│   ├── endpoints/           ← FastAPI route YAML specs
│   └── functions/           ← pure function YAML specs
├── ui/
│   ├── pages/               ← Alpine.js page YAML specs
│   └── components/          ← reusable Alpine.js component YAML specs
└── CLAUDE.md                ← session handoff document
```

---

## Running the Orchestrator

```bash
# Process one task and stop
python -m esc_orchestrator

# Check what was generated
cat build/output/T001_schema_tables_levy_account.txt
```

Run it again for each subsequent task. Each run processes exactly one
pending task, saves the output, and updates the queue.

---

## Configuration

Edit `esc_orchestrator/config.py` to change:

| Setting         | Default                | Description            |
|-----------------|------------------------|------------------------|
| OLLAMA_MODEL    | nemotron-3-nano:4b     | Model to use           |
| OLLAMA_BASE_URL | http://localhost:11434 | Ollama server          |
| OLLAMA_TIMEOUT  | 120                    | Seconds before timeout |
| QUEUE_PATH      | build/queue.yaml       | Queue file location    |
| OUTPUT_DIR      | build/output/          | Output folder          |

---

## Task Statuses

| Status  | Meaning                   |
|---------|---------------------------|
| pending | Not yet processed         |
| done    | Processed, output saved   |
| skipped | Deliberately deferred     |

---

## Queue File

All tasks live in `build/queue.yaml`. Tasks are processed in order,
top to bottom. Only the first `pending` task runs per execution.

### Task fields
- `id` — unique, increment T001, T002, T003 etc.
- `status` — always `pending` for new tasks
- `yaml` — path to spec file relative to project root
- `prompt` — one-line instruction from the task type reference below
- `output_file` is read from the spec itself — do not add it to the queue

### Rules
- The spec file must exist before adding the task to the queue
- Every spec file must include an `output_file` field
- Never manually set `output` or `status: done` — the orchestrator handles both

```yaml
version: 1
kind: build_queue

tasks:
  - id: T001
    status: done
    yaml: schema/tables/levy_account.yaml
    prompt: Generate the PostgreSQL migration SQL
    output: build/output/T001_schema_tables_levy_account.txt

  - id: T002
    status: pending
    yaml: schema/hasura/actions/post_levy_payment.yaml
    prompt: Generate the Hasura action metadata JSON
```

---

## Task Types — Full Reference

The following sections document every supported task type with a complete
working example based on the ESC sectional title platform domain.

---

### Task Type 1: Table Spec

**Purpose:** Defines a database table — columns, types, constraints, indexes,
and foreign keys. The orchestrator generates a PostgreSQL migration SQL file.

**Folder:** `schema/tables/`

**Prompt to use:** `Generate the PostgreSQL migration SQL for this table`

**Example spec — `schema/tables/levy_account.yaml`:**

```yaml
version: 1
kind: table

meta:
  source_legislation: STSMA
  use_case_ref: UC-FIN-001
  description: >
    Tracks the levy balance and payment status for each
    sectional title unit.

table:
  name: levy_account
  schema: public

columns:
  - name: id
    type: uuid
    default: gen_random_uuid()
    nullable: false

  - name: unit_id
    type: uuid
    nullable: false
    references:
      table: unit
      column: id
      on_delete: RESTRICT

  - name: balance_cents
    type: integer
    nullable: false
    default: 0
    description: Current balance in cents. Negative means in arrears.

  - name: last_levy_date
    type: date
    nullable: true

  - name: status
    type: text
    nullable: false
    default: current
    constraints:
      check: status IN ('current', 'arrears', 'legal', 'suspended')

  - name: created_at
    type: timestamptz
    default: now()

  - name: updated_at
    type: timestamptz
    default: now()

primary_key: [id]

indexes:
  - columns: [unit_id]
    unique: true

output_file: db/migrations/002_levy_account.sql
```

**Expected output:**

```sql
CREATE TABLE public.levy_account (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    unit_id UUID NOT NULL,
    balance_cents INTEGER NOT NULL DEFAULT 0,
    last_levy_date DATE,
    status TEXT NOT NULL DEFAULT 'current',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT chk_levy_status
        CHECK (status IN ('current', 'arrears', 'legal', 'suspended')),
    CONSTRAINT fk_levy_account_unit
        FOREIGN KEY (unit_id) REFERENCES unit(id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX idx_levy_account_unit_id ON public.levy_account (unit_id);
```

---

### Task Type 2: Hasura Action Spec

**Purpose:** Defines a custom Hasura mutation or query action — inputs,
outputs, handler route, permissions, and dependencies. The orchestrator
generates the Hasura action metadata JSON.

**Folder:** `schema/hasura/actions/`

**Prompt to use:** `Generate the Hasura action metadata JSON`

**Example spec — `schema/hasura/actions/post_levy_payment.yaml`:**

```yaml
version: 1
kind: hasura_action

meta:
  use_case_ref: UC-FIN-003
  description: >
    Records a levy payment against a unit levy account
    and updates the balance and status accordingly.

action:
  name: post_levy_payment
  type: mutation

input:
  name: PostLevyPaymentInput
  fields:
    - name: unit_id
      type: uuid!
    - name: amount_cents
      type: Int!
    - name: payment_date
      type: date!
    - name: reference
      type: String

output:
  name: PostLevyPaymentOutput
  fields:
    - name: success
      type: Boolean!
    - name: new_balance_cents
      type: Int!
    - name: new_status
      type: String!

handler:
  route: /actions/post_levy_payment
  method: POST
  timeout: 30

permissions:
  - role: trustee
  - role: managing_agent

depends_on:
  tables:
    - levy_account
    - unit

output_file: hasura/metadata/actions/post_levy_payment.json
```

**Expected output:**

```json
{
  "name": "post_levy_payment",
  "definition": {
    "handler": "{{ACTION_BASE_URL}}/actions/post_levy_payment",
    "output_type": "PostLevyPaymentOutput",
    "arguments": [
      { "name": "unit_id", "type": "uuid!" },
      { "name": "amount_cents", "type": "Int!" },
      { "name": "payment_date", "type": "date!" },
      { "name": "reference", "type": "String" }
    ],
    "type": "mutation",
    "timeout": 30
  },
  "permissions": [
    { "role": "trustee" },
    { "role": "managing_agent" }
  ]
}
```

---

### Task Type 3: Hasura Permission Spec

**Purpose:** Defines row-level and column-level permissions for a table
across roles. The orchestrator generates the Hasura permission metadata JSON.

**Folder:** `schema/hasura/permissions/`

**Prompt to use:** `Generate the Hasura permission metadata JSON for this table and role`

**Example spec — `schema/hasura/permissions/levy_account_trustee.yaml`:**

```yaml
version: 1
kind: hasura_permission

meta:
  use_case_ref: UC-FIN-001
  description: >
    Defines what a trustee can see and do with levy accounts.
    Trustees can view all accounts in their scheme.
    Only managing agents may insert or delete.

table:
  name: levy_account
  schema: public

role: trustee

select:
  filter:
    scheme_id:
      _eq: X-Hasura-Scheme-Id
  columns:
    - id
    - unit_id
    - balance_cents
    - last_levy_date
    - status
    - created_at
  allow_aggregations: true

insert: false
update: false
delete: false

output_file: hasura/metadata/databases/default/tables/public_levy_account.yaml
```

**Expected output:**

```json
{
  "table": { "schema": "public", "name": "levy_account" },
  "role": "trustee",
  "permission": {
    "select": {
      "filter": { "scheme_id": { "_eq": "X-Hasura-Scheme-Id" } },
      "columns": [
        "id", "unit_id", "balance_cents",
        "last_levy_date", "status", "created_at"
      ],
      "allow_aggregations": true
    }
  }
}
```

---

### Task Type 4: Hasura Relationship Spec

**Purpose:** Defines object and array relationships between tables in Hasura.
The orchestrator generates the Hasura relationship metadata JSON.

**Folder:** `schema/hasura/relationships/`

**Prompt to use:** `Generate the Hasura relationship metadata JSON`

**Example spec — `schema/hasura/relationships/unit_to_levy_account.yaml`:**

```yaml
version: 1
kind: hasura_relationship

meta:
  use_case_ref: UC-FIN-001
  description: >
    A unit has exactly one levy account.
    A levy account belongs to exactly one unit.

relationships:
  - name: levy_account
    type: object
    from:
      table: unit
      column: id
    to:
      table: levy_account
      column: unit_id

  - name: unit
    type: object
    from:
      table: levy_account
      column: unit_id
    to:
      table: unit
      column: id

output_file: hasura/metadata/databases/default/tables/public_unit.yaml
```

**Expected output:**

```json
[
  {
    "type": "create_object_relationship",
    "args": {
      "table": { "schema": "public", "name": "unit" },
      "name": "levy_account",
      "using": {
        "foreign_key_constraint_on": "id"
      }
    }
  },
  {
    "type": "create_object_relationship",
    "args": {
      "table": { "schema": "public", "name": "levy_account" },
      "name": "unit",
      "using": {
        "foreign_key_constraint_on": "unit_id"
      }
    }
  }
]
```

---

### Task Type 5: Endpoint Spec

**Purpose:** Defines a FastAPI route — HTTP method, route path, input
payload, output payload, error codes, business rules, and dependencies.
The orchestrator generates the FastAPI handler with Pydantic models.

**Folder:** `api/endpoints/`

**Prompt to use:** `Generate the FastAPI route with Pydantic input and output models`

**Example spec — `api/endpoints/post_levy_payment.yaml`:**

```yaml
version: 1
kind: endpoint

meta:
  use_case_ref: UC-FIN-003
  description: >
    Posts a levy payment against a unit account and updates
    the balance and status accordingly.

endpoint:
  name: post_levy_payment
  route: /actions/post_levy_payment
  method: POST

input:
  - name: unit_id
    type: uuid
    required: true
  - name: amount_cents
    type: integer
    required: true
    validation:
      min: 1
  - name: payment_date
    type: date
    required: true
  - name: reference
    type: string
    required: false

output:
  - name: success
    type: boolean
  - name: new_balance_cents
    type: integer
  - name: new_status
    type: string

errors:
  - code: UNIT_NOT_FOUND
    http: 404
  - code: INVALID_AMOUNT
    http: 422
  - code: INSUFFICIENT_PERMISSION
    http: 403

business_rules:
  - rule: Subtract amount_cents from current balance_cents
  - rule: Recalculate status based on new balance
  - rule: status becomes current if balance_cents >= 0

depends_on:
  tables:
    - levy_account
    - unit
  functions:
    - recalculate_levy_status

output_file: app/routers/post_levy_payment.py
```

**Expected output:**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, UUID4, validator
from datetime import date
from typing import Optional
from app.database import get_db

router = APIRouter()

class PostLevyPaymentInput(BaseModel):
    unit_id: UUID4
    amount_cents: int
    payment_date: date
    reference: Optional[str] = None

    @validator("amount_cents")
    def amount_must_be_positive(cls, v):
        if v < 1:
            raise ValueError("amount_cents must be at least 1")
        return v

class PostLevyPaymentOutput(BaseModel):
    success: bool
    new_balance_cents: int
    new_status: str

@router.post("/actions/post_levy_payment", response_model=PostLevyPaymentOutput)
async def post_levy_payment(payload: PostLevyPaymentInput, db=Depends(get_db)):
    account = await db.fetch_one(
        "SELECT * FROM levy_account WHERE unit_id = :unit_id",
        {"unit_id": payload.unit_id}
    )
    if not account:
        raise HTTPException(status_code=404, detail="UNIT_NOT_FOUND")

    new_balance = account["balance_cents"] - payload.amount_cents
    new_status = recalculate_levy_status(new_balance)

    await db.execute(
        """UPDATE levy_account
           SET balance_cents = :balance, status = :status, updated_at = now()
           WHERE unit_id = :unit_id""",
        {"balance": new_balance, "status": new_status, "unit_id": payload.unit_id}
    )

    return PostLevyPaymentOutput(
        success=True,
        new_balance_cents=new_balance,
        new_status=new_status
    )
```

---

### Task Type 6: Function Spec

**Purpose:** Defines a pure computational function — inputs, outputs, and
explicit business logic. No side effects, no database calls. The orchestrator
generates the Python function with unit tests.

**Folder:** `api/functions/`

**Prompt to use:** `Generate the pure Python function with unit tests`

**Example spec — `api/functions/recalculate_levy_status.yaml`:**

```yaml
version: 1
kind: function

meta:
  description: >
    Pure computational function. Determines levy account status
    based on current balance in cents. No side effects.

function:
  name: recalculate_levy_status
  type: pure

input:
  - name: balance_cents
    type: integer

output:
  - name: status
    type: string

logic:
  - if: balance_cents >= 0
    return: current
  - if: balance_cents < 0 and balance_cents >= -500000
    return: arrears
  - if: balance_cents < -500000
    return: legal

used_by:
  endpoints:
    - post_levy_payment
    - adjust_levy_balance

output_file: app/functions/recalculate_levy_status.py
```

**Expected output:**

```python
def recalculate_levy_status(balance_cents: int) -> str:
    """
    Determines levy account status based on balance in cents.
    Pure function — no side effects.
    """
    if balance_cents >= 0:
        return "current"
    elif balance_cents >= -500000:
        return "arrears"
    else:
        return "legal"


# Unit tests
import pytest

def test_positive_balance_is_current():
    assert recalculate_levy_status(0) == "current"
    assert recalculate_levy_status(1000) == "current"

def test_small_negative_balance_is_arrears():
    assert recalculate_levy_status(-1) == "arrears"
    assert recalculate_levy_status(-500000) == "arrears"

def test_large_negative_balance_is_legal():
    assert recalculate_levy_status(-500001) == "legal"
    assert recalculate_levy_status(-1000000) == "legal"
```

---

### Task Type 7: Page Spec

**Purpose:** Defines a full Alpine.js page — route, layout, components,
data sources, and permissions. The orchestrator generates the Alpine.js
page component.

**Folder:** `ui/pages/`

**Prompt to use:** `Generate the Alpine.js page component`

**Example spec — `ui/pages/levy_account_dashboard.yaml`:**

```yaml
version: 1
kind: page

meta:
  use_case_ref: UC-FIN-001
  description: Dashboard showing levy status for a single unit

route: /units/:unit_id/levy

layout: dashboard

components:
  - id: levy_balance_card
    type: stat_card
    label: Current Balance
    data_source: query.get_levy_account
    field: balance_cents
    format: currency_zar

  - id: levy_status_badge
    type: status_badge
    label: Status
    data_source: query.get_levy_account
    field: status
    variants:
      current: green
      arrears: orange
      legal: red
      suspended: grey

  - id: payment_history_table
    type: data_table
    label: Payment History
    data_source: query.get_levy_payments
    columns:
      - field: payment_date
        label: Date
      - field: amount_cents
        label: Amount
        format: currency_zar
      - field: reference
        label: Reference

  - id: post_payment_button
    type: action_button
    label: Post Payment
    triggers: action.post_levy_payment
    permission: trustee

permissions:
  - role: trustee
  - role: managing_agent

output_file: templates/pages/levy_account_dashboard.html
```

**Expected output:**

```html
<div x-data="levyDashboard()" x-init="init()">

  <!-- Balance Card -->
  <div class="stat-card">
    <span class="label">Current Balance</span>
    <span class="value" x-text="formatCurrency(account.balance_cents)"></span>
  </div>

  <!-- Status Badge -->
  <div class="status-badge" :class="statusClass(account.status)">
    <span x-text="account.status"></span>
  </div>

  <!-- Payment History Table -->
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Amount</th>
        <th>Reference</th>
      </tr>
    </thead>
    <tbody>
      <template x-for="payment in payments" :key="payment.id">
        <tr>
          <td x-text="payment.payment_date"></td>
          <td x-text="formatCurrency(payment.amount_cents)"></td>
          <td x-text="payment.reference"></td>
        </tr>
      </template>
    </tbody>
  </table>

  <!-- Post Payment Button (trustee only) -->
  <button x-show="hasRole('trustee')" @click="postPayment()">
    Post Payment
  </button>

</div>

<script>
function levyDashboard() {
  return {
    account: {},
    payments: [],

    async init() {
      const unitId = window.location.pathname.split('/')[2];
      this.account = await fetchGraphQL(`
        query GetLevyAccount($unit_id: uuid!) {
          levy_account(where: { unit_id: { _eq: $unit_id } }) {
            balance_cents status last_levy_date
          }
        }`, { unit_id: unitId });
      this.payments = await fetchGraphQL(`
        query GetLevyPayments($unit_id: uuid!) {
          levy_payment(where: { unit_id: { _eq: $unit_id } }
                       order_by: { payment_date: desc }) {
            payment_date amount_cents reference
          }
        }`, { unit_id: unitId });
    },

    formatCurrency(cents) {
      return `R ${(cents / 100).toFixed(2)}`;
    },

    statusClass(status) {
      return {
        'badge-green':  status === 'current',
        'badge-orange': status === 'arrears',
        'badge-red':    status === 'legal',
        'badge-grey':   status === 'suspended'
      };
    },

    async postPayment() {
      // triggers action.post_levy_payment
    }
  }
}
</script>
```

---

### Task Type 8: Component Spec

**Purpose:** Defines a reusable Alpine.js UI component — inputs, outputs,
events, and visual variants. The orchestrator generates a self-contained
Alpine.js component that can be embedded in any page.

**Folder:** `ui/components/`

**Prompt to use:** `Generate the reusable Alpine.js component`

**Example spec — `ui/components/levy_status_badge.yaml`:**

```yaml
version: 1
kind: component

meta:
  description: >
    Reusable status badge for levy account status.
    Displays a coloured pill with the current status label.
    Used on dashboard, unit list, and arrears report pages.

component:
  name: levy_status_badge
  type: display

props:
  - name: status
    type: string
    required: true
    allowed_values: [current, arrears, legal, suspended]

  - name: size
    type: string
    required: false
    default: medium
    allowed_values: [small, medium, large]

variants:
  current:
    color: green
    label: Current
  arrears:
    color: orange
    label: In Arrears
  legal:
    color: red
    label: Legal Action
  suspended:
    color: grey
    label: Suspended

events:
  emits: []
  listens: []

used_by:
  pages:
    - levy_account_dashboard
    - unit_list
    - arrears_report

output_file: templates/components/levy_status_badge.html
```

**Expected output:**

```html
<!-- levy-status-badge component -->
<template id="levy-status-badge">
  <div
    x-data="levyStatusBadge($props)"
    :class="['badge', colorClass, sizeClass]">
    <span x-text="label"></span>
  </div>
</template>

<script>
function levyStatusBadge({ status, size = 'medium' }) {
  const variants = {
    current:   { color: 'green',  label: 'Current'       },
    arrears:   { color: 'orange', label: 'In Arrears'    },
    legal:     { color: 'red',    label: 'Legal Action'  },
    suspended: { color: 'grey',   label: 'Suspended'     }
  };

  const variant = variants[status] || variants['suspended'];

  return {
    label:      variant.label,
    colorClass: `badge-${variant.color}`,
    sizeClass:  `badge-${size}`
  };
}
</script>

<style>
.badge            { display: inline-flex; border-radius: 9999px;
                    font-weight: 600; padding: 0.25rem 0.75rem; }
.badge-small      { font-size: 0.75rem; }
.badge-medium     { font-size: 0.875rem; }
.badge-large      { font-size: 1rem; }
.badge-green      { background: #d1fae5; color: #065f46; }
.badge-orange     { background: #ffedd5; color: #92400e; }
.badge-red        { background: #fee2e2; color: #991b1b; }
.badge-grey       { background: #f3f4f6; color: #374151; }
</style>
```

---

## Session Handoff

At the end of each session update `CLAUDE.md` with:
- What was completed
- What the next pending task is
- Any architectural decisions made

---

## Roadmap

- v0.2.0 — deployer.py: interactive review and file placement
- v0.3.0 — batch mode: process all pending tasks unattended
- v0.4.0 — multi-provider support via LLM rotator

---

## Author

ESC Software Solutions
Built for the South African sectional title management platform.
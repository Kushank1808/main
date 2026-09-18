# Billing validation POC — Workday · POMS · ORBIS

Two data layers over one static JSON API, hostable on GitHub Pages, plus a rule-based validator that
runs every hour.

| Path | What it is |
|---|---|
| `workday/` | **Workday** — customer invoicing UI for SE21, NO21, PT21, DK21: invoice worklist, invoice detail with the *Invoice Lines* tab (Sales Item, Revenue Category, Line Item Description, Quantity, UoM, Unit Price, Extended Amount), Tax, Attachments, Notes, **Validation** tab and a **Hourly validation monitor** |
| `poms/` | **POMS** — the order management system the invoice must agree with (buyer, financing partner, VIN, licence plate, base price, fees, gross taxable, total) |
| `validator/` | `rules.py` (one function per exception), `validate.py` (one run → `api/validation-runs/latest.json`), `scheduler.py` (hourly loop) |
| `.github/workflows/hourly-validation.yml` | Cron `0 * * * *` — runs the validator on GitHub and commits the results so the hosted UI updates |
| `generate_workday_poms.py` | Regenerates the Workday / POMS / tracker data deterministically (edit the scenario list to add cases) |
| `erp/`, `analytics/`, `generate.py`, `docs/` | The original **ORBIS** generic pre-billing dataset, unchanged |
| `api/` | Static JSON for everything above |
| `sql/` | MySQL schema + seed: `schema.sql` / `seed.sql` (ORBIS), `workday_poms_schema.sql` / `workday_poms_seed.sql` |

## Run it

```bash
python3 -m http.server 8080          # then open http://localhost:8080  (file:// will not work — the apps fetch JSON)
python3 validator/validate.py --check   # one validation run, graded against the answer key
python3 validator/scheduler.py          # run now, then at the top of every hour
python3 validator/scheduler.py --interval 5   # demo pace
```

Deploy to GitHub Pages exactly as before (`main` / root). Enable Actions and the hourly workflow keeps
`api/validation-runs/` current; the Workday UI reads `latest.json` on every page load, so the *Validation*
column, the per-invoice *Validation* tab and the monitor page always show the most recent run.

To validate a hosted copy from anywhere: `python3 validator/validate.py --base-url https://<you>.github.io/<repo>`.

## Data model (Workday / POMS layer)

```
company (SE21 NO21 PT21 DK21)
customer ──< customer_invoice ──< invoice_line (sales_item, revenue_category, description, qty, price, extended)
                 │                      revenue_category (3022 3027 3030 3033 · fee categories 3041 3042 3043 · 3055 · 9000)
                 ├── poms_order         (buyer, financing_type, financing_partner, vin, license_plate, base_price, fees, gross, vat, total)
                 ├── nga_tracker        (NO21: required fields, response_status, remove_fees, revised gross / base)
                 ├── factoring_tracker  (NO21: on-account payments captured)
                 ├── dk21_sharepoint_tracker (DK21: required PO ref, agreed price, required description text)
                 ├── ey_final_invoice   (PT21: E&Y number, sequence, date, customer, PO, VIN, amounts)
                 └── salesforce_account (PT21: fallback VAT numbers)
```

Join keys are listed in `api/workday/index.json`.

## Rules (from the entity exception notes)

| Rule | Company | Name | Severity | On fail |
|---|---|---|---|---|
| `GEN-001` | ALL | Line arithmetic | critical | FAIL |
| `GEN-002` | ALL | Workday vs POMS value match | critical | FAIL |
| `GEN-003` | ALL | VIN match | high | FAIL |
| `SE21-001` | SE21 | Related party revenue category | high | FAIL |
| `NO21-001` | NO21 | NGA tracker captured | high | FAIL |
| `NO21-002` | NO21 | NGA response received | high | HOLD |
| `NO21-003` | NO21 | Fee lines removed when instructed | critical | FAIL |
| `NO21-004` | NO21 | Revised gross and base applied | critical | FAIL |
| `NO21-005` | NO21 | VAT recalculated after amendment | critical | FAIL |
| `NO21-007` | NO21 | Factoring payment captured | medium | FAIL |
| `PT21-001` | PT21 | Leasing licence plate | high | FAIL |
| `PT21-002` | PT21 | Personal loan bill-to | high | FAIL |
| `PT21-003` | PT21 | Banco BPI exception | high | FAIL |
| `PT21-004` | PT21 | VAT number on extras / prepayment | medium | FAIL |
| `PT21-005` | PT21 | E&Y final invoice match | critical | FAIL |
| `PT21-006` | PT21 | Gapless numbering and approval order | critical | FAIL |
| `PT21-007` | PT21 | Exclude internal zero-value documents | info | INFO |
| `DK21-001` | DK21 | SharePoint tracker adjustments applied | high | FAIL |

GEN rules run for every company. GEN-002 compares the Workday subtotal (excl. VAT) with the POMS gross
taxable amount; it is skipped for prepayments, delivery notes and credit notes, and superseded by NO21-004
once the NGA team has revised the amounts. HOLD means the invoice cannot proceed until an external
input arrives (NGA response) — it is neither a data error nor a pass.

## Seeded scenarios (answer key: `api/workday/expected-results.json`)

16 PASS · 20 FAIL · 1 HOLD. Every exception appears at least once passing and once failing.

| Invoice | Expected | Rules | Scenario |
|---|---|---|---|
| `CI-SE21-100201` | PASS | — | SE21 normal: private cash buyer, bill-to = sold-to, no related party |
| `CI-SE21-100202` | PASS | — | SE21 exception PASS: bill-to Ziklo Bank, Brand line already on 3030 |
| `CI-SE21-100203` | FAIL | SE21-001 | SE21 exception FAIL: bill-to Volvo Bank, Brand line left on 3022 (the screenshot case) |
| `CI-SE21-100204` | FAIL | SE21-001 | SE21 exception FAIL: Ziklo Bank is sold-to, Brand line on 3027 |
| `CI-SE21-100205` | PASS | — | SE21 normal: corporate fleet buyer with PO |
| `CI-SE21-100206` | FAIL | GEN-001, GEN-002 | SE21 generic FAIL: extended amount does not equal quantity × unit price |
| `CI-NO21-200301` | PASS | — | NO21 normal: private buyer, not NGA, fees chargeable, matches POMS |
| `CI-NO21-200302` | PASS | — | NO21 NGA PASS: tracker says remove fees; fees removed, gross and base revised, VAT recalculated |
| `CI-NO21-200303` | FAIL | NO21-003, NO21-004 | NO21 NGA FAIL: tracker says remove fees but fee lines are still on the draft |
| `CI-NO21-200304` | FAIL | NO21-001 | NO21 NGA FAIL: NGA customer but invoice never captured in the NGA tracker |
| `CI-NO21-200305` | HOLD | NO21-002 | NO21 NGA HOLD: tracker submitted, NGA team response still pending |
| `CI-NO21-200306` | FAIL | NO21-005 | NO21 NGA FAIL: fees removed and gross revised but VAT still calculated on the old gross |
| `CI-NO21-200307` | FAIL | GEN-002 | NO21 FAIL: Workday vehicle price 459,900 vs POMS 449,900 (manual amendment needed) |
| `CI-NO21-200308` | FAIL | NO21-007 | NO21 FAIL: payment recorded On Account but missing from the factoring tracker (processing delay) |
| `CI-NO21-200309` | PASS | — | NO21 NGA PASS: tracker confirms fees are chargeable; fee lines retained, amounts unchanged |
| `CI-NO21-200310` | FAIL | NO21-001 | NO21 NGA FAIL: tracker row exists but Model Number and Base Price were not captured |
| `CI-PT21-300401` | PASS | — | PT21 normal: private cash buyer; E&Y final invoice matches on date, amount, name, PO |
| `CI-PT21-300402` | PASS | — | PT21 leasing PASS: LeasePlan, licence plate from POMS present in the line description |
| `CI-PT21-300403` | FAIL | PT21-001 | PT21 leasing FAIL: Arval, licence plate BH-44-LQ missing from the description |
| `CI-PT21-300404` | FAIL | PT21-001 | PT21 leasing FAIL: Kinto, plate on invoice CJ-10-MN, POMS has CJ-01-MN |
| `CI-PT21-300405` | PASS | — | PT21 personal loan PASS: Lusitânia Crédito finances; bill-to changed to buyer so bill-to = sold-to = buyer |
| `CI-PT21-300406` | FAIL | PT21-002 | PT21 personal loan FAIL: bill-to still Crédito Ibérico SA instead of the buyer |
| `CI-PT21-300407` | PASS | — | PT21 Banco BPI PASS: sold-to changed to Banco BPI SA so bill-to = sold-to = loan provider |
| `CI-PT21-300408` | FAIL | PT21-003 | PT21 Banco BPI FAIL: sold-to is still the buyer Rui Martins |
| `CI-PT21-300409` | FAIL | PT21-004 | PT21 prepayment FAIL: customer VAT number blank on the draft; Salesforce holds PT509876543 |
| `CI-PT21-300410` | PASS | — | PT21 prepayment PASS: VAT number populated |
| `CI-PT21-300411` | FAIL | PT21-005 | PT21 E&Y FAIL: E&Y final invoice amount 47,900.00 excl. VAT vs Workday 45,900.00 |
| `CI-PT21-300412` | FAIL | PT21-005 | PT21 E&Y FAIL: invoice date in Workday differs from the E&Y final invoice date |
| `CI-PT21-300413` | FAIL | PT21-006 | PT21 gapless FAIL: Workday statutory number is one ahead of the E&Y number for this invoice |
| `CI-PT21-300414` | FAIL | PT21-006 | PT21 gapless FAIL: approved in Workday before the E&Y final invoice was received |
| `CI-PT21-300415` | PASS | — | PT21 delivery note PASS: zero-value internal document, excluded from the daily E&Y report |
| `CI-PT21-300416` | PASS | — | PT21 credit note PASS: matches E&Y credit note; reason noted; kept in draft |
| `CI-DK21-400501` | PASS | — | DK21 normal: private cash buyer |
| `CI-DK21-400502` | PASS | — | DK21 tracker PASS: PO reference, agreed fleet price and cost-centre text all applied from SharePoint tracker |
| `CI-DK21-400503` | FAIL | DK21-001, GEN-002 | DK21 tracker FAIL: list price billed, PO reference missing, cost-centre text missing |
| `CI-DK21-400504` | PASS | — | DK21 normal: corporate buyer with accessory line |
| `CI-DK21-400505` | FAIL | GEN-003 | DK21 generic FAIL: VIN on the invoice does not match the POMS order |

`validate.py --check` grades the validator against this table (currently 37/37).

## Validation run shape

`api/validation-runs/latest.json`: `run_id`, `started_at`, `schedule.next_run_at`, `summary {PASS, FAIL, HOLD}`,
`by_company`, `by_rule`, and `results[]` — one row per invoice with `status`, `rules_failed[]` and
`findings[]` (`rule_id`, `severity`, `outcome`, `field`, `expected`, `actual`, `message`, `remediation`, `line`).
The Workday invoice screen highlights the exact cell a finding points at (the yellow Revenue Category cell
on `CI-SE21-100203` is the screenshot case).

---

## ORBIS (original dataset)

A dummy SAP/Oracle-style pre-billing system for a **billing validation POC**. It holds everything an
invoice is assembled from, plus source documents, plus the pre-invoice **billing drafts** your
validation tool is meant to check.

| Path | What it is |
|---|---|
| `erp/` | ORBIS ERP — transactional UI (drafts, orders, contracts, POs, deliveries, masters, documents) |
| `analytics/` | ORBIS Insight — Qlik-style analytics sheet with governing selections |
| `api/` | Static JSON API, served by GitHub Pages with `Access-Control-Allow-Origin: *` |
| `docs/` | 80 source PDFs: contracts, customer POs, order acknowledgements, delivery notes |
| `sql/` | MySQL schema + seed with identical data |
| `generate.py` | Regenerates everything, deterministically |

## Deploy

```bash
git init && git add . && git commit -m "ORBIS pre-billing system"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Settings → Pages → Deploy from a branch → `main` / `(root)`.

Locally: `python3 -m http.server 8080` then open <http://localhost:8080>. `file://` will not work —
the apps fetch JSON.

## Data model

```
customer ──< contract ──< price_list
    │           │
    │           ├──< purchase_order ──< po_line
    │           │
    └──────────< sales_order ──< so_line
                    │
                    ├──< delivery ──< delivery_line      (what actually shipped)
                    │
                    └──< billing_draft ──< billing_draft_line   (what we intend to invoice)
```

Join keys:

| From | To |
|---|---|
| `billing_draft.sales_order` | `sales_order.order_number` |
| `sales_order.customer_po_number` | `purchase_order.po_number` |
| `sales_order.contract_number` | `contract.contract_number` |
| `sales_order.delivery_number` | `delivery.delivery_number` |
| `draft line item + contract` | `price_list.contract_price` |
| `billing_draft.tax_code` | `tax_rule.tax_code` |

## Billing draft shape

The draft is a header with lines, so it is published two ways:

| Endpoint | Shape | Use it for |
|---|---|---|
| `api/billing-drafts.json` | one row per draft, ~50 header fields including full bill-to and ship-to blocks, all four subtotals, tax registration and exemption certificate, order status and invoiced date | header-level checks, worklists |
| `api/billing-drafts/{draft_number}.json` | header plus nested `lines[]` and `totals` | working a single draft |
| `api/billing-draft-lines.json` | **one row per draft line, 93 columns** — every header field denormalised onto each line, plus `ref_` columns | field-by-field validation, CSV export, spreadsheet review |

Columns prefixed `ref_` on the flat endpoint are joined from the source objects — contract price and
discount, ordered and shipped quantity, PO validity and authorised value, contract payment terms,
incoterms, currency, freight terms, surcharge permission, tolerances, expected tax code/rate/treatment,
and proof of delivery date. They are what the draft *should* agree with. Drop them if you would rather
your validator fetch the truth itself from the source endpoints.

## Contents

10 customers across two operating units (US life sciences in USD, EU industrial in EUR),
10 contracts, 24 customer POs, 24 sales orders (90 lines), 22 deliveries, 20 billing drafts,
80 PDFs, 24 validated invoice fields, 14 seeded defects.

Line types are separated deliberately — `GOODS`, `SURCHARGE`, `FREIGHT` — because whether a
surcharge or freight line may be billed at all is a contract question, not a pricing question.

## What makes this useful for validation

`api/field-map.json` is the specification for your rule set: each invoice field, its authoritative
source, the precedence order when sources disagree, and the match rule.

| Field group | Authoritative source |
|---|---|
| Unit price, discount | `contract.price_list` → contract price, within `price_tolerance_pct` |
| Quantity billed | `delivery.shipped_quantity` — never the ordered quantity |
| PO number, validity, authorised value | `purchase_order` |
| Payment terms, incoterms, currency, billing rule | `contract` |
| Freight billable? Surcharge billable? | `contract.freight_terms`, `contract.surcharge_allowed` |
| Tax code, rate, treatment | `tax_rules` + `customer.tax_code` |
| Bill-to / ship-to | `customer` master sites |
| Duplicate check | `sales_order.invoiced_date` must be null |

## Seeded defects (answer key: `api/mismatches.json`)

| Finding | Draft | Severity |
|---|---|---|
| `price_off_contract` | BD-2026-5501 | critical |
| `qty_exceeds_shipped` | BD-2026-5503 | critical |
| `po_expired` | BD-2026-5505 | high |
| `po_limit_exceeded` | BD-2026-5506 | high |
| `missing_po` | BD-2026-5507 | high |
| `tax_treatment_wrong` | BD-2026-5509 | critical |
| `bill_to_address_stale` | BD-2026-5510 | medium |
| `surcharge_not_allowed` | BD-2026-5511 | high |
| `freight_not_billable` | BD-2026-5512 | high |
| `payment_terms_off_contract` | BD-2026-5513 | medium |
| `currency_mismatch` | BD-2026-5515 | critical |
| `total_math_error` | BD-2026-5516 | critical |
| `billing_before_delivery` | BD-2026-5517 | medium |
| `duplicate_billing` | BD-2026-5519 | critical |

Negative controls are in there on purpose: drafts BD-2026-5514 and BD-2026-5518 bill **less** than the
ordered quantity because those orders shipped partially. A rule that compares billed quantity to
*ordered* quantity will flag them and lose precision; comparing to *shipped* quantity is correct.

## Regenerating

```bash
pip install reportlab
python3 generate.py
```

Edit `DEFECT_PLAN` to change which drafts break and how. Everything else — JSON, PDFs, SQL — follows.

## Connecting your validation tool

Read-only JSON over static hosting. No auth, no keys, no rate limits, and GitHub Pages returns
`Access-Control-Allow-Origin: *` on every file including the PDFs, so browser clients work too.

### Recommended entry point

`api/validation-packages/{draft_number}.json` returns a billing draft **with every upstream object
already joined** — sales order, purchase order, contract with its price list, delivery, customer,
tax rules, item master, and the URLs of all four source PDFs. One request instead of six.

```python
import requests

BASE = "https://<you>.github.io/<repo>"

# 1. list the drafts that need validating
drafts = requests.get(f"{BASE}/api/validation-packages.json").json()["data"]

# 2. pull one complete package
pkg = requests.get(f"{BASE}/api/validation-packages/{drafts[0]['draft_number']}.json").json()

draft    = pkg["billing_draft"]     # what we intend to invoice
order    = pkg["sales_order"]       # what was ordered, plus holds and invoiced_date
po       = pkg["purchase_order"]    # validity window and authorised value
contract = pkg["contract"]          # terms, tolerances, price_list_lines
delivery = pkg["delivery"]          # shipped and backordered quantities
customer = pkg["customer"]          # bill-to / ship-to sites, tax registration
taxes    = pkg["tax_rules"]         # expected rate and treatment
items    = pkg["items"]             # list price, UOM, taxability per item on the draft

# 3. fetch a source document
pdf = requests.get(f"{BASE}/{pkg['documents'][0]['url']}").content
```

### Other access patterns

| Need | Endpoint |
|---|---|
| Pull the whole model once and validate offline | `api/bundle.json` (~340 KB, every object) |
| Introspect the API | `api/openapi.json` (OpenAPI 3.1) |
| Discover paths, join keys, counts | `api/index.json` |
| Every draft line as a flat table (one row per line, header denormalised) | `api/billing-draft-lines.json` |
| Individual objects | `api/{object}.json` and `api/{object}/{key}.json` |
| Source PDFs | `docs/{file_name}` — URLs are listed in `api/documents.json` |

Document URLs are relative to the site root; join them with your base URL.

### Caching

Files are static, so ETags and `If-None-Match` work normally. The dataset only changes when you
re-run `generate.py` and push, so a client can cache aggressively.

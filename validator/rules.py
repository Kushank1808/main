"""
Rule implementations for the Workday / POMS validation POC.

Each rule is a function `rule(inv, ctx) -> list[Finding]`. `ctx` is a Context
holding every side system already indexed by its join key. A rule returns an
empty list when it passes or is not applicable; findings carry the field, the
expected and actual values, and the remediation the billing desk should apply.

Outcome precedence per invoice:  HOLD  >  FAIL  >  PASS.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from decimal import Decimal, ROUND_HALF_UP


def money(x) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass
class Finding:
    rule_id: str
    severity: str
    outcome: str            # FAIL | HOLD | INFO
    field: str
    expected: object
    actual: object
    message: str
    remediation: str = ""
    line: int | None = None

    def as_dict(self):
        return asdict(self)


@dataclass
class Context:
    customers: dict = field(default_factory=dict)          # customer_id -> customer
    revenue_categories: dict = field(default_factory=dict)  # code -> rc
    poms: dict = field(default_factory=dict)                # order_number -> order
    nga: dict = field(default_factory=dict)                 # invoice_number -> tracker row
    factoring: dict = field(default_factory=dict)           # payment_id -> row
    dk_tracker: dict = field(default_factory=dict)          # poms_order_number -> row
    ey: dict = field(default_factory=dict)                  # workday_invoice_number -> ey final invoice
    salesforce: dict = field(default_factory=dict)          # workday_customer_id -> account
    rules: dict = field(default_factory=dict)               # rule_id -> catalogue row

    def sev(self, rule_id):
        return self.rules.get(rule_id, {}).get("severity", "high")


VEHICLE_ITEMS = {"P2-CAR", "P3-CAR", "P4-CAR"}


def vehicle_lines(inv):
    return [l for l in inv["lines"] if l["sales_item"] in VEHICLE_ITEMS and "Brand" in (l["line_item_description"] or "")]


def is_true_invoice(inv):
    """Prepayments, delivery notes and credit notes are not compared to the POMS order value."""
    kind = (inv.get("document_kind") or "").lower()
    return kind == "customer invoice"


# --------------------------------------------------------------------------- #
# Generic rules — every company
# --------------------------------------------------------------------------- #
def gen_001_line_math(inv, ctx):
    out = []
    for l in inv["lines"]:
        exp = money(l["quantity"] * l["unit_price"])
        if abs(exp - money(l["extended_amount"])) > 0.005:
            out.append(Finding("GEN-001", ctx.sev("GEN-001"), "FAIL", "extended_amount", exp, l["extended_amount"],
                               f"Line {l['line']}: extended amount {l['extended_amount']:,.2f} ≠ {l['quantity']} × {l['unit_price']:,.2f}",
                               f"Correct extended amount on line {l['line']} to {exp:,.2f}.", line=l["line"]))
    return out


def gen_002_poms_value(inv, ctx):
    if not is_true_invoice(inv):
        return []
    order = ctx.poms.get(inv.get("poms_order_number") or "")
    if not order:
        return [Finding("GEN-002", ctx.sev("GEN-002"), "FAIL", "poms_order_number", "existing POMS order",
                        inv.get("poms_order_number"), "Order number not found in POMS", "Correct the POMS order reference.")]
    tr = ctx.nga.get(inv["invoice_number"])
    if tr and tr.get("response_status") == "RESPONDED":
        return []            # NO21-004 governs once the NGA team has revised the amounts
    exp, act = money(order["gross_taxable_amount"]), money(inv["totals"]["subtotal"])
    if abs(exp - act) > 0.005:
        return [Finding("GEN-002", ctx.sev("GEN-002"), "FAIL", "totals.subtotal", exp, act,
                        f"Workday subtotal {act:,.2f} ≠ POMS gross taxable amount {exp:,.2f} on order {order['order_number']}",
                        "Amend the Workday lines to agree with POMS, or raise a POMS correction.")]
    return []


def gen_003_vin(inv, ctx):
    order = ctx.poms.get(inv.get("poms_order_number") or "")
    if not order or not inv.get("vin"):
        return []
    if inv["vin"] != order["vin"]:
        return [Finding("GEN-003", ctx.sev("GEN-003"), "FAIL", "vin", order["vin"], inv["vin"],
                        "VIN on the invoice differs from the POMS order", f"Correct VIN to {order['vin']}.")]
    return []


# --------------------------------------------------------------------------- #
# SE21 — related party revenue category
# --------------------------------------------------------------------------- #
def se21_001_related_party(inv, ctx):
    bt, st = ctx.customers.get(inv["bill_to_customer_id"], {}), ctx.customers.get(inv["sold_to_customer_id"], {})
    if not (bt.get("related_party") or st.get("related_party")):
        return []
    party = bt["customer_name"] if bt.get("related_party") else st["customer_name"]
    out = []
    for l in inv["lines"]:
        if "Brand" in (l["line_item_description"] or "") and l["revenue_category"] != "3030":
            out.append(Finding("SE21-001", ctx.sev("SE21-001"), "FAIL", "revenue_category", "3030", l["revenue_category"],
                               f"Line {l['line']}: related party ({party}) with 'Brand' description is on revenue category "
                               f"{l['revenue_category']} — must be 3030",
                               f"Manually change revenue category on line {l['line']} to 3030 (Car Sales - Related Party).", line=l["line"]))
    return out


# --------------------------------------------------------------------------- #
# NO21 — NGA tracker process, POMS match, factoring
# --------------------------------------------------------------------------- #
NGA_REQUIRED = ("invoice_number", "customer_id", "model_number", "total_invoice_price", "gross_taxable_amount", "base_price")


def no21_001_tracker_captured(inv, ctx):
    bt = ctx.customers.get(inv["bill_to_customer_id"], {})
    if not bt.get("nga_customer"):
        return []
    tr = ctx.nga.get(inv["invoice_number"])
    if not tr:
        return [Finding("NO21-001", ctx.sev("NO21-001"), "FAIL", "nga_tracker", "tracker row", None,
                        f"NGA customer {bt['customer_name']}: invoice not captured in the NGA tracker",
                        "Capture invoice number, customer ID, model number, total price, gross/taxable amount and base price in the tracker.")]
    missing = [f for f in NGA_REQUIRED if tr.get(f) in (None, "")]
    if missing:
        return [Finding("NO21-001", ctx.sev("NO21-001"), "FAIL", "nga_tracker", "all required fields", f"missing: {', '.join(missing)}",
                        f"NGA tracker row {tr['tracker_id']} is incomplete ({', '.join(missing)})",
                        f"Complete the tracker row {tr['tracker_id']} before requesting NGA review.")]
    return []


def no21_002_response_received(inv, ctx):
    tr = ctx.nga.get(inv["invoice_number"])
    if not tr or any(tr.get(f) in (None, "") for f in NGA_REQUIRED):
        return []            # NO21-001 already reports the missing / incomplete row
    if tr.get("response_status") != "RESPONDED":
        return [Finding("NO21-002", ctx.sev("NO21-002"), "HOLD", "nga_tracker.response_status", "RESPONDED", tr.get("response_status"),
                        f"NGA team response pending since {tr.get('submitted_on')} — invoice cannot proceed",
                        "Wait for the NGA feedback (fees decision, revised gross amount, revised base price).")]
    return []


def no21_003_fees_removed(inv, ctx):
    tr = ctx.nga.get(inv["invoice_number"])
    if not tr or tr.get("response_status") != "RESPONDED" or not tr.get("remove_fees"):
        return []
    fee_lines = [l for l in inv["lines"] if ctx.revenue_categories.get(l["revenue_category"], {}).get("is_fee")]
    if fee_lines:
        nos = ", ".join(str(l["line"]) for l in fee_lines)
        return [Finding("NO21-003", ctx.sev("NO21-003"), "FAIL", "lines", "no fee lines", f"fee lines {nos}",
                        f"NGA instructed fee removal but fee lines {nos} remain ({', '.join(l['sales_item_name'] for l in fee_lines)})",
                        f"Remove lines {nos}, then update gross amount, base price and recalculate VAT.")]
    return []


def no21_004_revised_amounts(inv, ctx):
    tr = ctx.nga.get(inv["invoice_number"])
    if not tr or tr.get("response_status") != "RESPONDED":
        return []
    out = []
    if tr.get("revised_gross_amount") is not None:
        exp, act = money(tr["revised_gross_amount"]), money(inv["tax"]["taxable_amount"])
        if abs(exp - act) > 0.005:
            out.append(Finding("NO21-004", ctx.sev("NO21-004"), "FAIL", "tax.taxable_amount", exp, act,
                               f"Gross/taxable amount {act:,.2f} ≠ revised gross {exp:,.2f} from tracker {tr['tracker_id']}",
                               f"Update gross amount to {exp:,.2f}."))
    if tr.get("revised_base_price") is not None:
        veh = vehicle_lines(inv)
        if veh:
            exp, act = money(tr["revised_base_price"]), money(veh[0]["unit_price"])
            if abs(exp - act) > 0.005:
                out.append(Finding("NO21-004", ctx.sev("NO21-004"), "FAIL", "unit_price", exp, act,
                                   f"Vehicle base price {act:,.2f} ≠ revised base {exp:,.2f} from tracker",
                                   f"Update base price on line {veh[0]['line']} to {exp:,.2f}.", line=veh[0]["line"]))
    return out


def no21_005_tax_recalculated(inv, ctx):
    rate = inv["tax"]["tax_rate"]
    exp, act = money(inv["tax"]["taxable_amount"] * rate / 100), money(inv["tax"]["tax_amount"])
    if abs(exp - act) > 0.005:
        return [Finding("NO21-005", ctx.sev("NO21-005"), "FAIL", "tax.tax_amount", exp, act,
                        f"VAT {act:,.2f} is not {rate:g}% of the taxable amount {inv['tax']['taxable_amount']:,.2f} (expected {exp:,.2f})",
                        "Recalculate and update VAT after amending fee lines, gross amount or base price.")]
    return []


def no21_007_factoring(inv, ctx):
    pa = inv.get("payment_application")
    if not pa or pa.get("applied_as") != "ON_ACCOUNT":
        return []
    if pa["payment_id"] not in ctx.factoring:
        return [Finding("NO21-007", ctx.sev("NO21-007"), "FAIL", "payment_application.payment_id", "captured in factoring tracker",
                        f"{pa['payment_id']} not found",
                        f"Payment {pa['payment_id']} ({pa['amount']:,.2f} {inv['currency']}) recorded On Account but not captured in the factoring tracker",
                        "Log the payment in the factoring tracker and re-apply it to the invoice.")]
    return []


# --------------------------------------------------------------------------- #
# PT21 — leasing plates, loans, VAT numbers, E&Y, gapless numbering
# --------------------------------------------------------------------------- #
def pt21_001_license_plate(inv, ctx):
    bt = ctx.customers.get(inv["bill_to_customer_id"], {})
    if not bt.get("leasing_plate_required"):
        return []
    order = ctx.poms.get(inv.get("poms_order_number") or "", {})
    plate = order.get("license_plate")
    veh = vehicle_lines(inv)
    if not veh:
        return []
    out = []
    for l in veh:
        desc = l["line_item_description"] or ""
        if not plate:
            out.append(Finding("PT21-001", ctx.sev("PT21-001"), "FAIL", "poms.license_plate", "plate in POMS", None,
                               "Leasing customer but POMS has no licence plate yet", "Obtain the plate from POMS / market before invoicing.", line=l["line"]))
        elif plate not in desc:
            out.append(Finding("PT21-001", ctx.sev("PT21-001"), "FAIL", "line_item_description", f"contains {plate}", desc,
                               f"Line {l['line']}: licence plate {plate} (POMS) missing from the description for {bt['customer_name']}",
                               f"Append ' - Matrícula {plate}' to the vehicle line description.", line=l["line"]))
    return out


def pt21_002_personal_loan(inv, ctx):
    order = ctx.poms.get(inv.get("poms_order_number") or "", {})
    if order.get("financing_type") != "PERSONAL_LOAN":
        return []
    partner = ctx.customers.get(order.get("financing_partner_id") or "", {})
    if partner.get("bpi_exception"):
        return []
    buyer = order["buyer_customer_id"]
    out = []
    if inv["bill_to_customer_id"] != buyer:
        out.append(Finding("PT21-002", ctx.sev("PT21-002"), "FAIL", "bill_to_customer", order["buyer_name"], inv["bill_to_customer"],
                           f"Personal loan via {partner.get('customer_name')}: Bill-To must be the buyer {order['buyer_name']}",
                           f"Change Bill-To to {order['buyer_name']} (Bill-To = Sold-To = Buyer)."))
    if inv["sold_to_customer_id"] != buyer:
        out.append(Finding("PT21-002", ctx.sev("PT21-002"), "FAIL", "sold_to_customer", order["buyer_name"], inv["sold_to_customer"],
                           "Personal loan: Sold-To must be the buyer", f"Change Sold-To to {order['buyer_name']}."))
    return out


def pt21_003_bpi(inv, ctx):
    order = ctx.poms.get(inv.get("poms_order_number") or "", {})
    partner = ctx.customers.get(order.get("financing_partner_id") or "", {})
    if not partner.get("bpi_exception"):
        return []
    out = []
    for fld in ("bill_to", "sold_to"):
        if inv[f"{fld}_customer_id"] != partner["customer_id"]:
            out.append(Finding("PT21-003", ctx.sev("PT21-003"), "FAIL", f"{fld}_customer", partner["customer_name"], inv[f"{fld}_customer"],
                               f"Banco BPI exception: {fld.replace('_', '-').title()} must be {partner['customer_name']}",
                               f"Change {fld.replace('_', '-').title()} to {partner['customer_name']} (Bill-To = Sold-To = loan provider)."))
    return out


def pt21_004_vat_number(inv, ctx):
    kind = (inv.get("document_kind") or "").lower()
    if not ("extra" in kind or "prepayment" in kind):
        return []
    if inv.get("customer_vat_number"):
        return []
    sf = ctx.salesforce.get(inv["bill_to_customer_id"])
    hint = f"Salesforce account {sf['sf_account_id']} holds {sf['vat_number']}" if sf else "not in Salesforce either — ask market / sales"
    return [Finding("PT21-004", ctx.sev("PT21-004"), "FAIL", "customer_vat_number", sf["vat_number"] if sf else "populated", None,
                    f"VAT number missing on {inv['document_kind']} for {inv['bill_to_customer']} ({hint})",
                    f"Populate customer VAT number{' ' + sf['vat_number'] if sf else ''} before sending to E&Y.")]


def pt21_005_ey_match(inv, ctx):
    ey = ctx.ey.get(inv["invoice_number"])
    if not ey:
        return []
    checks = [
        ("invoice_date", inv["invoice_date"], ey["invoice_date"]),
        ("bill_to_customer", inv["bill_to_customer"], ey["customer_name"]),
        ("po_number", inv.get("po_number"), ey.get("po_number")),
        ("vin", inv.get("vin"), ey.get("vin")),
        ("totals.subtotal", money(inv["totals"]["subtotal"]), money(ey["amount_excl_vat"])),
        ("totals.total_amount", money(inv["totals"]["total_amount"]), money(ey["total_amount"])),
    ]
    out = []
    for fld, wd, eyv in checks:
        if wd != eyv:
            out.append(Finding("PT21-005", ctx.sev("PT21-005"), "FAIL", fld, eyv, wd,
                               f"{fld} differs between Workday ({wd}) and E&Y final invoice {ey['ey_invoice_number']} ({eyv})",
                               "Before Workday approval: mirror the E&Y details or have E&Y reissue. After approval: credit note and rebill, "
                               "reason 'Manual credit and rebill due to E&Y error.'"))
    return out


def pt21_006_gapless(inv, ctx):
    if not inv.get("statutory_invoice_type"):
        return []
    ey = ctx.ey.get(inv["invoice_number"])
    if inv.get("status") == "APPROVED" and not ey:
        return [Finding("PT21-006", ctx.sev("PT21-006"), "FAIL", "status", "DRAFT until E&Y final received", "APPROVED",
                        "Approved in Workday before the E&Y final invoice was received — breaks the gapless sequence",
                        "Approve only after E&Y's final invoice, strictly in E&Y sequence.")]
    if ey and inv.get("statutory_invoice_number") != ey["ey_invoice_number"]:
        return [Finding("PT21-006", ctx.sev("PT21-006"), "FAIL", "statutory_invoice_number", ey["ey_invoice_number"], inv.get("statutory_invoice_number"),
                        f"Statutory number {inv.get('statutory_invoice_number')} does not match E&Y {ey['ey_invoice_number']} "
                        f"({ey['statutory_invoice_type']}, sequence {ey['sequence']})",
                        "Set the statutory invoice number to the E&Y number and approve in sequence.")]
    return []


def pt21_007_exclude_internal(inv, ctx):
    kind = (inv.get("document_kind") or "").lower()
    if ("delivery note" in kind or "extra" in kind) and money(inv["totals"]["total_amount"]) == 0.0:
        return [Finding("PT21-007", "info", "INFO", "document_kind", "excluded from E&Y report", inv["document_kind"],
                        "Zero-value internal document — exclude from the daily E&Y report", "")]
    return []


# --------------------------------------------------------------------------- #
# DK21 — SharePoint tracker
# --------------------------------------------------------------------------- #
def dk21_001_tracker(inv, ctx):
    bt = ctx.customers.get(inv["bill_to_customer_id"], {})
    if not bt.get("sharepoint_tracker"):
        return []
    tr = ctx.dk_tracker.get(inv.get("poms_order_number") or "")
    if not tr:
        return []
    out = []
    if (inv.get("po_number") or "") != tr["required_po_reference"]:
        out.append(Finding("DK21-001", ctx.sev("DK21-001"), "FAIL", "po_number", tr["required_po_reference"], inv.get("po_number"),
                           f"PO reference does not match tracker {tr['tracker_id']}", f"Set PO number to {tr['required_po_reference']}."))
    veh = vehicle_lines(inv)
    if veh:
        exp, act = money(tr["agreed_unit_price"]), money(veh[0]["unit_price"])
        if abs(exp - act) > 0.005:
            out.append(Finding("DK21-001", ctx.sev("DK21-001"), "FAIL", "unit_price", exp, act,
                               f"Vehicle price {act:,.2f} ≠ agreed price {exp:,.2f} in tracker {tr['tracker_id']}",
                               f"Change unit price on line {veh[0]['line']} to {exp:,.2f}.", line=veh[0]["line"]))
        if tr["required_description_text"] not in (veh[0]["line_item_description"] or ""):
            out.append(Finding("DK21-001", ctx.sev("DK21-001"), "FAIL", "line_item_description", f"contains '{tr['required_description_text']}'",
                               veh[0]["line_item_description"], "Required description text from the tracker is missing",
                               f"Append '{tr['required_description_text']}' to line {veh[0]['line']}.", line=veh[0]["line"]))
    return out


RULES_BY_COMPANY = {
    "ALL": [gen_001_line_math, gen_002_poms_value, gen_003_vin],
    "SE21": [se21_001_related_party],
    "NO21": [no21_001_tracker_captured, no21_002_response_received, no21_003_fees_removed,
             no21_004_revised_amounts, no21_005_tax_recalculated, no21_007_factoring],
    "PT21": [pt21_001_license_plate, pt21_002_personal_loan, pt21_003_bpi, pt21_004_vat_number,
             pt21_005_ey_match, pt21_006_gapless, pt21_007_exclude_internal],
    "DK21": [dk21_001_tracker],
}


def validate_invoice(inv: dict, ctx: Context) -> dict:
    findings: list[Finding] = []
    for rule in RULES_BY_COMPANY["ALL"] + RULES_BY_COMPANY.get(inv["company"], []):
        findings.extend(rule(inv, ctx))
    outcomes = {f.outcome for f in findings}
    status = "HOLD" if "HOLD" in outcomes else "FAIL" if "FAIL" in outcomes else "PASS"
    rule_ids = sorted({f.rule_id for f in findings if f.outcome in ("FAIL", "HOLD")})
    return {
        "invoice_number": inv["invoice_number"], "company": inv["company"], "document_kind": inv.get("document_kind"),
        "bill_to_customer": inv["bill_to_customer"], "sold_to_customer": inv["sold_to_customer"],
        "poms_order_number": inv.get("poms_order_number"), "invoice_status": inv.get("status"),
        "total_amount": inv["totals"]["total_amount"], "currency": inv["currency"],
        "status": status, "rules_failed": rule_ids,
        "finding_count": sum(1 for f in findings if f.outcome != "INFO"),
        "findings": [f.as_dict() for f in findings],
    }

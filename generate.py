#!/usr/bin/env python3
"""
ORBIS — Order & Revenue Billing Information System.

Generates a dummy Oracle/SAP-style pre-billing dataset for a billing validation
POC: customer master, contracts, customer POs, sales orders with lines,
deliveries, tax rules, and the pre-invoice billing drafts that a validation tool
is meant to check. Source documents (contract, PO, order acknowledgement,
delivery note) are rendered as real PDFs.

POMS-style pattern: everything is emitted as static JSON so it can be hosted on
GitHub Pages and consumed as an API.

Run:  python3 generate.py
"""
from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

random.seed(4711)
ROOT = os.path.dirname(os.path.abspath(__file__))
API = os.path.join(ROOT, "api")
DOCS = os.path.join(ROOT, "docs")

TODAY = date(2026, 8, 26)


def money(x) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def dump(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


# =========================================================================== #
# 1. LEGAL ENTITIES / OPERATING UNITS
# =========================================================================== #
OPERATING_UNITS = [
    {
        "operating_unit": "GEAM_OU_USD_LS_US_BIO_WBO",
        "legal_entity": "ORBIS Life Sciences Inc.",
        "entity_country": "US",
        "entity_address": "455 Bioscience Parkway, Marlborough, MA 01752, United States",
        "tax_registration": "US-EIN 04-3921188",
        "currency": "USD",
        "ledger": "ORBIS US Primary Ledger",
        "business_line": "Bioprocess & Lab Consumables",
    },
    {
        "operating_unit": "GEAM_OU_EUR_IND_EU_TRB_WBO",
        "legal_entity": "ORBIS Industrial Solutions Ireland Ltd",
        "entity_country": "IE",
        "entity_address": "Eastgate Business Park, Little Island, Cork T45 K294, Ireland",
        "tax_registration": "IE 9812345K",
        "currency": "EUR",
        "ledger": "ORBIS EMEA Primary Ledger",
        "business_line": "Rotating Equipment & Flow Control",
    },
]
OU_US = OPERATING_UNITS[0]["operating_unit"]
OU_EU = OPERATING_UNITS[1]["operating_unit"]


# =========================================================================== #
# 2. TAX RULES
# =========================================================================== #
TAX_RULES = [
    {"tax_code": "US-AR-EXEMPT", "jurisdiction": "US-AR", "rate": 0.0, "treatment": "EXEMPT",
     "basis": "Non-profit hospital exemption certificate on file.", "requires_certificate": True},
    {"tax_code": "US-MN-EXEMPT", "jurisdiction": "US-MN", "rate": 0.0, "treatment": "EXEMPT",
     "basis": "Non-profit hospital exemption certificate on file.", "requires_certificate": True},
    {"tax_code": "US-OH-EXEMPT", "jurisdiction": "US-OH", "rate": 0.0, "treatment": "EXEMPT",
     "basis": "Non-profit hospital exemption certificate on file.", "requires_certificate": True},
    {"tax_code": "US-MA-SALES", "jurisdiction": "US-MA", "rate": 6.25, "treatment": "SALES_TAX",
     "basis": "Massachusetts state sales tax on tangible goods.", "requires_certificate": False},
    {"tax_code": "US-TX-EXEMPT", "jurisdiction": "US-TX", "rate": 0.0, "treatment": "EXEMPT",
     "basis": "State university exemption certificate on file.", "requires_certificate": True},
    {"tax_code": "US-PR-ZERO", "jurisdiction": "US-PR", "rate": 0.0, "treatment": "ZERO_RATED",
     "basis": "Puerto Rico manufacturing exemption (Act 60).", "requires_certificate": True},
    {"tax_code": "EU-RC-0", "jurisdiction": "EU-INTRA", "rate": 0.0, "treatment": "REVERSE_CHARGE",
     "basis": "Intra-Community supply, Art. 138 VAT Directive. VAT accounted by recipient.",
     "requires_certificate": False, "requires_vat_id": True},
    {"tax_code": "IE-VAT-23", "jurisdiction": "IE", "rate": 23.0, "treatment": "DOMESTIC_VAT",
     "basis": "Irish domestic supply, standard rate.", "requires_certificate": False},
]
TAX_BY_CODE = {t["tax_code"]: t for t in TAX_RULES}


# =========================================================================== #
# 3. CUSTOMER MASTER
# =========================================================================== #
CUSTOMERS = [
    {
        "customer_id": "C-100428", "customer_name": "ARKANSAS CHILDRENS HOSP",
        "customer_class": "HEALTHCARE-IDN", "country": "US", "currency": "USD",
        "operating_unit": OU_US, "tax_code": "US-AR-EXEMPT",
        "tax_registration": "US-EIN 71-0236856", "exemption_certificate": "AR-EX-8841207",
        "credit_limit": 750000, "payment_terms": "Net 45", "collector": "Bhattacharjee, Arpan",
        "bill_to": {"site_use_id": "BT-100428-1", "name": "ARKANSAS CHILDRENS HOSP",
                    "address_1": "ARKANSAS CHILDRENS HOSP", "address_2": "ACCOUNTS PAYABLE",
                    "address_3": "-", "address_4": "1 CHILDRENS WAY",
                    "city": "Little Rock", "state": "AR", "postal_code": "72202", "country": "US"},
        "ship_to": {"site_use_id": "ST-100428-1", "name": "ARKANSAS CHILDRENS HOSP",
                    "address_1": "ARKANSAS CHILDRENS HOSP", "address_2": "WAREHOUSE",
                    "address_3": "-", "address_4": "2410 W 8TH STREET",
                    "city": "Little Rock", "state": "AR", "postal_code": "72202", "country": "US"},
        "contact_name": "Mary Heroux", "contact_email": "HerouxME@archildrens.org",
        "contact_phone": "501-364-1100",
    },
    {
        "customer_id": "C-100731", "customer_name": "MAYO FDN",
        "customer_class": "HEALTHCARE-IDN", "country": "US", "currency": "USD",
        "operating_unit": OU_US, "tax_code": "US-MN-EXEMPT",
        "tax_registration": "US-EIN 41-6011702", "exemption_certificate": "MN-EX-2277341",
        "credit_limit": 2500000, "payment_terms": "Net 60", "collector": "C N, Pavithra",
        "bill_to": {"site_use_id": "BT-100731-1", "name": "MAYO CLINIC",
                    "address_1": "MAYO CLINIC", "address_2": "SUPPLY CHAIN AP",
                    "address_3": "-", "address_4": "200 1ST ST SW",
                    "city": "ROCHESTER", "state": "MN", "postal_code": "55905", "country": "US"},
        "ship_to": {"site_use_id": "ST-100731-1", "name": "MAYO FDN",
                    "address_1": "MAYO FDN", "address_2": "INV INVENTORY CENTER",
                    "address_3": "-", "address_4": "3131 VALLEY HIGH RD NW",
                    "city": "Rochester", "state": "MN", "postal_code": "55901", "country": "US"},
        "contact_name": "INV Inventory Center Procurement",
        "contact_email": "orderconfirmations@mayo.edu", "contact_phone": "507-266-5551",
    },
    {
        "customer_id": "C-101902", "customer_name": "SARTORIUS STEDIM FILTERS",
        "customer_class": "OEM-MANUFACTURER", "country": "US", "currency": "USD",
        "operating_unit": OU_US, "tax_code": "US-PR-ZERO",
        "tax_registration": "US-EIN 66-0512340", "exemption_certificate": "PR-ACT60-11938",
        "credit_limit": 1200000, "payment_terms": "Net 30", "collector": "Kumar, Abhijeet",
        "bill_to": {"site_use_id": "BT-101902-1", "name": "SARTORIUS STEDIM FILTERS",
                    "address_1": "SARTORIUS STEDIM FILTERS", "address_2": "ACCOUNTS PAYABLE",
                    "address_3": "-", "address_4": "PO BOX 6",
                    "city": "Yauco", "state": "PR", "postal_code": "00698", "country": "US"},
        "ship_to": {"site_use_id": "ST-101902-1", "name": "SARTORIUS PUERTO RICO",
                    "address_1": "SARTORIUS PUERTO RICO", "address_2": "-",
                    "address_3": "INT 368 KM 12 H 9", "address_4": "ROAD 128",
                    "city": "Yauco", "state": "PR", "postal_code": "00698", "country": "US"},
        "contact_name": "Astrid Oms A", "contact_email": "astrid.oms@sartorius.com",
        "contact_phone": "787-856-5020",
    },
    {
        "customer_id": "C-102255", "customer_name": "CLEVELAND CLINIC FDN",
        "customer_class": "HEALTHCARE-IDN", "country": "US", "currency": "USD",
        "operating_unit": OU_US, "tax_code": "US-OH-EXEMPT",
        "tax_registration": "US-EIN 34-0714585", "exemption_certificate": "OH-EX-5540912",
        "credit_limit": 1800000, "payment_terms": "Net 45", "collector": "Bhattacharjee, Arpan",
        "bill_to": {"site_use_id": "BT-102255-1", "name": "CLEVELAND CLINIC FDN",
                    "address_1": "CLEVELAND CLINIC FDN", "address_2": "ACCOUNTS PAYABLE MC W14",
                    "address_3": "-", "address_4": "9500 EUCLID AVE",
                    "city": "Cleveland", "state": "OH", "postal_code": "44195", "country": "US"},
        "ship_to": {"site_use_id": "ST-102255-1", "name": "CLEVELAND CLINIC FDN",
                    "address_1": "CLEVELAND CLINIC FDN", "address_2": "CENTRAL RECEIVING DOCK 4",
                    "address_3": "-", "address_4": "2049 E 100TH ST",
                    "city": "Cleveland", "state": "OH", "postal_code": "44106", "country": "US"},
        "contact_name": "Dana Whitfield", "contact_email": "whitfid@ccf.org",
        "contact_phone": "216-444-2200",
    },
    {
        "customer_id": "C-102640", "customer_name": "CHARLES RIVER LABS",
        "customer_class": "CRO-RESEARCH", "country": "US", "currency": "USD",
        "operating_unit": OU_US, "tax_code": "US-MA-SALES",
        "tax_registration": "US-EIN 06-1397316", "exemption_certificate": None,
        "credit_limit": 900000, "payment_terms": "Net 30", "collector": "Kumar, Abhijeet",
        "bill_to": {"site_use_id": "BT-102640-1", "name": "CHARLES RIVER LABS",
                    "address_1": "CHARLES RIVER LABORATORIES INTL", "address_2": "AP SHARED SERVICES",
                    "address_3": "-", "address_4": "251 BALLARDVALE ST",
                    "city": "Wilmington", "state": "MA", "postal_code": "01887", "country": "US"},
        "ship_to": {"site_use_id": "ST-102640-1", "name": "CHARLES RIVER LABS",
                    "address_1": "CHARLES RIVER LABORATORIES", "address_2": "RECEIVING BLDG C",
                    "address_3": "-", "address_4": "334 SOUTH ST",
                    "city": "Shrewsbury", "state": "MA", "postal_code": "01545", "country": "US"},
        "contact_name": "Gregory Nunes", "contact_email": "greg.nunes@criver.com",
        "contact_phone": "978-658-6000",
    },
    {
        "customer_id": "C-103018", "customer_name": "UT MD ANDERSON CANCER CTR",
        "customer_class": "ACADEMIC-MEDICAL", "country": "US", "currency": "USD",
        "operating_unit": OU_US, "tax_code": "US-TX-EXEMPT",
        "tax_registration": "US-EIN 74-6001118", "exemption_certificate": "TX-EX-3390174",
        "credit_limit": 1400000, "payment_terms": "Net 45", "collector": "C N, Pavithra",
        "bill_to": {"site_use_id": "BT-103018-1", "name": "UT MD ANDERSON CANCER CTR",
                    "address_1": "UT MD ANDERSON CANCER CTR", "address_2": "ACCOUNTS PAYABLE UNIT 1682",
                    "address_3": "-", "address_4": "PO BOX 301407",
                    "city": "Houston", "state": "TX", "postal_code": "77230", "country": "US"},
        "ship_to": {"site_use_id": "ST-103018-1", "name": "UT MD ANDERSON CANCER CTR",
                    "address_1": "UT MD ANDERSON CANCER CTR", "address_2": "CENTRAL RECEIVING",
                    "address_3": "-", "address_4": "1515 HOLCOMBE BLVD",
                    "city": "Houston", "state": "TX", "postal_code": "77030", "country": "US"},
        "contact_name": "Rosa Delgado", "contact_email": "rdelgado@mdanderson.org",
        "contact_phone": "713-792-2121",
    },
    {
        "customer_id": "C-200114", "customer_name": "NORDWIND TURBINES GMBH",
        "customer_class": "OEM-MANUFACTURER", "country": "DE", "currency": "EUR",
        "operating_unit": OU_EU, "tax_code": "EU-RC-0",
        "tax_registration": "DE 812447906", "exemption_certificate": None,
        "credit_limit": 3000000, "payment_terms": "Net 45", "collector": "Voss, Henrik",
        "bill_to": {"site_use_id": "BT-200114-1", "name": "NORDWIND TURBINES GMBH",
                    "address_1": "NORDWIND TURBINES GMBH", "address_2": "ACCOUNTS PAYABLE",
                    "address_3": "-", "address_4": "POSTFACH 44",
                    "city": "Hamburg", "state": "HH", "postal_code": "20095", "country": "DE"},
        "ship_to": {"site_use_id": "ST-200114-1", "name": "NORDWIND TURBINES GMBH",
                    "address_1": "NORDWIND TURBINES GMBH", "address_2": "PLANT 2 GOODS-IN",
                    "address_3": "-", "address_4": "OTTENSENER STR. 9",
                    "city": "Hamburg", "state": "HH", "postal_code": "22765", "country": "DE"},
        "contact_name": "Katrin Bauer", "contact_email": "k.bauer@nordwind-turbines.de",
        "contact_phone": "+49 40 4711 220",
    },
    {
        "customer_id": "C-200380", "customer_name": "HELIOS FLUID SYSTEMS SAS",
        "customer_class": "OEM-MANUFACTURER", "country": "FR", "currency": "EUR",
        "operating_unit": OU_EU, "tax_code": "EU-RC-0",
        "tax_registration": "FR 47812993041", "exemption_certificate": None,
        "credit_limit": 1600000, "payment_terms": "Net 60", "collector": "Voss, Henrik",
        "bill_to": {"site_use_id": "BT-200380-1", "name": "HELIOS FLUID SYSTEMS SAS",
                    "address_1": "HELIOS FLUID SYSTEMS SAS", "address_2": "SERVICE COMPTABILITE",
                    "address_3": "-", "address_4": "14 RUE DE LA VILLETTE",
                    "city": "Lyon", "state": "ARA", "postal_code": "69003", "country": "FR"},
        "ship_to": {"site_use_id": "ST-200380-1", "name": "HELIOS FLUID SYSTEMS SAS",
                    "address_1": "HELIOS FLUID SYSTEMS SAS", "address_2": "ATELIER SUD RECEPTION",
                    "address_3": "-", "address_4": "ZI DES GRANDES TERRES",
                    "city": "Saint-Priest", "state": "ARA", "postal_code": "69800", "country": "FR"},
        "contact_name": "Émilie Rousseau", "contact_email": "e.rousseau@helios-fluid.fr",
        "contact_phone": "+33 4 72 11 88 40",
    },
    {
        "customer_id": "C-200552", "customer_name": "VANTA ENERGY SYSTEMS AB",
        "customer_class": "EPC-CONTRACTOR", "country": "SE", "currency": "EUR",
        "operating_unit": OU_EU, "tax_code": "EU-RC-0",
        "tax_registration": "SE 556677889901", "exemption_certificate": None,
        "credit_limit": 1100000, "payment_terms": "Net 30", "collector": "Voss, Henrik",
        "bill_to": {"site_use_id": "BT-200552-1", "name": "VANTA ENERGY SYSTEMS AB",
                    "address_1": "VANTA ENERGY SYSTEMS AB", "address_2": "LEVERANTORSFAKTUROR",
                    "address_3": "-", "address_4": "BOX 1188",
                    "city": "Malmö", "state": "SK", "postal_code": "21120", "country": "SE"},
        "ship_to": {"site_use_id": "ST-200552-1", "name": "VANTA ENERGY SYSTEMS AB",
                    "address_1": "VANTA ENERGY SYSTEMS AB", "address_2": "GODSMOTTAGNING",
                    "address_3": "-", "address_4": "INDUSTRIGATAN 42",
                    "city": "Malmö", "state": "SK", "postal_code": "21275", "country": "SE"},
        "contact_name": "Anders Lindgren", "contact_email": "a.lindgren@vantaenergy.se",
        "contact_phone": "+46 40 660 1200",
    },
    {
        "customer_id": "C-200790", "customer_name": "BRAEMAR PROCESS LTD",
        "customer_class": "DISTRIBUTOR", "country": "IE", "currency": "EUR",
        "operating_unit": OU_EU, "tax_code": "IE-VAT-23",
        "tax_registration": "IE 6389047T", "exemption_certificate": None,
        "credit_limit": 600000, "payment_terms": "Net 30", "collector": "Voss, Henrik",
        "bill_to": {"site_use_id": "BT-200790-1", "name": "BRAEMAR PROCESS LTD",
                    "address_1": "BRAEMAR PROCESS LTD", "address_2": "FINANCE DEPT",
                    "address_3": "-", "address_4": "UNIT 7 KILBARRY BUSINESS PARK",
                    "city": "Cork", "state": "CO", "postal_code": "T23 XH92", "country": "IE"},
        "ship_to": {"site_use_id": "ST-200790-1", "name": "BRAEMAR PROCESS LTD",
                    "address_1": "BRAEMAR PROCESS LTD", "address_2": "STORES",
                    "address_3": "-", "address_4": "UNIT 7 KILBARRY BUSINESS PARK",
                    "city": "Cork", "state": "CO", "postal_code": "T23 XH92", "country": "IE"},
        "contact_name": "Sinead Kelleher", "contact_email": "s.kelleher@braemarprocess.ie",
        "contact_phone": "+353 21 450 9900",
    },
]
CUST_BY_ID = {c["customer_id"]: c for c in CUSTOMERS}


# =========================================================================== #
# 4. ITEM MASTER
# =========================================================================== #
ITEMS = [
    {"item_number": "VMPKPED", "description": "Vacuum Manifold Pack, Pediatric, sterile, 50/cs",
     "item_class": "CONSUMABLE", "uom": "EA", "list_price": 8.05, "line_type": "GOODS",
     "taxable": True, "hs_code": "9018.90", "operating_unit": OU_US},
    {"item_number": "NEO96", "description": "Neonatal Assay Plate, 96-well, non-treated",
     "item_class": "CONSUMABLE", "uom": "EA", "list_price": 7.36, "line_type": "GOODS",
     "taxable": True, "hs_code": "3926.90", "operating_unit": OU_US},
    {"item_number": "KA2V002PV1G", "description": "Filter Cartridge 0.2um PVDF, 10in, gamma-irradiated",
     "item_class": "FILTRATION", "uom": "EA", "list_price": 322.00, "line_type": "GOODS",
     "taxable": True, "hs_code": "8421.29", "operating_unit": OU_US},
    {"item_number": "CELLCUL500", "description": "Cell Culture Media, 500mL, animal-origin free",
     "item_class": "MEDIA", "uom": "BT", "list_price": 96.40, "line_type": "GOODS",
     "taxable": True, "hs_code": "3821.00", "operating_unit": OU_US},
    {"item_number": "BIOPROC-FLT-22", "description": "Bioprocess Inline Filter Assembly, 2.2in TC",
     "item_class": "FILTRATION", "uom": "EA", "list_price": 214.75, "line_type": "GOODS",
     "taxable": True, "hs_code": "8421.29", "operating_unit": OU_US},
    {"item_number": "CHROM-COL-16", "description": "Chromatography Column, 16mm, borosilicate",
     "item_class": "EQUIPMENT", "uom": "EA", "list_price": 1875.00, "line_type": "GOODS",
     "taxable": True, "hs_code": "9027.20", "operating_unit": OU_US},
    {"item_number": "TARIFF_SURCHARGE", "description": "Section 301 tariff surcharge, pass-through",
     "item_class": "SURCHARGE", "uom": "EA", "list_price": 0.00, "line_type": "SURCHARGE",
     "taxable": False, "hs_code": None, "operating_unit": OU_US},
    {"item_number": "FREIGHT-US", "description": "Outbound freight and handling",
     "item_class": "FREIGHT", "uom": "EA", "list_price": 0.00, "line_type": "FREIGHT",
     "taxable": False, "hs_code": None, "operating_unit": OU_US},
    {"item_number": "AX-PMP-320", "description": "Centrifugal Pump Assembly, 320mm impeller, SS316",
     "item_class": "ROTATING-EQUIP", "uom": "EA", "list_price": 1850.00, "line_type": "GOODS",
     "taxable": True, "hs_code": "8413.70", "operating_unit": OU_EU},
    {"item_number": "AX-SEAL-88", "description": "Mechanical Seal Kit, tungsten carbide faces",
     "item_class": "SPARES", "uom": "EA", "list_price": 145.00, "line_type": "GOODS",
     "taxable": True, "hs_code": "8484.20", "operating_unit": OU_EU},
    {"item_number": "AX-BRG-540", "description": "High-load Bearing Set, sealed, Class 5",
     "item_class": "SPARES", "uom": "SET", "list_price": 410.00, "line_type": "GOODS",
     "taxable": True, "hs_code": "8482.10", "operating_unit": OU_EU},
    {"item_number": "AX-GSKT-12", "description": "Gasket and Fastener Pack (per pump)",
     "item_class": "SPARES", "uom": "PK", "list_price": 62.50, "line_type": "GOODS",
     "taxable": True, "hs_code": "8484.10", "operating_unit": OU_EU},
    {"item_number": "AX-CTRL-PLC", "description": "Pump Control Panel, PLC, IP66",
     "item_class": "EQUIPMENT", "uom": "EA", "list_price": 4260.00, "line_type": "GOODS",
     "taxable": True, "hs_code": "8537.10", "operating_unit": OU_EU},
    {"item_number": "FREIGHT-DAP", "description": "Freight to named place under DAP terms",
     "item_class": "FREIGHT", "uom": "EA", "list_price": 0.00, "line_type": "FREIGHT",
     "taxable": True, "hs_code": None, "operating_unit": OU_EU},
]
ITEM_BY_NO = {i["item_number"]: i for i in ITEMS}


# =========================================================================== #
# 5. CONTRACTS  (the commercial source of truth for price, terms and tax)
# =========================================================================== #
CONTRACTS = [
    {
        "contract_number": "MSA-ACH-ORB-2024-011", "contract_type": "MSA",
        "customer_id": "C-100428", "status": "ACTIVE",
        "effective_from": "2024-10-01", "effective_to": "2027-09-30",
        "currency": "USD", "price_list": "US-IDN-2026-H1", "discount_pct": 12.0,
        "payment_terms": "Net 45", "incoterms": "FOB Destination",
        "freight_terms": "PREPAID_AND_ADD", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "EXEMPT", "po_required": True, "surcharge_allowed": True,
        "price_tolerance_pct": 0.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "M. Heroux, Director of Supply Chain",
        "signed_by_supplier": "D. Okafor, VP Commercial Operations",
        "clauses": [
            "Prices are firm for the contract term and taken from price list US-IDN-2026-H1 less 12%.",
            "A valid customer purchase order is required before any shipment is invoiced.",
            "Tariff surcharges may be passed through at cost with supporting documentation.",
            "Freight is prepaid by supplier and added to the invoice at actual cost.",
            "Invoices are raised on proof of delivery, not on order entry.",
        ],
    },
    {
        "contract_number": "MSA-MAYO-ORB-2023-004", "contract_type": "MSA",
        "customer_id": "C-100731", "status": "ACTIVE",
        "effective_from": "2023-07-01", "effective_to": "2026-12-31",
        "currency": "USD", "price_list": "US-IDN-2026-H1", "discount_pct": 15.0,
        "payment_terms": "Net 60", "incoterms": "FOB Destination",
        "freight_terms": "PREPAID", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "EXEMPT", "po_required": True, "surcharge_allowed": False,
        "price_tolerance_pct": 0.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "R. Ellingsen, Category Manager",
        "signed_by_supplier": "D. Okafor, VP Commercial Operations",
        "clauses": [
            "Prices are taken from price list US-IDN-2026-H1 less 15% for the contract term.",
            "Freight is prepaid by supplier and is NOT separately billable to the customer.",
            "Tariff and commodity surcharges are expressly excluded and may not be invoiced.",
            "A valid customer purchase order is required before any shipment is invoiced.",
        ],
    },
    {
        "contract_number": "PA-SART-ORB-2025-022", "contract_type": "PRICING_AGREEMENT",
        "customer_id": "C-101902", "status": "ACTIVE",
        "effective_from": "2025-01-01", "effective_to": "2026-12-31",
        "currency": "USD", "price_list": "US-OEM-2026", "discount_pct": 8.0,
        "payment_terms": "Net 30", "incoterms": "EXW Marlborough",
        "freight_terms": "COLLECT", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "ZERO_RATED", "po_required": True, "surcharge_allowed": True,
        "price_tolerance_pct": 1.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "A. Oms, Procurement Lead",
        "signed_by_supplier": "D. Okafor, VP Commercial Operations",
        "clauses": [
            "Prices are taken from price list US-OEM-2026 less 8%, with a 1% price tolerance.",
            "Freight is collect on the customer's carrier account and is never invoiced.",
            "Puerto Rico Act 60 exemption applies; supplies are zero rated.",
        ],
    },
    {
        "contract_number": "MSA-CCF-ORB-2025-008", "contract_type": "MSA",
        "customer_id": "C-102255", "status": "ACTIVE",
        "effective_from": "2025-04-01", "effective_to": "2028-03-31",
        "currency": "USD", "price_list": "US-IDN-2026-H1", "discount_pct": 10.0,
        "payment_terms": "Net 45", "incoterms": "FOB Destination",
        "freight_terms": "PREPAID_AND_ADD", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "EXEMPT", "po_required": True, "surcharge_allowed": True,
        "price_tolerance_pct": 0.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "D. Whitfield, Sourcing Director",
        "signed_by_supplier": "D. Okafor, VP Commercial Operations",
        "clauses": [
            "Prices are taken from price list US-IDN-2026-H1 less 10%.",
            "A valid customer purchase order is required before any shipment is invoiced.",
            "Freight is prepaid and added at actual cost, capped at 4% of goods value.",
        ],
    },
    {
        "contract_number": "MSA-CRL-ORB-2024-019", "contract_type": "MSA",
        "customer_id": "C-102640", "status": "ACTIVE",
        "effective_from": "2024-06-01", "effective_to": "2026-05-31",
        "currency": "USD", "price_list": "US-CRO-2026", "discount_pct": 5.0,
        "payment_terms": "Net 30", "incoterms": "FOB Origin",
        "freight_terms": "PREPAID_AND_ADD", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "SALES_TAX", "po_required": False, "surcharge_allowed": True,
        "price_tolerance_pct": 2.0, "qty_tolerance_pct": 5.0,
        "signed_by_customer": "G. Nunes, Procurement Manager",
        "signed_by_supplier": "D. Okafor, VP Commercial Operations",
        "clauses": [
            "Prices are taken from price list US-CRO-2026 less 5%, with a 2% price tolerance.",
            "Massachusetts sales tax applies; no exemption certificate is held.",
            "Blanket release orders may be shipped without a discrete purchase order.",
        ],
    },
    {
        "contract_number": "MSA-MDA-ORB-2025-031", "contract_type": "MSA",
        "customer_id": "C-103018", "status": "ACTIVE",
        "effective_from": "2025-09-01", "effective_to": "2027-08-31",
        "currency": "USD", "price_list": "US-IDN-2026-H1", "discount_pct": 11.0,
        "payment_terms": "Net 45", "incoterms": "FOB Destination",
        "freight_terms": "PREPAID_AND_ADD", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "EXEMPT", "po_required": True, "surcharge_allowed": True,
        "price_tolerance_pct": 0.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "R. Delgado, Associate Director Supply Chain",
        "signed_by_supplier": "D. Okafor, VP Commercial Operations",
        "clauses": [
            "Prices are taken from price list US-IDN-2026-H1 less 11%.",
            "Texas state exemption certificate TX-EX-3390174 is held on file.",
            "A valid customer purchase order is required before any shipment is invoiced.",
        ],
    },
    {
        "contract_number": "MSA-NW-ORB-2024-017", "contract_type": "MSA",
        "customer_id": "C-200114", "status": "ACTIVE",
        "effective_from": "2024-03-01", "effective_to": "2027-02-28",
        "currency": "EUR", "price_list": "EU-IND-2026", "discount_pct": 7.5,
        "payment_terms": "Net 45", "incoterms": "DAP Hamburg Plant 2",
        "freight_terms": "PREPAID_AND_ADD", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "REVERSE_CHARGE", "po_required": True, "surcharge_allowed": False,
        "price_tolerance_pct": 0.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "K. Bauer, Head of Procurement",
        "signed_by_supplier": "S. Moloney, Commercial Director EMEA",
        "clauses": [
            "Prices are taken from price list EU-IND-2026 less 7.5% for the contract term.",
            "Delivery is DAP Hamburg Plant 2 under Incoterms 2020; freight is billable at actual cost.",
            "Supplies are intra-Community; VAT is accounted for by the recipient under reverse charge.",
            "Early settlement discount of 2% applies if paid within 10 days.",
            "A valid customer purchase order is required before any shipment is invoiced.",
        ],
    },
    {
        "contract_number": "MSA-HFS-ORB-2025-006", "contract_type": "MSA",
        "customer_id": "C-200380", "status": "ACTIVE",
        "effective_from": "2025-02-01", "effective_to": "2027-01-31",
        "currency": "EUR", "price_list": "EU-IND-2026", "discount_pct": 6.0,
        "payment_terms": "Net 60", "incoterms": "DAP Saint-Priest",
        "freight_terms": "PREPAID_AND_ADD", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "REVERSE_CHARGE", "po_required": True, "surcharge_allowed": False,
        "price_tolerance_pct": 0.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "E. Rousseau, Responsable Achats",
        "signed_by_supplier": "S. Moloney, Commercial Director EMEA",
        "clauses": [
            "Prices are taken from price list EU-IND-2026 less 6% for the contract term.",
            "Supplies are intra-Community; VAT is accounted for by the recipient under reverse charge.",
            "Customer VAT identification number must be validated before each invoice is raised.",
        ],
    },
    {
        "contract_number": "FA-VANTA-ORB-2026-002", "contract_type": "FRAME_AGREEMENT",
        "customer_id": "C-200552", "status": "ACTIVE",
        "effective_from": "2026-01-01", "effective_to": "2026-12-31",
        "currency": "EUR", "price_list": "EU-IND-2026", "discount_pct": 4.0,
        "payment_terms": "Net 30", "incoterms": "FCA Cork",
        "freight_terms": "COLLECT", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "REVERSE_CHARGE", "po_required": True, "surcharge_allowed": False,
        "price_tolerance_pct": 0.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "A. Lindgren, Category Buyer",
        "signed_by_supplier": "S. Moloney, Commercial Director EMEA",
        "clauses": [
            "Prices are taken from price list EU-IND-2026 less 4% for the agreement year.",
            "Delivery is FCA Cork; freight is arranged and paid by the customer and is not billable.",
            "Supplies are intra-Community; VAT is accounted for by the recipient under reverse charge.",
        ],
    },
    {
        "contract_number": "DA-BRAE-ORB-2025-014", "contract_type": "DISTRIBUTION_AGREEMENT",
        "customer_id": "C-200790", "status": "ACTIVE",
        "effective_from": "2025-05-01", "effective_to": "2027-04-30",
        "currency": "EUR", "price_list": "EU-DIST-2026", "discount_pct": 22.0,
        "payment_terms": "Net 30", "incoterms": "DAP Cork",
        "freight_terms": "PREPAID", "billing_rule": "DELIVERY_BASED",
        "tax_treatment": "DOMESTIC_VAT", "po_required": False, "surcharge_allowed": False,
        "price_tolerance_pct": 0.0, "qty_tolerance_pct": 0.0,
        "signed_by_customer": "S. Kelleher, Managing Director",
        "signed_by_supplier": "S. Moloney, Commercial Director EMEA",
        "clauses": [
            "Distributor pricing is price list EU-DIST-2026 less 22%.",
            "Domestic Irish supply; VAT at the standard rate of 23% applies.",
            "Freight is prepaid by supplier and is not separately billable.",
        ],
    },
]
CONTRACT_BY_NO = {c["contract_number"]: c for c in CONTRACTS}
CONTRACT_BY_CUST = {c["customer_id"]: c for c in CONTRACTS}


def contract_price(contract: dict, item_number: str) -> float:
    """Net contract price = list price less the contract discount."""
    item = ITEM_BY_NO[item_number]
    if item["line_type"] != "GOODS":
        return 0.0
    return money(item["list_price"] * (1 - contract["discount_pct"] / 100))


# price list rows, exposed as its own endpoint
PRICE_LIST = [
    {
        "price_list": c["price_list"], "contract_number": c["contract_number"],
        "customer_id": c["customer_id"], "item_number": i["item_number"],
        "uom": i["uom"], "list_price": i["list_price"],
        "discount_pct": c["discount_pct"], "contract_price": contract_price(c, i["item_number"]),
        "currency": c["currency"], "effective_from": c["effective_from"], "effective_to": c["effective_to"],
    }
    for c in CONTRACTS
    for i in ITEMS
    if i["operating_unit"] == CUST_BY_ID[c["customer_id"]]["operating_unit"] and i["line_type"] == "GOODS"
]


# =========================================================================== #
# 6. TRANSACTIONS: purchase orders, sales orders, deliveries
# =========================================================================== #
GOODS_BY_OU = {
    OU_US: ["VMPKPED", "NEO96", "KA2V002PV1G", "CELLCUL500", "BIOPROC-FLT-22", "CHROM-COL-16"],
    OU_EU: ["AX-PMP-320", "AX-SEAL-88", "AX-BRG-540", "AX-GSKT-12", "AX-CTRL-PLC"],
}
FREIGHT_ITEM = {OU_US: "FREIGHT-US", OU_EU: "FREIGHT-DAP"}
QTY_BANDS = {"CONSUMABLE": (60, 400), "MEDIA": (10, 60), "FILTRATION": (5, 40),
             "EQUIPMENT": (1, 6), "ROTATING-EQUIP": (2, 18), "SPARES": (6, 60)}

# Which defect goes on which billing draft. Index is the draft sequence number.
DEFECT_PLAN = {
    1: "price_off_contract",
    3: "qty_exceeds_shipped",
    5: "po_expired",
    6: "po_limit_exceeded",
    7: "missing_po",
    9: "tax_treatment_wrong",
    10: "bill_to_address_stale",
    11: "surcharge_not_allowed",
    12: "freight_not_billable",
    13: "payment_terms_off_contract",
    15: "currency_mismatch",
    16: "total_math_error",
    17: "billing_before_delivery",
    19: "duplicate_billing",
}

purchase_orders: list[dict] = []
sales_orders: list[dict] = []
deliveries: list[dict] = []
documents: list[dict] = []

N_ORDERS = 24

for i in range(N_ORDERS):
    cust = CUSTOMERS[i % len(CUSTOMERS)]
    contract = CONTRACT_BY_CUST[cust["customer_id"]]
    ou_name = cust["operating_unit"]
    ou = next(o for o in OPERATING_UNITS if o["operating_unit"] == ou_name)
    is_us = ou_name == OU_US

    order_number = str(1886400 + i * 17) if is_us else f"SO-2026-{7700 + i * 13}"
    entered = TODAY - timedelta(days=52 - i * 2)
    booked = entered + timedelta(days=1)
    ship_date = entered + timedelta(days=4)

    # ---------------- customer purchase order -----------------------------
    po_number = (f"PO{249600 + i * 37}" if cust["country"] == "US"
                 else f"45001988{40 + i}")
    po_date = entered - timedelta(days=6)
    po_valid_to = po_date + timedelta(days=365)

    # ---------------- order lines -----------------------------------------
    pool = GOODS_BY_OU[ou_name]
    n_lines = 2 + (i % 3)
    chosen = [pool[(i + k) % len(pool)] for k in range(n_lines)]

    lines: list[dict] = []
    line_no = 0
    for item_no in chosen:
        item = ITEM_BY_NO[item_no]
        lo, hi = QTY_BANDS[item["item_class"]]
        qty = random.randint(lo, hi)
        unit = contract_price(contract, item_no)
        line_no += 1
        lines.append({
            "line_number": line_no, "item_number": item_no, "description": item["description"],
            "line_type": "GOODS", "uom": item["uom"], "ordered_quantity": qty,
            "shipped_quantity": qty, "unit_list_price": item["list_price"],
            "contract_price": unit, "unit_selling_price": unit,
            "discount_pct": contract["discount_pct"],
            "extended_amount": money(qty * unit),
            "revenue_account": "4100-PRODUCT-REVENUE",
            "hs_code": item["hs_code"],
        })

    # partial shipment on a couple of orders — a real reason billed qty < ordered
    if i in (3, 14, 18):
        lines[0]["shipped_quantity"] = max(1, int(lines[0]["ordered_quantity"] * 0.6))

    # tariff surcharge line, US only and only where the contract allows it
    if is_us and contract["surcharge_allowed"] and i % 4 == 0:
        goods_value = sum(l["extended_amount"] for l in lines)
        line_no += 1
        lines.append({
            "line_number": line_no, "item_number": "TARIFF_SURCHARGE",
            "description": ITEM_BY_NO["TARIFF_SURCHARGE"]["description"], "line_type": "SURCHARGE",
            "uom": "EA", "ordered_quantity": 1, "shipped_quantity": 1,
            "unit_list_price": 0.0, "contract_price": 0.0,
            "unit_selling_price": money(goods_value * 0.025),
            "discount_pct": 0.0, "extended_amount": money(goods_value * 0.025),
            "revenue_account": "4180-SURCHARGE-RECOVERY", "hs_code": None,
        })

    # freight line, only where the contract says freight is billable
    freight_amount = 0.0
    if contract["freight_terms"] == "PREPAID_AND_ADD":
        goods_value = sum(l["extended_amount"] for l in lines if l["line_type"] == "GOODS")
        freight_amount = money(min(goods_value * 0.018, 640))
        line_no += 1
        lines.append({
            "line_number": line_no, "item_number": FREIGHT_ITEM[ou_name],
            "description": ITEM_BY_NO[FREIGHT_ITEM[ou_name]]["description"], "line_type": "FREIGHT",
            "uom": "EA", "ordered_quantity": 1, "shipped_quantity": 1,
            "unit_list_price": 0.0, "contract_price": 0.0, "unit_selling_price": freight_amount,
            "discount_pct": 0.0, "extended_amount": freight_amount,
            "revenue_account": "4300-FREIGHT-RECOVERY", "hs_code": None,
        })

    tax = TAX_BY_CODE[cust["tax_code"]]
    for l in lines:
        item = ITEM_BY_NO[l["item_number"]]
        taxable = item["taxable"]
        l["tax_code"] = cust["tax_code"] if taxable else "NON-TAXABLE"
        l["tax_rate"] = tax["rate"] if taxable else 0.0
        l["tax_amount"] = money(l["extended_amount"] * (l["tax_rate"] / 100))

    goods_total = money(sum(l["extended_amount"] for l in lines if l["line_type"] == "GOODS"))
    surcharge_total = money(sum(l["extended_amount"] for l in lines if l["line_type"] == "SURCHARGE"))
    freight_total = money(sum(l["extended_amount"] for l in lines if l["line_type"] == "FREIGHT"))
    tax_total = money(sum(l["tax_amount"] for l in lines))
    order_total = money(goods_total + surcharge_total + freight_total + tax_total)

    # ---------------- status / lifecycle ----------------------------------
    if i in (20, 21):
        status, invoiced_date, has_delivery = "BOOKED", None, False
    elif i == 22:
        status, invoiced_date, has_delivery = "CLOSED", (ship_date + timedelta(days=2)), True
    else:
        status, invoiced_date, has_delivery = "AWAITING_BILLING", None, True

    holds = []
    if i == 21:
        holds.append({"hold_name": "CREDIT CHECK FAILURE", "applied_on": booked.isoformat(),
                      "applied_by": "AUTO-CREDIT-ENGINE", "released": False})
    if i == 5:
        holds.append({"hold_name": "PRICING APPROVAL", "applied_on": booked.isoformat(),
                      "applied_by": contract["signed_by_supplier"], "released": True,
                      "released_on": (booked + timedelta(days=1)).isoformat()})

    po_amount_limit = money(order_total * (1.6 if i != 6 else 0.55))
    po_status = "OPEN"
    if i == 5:
        po_valid_to = entered - timedelta(days=15)   # expired before the shipment
        po_status = "EXPIRED"

    purchase_orders.append({
        "po_number": po_number, "customer_id": cust["customer_id"],
        "customer_name": cust["customer_name"], "contract_number": contract["contract_number"],
        "po_date": po_date.isoformat(), "valid_from": po_date.isoformat(),
        "valid_to": po_valid_to.isoformat(), "status": po_status,
        "currency": contract["currency"], "po_amount_limit": po_amount_limit,
        "released_amount": money(order_total),
        "buyer_name": cust["contact_name"], "buyer_email": cust["contact_email"],
        "payment_terms": contract["payment_terms"], "incoterms": contract["incoterms"],
        "sales_order": order_number,
        "lines": [
            {"po_line": l["line_number"], "item_number": l["item_number"],
             "description": l["description"], "uom": l["uom"],
             "quantity": l["ordered_quantity"], "unit_price": l["unit_selling_price"],
             "amount": l["extended_amount"]}
            for l in lines if l["line_type"] == "GOODS"
        ],
        "document_id": f"DOC-PO-{po_number}",
    })

    delivery_number = None
    if has_delivery:
        delivery_number = f"DN-{88200 + i}" if not is_us else f"WBO-{760400 + i}"
        deliveries.append({
            "delivery_number": delivery_number, "sales_order": order_number,
            "customer_id": cust["customer_id"], "ship_date": ship_date.isoformat(),
            "carrier": "FedEx Freight" if is_us else "DB Schenker",
            "waybill": f"{'FX' if is_us else 'DBS'}{random.randint(10**9, 10**10 - 1)}",
            "ship_from": ou["entity_address"],
            "ship_to": cust["ship_to"],
            "proof_of_delivery_date": (ship_date + timedelta(days=2)).isoformat(),
            "incoterms": contract["incoterms"],
            "gross_weight_kg": money(sum(l["shipped_quantity"] for l in lines if l["line_type"] == "GOODS") * 0.42),
            "lines": [
                {"delivery_line": l["line_number"], "item_number": l["item_number"],
                 "uom": l["uom"], "ordered_quantity": l["ordered_quantity"],
                 "shipped_quantity": l["shipped_quantity"],
                 "backordered_quantity": l["ordered_quantity"] - l["shipped_quantity"]}
                for l in lines if l["line_type"] == "GOODS"
            ],
            "document_id": f"DOC-DN-{delivery_number}",
        })

    sales_orders.append({
        "order_number": order_number,
        "customer_po_number": po_number,
        "contract_number": contract["contract_number"],
        "operating_unit": ou_name,
        "legal_entity": ou["legal_entity"],
        "order_type": "Standard Order",
        "order_source": "EDI 850" if i % 3 == 0 else "Manual Entry",
        "status": status,
        "entered_date": entered.isoformat(),
        "booked_date": booked.isoformat(),
        "requested_ship_date": ship_date.isoformat(),
        "invoiced_date": invoiced_date.isoformat() if invoiced_date else None,
        "transaction_originator": cust["collector"],
        "caller_name": cust["contact_name"],
        "caller_email": cust["contact_email"],
        "caller_phone": cust["contact_phone"],
        "customer_id": cust["customer_id"],
        "customer_name_bill_to": cust["bill_to"]["name"],
        "customer_name_ship_to": cust["ship_to"]["name"],
        "bill_to": cust["bill_to"],
        "ship_to": cust["ship_to"],
        "currency": contract["currency"],
        "payment_terms": contract["payment_terms"],
        "incoterms": contract["incoterms"],
        "freight_terms": contract["freight_terms"],
        "tax_code": cust["tax_code"],
        "tax_treatment": TAX_BY_CODE[cust["tax_code"]]["treatment"],
        "tax_registration_customer": cust["tax_registration"],
        "exemption_certificate": cust["exemption_certificate"],
        "price_list": contract["price_list"],
        "delivery_number": delivery_number,
        "holds": holds,
        "lines": lines,
        "totals": {
            "goods_amount": goods_total, "surcharge_amount": surcharge_total,
            "freight_amount": freight_total, "tax_amount": tax_total,
            "order_total": order_total, "currency": contract["currency"],
        },
        "document_id": f"DOC-SO-{order_number}",
    })

SO_BY_NO = {o["order_number"]: o for o in sales_orders}
PO_BY_NO = {p["po_number"]: p for p in purchase_orders}
DN_BY_NO = {d["delivery_number"]: d for d in deliveries}


# =========================================================================== #
# 7. BILLING DRAFTS  (the pre-invoice artefact a validation tool must check)
# =========================================================================== #
DEFECT_TEXT = {
    "price_off_contract": "Unit price billed does not match the contract price list.",
    "qty_exceeds_shipped": "Quantity billed is greater than the quantity shipped on the delivery.",
    "po_expired": "The customer purchase order had expired before the shipment date.",
    "po_limit_exceeded": "Draft value exceeds the remaining value authorised on the customer PO.",
    "missing_po": "The contract requires a customer PO but the draft carries none.",
    "tax_treatment_wrong": "Tax treatment on the draft contradicts the contract and the tax rules.",
    "bill_to_address_stale": "Bill-to address on the draft does not match the customer master site.",
    "surcharge_not_allowed": "A surcharge is billed although the contract prohibits surcharges.",
    "freight_not_billable": "Freight is billed although the contract makes freight non-billable.",
    "payment_terms_off_contract": "Payment terms on the draft differ from the contract terms.",
    "currency_mismatch": "Draft currency differs from the contract and customer master currency.",
    "total_math_error": "Total payable does not equal goods plus surcharge plus freight plus tax.",
    "billing_before_delivery": "Invoice date precedes proof of delivery on a delivery-based contract.",
    "duplicate_billing": "A draft exists for an order that has already been invoiced.",
}
DEFECT_SEVERITY = {
    "price_off_contract": "critical", "qty_exceeds_shipped": "critical",
    "po_expired": "high", "po_limit_exceeded": "high", "missing_po": "high",
    "tax_treatment_wrong": "critical", "bill_to_address_stale": "medium",
    "surcharge_not_allowed": "high", "freight_not_billable": "high",
    "payment_terms_off_contract": "medium", "currency_mismatch": "critical",
    "total_math_error": "critical", "billing_before_delivery": "medium",
    "duplicate_billing": "critical",
}

eligible = [o for o in sales_orders if o["status"] == "AWAITING_BILLING"][:19]
eligible.append(SO_BY_NO[sales_orders[22]["order_number"]])   # already invoiced -> duplicate

billing_drafts: list[dict] = []
answer_key: list[dict] = []

for d, order in enumerate(eligible):
    cust = CUST_BY_ID[order["customer_id"]]
    contract = CONTRACT_BY_NO[order["contract_number"]]
    delivery = DN_BY_NO.get(order["delivery_number"])
    tax = TAX_BY_CODE[cust["tax_code"]]
    defect = DEFECT_PLAN.get(d)
    is_us = order["operating_unit"] == OU_US

    draft_number = f"BD-2026-{5500 + d}"
    proposed_invoice = f"ORB-{'US' if is_us else 'EU'}-INV-2026-{5580 + d:05d}"
    pod = date.fromisoformat(delivery["proof_of_delivery_date"]) if delivery else TODAY
    invoice_date = pod + timedelta(days=1)

    # --- lines are built from what was actually shipped ---------------------
    draft_lines = []
    for l in order["lines"]:
        if l["line_type"] == "GOODS":
            qty = l["shipped_quantity"]
        else:
            qty = l["ordered_quantity"]
        if qty <= 0:
            continue
        draft_lines.append({
            "line": len(draft_lines) + 1,
            "item_number": l["item_number"],
            "description": l["description"],
            "line_type": l["line_type"],
            "uom": l["uom"],
            "quantity_to_bill": qty,
            "unit_price": l["unit_selling_price"],
            "amount": money(qty * l["unit_selling_price"]),
            "source": "DELIVERY" if l["line_type"] == "GOODS" else "ORDER",
            "source_reference": order["delivery_number"] if l["line_type"] == "GOODS" else order["order_number"],
        })

    draft = {
        "draft_number": draft_number,
        "proposed_invoice_number": proposed_invoice,
        "status": "PENDING_VALIDATION",
        "prepared_by": "BPO O2C Billing Desk",
        "prepared_on": (invoice_date - timedelta(days=1)).isoformat(),
        "invoice_date": invoice_date.isoformat(),
        "billing_type": "Delivery-based (goods)",
        "operating_unit": order["operating_unit"],
        "legal_entity": order["legal_entity"],
        "sales_order": order["order_number"],
        "customer_po_number": order["customer_po_number"],
        "contract_number": order["contract_number"],
        "delivery_number": order["delivery_number"],
        "customer_id": order["customer_id"],
        "bill_to": dict(cust["bill_to"]),
        "ship_to": dict(cust["ship_to"]),
        "currency": contract["currency"],
        "payment_terms": contract["payment_terms"],
        "incoterms": contract["incoterms"],
        "tax_code": cust["tax_code"],
        "tax_treatment": tax["treatment"],
        "tax_rate": tax["rate"],
        "customer_tax_registration": cust["tax_registration"],
        "exemption_certificate": cust["exemption_certificate"],
        "notes": ("Cross-border supply; VAT accounted by recipient under reverse charge."
                  if tax["treatment"] == "REVERSE_CHARGE" else
                  "Exemption certificate held on file." if tax["treatment"] == "EXEMPT" else
                  "Standard taxable supply."),
        "lines": draft_lines,
    }

    # ---------------- defect injection -------------------------------------
    if defect == "price_off_contract":
        target = next(l for l in draft_lines if l["line_type"] == "GOODS")
        target["unit_price"] = money(target["unit_price"] * 1.075)
        target["amount"] = money(target["quantity_to_bill"] * target["unit_price"])
    elif defect == "qty_exceeds_shipped":
        target = next(l for l in draft_lines if l["line_type"] == "GOODS")
        target["quantity_to_bill"] += 20
        target["amount"] = money(target["quantity_to_bill"] * target["unit_price"])
    elif defect == "missing_po":
        draft["customer_po_number"] = ""
    elif defect == "tax_treatment_wrong":
        if tax["treatment"] == "REVERSE_CHARGE":
            draft["tax_code"], draft["tax_treatment"], draft["tax_rate"] = "IE-VAT-23", "DOMESTIC_VAT", 23.0
            draft["notes"] = "Standard taxable supply."
        else:
            draft["tax_code"], draft["tax_treatment"], draft["tax_rate"] = "EU-RC-0", "REVERSE_CHARGE", 0.0
            draft["notes"] = "Cross-border supply; VAT accounted by recipient under reverse charge."
    elif defect == "bill_to_address_stale":
        draft["bill_to"] = dict(draft["bill_to"], address_4="800 MARSHALL ST", postal_code="72202",
                                site_use_id="BT-100428-0")
    elif defect == "surcharge_not_allowed":
        goods_value = sum(l["amount"] for l in draft_lines if l["line_type"] == "GOODS")
        draft_lines.append({
            "line": len(draft_lines) + 1, "item_number": "TARIFF_SURCHARGE",
            "description": ITEM_BY_NO["TARIFF_SURCHARGE"]["description"], "line_type": "SURCHARGE",
            "uom": "EA", "quantity_to_bill": 1, "unit_price": money(goods_value * 0.025),
            "amount": money(goods_value * 0.025), "source": "MANUAL", "source_reference": None,
        })
    elif defect == "freight_not_billable":
        goods_value = sum(l["amount"] for l in draft_lines if l["line_type"] == "GOODS")
        fr = money(min(goods_value * 0.018, 640))
        draft_lines.append({
            "line": len(draft_lines) + 1, "item_number": FREIGHT_ITEM[order["operating_unit"]],
            "description": ITEM_BY_NO[FREIGHT_ITEM[order["operating_unit"]]]["description"],
            "line_type": "FREIGHT", "uom": "EA", "quantity_to_bill": 1,
            "unit_price": fr, "amount": fr, "source": "MANUAL", "source_reference": None,
        })
    elif defect == "payment_terms_off_contract":
        draft["payment_terms"] = "Net 30"
    elif defect == "currency_mismatch":
        draft["currency"] = "EUR" if contract["currency"] == "USD" else "USD"
    elif defect == "billing_before_delivery":
        draft["invoice_date"] = (pod - timedelta(days=3)).isoformat()

    # ---------------- totals ------------------------------------------------
    goods = money(sum(l["amount"] for l in draft_lines if l["line_type"] == "GOODS"))
    surcharge = money(sum(l["amount"] for l in draft_lines if l["line_type"] == "SURCHARGE"))
    freight = money(sum(l["amount"] for l in draft_lines if l["line_type"] == "FREIGHT"))

    for l in draft_lines:
        taxable = ITEM_BY_NO[l["item_number"]]["taxable"]
        l["tax_code"] = draft["tax_code"] if taxable else "NON-TAXABLE"
        l["tax_rate"] = draft["tax_rate"] if taxable else 0.0
        l["tax_amount"] = money(l["amount"] * l["tax_rate"] / 100)

    tax_amount = money(sum(l["tax_amount"] for l in draft_lines))
    total = money(goods + surcharge + freight + tax_amount)
    if defect == "total_math_error":
        total = money(total - 250.00)

    draft["totals"] = {
        "goods_subtotal": goods, "surcharge_total": surcharge, "freight_total": freight,
        "tax_amount": tax_amount, "total_payable": total, "currency": draft["currency"],
    }
    draft["lines"] = draft_lines
    billing_drafts.append(draft)

    if defect:
        answer_key.append({
            "draft_number": draft_number, "sales_order": order["order_number"],
            "customer_id": order["customer_id"], "finding": defect,
            "description": DEFECT_TEXT[defect], "severity": DEFECT_SEVERITY[defect],
        })


# =========================================================================== #
# 8. FIELD LINEAGE MAP  (what a billing validation tool should check, and where
#    the authoritative value lives)
# =========================================================================== #
FIELD_MAP = [
    {"invoice_field": "Bill-to customer name", "category": "Identity", "severity": "high",
     "authoritative_source": "customer.bill_to.name", "precedence": ["customer_master"],
     "compare_to": "billing_draft.bill_to.name", "match": "exact_text"},
    {"invoice_field": "Bill-to address", "category": "Identity", "severity": "medium",
     "authoritative_source": "customer.bill_to (address_1..4, city, state, postal_code)",
     "precedence": ["customer_master"], "compare_to": "billing_draft.bill_to", "match": "exact_text_block"},
    {"invoice_field": "Ship-to address / tax jurisdiction", "category": "Identity", "severity": "high",
     "authoritative_source": "delivery.ship_to", "precedence": ["delivery", "sales_order", "customer_master"],
     "compare_to": "billing_draft.ship_to", "match": "exact_text_block"},
    {"invoice_field": "Customer PO number", "category": "Commercial", "severity": "high",
     "authoritative_source": "purchase_order.po_number", "precedence": ["purchase_order", "sales_order"],
     "compare_to": "billing_draft.customer_po_number",
     "match": "exact_text; mandatory when contract.po_required is true"},
    {"invoice_field": "PO validity at invoice date", "category": "Commercial", "severity": "high",
     "authoritative_source": "purchase_order.valid_from / valid_to", "precedence": ["purchase_order"],
     "compare_to": "billing_draft.invoice_date", "match": "date_within_range"},
    {"invoice_field": "PO authorised value", "category": "Commercial", "severity": "high",
     "authoritative_source": "purchase_order.po_amount_limit", "precedence": ["purchase_order"],
     "compare_to": "billing_draft.totals.total_payable", "match": "less_than_or_equal"},
    {"invoice_field": "Contract reference", "category": "Commercial", "severity": "medium",
     "authoritative_source": "sales_order.contract_number", "precedence": ["sales_order", "purchase_order"],
     "compare_to": "billing_draft.contract_number", "match": "exact_text"},
    {"invoice_field": "Item number", "category": "Line", "severity": "high",
     "authoritative_source": "delivery.lines.item_number", "precedence": ["delivery", "sales_order"],
     "compare_to": "billing_draft.lines.item_number", "match": "exact_text"},
    {"invoice_field": "Quantity billed", "category": "Line", "severity": "critical",
     "authoritative_source": "delivery.lines.shipped_quantity",
     "precedence": ["delivery", "sales_order"], "compare_to": "billing_draft.lines.quantity_to_bill",
     "match": "less_than_or_equal within contract.qty_tolerance_pct"},
    {"invoice_field": "Unit price", "category": "Pricing", "severity": "critical",
     "authoritative_source": "price_list.contract_price",
     "precedence": ["contract_price_list", "purchase_order", "sales_order"],
     "compare_to": "billing_draft.lines.unit_price",
     "match": "equal within contract.price_tolerance_pct"},
    {"invoice_field": "Discount percentage", "category": "Pricing", "severity": "high",
     "authoritative_source": "contract.discount_pct", "precedence": ["contract"],
     "compare_to": "derived from billing_draft.lines.unit_price vs item.list_price", "match": "equal"},
    {"invoice_field": "Extended line amount", "category": "Pricing", "severity": "critical",
     "authoritative_source": "quantity_to_bill * unit_price", "precedence": ["computed"],
     "compare_to": "billing_draft.lines.amount", "match": "equal within 0.01"},
    {"invoice_field": "Currency", "category": "Financial", "severity": "critical",
     "authoritative_source": "contract.currency", "precedence": ["contract", "customer_master"],
     "compare_to": "billing_draft.currency", "match": "exact_text"},
    {"invoice_field": "Payment terms", "category": "Financial", "severity": "medium",
     "authoritative_source": "contract.payment_terms", "precedence": ["contract", "customer_master"],
     "compare_to": "billing_draft.payment_terms", "match": "exact_text"},
    {"invoice_field": "Incoterms", "category": "Financial", "severity": "medium",
     "authoritative_source": "contract.incoterms", "precedence": ["contract", "delivery"],
     "compare_to": "billing_draft.incoterms", "match": "exact_text"},
    {"invoice_field": "Freight charge", "category": "Charges", "severity": "high",
     "authoritative_source": "contract.freight_terms", "precedence": ["contract"],
     "compare_to": "billing_draft freight lines",
     "match": "billable only when freight_terms = PREPAID_AND_ADD"},
    {"invoice_field": "Surcharge", "category": "Charges", "severity": "high",
     "authoritative_source": "contract.surcharge_allowed", "precedence": ["contract"],
     "compare_to": "billing_draft surcharge lines",
     "match": "billable only when surcharge_allowed is true"},
    {"invoice_field": "Tax code and treatment", "category": "Tax", "severity": "critical",
     "authoritative_source": "tax_rule for customer.tax_code",
     "precedence": ["tax_rules", "contract", "customer_master"],
     "compare_to": "billing_draft.tax_code / tax_treatment", "match": "exact_text"},
    {"invoice_field": "Tax rate and amount", "category": "Tax", "severity": "critical",
     "authoritative_source": "tax_rule.rate applied to taxable lines", "precedence": ["tax_rules"],
     "compare_to": "billing_draft.totals.tax_amount", "match": "equal within 0.01"},
    {"invoice_field": "Customer tax registration / exemption certificate", "category": "Tax",
     "severity": "high", "authoritative_source": "customer.tax_registration, customer.exemption_certificate",
     "precedence": ["customer_master"], "compare_to": "billing_draft.customer_tax_registration",
     "match": "exact_text; certificate mandatory when treatment = EXEMPT"},
    {"invoice_field": "Total payable", "category": "Financial", "severity": "critical",
     "authoritative_source": "goods + surcharge + freight + tax", "precedence": ["computed"],
     "compare_to": "billing_draft.totals.total_payable", "match": "equal within 0.01"},
    {"invoice_field": "Invoice date vs proof of delivery", "category": "Timing", "severity": "medium",
     "authoritative_source": "delivery.proof_of_delivery_date", "precedence": ["delivery"],
     "compare_to": "billing_draft.invoice_date",
     "match": "invoice_date >= pod when contract.billing_rule = DELIVERY_BASED"},
    {"invoice_field": "Already invoiced check", "category": "Duplicate", "severity": "critical",
     "authoritative_source": "sales_order.invoiced_date", "precedence": ["sales_order"],
     "compare_to": "existence of a billing draft", "match": "must be null"},
    {"invoice_field": "Order holds", "category": "Commercial", "severity": "high",
     "authoritative_source": "sales_order.holds", "precedence": ["sales_order"],
     "compare_to": "billing eligibility", "match": "no unreleased holds"},
]


# =========================================================================== #
# 9. SOURCE DOCUMENTS (real PDFs)
# =========================================================================== #
styles = getSampleStyleSheet()
S_TITLE = ParagraphStyle("t", parent=styles["Title"], fontSize=15, spaceAfter=2, alignment=0)
S_SUB = ParagraphStyle("s", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#5a6673"))
S_H = ParagraphStyle("h", parent=styles["Heading2"], fontSize=10.5, spaceBefore=10, spaceAfter=4,
                     textColor=colors.HexColor("#1f3348"))
S_N = ParagraphStyle("n", parent=styles["Normal"], fontSize=8.6, leading=12)
S_SMALL = ParagraphStyle("sm", parent=styles["Normal"], fontSize=7.4, textColor=colors.HexColor("#6b7885"))

GRID = TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3348")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c3ccd5")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f8")]),
    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
])
KV = TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 8.2),
    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#5a6673")),
    ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 1.6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
])


def kv_table(rows, widths=(38 * mm, 62 * mm)):
    t = Table([[k, Paragraph(str(v), S_N)] for k, v in rows], colWidths=list(widths))
    t.setStyle(KV)
    return t


def addr_block(a: dict) -> str:
    parts = [a.get("name"), a.get("address_1"), a.get("address_2"), a.get("address_3"), a.get("address_4"),
             f"{a.get('city', '')} {a.get('state', '')} {a.get('postal_code', '')}".strip(), a.get("country")]
    return "<br/>".join(p for p in parts if p and p != "-")


def build_pdf(filename: str, entity: dict, doc_title: str, doc_ref: str, story_body: list) -> str:
    path = os.path.join(DOCS, filename)
    os.makedirs(DOCS, exist_ok=True)
    doc = SimpleDocTemplate(path, pagesize=LETTER, title=doc_ref,
                            author=entity["legal_entity"], subject=doc_title,
                            leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    story = [
        Paragraph(f"ORBIS &nbsp;|&nbsp; {entity['legal_entity']}", S_TITLE),
        Paragraph(f"{entity['entity_address']} &nbsp;·&nbsp; Tax registration {entity['tax_registration']}", S_SUB),
        Spacer(1, 7),
        Paragraph(f"{doc_title} &nbsp;—&nbsp; {doc_ref}", S_H),
    ]
    story += story_body
    story += [Spacer(1, 12),
              Paragraph("System-generated document from ORBIS. Dummy data for validation testing only — "
                        "not a commercial document and not evidence of any real transaction.", S_SMALL)]
    doc.build(story)
    return path


def register_doc(doc_id, doc_type, filename, title, ref, owner_object, owner_key, doc_date):
    size = os.path.getsize(os.path.join(DOCS, filename))
    documents.append({
        "document_id": doc_id, "document_type": doc_type, "title": title, "reference": ref,
        "file_name": filename, "url": f"docs/{filename}", "mime_type": "application/pdf",
        "size_bytes": size, "related_object": owner_object, "related_key": owner_key,
        "document_date": doc_date, "uploaded_by": "ORBIS Document Service",
    })


ENTITY_BY_OU = {o["operating_unit"]: o for o in OPERATING_UNITS}

# --- contract PDFs ---------------------------------------------------------
for c in CONTRACTS:
    cust = CUST_BY_ID[c["customer_id"]]
    ent = ENTITY_BY_OU[cust["operating_unit"]]
    body = [
        Spacer(1, 3),
        kv_table([
            ("Customer", f"{cust['customer_name']} ({cust['customer_id']})"),
            ("Contract type", c["contract_type"].replace("_", " ").title()),
            ("Status", c["status"]),
            ("Effective", f"{c['effective_from']} to {c['effective_to']}"),
            ("Currency", c["currency"]),
            ("Price list", f"{c['price_list']} less {c['discount_pct']}%"),
            ("Payment terms", c["payment_terms"]),
            ("Incoterms", c["incoterms"]),
            ("Freight terms", c["freight_terms"].replace("_", " ").title()),
            ("Billing rule", c["billing_rule"].replace("_", " ").title()),
            ("Tax treatment", c["tax_treatment"].replace("_", " ").title()),
            ("Customer PO required", "Yes" if c["po_required"] else "No"),
            ("Surcharges permitted", "Yes" if c["surcharge_allowed"] else "No"),
            ("Price tolerance", f"{c['price_tolerance_pct']}%"),
        ], widths=(46 * mm, 110 * mm)),
        Paragraph("Commercial terms", S_H),
    ]
    body += [Paragraph(f"{n}. {txt}", S_N) for n, txt in enumerate(c["clauses"], 1)]
    body += [
        Paragraph("Agreed pricing (extract)", S_H),
        Table([["Item", "Description", "UOM", "List price", "Contract price"]] +
              [[r["item_number"], Paragraph(ITEM_BY_NO[r["item_number"]]["description"], S_N), r["uom"],
                f"{r['list_price']:,.2f}", f"{r['contract_price']:,.2f}"]
               for r in PRICE_LIST if r["contract_number"] == c["contract_number"]],
              colWidths=[28 * mm, 72 * mm, 14 * mm, 21 * mm, 24 * mm], style=GRID),
        Spacer(1, 9),
        kv_table([("Signed for the customer", c["signed_by_customer"]),
                  ("Signed for the supplier", c["signed_by_supplier"])], widths=(46 * mm, 110 * mm)),
    ]
    fn = f"contract_{c['contract_number']}.pdf"
    build_pdf(fn, ent, "Master Commercial Agreement", c["contract_number"], body)
    c["document_id"] = f"DOC-CT-{c['contract_number']}"
    register_doc(c["document_id"], "CONTRACT", fn, "Master Commercial Agreement",
                 c["contract_number"], "contract", c["contract_number"], c["effective_from"])

# --- purchase order PDFs ---------------------------------------------------
for po in purchase_orders:
    cust = CUST_BY_ID[po["customer_id"]]
    ent = ENTITY_BY_OU[cust["operating_unit"]]
    body = [
        Spacer(1, 3),
        Table([[Paragraph("<b>Issued by (customer)</b><br/>" + addr_block(cust["bill_to"]), S_N),
                Paragraph("<b>Deliver to</b><br/>" + addr_block(cust["ship_to"]), S_N),
                Paragraph("<b>Supplier</b><br/>" + ent["legal_entity"] + "<br/>" + ent["entity_address"], S_N)]],
              colWidths=[56 * mm, 56 * mm, 56 * mm],
              style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8)])),
        Spacer(1, 6),
        kv_table([("PO number", po["po_number"]), ("PO date", po["po_date"]),
                  ("Valid to", po["valid_to"]), ("Status", po["status"]),
                  ("Currency", po["currency"]),
                  ("Authorised value", f"{po['po_amount_limit']:,.2f} {po['currency']}"),
                  ("Payment terms", po["payment_terms"]), ("Incoterms", po["incoterms"]),
                  ("Contract reference", po["contract_number"]),
                  ("Buyer", f"{po['buyer_name']} · {po['buyer_email']}")], widths=(40 * mm, 116 * mm)),
        Paragraph("Ordered items", S_H),
        Table([["Ln", "Item", "Description", "UOM", "Qty", "Unit price", "Amount"]] +
              [[l["po_line"], l["item_number"], Paragraph(l["description"], S_N), l["uom"],
                f"{l['quantity']:,}", f"{l['unit_price']:,.2f}", f"{l['amount']:,.2f}"]
               for l in po["lines"]],
              colWidths=[9 * mm, 27 * mm, 62 * mm, 12 * mm, 15 * mm, 22 * mm, 24 * mm], style=GRID),
        Spacer(1, 8),
        Paragraph("Goods must be accompanied by a delivery note quoting this PO number. "
                  "Invoices without a valid PO reference will be returned unpaid.", S_N),
    ]
    fn = f"po_{po['po_number']}.pdf"
    build_pdf(fn, ent, "Customer Purchase Order", po["po_number"], body)
    register_doc(po["document_id"], "PURCHASE_ORDER", fn, "Customer Purchase Order",
                 po["po_number"], "purchase_order", po["po_number"], po["po_date"])

# --- sales order acknowledgement PDFs -------------------------------------
for so in sales_orders:
    ent = ENTITY_BY_OU[so["operating_unit"]]
    body = [
        Spacer(1, 3),
        Table([[Paragraph("<b>Bill to</b><br/>" + addr_block(so["bill_to"]), S_N),
                Paragraph("<b>Ship to</b><br/>" + addr_block(so["ship_to"]), S_N)]],
              colWidths=[84 * mm, 84 * mm],
              style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8)])),
        Spacer(1, 6),
        kv_table([("Order number", so["order_number"]), ("Customer PO", so["customer_po_number"]),
                  ("Contract", so["contract_number"]), ("Operating unit", so["operating_unit"]),
                  ("Order status", so["status"]), ("Entered / booked", f"{so['entered_date']} / {so['booked_date']}"),
                  ("Requested ship date", so["requested_ship_date"]),
                  ("Delivery", so["delivery_number"] or "—"),
                  ("Currency", so["currency"]), ("Payment terms", so["payment_terms"]),
                  ("Incoterms", so["incoterms"]), ("Freight terms", so["freight_terms"].replace("_", " ").title()),
                  ("Tax code", f"{so['tax_code']} ({so['tax_treatment'].replace('_', ' ').title()})"),
                  ("Order taker", so["transaction_originator"]),
                  ("Requested by", f"{so['caller_name']} · {so['caller_email']}")], widths=(40 * mm, 116 * mm)),
        Paragraph("Order lines", S_H),
        Table([["Ln", "Item", "Description", "UOM", "Ordered", "Shipped", "Unit price", "Amount"]] +
              [[l["line_number"], l["item_number"], Paragraph(l["description"], S_N), l["uom"],
                f"{l['ordered_quantity']:,}", f"{l['shipped_quantity']:,}",
                f"{l['unit_selling_price']:,.2f}", f"{l['extended_amount']:,.2f}"]
               for l in so["lines"]],
              colWidths=[8 * mm, 26 * mm, 54 * mm, 11 * mm, 16 * mm, 16 * mm, 20 * mm, 22 * mm], style=GRID),
        Spacer(1, 7),
        kv_table([("Goods", f"{so['totals']['goods_amount']:,.2f}"),
                  ("Surcharges", f"{so['totals']['surcharge_amount']:,.2f}"),
                  ("Freight", f"{so['totals']['freight_amount']:,.2f}"),
                  ("Tax", f"{so['totals']['tax_amount']:,.2f}"),
                  ("Order total", f"{so['totals']['order_total']:,.2f} {so['currency']}")],
                 widths=(40 * mm, 40 * mm)),
    ]
    fn = f"so_{so['order_number']}.pdf"
    build_pdf(fn, ent, "Sales Order Acknowledgement", so["order_number"], body)
    register_doc(so["document_id"], "SALES_ORDER", fn, "Sales Order Acknowledgement",
                 so["order_number"], "sales_order", so["order_number"], so["entered_date"])

# --- delivery note PDFs ----------------------------------------------------
for dn in deliveries:
    cust = CUST_BY_ID[dn["customer_id"]]
    ent = ENTITY_BY_OU[cust["operating_unit"]]
    so = SO_BY_NO[dn["sales_order"]]
    body = [
        Spacer(1, 3),
        Table([[Paragraph("<b>Ship from</b><br/>" + dn["ship_from"], S_N),
                Paragraph("<b>Ship to</b><br/>" + addr_block(dn["ship_to"]), S_N)]],
              colWidths=[84 * mm, 84 * mm],
              style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8)])),
        Spacer(1, 6),
        kv_table([("Delivery note", dn["delivery_number"]), ("Sales order", dn["sales_order"]),
                  ("Customer PO", so["customer_po_number"]), ("Ship date", dn["ship_date"]),
                  ("Carrier", dn["carrier"]), ("Waybill", dn["waybill"]),
                  ("Incoterms", dn["incoterms"]),
                  ("Proof of delivery", dn["proof_of_delivery_date"]),
                  ("Gross weight", f"{dn['gross_weight_kg']:,.2f} kg")], widths=(40 * mm, 116 * mm)),
        Paragraph("Shipped items", S_H),
        Table([["Ln", "Item", "UOM", "Ordered", "Shipped", "Backordered"]] +
              [[l["delivery_line"], l["item_number"], l["uom"], f"{l['ordered_quantity']:,}",
                f"{l['shipped_quantity']:,}", f"{l['backordered_quantity']:,}"]
               for l in dn["lines"]],
              colWidths=[10 * mm, 40 * mm, 16 * mm, 26 * mm, 26 * mm, 30 * mm], style=GRID),
        Spacer(1, 8),
        Paragraph("Quantities shown as shipped are the quantities eligible for invoicing under a "
                  "delivery-based billing rule.", S_N),
    ]
    fn = f"dn_{dn['delivery_number']}.pdf"
    build_pdf(fn, ent, "Delivery Note / Packing List", dn["delivery_number"], body)
    register_doc(dn["document_id"], "DELIVERY_NOTE", fn, "Delivery Note / Packing List",
                 dn["delivery_number"], "delivery", dn["delivery_number"], dn["ship_date"])


# =========================================================================== #
# 10. EMIT THE JSON API
# =========================================================================== #
DOC_BY_ID = {d["document_id"]: d for d in documents}
GENERATED = datetime.now().replace(microsecond=0).isoformat() + "Z"


def envelope(obj_name, rows, **extra):
    return {"source_system": "ORBIS ERP", "object": obj_name, "count": len(rows),
            "generated_at": GENERATED, **extra, "data": rows}


def docs_for(object_name, key):
    return [{"document_id": d["document_id"], "document_type": d["document_type"],
             "title": d["title"], "url": d["url"], "size_bytes": d["size_bytes"]}
            for d in documents if d["related_object"] == object_name and d["related_key"] == key]


# masters
dump(f"{API}/operating-units.json", envelope("Operating Unit", OPERATING_UNITS))
dump(f"{API}/tax-rules.json", envelope("Tax Rule", TAX_RULES))
dump(f"{API}/items.json", envelope("Item Master", ITEMS))
dump(f"{API}/price-list.json", envelope("Price List Line", PRICE_LIST))
dump(f"{API}/field-map.json", {
    "source_system": "ORBIS ERP", "object": "Invoice Field Lineage",
    "note": "Which invoice field is validated against which upstream object, and in what precedence.",
    "count": len(FIELD_MAP), "generated_at": GENERATED, "data": FIELD_MAP,
})

customer_grid = ["customer_id", "customer_name", "customer_class", "country", "currency",
                 "operating_unit", "tax_code", "payment_terms", "credit_limit", "collector"]
dump(f"{API}/customers.json", envelope("Customer", [{k: c[k] for k in customer_grid} for c in CUSTOMERS]))
for c in CUSTOMERS:
    contract = CONTRACT_BY_CUST[c["customer_id"]]
    dump(f"{API}/customers/{c['customer_id']}.json", {
        "source_system": "ORBIS ERP", "object": "Customer",
        "data": {**c, "contract_number": contract["contract_number"],
                 "orders": [o["order_number"] for o in sales_orders if o["customer_id"] == c["customer_id"]]},
    })

contract_grid = ["contract_number", "contract_type", "customer_id", "status", "effective_from",
                 "effective_to", "currency", "price_list", "discount_pct", "payment_terms",
                 "incoterms", "freight_terms", "tax_treatment", "po_required", "surcharge_allowed"]
dump(f"{API}/contracts.json", envelope("Contract", [
    {**{k: c[k] for k in contract_grid}, "customer_name": CUST_BY_ID[c["customer_id"]]["customer_name"]}
    for c in CONTRACTS]))
for c in CONTRACTS:
    dump(f"{API}/contracts/{c['contract_number']}.json", {
        "source_system": "ORBIS ERP", "object": "Contract",
        "data": {**c, "customer_name": CUST_BY_ID[c["customer_id"]]["customer_name"],
                 "price_list_lines": [r for r in PRICE_LIST if r["contract_number"] == c["contract_number"]],
                 "documents": docs_for("contract", c["contract_number"]),
                 "orders": [o["order_number"] for o in sales_orders if o["contract_number"] == c["contract_number"]]},
    })

po_grid = ["po_number", "customer_id", "customer_name", "contract_number", "po_date", "valid_to",
           "status", "currency", "po_amount_limit", "released_amount", "sales_order", "buyer_name"]
dump(f"{API}/purchase-orders.json", envelope("Customer Purchase Order",
                                             [{k: p[k] for k in po_grid} for p in purchase_orders]))
for p in purchase_orders:
    dump(f"{API}/purchase-orders/{p['po_number']}.json", {
        "source_system": "ORBIS ERP", "object": "Customer Purchase Order",
        "data": {**p, "documents": docs_for("purchase_order", p["po_number"])},
    })

so_grid = ["order_number", "customer_po_number", "contract_number", "customer_id",
           "customer_name_bill_to", "customer_name_ship_to", "operating_unit", "status",
           "entered_date", "invoiced_date", "requested_ship_date", "currency", "payment_terms",
           "incoterms", "tax_code", "delivery_number", "transaction_originator", "caller_email"]
dump(f"{API}/sales-orders.json", envelope("Sales Order", [
    {**{k: o[k] for k in so_grid},
     "state_bill_to": o["bill_to"]["state"], "state_ship_to": o["ship_to"]["state"],
     "city_bill_to": o["bill_to"]["city"], "city_ship_to": o["ship_to"]["city"],
     "line_count": len(o["lines"]), "order_total": o["totals"]["order_total"],
     "on_hold": any(not h.get("released") for h in o["holds"])}
    for o in sales_orders]))
for o in sales_orders:
    dump(f"{API}/sales-orders/{o['order_number']}.json", {
        "source_system": "ORBIS ERP", "object": "Sales Order",
        "data": {**o, "documents": docs_for("sales_order", o["order_number"])},
    })

dn_grid = ["delivery_number", "sales_order", "customer_id", "ship_date", "carrier", "waybill",
           "proof_of_delivery_date", "incoterms"]
dump(f"{API}/deliveries.json", envelope("Delivery", [{k: d[k] for k in dn_grid} for d in deliveries]))
for d in deliveries:
    dump(f"{API}/deliveries/{d['delivery_number']}.json", {
        "source_system": "ORBIS ERP", "object": "Delivery",
        "data": {**d, "documents": docs_for("delivery", d["delivery_number"])},
    })

bd_grid = ["draft_number", "proposed_invoice_number", "status", "sales_order", "customer_po_number",
           "contract_number", "delivery_number", "customer_id", "invoice_date", "prepared_on",
           "prepared_by", "billing_type", "currency", "payment_terms", "incoterms", "tax_code",
           "tax_treatment", "tax_rate", "customer_tax_registration", "exemption_certificate",
           "operating_unit", "legal_entity", "notes"]


def draft_header_row(b: dict) -> dict:
    """Full header row: every field on the draft a validator has to check."""
    order = SO_BY_NO[b["sales_order"]]
    cust = CUST_BY_ID[b["customer_id"]]
    t = b["totals"]
    bt, st = b["bill_to"], b["ship_to"]
    return {
        **{k: b[k] for k in bd_grid},
        "customer_name": cust["customer_name"],
        "order_status": order["status"],
        "order_invoiced_date": order["invoiced_date"],
        "order_on_hold": any(not h.get("released") for h in order["holds"]),
        "bill_to_name": bt["name"], "bill_to_site_use_id": bt["site_use_id"],
        "bill_to_address_1": bt["address_1"], "bill_to_address_2": bt["address_2"],
        "bill_to_address_3": bt["address_3"], "bill_to_address_4": bt["address_4"],
        "bill_to_city": bt["city"], "bill_to_state": bt["state"],
        "bill_to_postal_code": bt["postal_code"], "bill_to_country": bt["country"],
        "ship_to_name": st["name"], "ship_to_site_use_id": st["site_use_id"],
        "ship_to_address_1": st["address_1"], "ship_to_address_2": st["address_2"],
        "ship_to_address_3": st["address_3"], "ship_to_address_4": st["address_4"],
        "ship_to_city": st["city"], "ship_to_state": st["state"],
        "ship_to_postal_code": st["postal_code"], "ship_to_country": st["country"],
        "line_count": len(b["lines"]),
        "goods_line_count": sum(1 for l in b["lines"] if l["line_type"] == "GOODS"),
        "total_quantity": sum(l["quantity_to_bill"] for l in b["lines"] if l["line_type"] == "GOODS"),
        "goods_subtotal": t["goods_subtotal"], "surcharge_total": t["surcharge_total"],
        "freight_total": t["freight_total"],
        "net_subtotal": money(t["goods_subtotal"] + t["surcharge_total"] + t["freight_total"]),
        "tax_amount": t["tax_amount"], "total_payable": t["total_payable"],
    }


dump(f"{API}/billing-drafts.json", envelope("Billing Draft",
                                            [draft_header_row(b) for b in billing_drafts]))


def draft_line_rows(b: dict) -> list[dict]:
    """One row per draft line, header denormalised on, plus ref_ values from the source objects."""
    order = SO_BY_NO[b["sales_order"]]
    contract = CONTRACT_BY_NO[b["contract_number"]]
    delivery = DN_BY_NO.get(b["delivery_number"] or "")
    cust = CUST_BY_ID[b["customer_id"]]
    po = PO_BY_NO.get(order["customer_po_number"]) or {}
    header = draft_header_row(b)
    header_fields = {k: v for k, v in header.items()
                     if k not in ("line_count", "goods_line_count", "total_quantity")}
    so_by_item = {l["item_number"]: l for l in order["lines"]}
    dn_by_item = {l["item_number"]: l for l in (delivery["lines"] if delivery else [])}
    price_by_item = {r["item_number"]: r for r in PRICE_LIST
                     if r["contract_number"] == contract["contract_number"]}
    tax = TAX_BY_CODE[cust["tax_code"]]

    rows = []
    for l in b["lines"]:
        item = ITEM_BY_NO[l["item_number"]]
        so_l = so_by_item.get(l["item_number"], {})
        dn_l = dn_by_item.get(l["item_number"], {})
        pr = price_by_item.get(l["item_number"], {})
        rows.append({
            **header_fields,
            "line": l["line"], "item_number": l["item_number"], "item_description": l["description"],
            "item_class": item["item_class"], "line_type": l["line_type"], "uom": l["uom"],
            "quantity_to_bill": l["quantity_to_bill"], "unit_price": l["unit_price"],
            "line_amount": l["amount"], "line_tax_code": l["tax_code"], "line_tax_rate": l["tax_rate"],
            "line_tax_amount": l["tax_amount"],
            "line_total_incl_tax": money(l["amount"] + l["tax_amount"]),
            "line_source": l["source"], "line_source_reference": l["source_reference"],
            "hs_code": item["hs_code"], "taxable_item": item["taxable"],
            "ref_item_list_price": item["list_price"],
            "ref_contract_price": pr.get("contract_price"),
            "ref_contract_discount_pct": contract["discount_pct"],
            "ref_ordered_quantity": so_l.get("ordered_quantity"),
            "ref_shipped_quantity": dn_l.get("shipped_quantity", so_l.get("shipped_quantity")),
            "ref_backordered_quantity": dn_l.get("backordered_quantity"),
            "ref_order_unit_selling_price": so_l.get("unit_selling_price"),
            "ref_order_extended_amount": so_l.get("extended_amount"),
            "ref_contract_payment_terms": contract["payment_terms"],
            "ref_contract_incoterms": contract["incoterms"],
            "ref_contract_currency": contract["currency"],
            "ref_contract_freight_terms": contract["freight_terms"],
            "ref_contract_surcharge_allowed": contract["surcharge_allowed"],
            "ref_contract_po_required": contract["po_required"],
            "ref_contract_price_tolerance_pct": contract["price_tolerance_pct"],
            "ref_contract_qty_tolerance_pct": contract["qty_tolerance_pct"],
            "ref_customer_tax_code": cust["tax_code"],
            "ref_customer_tax_rate": tax["rate"],
            "ref_customer_tax_treatment": tax["treatment"],
            "ref_po_valid_to": po.get("valid_to"), "ref_po_status": po.get("status"),
            "ref_po_amount_limit": po.get("po_amount_limit"),
            "ref_proof_of_delivery_date": (delivery or {}).get("proof_of_delivery_date"),
        })
    return rows


flat_lines = [r for b in billing_drafts for r in draft_line_rows(b)]
dump(f"{API}/billing-draft-lines.json", envelope(
    "Billing Draft Line (flat)", flat_lines,
    note="One row per draft line with every header field denormalised onto it. Columns prefixed ref_ "
         "are joined from the source objects (contract, purchase order, sales order, delivery, tax "
         "rules) for convenience - they are the values the draft should agree with, not part of the "
         "draft itself."))
for b in billing_drafts:
    order = SO_BY_NO[b["sales_order"]]
    dump(f"{API}/billing-drafts/{b['draft_number']}.json", {
        "source_system": "ORBIS ERP", "object": "Billing Draft",
        "data": {**b, "customer_name": CUST_BY_ID[b["customer_id"]]["customer_name"],
                 "order_status": order["status"], "order_invoiced_date": order["invoiced_date"],
                 "documents": (docs_for("sales_order", b["sales_order"])
                               + docs_for("purchase_order", order["customer_po_number"])
                               + docs_for("contract", b["contract_number"])
                               + docs_for("delivery", b["delivery_number"] or ""))},
    })

dump(f"{API}/documents.json", envelope("Document", documents))
dump(f"{API}/mismatches.json", {
    "note": "Answer key for the billing validation POC. ORBIS is the source of truth; "
            "the defects listed here were deliberately seeded into the billing drafts.",
    "count": len(answer_key), "generated_at": GENERATED, "data": answer_key,
})

INTEGRATION_ENDPOINTS = {
    "validation_package_index": "api/validation-packages.json",
    "validation_package": "api/validation-packages/{draft_number}.json",
    "full_bundle": "api/bundle.json",
    "openapi": "api/openapi.json",
}

dump(f"{API}/index.json", {
    "system": "ORBIS — Order & Revenue Billing Information System",
    "purpose": "Pre-billing source of truth for an invoice field validation POC.",
    "generated_at": GENERATED,
    "endpoints": {
        "operating_units": "api/operating-units.json",
        "customers": "api/customers.json",
        "customer_detail": "api/customers/{customer_id}.json",
        "contracts": "api/contracts.json",
        "contract_detail": "api/contracts/{contract_number}.json",
        "price_list": "api/price-list.json",
        "items": "api/items.json",
        "tax_rules": "api/tax-rules.json",
        "purchase_orders": "api/purchase-orders.json",
        "purchase_order_detail": "api/purchase-orders/{po_number}.json",
        "sales_orders": "api/sales-orders.json",
        "sales_order_detail": "api/sales-orders/{order_number}.json",
        "deliveries": "api/deliveries.json",
        "delivery_detail": "api/deliveries/{delivery_number}.json",
        "billing_drafts": "api/billing-drafts.json",
        "billing_draft_detail": "api/billing-drafts/{draft_number}.json",
        "billing_draft_lines_flat": "api/billing-draft-lines.json",
        "documents": "api/documents.json",
        "field_map": "api/field-map.json",
        "expected_findings": "api/mismatches.json",
        **INTEGRATION_ENDPOINTS,
    },
    "integration_notes": {
        "auth": "None. Public read-only static hosting.",
        "cors": "Access-Control-Allow-Origin: * on every file, PDFs included.",
        "recommended_entry_point": "api/validation-packages/{draft_number}.json returns a draft with all "
                                   "upstream objects pre-joined, so one request replaces six.",
        "document_urls": "Relative to the site root. Join with the base URL: {base}/docs/{file_name}.",
    },
    "join_keys": {
        "draft_to_order": "billing_draft.sales_order = sales_order.order_number",
        "order_to_po": "sales_order.customer_po_number = purchase_order.po_number",
        "order_to_contract": "sales_order.contract_number = contract.contract_number",
        "order_to_delivery": "sales_order.delivery_number = delivery.delivery_number",
        "line_price": "billing_draft.lines.unit_price = price_list.contract_price (by item and contract)",
        "tax": "billing_draft.tax_code = tax_rule.tax_code",
    },
    "counts": {
        "customers": len(CUSTOMERS), "contracts": len(CONTRACTS),
        "purchase_orders": len(purchase_orders), "sales_orders": len(sales_orders),
        "order_lines": sum(len(o["lines"]) for o in sales_orders),
        "deliveries": len(deliveries), "billing_drafts": len(billing_drafts),
        "documents": len(documents), "validated_fields": len(FIELD_MAP),
        "seeded_findings": len(answer_key),
    },
})


# =========================================================================== #
# 11. MYSQL MIRROR
# =========================================================================== #
def q(v):
    if v is None or v == "":
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


schema = """-- ORBIS pre-billing dataset, MySQL mirror of the JSON API.
CREATE DATABASE IF NOT EXISTS orbis_erp CHARACTER SET utf8mb4;
USE orbis_erp;

DROP TABLE IF EXISTS billing_draft_line, billing_draft, delivery_line, delivery,
  so_line, sales_order, po_line, purchase_order, price_list, contract, customer, item, tax_rule;

CREATE TABLE tax_rule (
  tax_code VARCHAR(20) PRIMARY KEY, jurisdiction VARCHAR(20), rate DECIMAL(6,3),
  treatment VARCHAR(24), basis VARCHAR(160), requires_certificate TINYINT
);

CREATE TABLE item (
  item_number VARCHAR(30) PRIMARY KEY, description VARCHAR(120), item_class VARCHAR(24),
  uom VARCHAR(6), list_price DECIMAL(12,2), line_type VARCHAR(12), taxable TINYINT,
  hs_code VARCHAR(12), operating_unit VARCHAR(40)
);

CREATE TABLE customer (
  customer_id VARCHAR(12) PRIMARY KEY, customer_name VARCHAR(80), customer_class VARCHAR(24),
  country CHAR(2), currency CHAR(3), operating_unit VARCHAR(40), tax_code VARCHAR(20),
  tax_registration VARCHAR(30), exemption_certificate VARCHAR(30), credit_limit DECIMAL(14,2),
  payment_terms VARCHAR(20), collector VARCHAR(40),
  bill_to_name VARCHAR(80), bill_to_address_1 VARCHAR(80), bill_to_address_2 VARCHAR(80),
  bill_to_address_3 VARCHAR(80), bill_to_address_4 VARCHAR(80), bill_to_city VARCHAR(40),
  bill_to_state VARCHAR(6), bill_to_postal VARCHAR(12),
  ship_to_name VARCHAR(80), ship_to_address_1 VARCHAR(80), ship_to_address_2 VARCHAR(80),
  ship_to_address_3 VARCHAR(80), ship_to_address_4 VARCHAR(80), ship_to_city VARCHAR(40),
  ship_to_state VARCHAR(6), ship_to_postal VARCHAR(12),
  contact_name VARCHAR(60), contact_email VARCHAR(80), contact_phone VARCHAR(30),
  INDEX idx_cust_tax (tax_code)
);

CREATE TABLE contract (
  contract_number VARCHAR(32) PRIMARY KEY, contract_type VARCHAR(24), customer_id VARCHAR(12),
  status VARCHAR(12), effective_from DATE, effective_to DATE, currency CHAR(3),
  price_list VARCHAR(24), discount_pct DECIMAL(6,2), payment_terms VARCHAR(20),
  incoterms VARCHAR(40), freight_terms VARCHAR(20), billing_rule VARCHAR(20),
  tax_treatment VARCHAR(24), po_required TINYINT, surcharge_allowed TINYINT,
  price_tolerance_pct DECIMAL(5,2), qty_tolerance_pct DECIMAL(5,2),
  INDEX idx_contract_cust (customer_id)
);

CREATE TABLE price_list (
  price_list VARCHAR(24), contract_number VARCHAR(32), item_number VARCHAR(30),
  uom VARCHAR(6), list_price DECIMAL(12,2), discount_pct DECIMAL(6,2),
  contract_price DECIMAL(12,2), currency CHAR(3), effective_from DATE, effective_to DATE,
  PRIMARY KEY (contract_number, item_number)
);

CREATE TABLE purchase_order (
  po_number VARCHAR(24) PRIMARY KEY, customer_id VARCHAR(12), contract_number VARCHAR(32),
  po_date DATE, valid_from DATE, valid_to DATE, status VARCHAR(12), currency CHAR(3),
  po_amount_limit DECIMAL(14,2), released_amount DECIMAL(14,2), buyer_name VARCHAR(60),
  buyer_email VARCHAR(80), payment_terms VARCHAR(20), incoterms VARCHAR(40), sales_order VARCHAR(24)
);

CREATE TABLE po_line (
  po_number VARCHAR(24), po_line INT, item_number VARCHAR(30), uom VARCHAR(6),
  quantity DECIMAL(14,3), unit_price DECIMAL(12,4), amount DECIMAL(14,2),
  PRIMARY KEY (po_number, po_line)
);

CREATE TABLE sales_order (
  order_number VARCHAR(24) PRIMARY KEY, customer_po_number VARCHAR(24), contract_number VARCHAR(32),
  customer_id VARCHAR(12), operating_unit VARCHAR(40), legal_entity VARCHAR(60),
  order_type VARCHAR(24), order_source VARCHAR(20), status VARCHAR(20),
  entered_date DATE, booked_date DATE, requested_ship_date DATE, invoiced_date DATE,
  transaction_originator VARCHAR(40), caller_name VARCHAR(60), caller_email VARCHAR(80),
  caller_phone VARCHAR(30), currency CHAR(3), payment_terms VARCHAR(20), incoterms VARCHAR(40),
  freight_terms VARCHAR(20), tax_code VARCHAR(20), tax_treatment VARCHAR(24),
  price_list VARCHAR(24), delivery_number VARCHAR(24),
  goods_amount DECIMAL(14,2), surcharge_amount DECIMAL(14,2), freight_amount DECIMAL(14,2),
  tax_amount DECIMAL(14,2), order_total DECIMAL(14,2),
  INDEX idx_so_po (customer_po_number), INDEX idx_so_contract (contract_number)
);

CREATE TABLE so_line (
  order_number VARCHAR(24), line_number INT, item_number VARCHAR(30), line_type VARCHAR(12),
  uom VARCHAR(6), ordered_quantity DECIMAL(14,3), shipped_quantity DECIMAL(14,3),
  unit_list_price DECIMAL(12,4), contract_price DECIMAL(12,4), unit_selling_price DECIMAL(12,4),
  discount_pct DECIMAL(6,2), extended_amount DECIMAL(14,2), tax_code VARCHAR(20),
  tax_rate DECIMAL(6,3), tax_amount DECIMAL(14,2), revenue_account VARCHAR(30),
  PRIMARY KEY (order_number, line_number)
);

CREATE TABLE delivery (
  delivery_number VARCHAR(24) PRIMARY KEY, sales_order VARCHAR(24), customer_id VARCHAR(12),
  ship_date DATE, carrier VARCHAR(40), waybill VARCHAR(30), incoterms VARCHAR(40),
  proof_of_delivery_date DATE, gross_weight_kg DECIMAL(12,2)
);

CREATE TABLE delivery_line (
  delivery_number VARCHAR(24), delivery_line INT, item_number VARCHAR(30), uom VARCHAR(6),
  ordered_quantity DECIMAL(14,3), shipped_quantity DECIMAL(14,3), backordered_quantity DECIMAL(14,3),
  PRIMARY KEY (delivery_number, delivery_line)
);

CREATE TABLE billing_draft (
  draft_number VARCHAR(24) PRIMARY KEY, proposed_invoice_number VARCHAR(32), status VARCHAR(24),
  sales_order VARCHAR(24), customer_po_number VARCHAR(24), contract_number VARCHAR(32),
  delivery_number VARCHAR(24), customer_id VARCHAR(12), operating_unit VARCHAR(40),
  invoice_date DATE, prepared_on DATE, prepared_by VARCHAR(40), billing_type VARCHAR(40),
  currency CHAR(3), payment_terms VARCHAR(20), incoterms VARCHAR(40),
  tax_code VARCHAR(20), tax_treatment VARCHAR(24), tax_rate DECIMAL(6,3),
  bill_to_name VARCHAR(80), bill_to_address_4 VARCHAR(80), bill_to_city VARCHAR(40),
  bill_to_state VARCHAR(6), bill_to_postal VARCHAR(12),
  goods_subtotal DECIMAL(14,2), surcharge_total DECIMAL(14,2), freight_total DECIMAL(14,2),
  tax_amount DECIMAL(14,2), total_payable DECIMAL(14,2),
  INDEX idx_bd_order (sales_order)
);

CREATE TABLE billing_draft_line (
  draft_number VARCHAR(24), line INT, item_number VARCHAR(30), line_type VARCHAR(12),
  uom VARCHAR(6), quantity_to_bill DECIMAL(14,3), unit_price DECIMAL(12,4),
  amount DECIMAL(14,2), tax_code VARCHAR(20), tax_rate DECIMAL(6,3), tax_amount DECIMAL(14,2),
  source VARCHAR(16), source_reference VARCHAR(24),
  PRIMARY KEY (draft_number, line)
);
"""
os.makedirs(os.path.join(ROOT, "sql"), exist_ok=True)
with open(os.path.join(ROOT, "sql", "schema.sql"), "w") as f:
    f.write(schema)

rows = ["USE orbis_erp;", ""]
for t in TAX_RULES:
    rows.append("INSERT INTO tax_rule VALUES (" + ", ".join(map(q, [
        t["tax_code"], t["jurisdiction"], t["rate"], t["treatment"], t["basis"],
        t["requires_certificate"]])) + ");")
for i in ITEMS:
    rows.append("INSERT INTO item VALUES (" + ", ".join(map(q, [
        i["item_number"], i["description"], i["item_class"], i["uom"], i["list_price"],
        i["line_type"], i["taxable"], i["hs_code"], i["operating_unit"]])) + ");")
for c in CUSTOMERS:
    b, s = c["bill_to"], c["ship_to"]
    rows.append("INSERT INTO customer VALUES (" + ", ".join(map(q, [
        c["customer_id"], c["customer_name"], c["customer_class"], c["country"], c["currency"],
        c["operating_unit"], c["tax_code"], c["tax_registration"], c["exemption_certificate"],
        c["credit_limit"], c["payment_terms"], c["collector"],
        b["name"], b["address_1"], b["address_2"], b["address_3"], b["address_4"], b["city"],
        b["state"], b["postal_code"],
        s["name"], s["address_1"], s["address_2"], s["address_3"], s["address_4"], s["city"],
        s["state"], s["postal_code"],
        c["contact_name"], c["contact_email"], c["contact_phone"]])) + ");")
for c in CONTRACTS:
    rows.append("INSERT INTO contract VALUES (" + ", ".join(map(q, [
        c["contract_number"], c["contract_type"], c["customer_id"], c["status"],
        c["effective_from"], c["effective_to"], c["currency"], c["price_list"], c["discount_pct"],
        c["payment_terms"], c["incoterms"], c["freight_terms"], c["billing_rule"],
        c["tax_treatment"], c["po_required"], c["surcharge_allowed"],
        c["price_tolerance_pct"], c["qty_tolerance_pct"]])) + ");")
for r in PRICE_LIST:
    rows.append("INSERT INTO price_list VALUES (" + ", ".join(map(q, [
        r["price_list"], r["contract_number"], r["item_number"], r["uom"], r["list_price"],
        r["discount_pct"], r["contract_price"], r["currency"], r["effective_from"],
        r["effective_to"]])) + ");")
for p in purchase_orders:
    rows.append("INSERT INTO purchase_order VALUES (" + ", ".join(map(q, [
        p["po_number"], p["customer_id"], p["contract_number"], p["po_date"], p["valid_from"],
        p["valid_to"], p["status"], p["currency"], p["po_amount_limit"], p["released_amount"],
        p["buyer_name"], p["buyer_email"], p["payment_terms"], p["incoterms"], p["sales_order"]])) + ");")
    for l in p["lines"]:
        rows.append("INSERT INTO po_line VALUES (" + ", ".join(map(q, [
            p["po_number"], l["po_line"], l["item_number"], l["uom"], l["quantity"],
            l["unit_price"], l["amount"]])) + ");")
for o in sales_orders:
    t = o["totals"]
    rows.append("INSERT INTO sales_order VALUES (" + ", ".join(map(q, [
        o["order_number"], o["customer_po_number"], o["contract_number"], o["customer_id"],
        o["operating_unit"], o["legal_entity"], o["order_type"], o["order_source"], o["status"],
        o["entered_date"], o["booked_date"], o["requested_ship_date"], o["invoiced_date"],
        o["transaction_originator"], o["caller_name"], o["caller_email"], o["caller_phone"],
        o["currency"], o["payment_terms"], o["incoterms"], o["freight_terms"], o["tax_code"],
        o["tax_treatment"], o["price_list"], o["delivery_number"],
        t["goods_amount"], t["surcharge_amount"], t["freight_amount"], t["tax_amount"],
        t["order_total"]])) + ");")
    for l in o["lines"]:
        rows.append("INSERT INTO so_line VALUES (" + ", ".join(map(q, [
            o["order_number"], l["line_number"], l["item_number"], l["line_type"], l["uom"],
            l["ordered_quantity"], l["shipped_quantity"], l["unit_list_price"], l["contract_price"],
            l["unit_selling_price"], l["discount_pct"], l["extended_amount"], l["tax_code"],
            l["tax_rate"], l["tax_amount"], l["revenue_account"]])) + ");")
for d in deliveries:
    rows.append("INSERT INTO delivery VALUES (" + ", ".join(map(q, [
        d["delivery_number"], d["sales_order"], d["customer_id"], d["ship_date"], d["carrier"],
        d["waybill"], d["incoterms"], d["proof_of_delivery_date"], d["gross_weight_kg"]])) + ");")
    for l in d["lines"]:
        rows.append("INSERT INTO delivery_line VALUES (" + ", ".join(map(q, [
            d["delivery_number"], l["delivery_line"], l["item_number"], l["uom"],
            l["ordered_quantity"], l["shipped_quantity"], l["backordered_quantity"]])) + ");")
for b in billing_drafts:
    t, bt = b["totals"], b["bill_to"]
    rows.append("INSERT INTO billing_draft VALUES (" + ", ".join(map(q, [
        b["draft_number"], b["proposed_invoice_number"], b["status"], b["sales_order"],
        b["customer_po_number"], b["contract_number"], b["delivery_number"], b["customer_id"],
        b["operating_unit"], b["invoice_date"], b["prepared_on"], b["prepared_by"],
        b["billing_type"], b["currency"], b["payment_terms"], b["incoterms"], b["tax_code"],
        b["tax_treatment"], b["tax_rate"], bt["name"], bt["address_4"], bt["city"], bt["state"],
        bt["postal_code"], t["goods_subtotal"], t["surcharge_total"], t["freight_total"],
        t["tax_amount"], t["total_payable"]])) + ");")
    for l in b["lines"]:
        rows.append("INSERT INTO billing_draft_line VALUES (" + ", ".join(map(q, [
            b["draft_number"], l["line"], l["item_number"], l["line_type"], l["uom"],
            l["quantity_to_bill"], l["unit_price"], l["amount"], l["tax_code"], l["tax_rate"],
            l["tax_amount"], l["source"], l["source_reference"]])) + ");")

with open(os.path.join(ROOT, "sql", "seed.sql"), "w") as f:
    f.write("\n".join(rows) + "\n")

print(f"customers {len(CUSTOMERS)} | contracts {len(CONTRACTS)} | POs {len(purchase_orders)} | "
      f"orders {len(sales_orders)} | deliveries {len(deliveries)} | drafts {len(billing_drafts)} | "
      f"documents {len(documents)} | seeded findings {len(answer_key)}")


# =========================================================================== #
# 12. INTEGRATION ENDPOINTS
#     Built for an external validation client: one pre-joined package per
#     billing draft, one full-dataset bundle, and a machine-readable spec.
# =========================================================================== #
TAX_BY_CODE_ALL = {t["tax_code"]: t for t in TAX_RULES}


def validation_package(b: dict) -> dict:
    """Everything needed to validate one billing draft, in a single response."""
    order = SO_BY_NO[b["sales_order"]]
    contract = CONTRACT_BY_NO[b["contract_number"]]
    cust = CUST_BY_ID[b["customer_id"]]
    po = PO_BY_NO.get(order["customer_po_number"])
    dn = DN_BY_NO.get(order["delivery_number"] or "")
    return {
        "package_for": b["draft_number"],
        "generated_at": GENERATED,
        "billing_draft": {**b, "customer_name": cust["customer_name"],
                          "order_status": order["status"], "order_invoiced_date": order["invoiced_date"]},
        "sales_order": order,
        "purchase_order": po,
        "contract": {**contract,
                     "price_list_lines": [r for r in PRICE_LIST if r["contract_number"] == contract["contract_number"]]},
        "delivery": dn,
        "customer": cust,
        "tax_rules": {
            "draft_tax_code": TAX_BY_CODE_ALL.get(b["tax_code"]),
            "customer_tax_code": TAX_BY_CODE_ALL.get(cust["tax_code"]),
        },
        "items": {l["item_number"]: ITEM_BY_NO[l["item_number"]] for l in b["lines"]},
        "documents": (docs_for("contract", contract["contract_number"])
                      + docs_for("purchase_order", order["customer_po_number"])
                      + docs_for("sales_order", order["order_number"])
                      + (docs_for("delivery", order["delivery_number"]) if order["delivery_number"] else [])),
    }


packages = [validation_package(b) for b in billing_drafts]
for p in packages:
    dump(f"{API}/validation-packages/{p['package_for']}.json", p)

dump(f"{API}/validation-packages.json", {
    "source_system": "ORBIS ERP", "object": "Validation Package",
    "note": "One call per draft returns the draft plus every upstream object needed to validate it: "
            "sales order, purchase order, contract with price list, delivery, customer, tax rules, "
            "item master and the URLs of all source documents.",
    "count": len(packages), "generated_at": GENERATED,
    "data": [{"draft_number": p["package_for"],
              "url": f"api/validation-packages/{p['package_for']}.json",
              "sales_order": p["billing_draft"]["sales_order"],
              "customer_id": p["billing_draft"]["customer_id"],
              "total_payable": p["billing_draft"]["totals"]["total_payable"],
              "currency": p["billing_draft"]["totals"]["currency"],
              "document_count": len(p["documents"])}
             for p in packages],
})

# whole dataset in one request, for clients that would rather cache locally
dump(f"{API}/bundle.json", {
    "source_system": "ORBIS ERP", "object": "Full Dataset", "generated_at": GENERATED,
    "note": "Every object in one response. Use this to pull the model once and validate offline.",
    "operating_units": OPERATING_UNITS,
    "tax_rules": TAX_RULES,
    "items": ITEMS,
    "price_list": PRICE_LIST,
    "customers": CUSTOMERS,
    "contracts": CONTRACTS,
    "purchase_orders": purchase_orders,
    "sales_orders": sales_orders,
    "deliveries": deliveries,
    "billing_drafts": billing_drafts,
    "documents": documents,
    "field_map": FIELD_MAP,
})

# machine-readable description of the read-only API
def _get(path, summary, description):
    return {path: {"get": {"summary": summary, "description": description,
                           "responses": {"200": {"description": "JSON document",
                                                 "content": {"application/json": {}}}}}}}


paths = {}
for p, s, d in [
    ("/api/index.json", "Service catalogue", "Endpoint list, join keys and record counts."),
    ("/api/bundle.json", "Full dataset", "Every object in one response."),
    ("/api/validation-packages.json", "Validation package index", "One entry per billing draft."),
    ("/api/validation-packages/{draft_number}.json", "Validation package",
     "A billing draft plus every upstream object needed to validate it."),
    ("/api/billing-drafts.json", "Billing drafts", "Pre-invoice drafts awaiting validation."),
    ("/api/billing-drafts/{draft_number}.json", "Billing draft", "Draft header, lines and totals."),
    ("/api/billing-draft-lines.json", "Billing draft lines (flat)",
     "One row per draft line, header denormalised, plus ref_ columns joined from the source objects."),
    ("/api/sales-orders.json", "Sales orders", "Order headers with billing status."),
    ("/api/sales-orders/{order_number}.json", "Sales order", "Header, lines, holds, documents."),
    ("/api/purchase-orders.json", "Customer purchase orders", "Validity window and authorised value."),
    ("/api/purchase-orders/{po_number}.json", "Customer purchase order", "Header, lines, documents."),
    ("/api/contracts.json", "Contracts", "Commercial terms per customer."),
    ("/api/contracts/{contract_number}.json", "Contract", "Terms, clauses and agreed price list."),
    ("/api/deliveries.json", "Deliveries", "Shipment headers with proof of delivery dates."),
    ("/api/deliveries/{delivery_number}.json", "Delivery", "Shipped and backordered quantities."),
    ("/api/customers.json", "Customers", "Customer master."),
    ("/api/customers/{customer_id}.json", "Customer", "Bill-to and ship-to sites, tax registration."),
    ("/api/price-list.json", "Price list", "Contract price per item."),
    ("/api/items.json", "Item master", "List price, UOM, taxability."),
    ("/api/tax-rules.json", "Tax rules", "Rate and treatment per jurisdiction."),
    ("/api/documents.json", "Document registry", "URL and metadata for every source PDF."),
    ("/api/field-map.json", "Invoice field lineage", "Authoritative source and precedence per field."),
    ("/api/mismatches.json", "Seeded defects", "Answer key for scoring a validation run."),
    ("/docs/{file_name}", "Source document", "A contract, PO, order acknowledgement or delivery note as PDF."),
]:
    paths.update(_get(p, s, d))

dump(f"{API}/openapi.json", {
    "openapi": "3.1.0",
    "info": {
        "title": "ORBIS ERP — pre-billing read API",
        "version": "1.0.0",
        "description": "Read-only JSON over static hosting. Every path is a file, so any HTTP client "
                       "works and no authentication is required. Responses carry "
                       "Access-Control-Allow-Origin: * so browser clients can call it directly.",
    },
    "servers": [{"url": "https://{user}.github.io/{repo}",
                 "variables": {"user": {"default": "your-user"}, "repo": {"default": "your-repo"}}}],
    "paths": paths,
})
print(f"integration: {len(packages)} validation packages, bundle.json, openapi.json")

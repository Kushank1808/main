-- ORBIS pre-billing dataset, MySQL mirror of the JSON API.
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

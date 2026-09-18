-- Workday + POMS layer — schema (MySQL 8)

CREATE TABLE wd_company (
  `company` VARCHAR(255),
  `company_name` VARCHAR(255),
  `country` VARCHAR(255),
  `currency` VARCHAR(255),
  `vat_rate` DECIMAL(16,2),
  `vat_registration` VARCHAR(255),
  `statutory_invoicing` VARCHAR(255),
  `market` VARCHAR(255),
  `exception_scope` VARCHAR(255),
  PRIMARY KEY (`company`)
);

CREATE TABLE wd_revenue_category (
  `revenue_category` VARCHAR(255),
  `name` VARCHAR(255),
  `is_fee` TINYINT(1),
  `ledger_account` VARCHAR(255),
  `note` VARCHAR(255),
  PRIMARY KEY (`revenue_category`)
);

CREATE TABLE wd_sales_item (
  `sales_item` VARCHAR(255),
  `name` VARCHAR(255),
  `default_revenue_category` VARCHAR(255),
  `item_group` VARCHAR(255),
  PRIMARY KEY (`sales_item`)
);

CREATE TABLE wd_customer (
  `customer_id` VARCHAR(255),
  `customer_name` VARCHAR(255),
  `company` VARCHAR(255),
  `customer_type` VARCHAR(255),
  `country` VARCHAR(255),
  `vat_number` VARCHAR(255),
  `related_party` TINYINT(1),
  `nga_customer` TINYINT(1),
  `leasing_plate_required` TINYINT(1),
  `loan_provider` TINYINT(1),
  `bpi_exception` TINYINT(1),
  `sharepoint_tracker` TINYINT(1),
  PRIMARY KEY (`customer_id`)
);

CREATE TABLE wd_customer_invoice (
  `invoice_number` VARCHAR(255),
  `document_kind` VARCHAR(255),
  `company` VARCHAR(255),
  `company_name` VARCHAR(255),
  `status` VARCHAR(255),
  `invoice_date` VARCHAR(255),
  `due_date` VARCHAR(255),
  `payment_terms` VARCHAR(255),
  `bill_to_customer_id` VARCHAR(255),
  `bill_to_customer` VARCHAR(255),
  `sold_to_customer_id` VARCHAR(255),
  `sold_to_customer` VARCHAR(255),
  `customer_vat_number` VARCHAR(255),
  `currency` VARCHAR(255),
  `po_number` VARCHAR(255),
  `vin` VARCHAR(255),
  `poms_order_number` VARCHAR(255),
  `model` VARCHAR(255),
  `statutory_invoice_type` VARCHAR(255),
  `statutory_invoice_number` VARCHAR(255),
  `memo` VARCHAR(255),
  `created_by` VARCHAR(255),
  `created_on` VARCHAR(255),
  `last_updated` VARCHAR(255),
  `line_count` BIGINT,
  `taxable_amount` DECIMAL(16,2),
  `tax_rate` DECIMAL(16,2),
  `tax_amount` DECIMAL(16,2),
  `subtotal` DECIMAL(16,2),
  `total_amount` DECIMAL(16,2),
  `has_fee_lines` TINYINT(1),
  `payment_applied_as` VARCHAR(255),
  PRIMARY KEY (`invoice_number`)
);

CREATE TABLE wd_customer_invoice_line (
  `invoice_number` VARCHAR(255),
  `line` BIGINT,
  `line_key` VARCHAR(255),
  `company` VARCHAR(255),
  `sales_item` VARCHAR(255),
  `sales_item_name` VARCHAR(255),
  `revenue_category` VARCHAR(255),
  `revenue_category_name` VARCHAR(255),
  `line_item_description` VARCHAR(255),
  `quantity` BIGINT,
  `unit_of_measure` VARCHAR(255),
  `quantity_2` BIGINT,
  `unit_of_measure_2` VARCHAR(255),
  `unit_price` DECIMAL(16,2),
  `extended_amount` DECIMAL(16,2),
  `released_on_invoice_lines` VARCHAR(255),
  `tax_applicability` VARCHAR(255),
  PRIMARY KEY (`line_key`)
);

CREATE TABLE poms_order (
  `order_number` VARCHAR(255),
  `market` VARCHAR(255),
  `company` VARCHAR(255),
  `vin` VARCHAR(255),
  `model` VARCHAR(255),
  `model_code` VARCHAR(255),
  `model_year` BIGINT,
  `exterior_colour` VARCHAR(255),
  `buyer_customer_id` VARCHAR(255),
  `buyer_name` VARCHAR(255),
  `financing_type` VARCHAR(255),
  `financing_partner_id` VARCHAR(255),
  `financing_partner` VARCHAR(255),
  `license_plate` VARCHAR(255),
  `order_date` VARCHAR(255),
  `handover_date` VARCHAR(255),
  `order_status` VARCHAR(255),
  `currency` VARCHAR(255),
  `base_price` DECIMAL(16,2),
  `paint_amount` DECIMAL(16,2),
  `options` JSON,
  `fees` JSON,
  `discount_amount` DECIMAL(16,2),
  `gross_taxable_amount` DECIMAL(16,2),
  `vat_rate` DECIMAL(16,2),
  `vat_amount` DECIMAL(16,2),
  `total_price` DECIMAL(16,2),
  `payment_status` VARCHAR(255),
  `poms_last_updated` VARCHAR(255),
  `workday_invoices` JSON,
  PRIMARY KEY (`order_number`)
);

CREATE TABLE nga_tracker (
  `tracker_id` VARCHAR(255),
  `invoice_number` VARCHAR(255),
  `customer_id` VARCHAR(255),
  `customer_name` VARCHAR(255),
  `model_number` VARCHAR(255),
  `total_invoice_price` DECIMAL(16,2),
  `gross_taxable_amount` DECIMAL(16,2),
  `base_price` DECIMAL(16,2),
  `poms_order_number` VARCHAR(255),
  `submitted_on` VARCHAR(255),
  `submitted_by` VARCHAR(255),
  `response_status` VARCHAR(255),
  `response_on` VARCHAR(255),
  `remove_fees` TINYINT(1),
  `revised_gross_amount` BIGINT,
  `revised_base_price` BIGINT,
  `comments` VARCHAR(255),
  PRIMARY KEY (`tracker_id`)
);

CREATE TABLE factoring_tracker (
  `factoring_id` VARCHAR(255),
  `payment_id` VARCHAR(255),
  `poms_order_number` VARCHAR(255),
  `invoice_number` VARCHAR(255),
  `customer_name` VARCHAR(255),
  `amount` DECIMAL(16,2),
  `currency` VARCHAR(255),
  `payment_date` VARCHAR(255),
  `factoring_partner` VARCHAR(255),
  `captured_on` VARCHAR(255),
  `status` VARCHAR(255),
  PRIMARY KEY (`factoring_id`)
);

CREATE TABLE dk21_sharepoint_tracker (
  `tracker_id` VARCHAR(255),
  `customer_id` VARCHAR(255),
  `customer_name` VARCHAR(255),
  `poms_order_number` VARCHAR(255),
  `vin` VARCHAR(255),
  `required_po_reference` VARCHAR(255),
  `agreed_unit_price` DECIMAL(16,2),
  `required_description_text` VARCHAR(255),
  `uploaded_by` VARCHAR(255),
  `uploaded_on` VARCHAR(255),
  `sharepoint_url` VARCHAR(255),
  PRIMARY KEY (`tracker_id`)
);

CREATE TABLE ey_final_invoice (
  `ey_invoice_number` VARCHAR(255),
  `statutory_invoice_type` VARCHAR(255),
  `sequence` BIGINT,
  `invoice_date` VARCHAR(255),
  `customer_name` VARCHAR(255),
  `po_number` VARCHAR(255),
  `vin` VARCHAR(255),
  `amount_excl_vat` DECIMAL(16,2),
  `total_amount` DECIMAL(16,2),
  `currency` VARCHAR(255),
  `workday_invoice_number` VARCHAR(255),
  `issued_on` VARCHAR(255),
  `approved_by` VARCHAR(255),
  `pdf` VARCHAR(255),
  PRIMARY KEY (`ey_invoice_number`)
);

CREATE TABLE sf_account (
  `sf_account_id` VARCHAR(255),
  `account_name` VARCHAR(255),
  `workday_customer_id` VARCHAR(255),
  `vat_number` VARCHAR(255),
  `billing_country` VARCHAR(255),
  `owner` VARCHAR(255),
  PRIMARY KEY (`sf_account_id`)
);

CREATE TABLE validation_rule (
  `rule_id` VARCHAR(255),
  `company` VARCHAR(255),
  `name` VARCHAR(255),
  `severity` VARCHAR(255),
  `condition` VARCHAR(255),
  `check` VARCHAR(255),
  `source` VARCHAR(255),
  `outcome_on_fail` VARCHAR(255),
  `remediation` VARCHAR(255),
  PRIMARY KEY (`rule_id`)
);

CREATE TABLE expected_result (
  `invoice_number` VARCHAR(255),
  `company` VARCHAR(255),
  `scenario` VARCHAR(255),
  `expected_status` VARCHAR(255),
  `expected_findings` JSON,
  `remediation` VARCHAR(255),
  PRIMARY KEY (`invoice_number`)
);

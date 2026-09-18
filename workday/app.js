/* Workday customer invoicing (POC) — static client over ../api.
   Reads the Workday layer, the POMS orders, the side trackers and the latest
   validation run written by validator/validate.py. */
const API = '../api'
const view = document.getElementById('view')
const cache = new Map()

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]))
const num = (n, dp = 2) => (n === null || n === undefined || n === '' ? '' : Number(n).toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp }))
const paren = (n, dp = 2) => (Number(n) < 0 ? `(${num(-n, dp)})` : num(n, dp))   // Workday shows negatives in parentheses
const title = (s) => String(s ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
const link = (route, id, text) => `<a href="#/${route}/${encodeURIComponent(id)}">${esc(text ?? id)}</a>`
const pomsLink = (o) => (o ? `<a href="../poms/index.html#/order/${encodeURIComponent(o)}" target="_blank" rel="noopener">${esc(o)} ↗</a>` : '')

async function get(path, optional = false) {
  if (cache.has(path)) return cache.get(path)
  const r = await fetch(`${API}/${path}`, { cache: 'no-store' })
  if (!r.ok) { if (optional) return null; throw new Error(`${r.status} ${path}`) }
  const j = await r.json()
  cache.set(path, j)
  return j
}
async function latestRun() {
  const run = await get('validation-runs/latest.json', true)
  const byInv = new Map((run?.results ?? []).map((r) => [r.invoice_number, r]))
  return { run, byInv }
}

/* ------------------------------ rendering -------------------------------- */
const chip = (t, k = 'neutral') => `<span class="chip ${k}">${esc(t)}</span>`
const statusChip = (s) => chip(title(s), { DRAFT: 'warn', APPROVED: 'ok', PASS: 'ok', FAIL: 'bad', HOLD: 'hold', PENDING: 'warn', RESPONDED: 'ok' }[s] || 'neutral')
const valChip = (r) => (r ? statusChip(r.status) + (r.rules_failed?.length ? ' ' + r.rules_failed.map((x) => chip(x, 'rule')).join(' ') : '') : chip('not run', 'neutral'))
const sevChip = (s) => chip(s, s === 'critical' ? 'bad' : s === 'high' ? 'warn' : 'neutral')

const panel = (heading, body, count = '', tools = '') =>
  `<div class="panel"><div class="ph"><h2>${heading}</h2>${count ? `<span class="count">${count}</span>` : ''}${tools ? `<div class="tools">${tools}</div>` : ''}</div>${body}</div>`
const fields = (rows) => `<div class="fields">${rows.map(([l, v]) => `<div class="field"><label>${l}</label><div class="v ${v === '' || v === null || v === undefined ? 'empty' : ''}">${v === '' || v === null || v === undefined ? '(empty)' : v}</div></div>`).join('')}</div>`

function table(cols, rows, rowClass) {
  if (!rows.length) return '<div class="empty">Nothing to show.</div>'
  const head = cols.map((c) => `<th class="${c.num ? 'num' : ''}">${c.label}</th>`).join('')
  const body = rows.map((r) => `<tr class="${rowClass ? rowClass(r) : ''}">${cols.map((c) => `<td class="${c.num ? 'num' : ''} ${c.wrap ? 'wrap' : ''}">${c.render ? c.render(r) : esc(r[c.key] ?? '')}</td>`).join('')}</tr>`).join('')
  return `<div class="scroll"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`
}

function searchable(rows, cols, placeholder, heading, rowClass, extraTools = '') {
  const id = 'q' + Math.random().toString(36).slice(2, 7)
  setTimeout(() => {
    const input = document.getElementById(id)
    if (!input) return
    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase()
      const hit = q ? rows.filter((r) => JSON.stringify(r).toLowerCase().includes(q)) : rows
      document.getElementById(id + '-t').innerHTML = table(cols, hit, rowClass)
      document.getElementById(id + '-c').textContent = `${hit.length} of ${rows.length} items`
    })
  }, 0)
  return `<div class="toolbar"><input id="${id}" placeholder="${placeholder}">${extraTools}<span class="spacer"></span><span class="count" id="${id}-c">${rows.length} items</span></div>
    <div class="panel"><div class="ph"><h2>${heading}</h2></div><div id="${id}-t">${table(cols, rows, rowClass)}</div></div>`
}

function page(crumbs, heading, sub, html) {
  view.innerHTML = `<div class="crumbs">${crumbs}</div><h1>${heading}</h1>${sub ? `<div class="sub">${sub}</div>` : ''}${html}`
  window.scrollTo(0, 0)
}
const home = '<a href="#/">Customer Invoices</a>'

function tabs(defs) {
  const id = 't' + Math.random().toString(36).slice(2, 7)
  setTimeout(() => {
    const host = document.getElementById(id)
    if (!host) return
    host.parentElement.querySelectorAll('.tab').forEach((b, i) => b.addEventListener('click', () => {
      host.parentElement.querySelectorAll('.tab').forEach((x) => x.classList.remove('active'))
      b.classList.add('active')
      host.innerHTML = defs[i][1]()
    }))
  }, 0)
  return `<div class="tabs">${defs.map(([l], i) => `<button class="tab ${i === 0 ? 'active' : ''}">${l}</button>`).join('')}</div><div id="${id}">${defs[0][1]()}</div>`
}

function csvDownload(rows, filename) {
  const cols = Object.keys(rows[0] ?? {})
  const cell = (v) => { const t = v === null || v === undefined ? '' : String(v); return /[",\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t }
  const csv = [cols.join(','), ...rows.map((r) => cols.map((c) => cell(r[c])).join(','))].join('\n')
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  a.download = filename
  a.click()
}
window.csvDownload = csvDownload

/* ------------------------------ worklist --------------------------------- */
const INV_COLS = (byInv) => [
  { label: 'Customer Invoice', key: 'invoice_number', render: (r) => link('invoice', r.invoice_number) },
  { label: 'Company', key: 'company' },
  { label: 'Document', key: 'document_kind' },
  { label: 'Status', key: 'status', render: (r) => statusChip(r.status) },
  { label: 'Validation (last run)', key: 'v', render: (r) => valChip(byInv.get(r.invoice_number)) },
  { label: 'Bill-To Customer', key: 'bill_to_customer' },
  { label: 'Sold-To Customer', key: 'sold_to_customer' },
  { label: 'Invoice Date', key: 'invoice_date' },
  { label: 'POMS Order', key: 'poms_order_number', render: (r) => pomsLink(r.poms_order_number) },
  { label: 'Model', key: 'model' },
  { label: 'VIN', key: 'vin', render: (r) => `<span class="mono">${esc(r.vin ?? '')}</span>` },
  { label: 'PO Number', key: 'po_number' },
  { label: 'Statutory Type', key: 'statutory_invoice_type' },
  { label: 'Statutory No.', key: 'statutory_invoice_number' },
  { label: 'Lines', key: 'line_count', num: true },
  { label: 'Fee lines', key: 'has_fee_lines', render: (r) => (r.has_fee_lines ? chip('yes', 'warn') : '') },
  { label: 'Subtotal', key: 'subtotal', num: true, render: (r) => paren(r.subtotal) },
  { label: 'Tax', key: 'tax_amount', num: true, render: (r) => paren(r.tax_amount) },
  { label: 'Total', key: 'total_amount', num: true, render: (r) => `<b>${paren(r.total_amount)}</b>` },
  { label: 'Ccy', key: 'currency' },
  { label: 'Payment', key: 'payment_applied_as', render: (r) => (r.payment_applied_as ? chip(title(r.payment_applied_as), 'warn') : '') },
]
const rowClass = (byInv) => (r) => ({ FAIL: 'fail', HOLD: 'hold' }[byInv.get(r.invoice_number)?.status] || '')

let filterCompany = 'ALL'
let filterVal = 'ALL'
async function worklist() {
  const [inv, { run, byInv }] = await Promise.all([get('workday/customer-invoices.json'), latestRun()])
  const all = inv.data
  const rows = all.filter((r) => (filterCompany === 'ALL' || r.company === filterCompany) && (filterVal === 'ALL' || byInv.get(r.invoice_number)?.status === filterVal))
  const cnt = (s) => all.filter((r) => byInv.get(r.invoice_number)?.status === s).length
  const seg = (name, opts, cur) => `<div class="seg">${opts.map((o) => `<button class="${cur === o ? 'on' : ''}" data-${name}="${o}">${o === 'ALL' ? 'All' : o}</button>`).join('')}</div>`
  setTimeout(() => {
    view.querySelectorAll('[data-co]').forEach((b) => b.addEventListener('click', () => { filterCompany = b.dataset.co; worklist() }))
    view.querySelectorAll('[data-val]').forEach((b) => b.addEventListener('click', () => { filterVal = b.dataset.val; worklist() }))
  }, 0)
  page(home, 'Find Customer Invoices', `Draft and approved customer invoices for SE21, NO21, PT21 and DK21. ${run ? `Last validation ${esc(run.started_at)} (${esc(run.schedule.trigger)}), next ${esc(run.schedule.next_run_at)}.` : 'No validation run found yet — run validator/validate.py.'}`,
    `<div class="tiles">
      <div class="tile"><div class="l">Customer invoices</div><div class="v">${all.length}</div><div class="s">${all.filter((r) => r.status === 'DRAFT').length} draft</div></div>
      <div class="tile ok"><div class="l">Pass</div><div class="v">${cnt('PASS')}</div><div class="s">no findings</div></div>
      <div class="tile bad"><div class="l">Fail</div><div class="v">${cnt('FAIL')}</div><div class="s">manual correction needed</div></div>
      <div class="tile hold"><div class="l">Hold</div><div class="v">${cnt('HOLD')}</div><div class="s">waiting on external input</div></div>
      <div class="tile"><div class="l">Next scheduled run</div><div class="v" style="font-size:15px;margin-top:8px">${esc(run?.schedule?.next_run_at?.replace('T', ' ').replace('Z', ' UTC') ?? '—')}</div><div class="s">every ${run?.schedule?.interval_minutes ?? 60} minutes</div></div>
    </div>
    ${searchable(rows, INV_COLS(byInv), 'Search invoice, customer, VIN, order…', 'Customer Invoices', rowClass(byInv),
      seg('co', ['ALL', 'SE21', 'NO21', 'PT21', 'DK21'], filterCompany) + seg('val', ['ALL', 'PASS', 'FAIL', 'HOLD'], filterVal))}`)
}

/* ---------------------------- invoice detail ----------------------------- */
async function invoiceDetail(id) {
  const [d, { run, byInv }, cust, nga, fact, dk, ey, sf, rules] = await Promise.all([
    get(`workday/customer-invoices/${id}.json`).then((x) => x.data), latestRun(), get('workday/customers.json'),
    get('trackers/nga-tracker.json'), get('trackers/factoring-tracker.json'), get('trackers/dk21-sharepoint-tracker.json'),
    get('ey/final-invoices.json'), get('salesforce/accounts.json'), get('workday/exception-rules.json'),
  ])
  const order = d.poms_order_number ? (await get(`poms/orders/${d.poms_order_number}.json`, true))?.data : null
  const res = byInv.get(d.invoice_number)
  window.__inv = d.lines
  const custBy = new Map(cust.data.map((c) => [c.customer_id, c]))
  const bt = custBy.get(d.bill_to_customer_id), st = custBy.get(d.sold_to_customer_id)
  const flags = (c) => !c ? '' : ['related_party', 'nga_customer', 'leasing_plate_required', 'loan_provider', 'bpi_exception', 'sharepoint_tracker'].filter((f) => c[f]).map((f) => chip(title(f), 'warn')).join(' ')
  const ruleBy = new Map(rules.data.map((r) => [r.rule_id, r]))

  const header = fields([
    ['Customer Invoice', `<b>${esc(d.invoice_number)}</b>`], ['Company', esc(d.company_name)],
    ['Invoice Status', statusChip(d.status)], ['Document Kind', esc(d.document_kind)],
    ['Bill-To Customer', `${link('customer', d.bill_to_customer_id, d.bill_to_customer)} ${flags(bt)}`],
    ['Sold-To Customer', `${link('customer', d.sold_to_customer_id, d.sold_to_customer)} ${flags(st)}`],
    ['Invoice Date', esc(d.invoice_date)], ['Due Date', esc(d.due_date)], ['Payment Terms', esc(d.payment_terms)],
    ['Customer VAT Number', d.customer_vat_number ? esc(d.customer_vat_number) : ''],
    ['PO Number', d.po_number ? esc(d.po_number) : ''], ['Currency', esc(d.currency)],
    ['POMS Order Number', pomsLink(d.poms_order_number)], ['Model', esc(d.model)], ['VIN', `<span class="mono">${esc(d.vin)}</span>`],
    ['Statutory Invoice Type', d.statutory_invoice_type ? esc(d.statutory_invoice_type) : ''],
    ['Statutory Invoice Number', d.statutory_invoice_number ? esc(d.statutory_invoice_number) : ''],
    ['Memo', d.memo ? esc(d.memo) : ''],
    ['Created', `${esc(d.created_by)} · ${esc(d.created_on)}`], ['Last Updated', esc(d.last_updated)],
  ])

  // Highlight the cells a finding points at, the way the screenshot marks them.
  const flaggedLines = new Map()
  ;(res?.findings ?? []).forEach((f) => { if (f.line) flaggedLines.set(f.line, [...(flaggedLines.get(f.line) ?? []), f.field]) })
  const hl = (line, field, html) => (flaggedLines.get(line)?.includes(field) ? `<span class="hl" title="flagged by validation">${html}</span>` : html)
  const LINE_COLS = [
    { label: 'Line', key: 'line', render: (r) => `<span class="icon">🔍</span> ${r.line}` },
    { label: 'Company', key: 'company', render: (r) => `<a>${esc(r.company)}</a>` },
    { label: 'Sales Item', key: 'sales_item_name', render: (r) => `<a>${esc(r.sales_item_name)}</a>` },
    { label: 'Revenue Category', key: 'revenue_category', render: (r) => hl(r.line, 'revenue_category', `<a>${esc(r.revenue_category)} ${esc(r.revenue_category_name)}</a>`) },
    { label: 'Line Item Description', key: 'line_item_description', wrap: true, render: (r) => hl(r.line, 'line_item_description', esc(r.line_item_description)) },
    { label: 'Quantity', key: 'quantity', num: true },
    { label: 'Unit of Measure', key: 'unit_of_measure' },
    { label: 'Quantity 2', key: 'quantity_2', num: true },
    { label: 'Unit of Measure 2', key: 'unit_of_measure_2' },
    { label: 'Unit Price', key: 'unit_price', num: true, render: (r) => hl(r.line, 'unit_price', paren(r.unit_price)) },
    { label: 'Released on Invoice Lines', key: 'released_on_invoice_lines' },
    { label: 'Extended Amount', key: 'extended_amount', num: true, render: (r) => hl(r.line, 'extended_amount', paren(r.extended_amount)) },
    { label: 'Tax Applicability', key: 'tax_applicability' },
  ]
  const linesTab = () => panel('Invoice Lines', table(LINE_COLS, d.lines), `${d.lines.length} items`,
      `<button class="btn" onclick="csvDownload(window.__inv, '${esc(d.invoice_number)}-lines.csv')">Export</button>`) +
    panel('Totals', fields([['Subtotal', paren(d.totals.subtotal)], ['Tax', paren(d.totals.tax_amount)], ['Total Invoice Amount', `<b>${paren(d.totals.total_amount)} ${esc(d.currency)}</b>`]]))
  const fxTab = () => panel('Currency Rate', fields([['Transaction Currency', esc(d.currency)], ['Company Currency', esc(d.currency)], ['Currency Rate', '1.000000'], ['Rate Type', 'Current'], ['Rate Date', esc(d.invoice_date)]]))
  const taxTab = () => panel('Tax', fields([['Tax Code', esc(d.tax.tax_code)], ['Tax Rate', `${num(d.tax.tax_rate, 2)}%`], ['Taxable (Gross) Amount', paren(d.tax.taxable_amount)], ['Tax Amount', paren(d.tax.tax_amount)],
    ['Expected at rate', paren(d.tax.taxable_amount * d.tax.tax_rate / 100)], ['Tax Applicability', d.lines.every((l) => l.tax_applicability === 'Taxable') ? 'Taxable' : 'Mixed']]))
  const attTab = () => panel('Attachments', d.attachments.length ? table([{ label: 'File', key: 'name' }, { label: 'Type', key: 'type' }, { label: 'Attached to', key: 'attached_to' }], d.attachments) : '<div class="empty">No attachments. For PT21, attach the E&Y final invoice to the PO once it has been checked.</div>')
  const notesTab = () => panel('Notes', `<div class="pb"><p class="note">${d.memo ? esc(d.memo) : 'No notes on this invoice.'}</p>${d.payment_application ? `<p class="note">Payment ${esc(d.payment_application.payment_id)} for ${num(d.payment_application.amount)} ${esc(d.currency)} applied as <b>${esc(title(d.payment_application.applied_as))}</b> on ${esc(d.payment_application.payment_date)} (${esc(d.payment_application.factoring_partner)}).</p>` : ''}</div>`)

  const valTab = () => {
    if (!res) return '<div class="empty">No validation run yet. Run validator/validate.py or wait for the hourly scheduler.</div>'
    const fs = res.findings
    const body = fs.length ? fs.map((f) => `<div class="finding ${f.outcome.toLowerCase()}">
        <div class="t">${chip(f.rule_id, 'rule')} <b>${esc(ruleBy.get(f.rule_id)?.name ?? '')}</b> ${sevChip(f.severity)} ${statusChip(f.outcome)} ${f.line ? chip(`line ${f.line}`) : ''}</div>
        <div class="msg">${esc(f.message)}</div>
        <div class="ea"><span>Field</span><b class="mono">${esc(f.field)}</b><span>Expected</span><b>${esc(typeof f.expected === 'number' ? num(f.expected) : f.expected ?? '(empty)')}</b><span>Actual</span><b>${esc(typeof f.actual === 'number' ? num(f.actual) : f.actual ?? '(empty)')}</b></div>
        ${f.remediation ? `<div class="fix">Fix: ${esc(f.remediation)}</div>` : ''}</div>`).join('')
      : `<div class="allgood">All ${rules.data.filter((r) => r.company === 'ALL' || r.company === d.company).length} applicable rules passed.</div>`
    return panel(`Validation result — ${res.status}`, `<div class="pb"><p class="note">Run ${esc(run.run_id)} · ${esc(run.started_at)} · trigger ${esc(run.schedule.trigger)} · source ${esc(run.source)}</p>${body}</div>`)
  }

  const relTab = () => {
    const ngaRow = nga.data.find((t) => t.invoice_number === d.invoice_number)
    const eyRow = ey.data.find((e) => e.workday_invoice_number === d.invoice_number)
    const dkRow = dk.data.find((t) => t.poms_order_number === d.poms_order_number)
    const sfRow = sf.data.find((a) => a.workday_customer_id === d.bill_to_customer_id)
    const factRow = d.payment_application ? fact.data.find((p) => p.payment_id === d.payment_application.payment_id) : null
    let html = ''
    html += order ? panel('POMS order', fields([['Order', pomsLink(order.order_number)], ['Buyer', esc(order.buyer_name)], ['Financing', `${esc(title(order.financing_type))}${order.financing_partner ? ' via ' + esc(order.financing_partner) : ''}`],
      ['VIN', `<span class="mono">${esc(order.vin)}</span>`], ['Licence plate', order.license_plate ? esc(order.license_plate) : ''], ['Base price', num(order.base_price)], ['Fees', order.fees.length ? order.fees.map((f) => `${esc(f.description)} ${num(f.amount)}`).join('<br>') : 'none'],
      ['Gross taxable', num(order.gross_taxable_amount)], ['VAT', num(order.vat_amount)], ['Total', `<b>${num(order.total_price)} ${esc(order.currency)}</b>`], ['Payment', esc(title(order.payment_status))], ['Handover', esc(order.handover_date)]]))
      : panel('POMS order', '<div class="empty">No POMS order linked.</div>')
    if (bt?.nga_customer) html += panel('NGA tracker', ngaRow ? fields([['Tracker row', esc(ngaRow.tracker_id)], ['Submitted', `${esc(ngaRow.submitted_on)} by ${esc(ngaRow.submitted_by)}`], ['Response', statusChip(ngaRow.response_status)], ['Model number', ngaRow.model_number ?? ''], ['Total invoice price', ngaRow.total_invoice_price != null ? num(ngaRow.total_invoice_price) : ''], ['Gross / taxable', ngaRow.gross_taxable_amount != null ? num(ngaRow.gross_taxable_amount) : ''], ['Base price', ngaRow.base_price != null ? num(ngaRow.base_price) : ''],
      ['Remove fees?', ngaRow.remove_fees === null ? '' : ngaRow.remove_fees ? chip('yes — remove', 'bad') : chip('no — keep', 'ok')], ['Revised gross', ngaRow.revised_gross_amount != null ? num(ngaRow.revised_gross_amount) : ''], ['Revised base', ngaRow.revised_base_price != null ? num(ngaRow.revised_base_price) : ''], ['Comments', esc(ngaRow.comments)]])
      : '<div class="empty">NGA customer, but this invoice has not been captured in the NGA tracker.</div>')
    if (d.payment_application) html += panel('Factoring tracker', factRow ? fields([['Factoring row', esc(factRow.factoring_id)], ['Payment', esc(factRow.payment_id)], ['Amount', num(factRow.amount)], ['Status', esc(factRow.status)]]) : `<div class="empty">Payment ${esc(d.payment_application.payment_id)} is not in the factoring tracker.</div>`)
    if (d.company === 'PT21') html += panel('E&Y final invoice', eyRow ? fields([['E&Y number', esc(eyRow.ey_invoice_number)], ['Type', esc(eyRow.statutory_invoice_type)], ['Sequence', eyRow.sequence], ['Date', esc(eyRow.invoice_date)], ['Customer', esc(eyRow.customer_name)], ['PO', eyRow.po_number ?? ''], ['VIN', `<span class="mono">${esc(eyRow.vin)}</span>`], ['Amount excl. VAT', num(eyRow.amount_excl_vat)], ['Total', num(eyRow.total_amount)], ['Approved by', esc(eyRow.approved_by)]]) : '<div class="empty">No E&Y final invoice received for this Workday invoice.</div>')
    if (bt?.sharepoint_tracker) html += panel('DK21 SharePoint tracker', dkRow ? fields([['Tracker row', esc(dkRow.tracker_id)], ['Required PO reference', esc(dkRow.required_po_reference)], ['Agreed unit price', num(dkRow.agreed_unit_price)], ['Required description text', esc(dkRow.required_description_text)], ['Uploaded', `${esc(dkRow.uploaded_on)} by ${esc(dkRow.uploaded_by)}`], ['SharePoint', `<a href="${esc(dkRow.sharepoint_url)}" target="_blank" rel="noopener">open ↗</a>`]]) : '<div class="empty">No tracker row for this order.</div>')
    if (sfRow) html += panel('Salesforce account', fields([['Account', esc(sfRow.sf_account_id)], ['Name', esc(sfRow.account_name)], ['VAT number', esc(sfRow.vat_number)], ['Owner', esc(sfRow.owner)]]))
    return html
  }

  const fcount = res ? res.findings.filter((f) => f.outcome !== 'INFO').length : 0
  page(`${home} › ${esc(d.invoice_number)}`, `View Customer Invoice: ${esc(d.invoice_number)}`,
    `${esc(d.bill_to_customer)} · ${esc(d.company)} · ${paren(d.totals.total_amount)} ${esc(d.currency)} · ${statusChip(d.status)} · Validation ${res ? statusChip(res.status) : chip('not run')}`,
    panel('Invoice Information', header) +
    tabs([
      [`Invoice Lines <span class="badge">${d.lines.length}</span>`, linesTab], ['Currency Rate', fxTab], ['Tax', taxTab],
      ['Attachments', attTab], ['Notes', notesTab],
      [`Validation <span class="badge ${res ? (res.status === 'PASS' ? 'ok' : res.status === 'HOLD' ? 'hold' : 'bad') : ''}">${res ? (fcount || 'OK') : '–'}</span>`, valTab],
      ['Related systems', relTab],
    ]))
}

/* ------------------------------ flat lines -------------------------------- */
async function flatLines() {
  const [payload, { byInv }] = await Promise.all([get('workday/invoice-lines.json'), latestRun()])
  const rows = payload.data
  const FIRST = ['invoice_number', 'line', 'company', 'sales_item', 'sales_item_name', 'revenue_category', 'revenue_category_name', 'line_item_description', 'quantity', 'unit_of_measure', 'unit_price', 'extended_amount', 'tax_applicability', 'status', 'document_kind', 'bill_to_customer', 'sold_to_customer', 'invoice_date', 'poms_order_number', 'vin', 'po_number', 'currency', 'subtotal', 'tax_amount', 'total_amount']
  const keys = [...FIRST, ...Object.keys(rows[0]).filter((k) => !FIRST.includes(k))]
  const NUMERIC = /quantity|price|amount|total|rate|subtotal|count/
  const cols = keys.map((k) => ({ label: title(k), key: k, num: NUMERIC.test(k) && k !== 'quantity_2',
    render: k === 'invoice_number' ? (r) => link('invoice', r.invoice_number) : k === 'poms_order_number' ? (r) => pomsLink(r.poms_order_number)
      : NUMERIC.test(k) ? (r) => (r[k] == null ? '' : paren(r[k], /quantity|count/.test(k) ? 0 : 2)) : k === 'line_item_description' ? (r) => esc(r[k]) : undefined, wrap: k === 'line_item_description' }))
  cols.splice(1, 0, { label: 'Validation', key: '_v', render: (r) => statusChip(byInv.get(r.invoice_number)?.status ?? 'not run') })
  page(`${home} › Invoice lines`, 'Customer Invoice Lines (flat)', 'One row per invoice line with the header denormalised — Revenue Category and Sales Item on every row. This is the extract the hourly validator reads line by line.',
    searchable(rows, cols, 'Search lines…', `${rows.length} invoice lines`, rowClass(byInv), `<button class="btn" onclick="csvDownload(window.__lines,'workday-invoice-lines.csv')">Export CSV</button>`))
  window.__lines = rows
}

/* ------------------------------- masters --------------------------------- */
async function customers() {
  const c = await get('workday/customers.json')
  const flags = ['related_party', 'nga_customer', 'leasing_plate_required', 'loan_provider', 'bpi_exception', 'sharepoint_tracker']
  const cols = [
    { label: 'Customer', key: 'customer_id', render: (r) => link('customer', r.customer_id) }, { label: 'Name', key: 'customer_name' }, { label: 'Company', key: 'company' },
    { label: 'Type', key: 'customer_type' }, { label: 'VAT number', key: 'vat_number', render: (r) => (r.vat_number ? esc(r.vat_number) : chip('missing', 'bad')) },
    { label: 'Exception flags', key: 'f', render: (r) => flags.filter((f) => r[f]).map((f) => chip(title(f), 'warn')).join(' ') },
  ]
  page(`${home} › Customers`, 'Customers', 'Customer master with the flags the entity exceptions key on: related party (SE21), NGA list (NO21), leasing companies and loan providers (PT21), SharePoint tracker (DK21).',
    searchable(c.data, cols, 'Search customers…', 'Customers'))
}
async function customerDetail(id) {
  const [c, inv, { byInv }] = await Promise.all([get(`workday/customers/${id}.json`).then((x) => x.data), get('workday/customer-invoices.json'), latestRun()])
  const mine = inv.data.filter((r) => r.bill_to_customer_id === id || r.sold_to_customer_id === id)
  page(`${home} › <a href="#/customers">Customers</a> › ${esc(id)}`, esc(c.customer_name), `${esc(c.company)} · ${esc(c.customer_type)}`,
    panel('Customer', fields([['Customer ID', esc(c.customer_id)], ['Name', esc(c.customer_name)], ['Company', esc(c.company)], ['Type', esc(c.customer_type)], ['Country', esc(c.country)], ['VAT number', c.vat_number ?? ''],
      ['Related party', c.related_party ? 'Yes' : 'No'], ['NGA customer', c.nga_customer ? 'Yes' : 'No'], ['Licence plate required', c.leasing_plate_required ? 'Yes' : 'No'], ['Loan provider', c.loan_provider ? 'Yes' : 'No'], ['Banco BPI exception', c.bpi_exception ? 'Yes' : 'No'], ['SharePoint tracker', c.sharepoint_tracker ? 'Yes' : 'No']])) +
    panel('Customer invoices', table(INV_COLS(byInv), mine, rowClass(byInv)), `${mine.length} items`))
}
async function revcats() {
  const [rc, lines] = await Promise.all([get('workday/revenue-categories.json'), get('workday/invoice-lines.json')])
  const use = {}
  lines.data.forEach((l) => { use[l.revenue_category] = (use[l.revenue_category] || 0) + 1 })
  const cols = [{ label: 'Revenue Category', key: 'revenue_category' }, { label: 'Name', key: 'name' }, { label: 'Fee category', key: 'is_fee', render: (r) => (r.is_fee ? chip('fee — removable under NGA', 'warn') : '') }, { label: 'Ledger account', key: 'ledger_account' }, { label: 'Lines using it', key: 'u', num: true, render: (r) => use[r.revenue_category] || 0 }, { label: 'Note', key: 'note', wrap: true }]
  page(`${home} › Revenue categories`, 'Revenue Categories', '3030 is the related-party category SE21 must use on vehicle (Brand) lines billed or sold to Ziklo Bank or Volvo Bank. 3041–3043 are the fee categories NO21 removes when the NGA team says so.', panel('Revenue Categories', table(cols, rc.data), `${rc.data.length} items`))
}
async function items() {
  const si = await get('workday/sales-items.json')
  page(`${home} › Sales items`, 'Sales Items', 'Each sales item defaults a revenue category; the billing desk can override it on the line — which is exactly what SE21-001 checks.',
    panel('Sales Items', table([{ label: 'Sales Item', key: 'sales_item' }, { label: 'Name', key: 'name' }, { label: 'Group', key: 'item_group' }, { label: 'Default Revenue Category', key: 'default_revenue_category' }], si.data), `${si.data.length} items`))
}

/* ------------------------------- trackers -------------------------------- */
async function trackers() {
  const [nga, fact, dk, ey, sf] = await Promise.all([get('trackers/nga-tracker.json'), get('trackers/factoring-tracker.json'), get('trackers/dk21-sharepoint-tracker.json'), get('ey/final-invoices.json'), get('salesforce/accounts.json')])
  const money = (k) => ({ label: title(k), key: k, num: true, render: (r) => (r[k] == null ? chip('missing', 'bad') : num(r[k])) })
  const ngaCols = [{ label: 'Tracker', key: 'tracker_id' }, { label: 'Invoice', key: 'invoice_number', render: (r) => link('invoice', r.invoice_number) }, { label: 'Customer ID', key: 'customer_id' }, { label: 'Customer', key: 'customer_name' }, { label: 'Model Number', key: 'model_number', render: (r) => r.model_number ?? chip('missing', 'bad') },
    money('total_invoice_price'), money('gross_taxable_amount'), money('base_price'), { label: 'Submitted', key: 'submitted_on' }, { label: 'Response', key: 'response_status', render: (r) => statusChip(r.response_status) }, { label: 'Remove fees?', key: 'remove_fees', render: (r) => (r.remove_fees === null ? '' : r.remove_fees ? chip('remove', 'bad') : chip('keep', 'ok')) },
    { label: 'Revised Gross', key: 'revised_gross_amount', num: true, render: (r) => (r.revised_gross_amount == null ? '' : num(r.revised_gross_amount)) }, { label: 'Revised Base', key: 'revised_base_price', num: true, render: (r) => (r.revised_base_price == null ? '' : num(r.revised_base_price)) }, { label: 'Comments', key: 'comments', wrap: true }]
  const factCols = [{ label: 'Factoring', key: 'factoring_id' }, { label: 'Payment', key: 'payment_id' }, { label: 'POMS order', key: 'poms_order_number', render: (r) => pomsLink(r.poms_order_number) }, { label: 'Customer', key: 'customer_name' }, { label: 'Amount', key: 'amount', num: true, render: (r) => num(r.amount) }, { label: 'Ccy', key: 'currency' }, { label: 'Payment date', key: 'payment_date' }, { label: 'Partner', key: 'factoring_partner' }, { label: 'Status', key: 'status' }]
  const dkCols = [{ label: 'Tracker', key: 'tracker_id' }, { label: 'Customer', key: 'customer_name' }, { label: 'POMS order', key: 'poms_order_number', render: (r) => pomsLink(r.poms_order_number) }, { label: 'VIN', key: 'vin', render: (r) => `<span class="mono">${esc(r.vin)}</span>` }, { label: 'Required PO', key: 'required_po_reference' }, { label: 'Agreed unit price', key: 'agreed_unit_price', num: true, render: (r) => num(r.agreed_unit_price) }, { label: 'Required description text', key: 'required_description_text' }, { label: 'Uploaded', key: 'uploaded_on' }, { label: 'By', key: 'uploaded_by' }]
  const eyCols = [{ label: 'E&Y number', key: 'ey_invoice_number' }, { label: 'Type', key: 'statutory_invoice_type' }, { label: 'Seq', key: 'sequence', num: true }, { label: 'Workday invoice', key: 'workday_invoice_number', render: (r) => link('invoice', r.workday_invoice_number) }, { label: 'Date', key: 'invoice_date' }, { label: 'Customer', key: 'customer_name' }, { label: 'PO', key: 'po_number' }, { label: 'VIN', key: 'vin', render: (r) => `<span class="mono">${esc(r.vin)}</span>` }, { label: 'Excl. VAT', key: 'amount_excl_vat', num: true, render: (r) => paren(r.amount_excl_vat) }, { label: 'Total', key: 'total_amount', num: true, render: (r) => paren(r.total_amount) }, { label: 'Approved by', key: 'approved_by' }]
  const sfCols = [{ label: 'Account', key: 'sf_account_id' }, { label: 'Name', key: 'account_name' }, { label: 'Workday customer', key: 'workday_customer_id', render: (r) => link('customer', r.workday_customer_id) }, { label: 'VAT number', key: 'vat_number' }, { label: 'Country', key: 'billing_country' }, { label: 'Owner', key: 'owner' }]
  page(`${home} › Side systems`, 'Trackers and side systems', 'The Excel / SharePoint trackers and external systems the exceptions depend on. The validator joins these to each invoice on every run.',
    tabs([
      [`NGA tracker (NO21) <span class="badge">${nga.data.length}</span>`, () => panel('NGA tracker', table(ngaCols, nga.data), 'Excel on SharePoint · required fields: Invoice Number, Customer ID, Model Number, Total Invoice Price, Gross/Taxable Amount, Base Price')],
      [`Factoring tracker (NO21) <span class="badge">${fact.data.length}</span>`, () => panel('Factoring tracker', table(factCols, fact.data))],
      [`SharePoint tracker (DK21) <span class="badge">${dk.data.length}</span>`, () => panel('DK21 customer-specific tracker', table(dkCols, dk.data), 'Uploaded by Sales Denmark')],
      [`E&Y final invoices (PT21) <span class="badge">${ey.data.length}</span>`, () => panel('E&Y certified invoicing — final invoices', table(eyCols, ey.data), 'Sequences: PRT Invoice PT240001…, Credit note PT2400001…, Retrobonus PT2500001…')],
      [`Salesforce accounts <span class="badge">${sf.data.length}</span>`, () => panel('Salesforce', table(sfCols, sf.data), 'Fallback source for VAT numbers on PT21 extras and prepayments')],
    ]))
}

/* -------------------------------- rules ---------------------------------- */
async function rules() {
  const [r, { run }] = await Promise.all([get('workday/exception-rules.json'), latestRun()])
  const hits = new Map((run?.by_rule ?? []).map((x) => [x.rule_id, x]))
  const cols = [{ label: 'Rule', key: 'rule_id', render: (x) => chip(x.rule_id, 'rule') }, { label: 'Company', key: 'company' }, { label: 'Name', key: 'name' }, { label: 'Severity', key: 'severity', render: (x) => sevChip(x.severity) }, { label: 'On fail', key: 'outcome_on_fail', render: (x) => statusChip(x.outcome_on_fail) },
    { label: 'Condition (when it applies)', key: 'condition', wrap: true }, { label: 'Check', key: 'check', wrap: true }, { label: 'Source of truth', key: 'source', wrap: true },
    { label: 'Hits in last run', key: 'h', num: true, render: (x) => (hits.get(x.rule_id)?.hits ?? 0) || '' }, { label: 'Invoices', key: 'i', wrap: true, render: (x) => (hits.get(x.rule_id)?.invoices ?? []).map((i) => link('invoice', i)).join(', ') }]
  page(`${home} › Rules`, 'Exception rule catalogue', 'Every rule the hourly validator applies, taken from the entity exception document. GEN rules run for all companies; the others only for their entity.',
    panel('Rules', table(cols, r.data), `${r.data.length} rules`))
}

/* ------------------------------- monitor --------------------------------- */
async function monitor() {
  const [{ run }, hist, exp] = await Promise.all([latestRun(), get('validation-runs/history.json', true), get('workday/expected-results.json')])
  if (!run) return page(`${home} › Validation monitor`, 'Validation monitor', '', '<div class="empty">No run yet. Run <span class="mono">python3 validator/validate.py</span> or start <span class="mono">validator/scheduler.py</span>.</div>')
  const s = run.summary
  const expBy = new Map(exp.data.map((e) => [e.invoice_number, e]))
  const resCols = [{ label: 'Invoice', key: 'invoice_number', render: (r) => link('invoice', r.invoice_number) }, { label: 'Company', key: 'company' }, { label: 'Result', key: 'status', render: (r) => statusChip(r.status) }, { label: 'Rules failed', key: 'rules_failed', render: (r) => r.rules_failed.map((x) => chip(x, 'rule')).join(' ') },
    { label: 'Findings', key: 'finding_count', num: true }, { label: 'Bill-To', key: 'bill_to_customer' }, { label: 'Total', key: 'total_amount', num: true, render: (r) => `${paren(r.total_amount)} ${esc(r.currency)}` },
    { label: 'Scenario (POC answer key)', key: 'sc', wrap: true, render: (r) => esc(expBy.get(r.invoice_number)?.scenario ?? '') }, { label: 'Expected', key: 'ex', render: (r) => { const e = expBy.get(r.invoice_number); return e ? statusChip(e.expected_status) + (e.expected_status === r.status ? '' : ' ' + chip('mismatch', 'bad')) : '' } }]
  const ruleCols = [{ label: 'Rule', key: 'rule_id', render: (r) => chip(r.rule_id, 'rule') }, { label: 'Name', key: 'name' }, { label: 'Severity', key: 'severity', render: (r) => sevChip(r.severity) }, { label: 'Hits', key: 'hits', num: true }, { label: 'Invoices', key: 'invoices', wrap: true, render: (r) => r.invoices.map((i) => link('invoice', i)).join(', ') }]
  const coCols = [{ label: 'Company', key: 'company' }, { label: 'Invoices', key: 'invoices', num: true }, { label: 'Pass', key: 'PASS', num: true }, { label: 'Fail', key: 'FAIL', num: true }, { label: 'Hold', key: 'HOLD', num: true }, { label: 'Pass rate', key: 'pr', num: true, render: (r) => `${Math.round((r.PASS / r.invoices) * 100)}%` }]
  const coRows = Object.entries(run.by_company).map(([company, v]) => ({ company, ...v }))
  const runs = hist?.runs ?? []
  const maxN = Math.max(1, ...runs.map((r) => r.invoices_checked))
  const bars = runs.length ? `<div class="bars">${runs.slice(-48).map((r) => `<div class="b" title="${esc(r.run_id)} — pass ${r.summary.PASS} fail ${r.summary.FAIL} hold ${r.summary.HOLD}"><span class="h" style="height:${(r.summary.HOLD / maxN) * 60}px"></span><span class="f" style="height:${(r.summary.FAIL / maxN) * 60}px"></span><span class="p" style="height:${(r.summary.PASS / maxN) * 60}px"></span></div>`).join('')}</div>` : ''
  const ak = run.answer_key_check
  page(`${home} › Validation monitor`, 'Hourly validation monitor', `Run ${esc(run.run_id)} started ${esc(run.started_at)} (${esc(run.schedule.trigger)}), ${run.duration_seconds}s, source ${esc(run.source)}. Next run ${esc(run.schedule.next_run_at)}.`,
    `<div class="tiles">
      <div class="tile"><div class="l">Invoices checked</div><div class="v">${run.invoices_checked}</div><div class="s">${esc(run.scope)}</div></div>
      <div class="tile ok"><div class="l">Pass</div><div class="v">${s.PASS}</div></div>
      <div class="tile bad"><div class="l">Fail</div><div class="v">${s.FAIL}</div></div>
      <div class="tile hold"><div class="l">Hold</div><div class="v">${s.HOLD}</div></div>
      <div class="tile"><div class="l">Rules with hits</div><div class="v">${run.by_rule.length}</div></div>
      ${ak ? `<div class="tile ${ak.matched === ak.graded ? 'ok' : 'bad'}"><div class="l">Answer key match</div><div class="v">${ak.matched}/${ak.graded}</div><div class="s">validator accuracy on seeded scenarios</div></div>` : ''}
    </div>
    ${panel('Run history', `<div class="pb">${bars || '<p class="note">History fills as the scheduler runs.</p>'}<p class="note">Green pass, red fail, purple hold — one bar per run, newest on the right (${runs.length} runs kept).</p></div>`)}
    ${panel('By company', table(coCols, coRows))}
    ${panel('By rule', table(ruleCols, run.by_rule), `${run.by_rule.length} rules fired`)}
    ${panel('Per invoice', table(resCols, run.results, (r) => ({ FAIL: 'fail', HOLD: 'hold' }[r.status] || '')), `${run.results.length} items`)}`)
}

/* -------------------------------- routing -------------------------------- */
const ROUTES = { '': worklist, invoice: invoiceDetail, lines: flatLines, customers, customer: customerDetail, revcats, items, trackers, rules, monitor }
const NAV = [
  ['Customer Accounts', [['', 'Find Customer Invoices'], ['lines', 'Invoice Lines (flat)'], ['customers', 'Customers']]],
  ['Setup', [['revcats', 'Revenue Categories'], ['items', 'Sales Items']]],
  ['Validation', [['monitor', 'Hourly validation monitor'], ['rules', 'Exception rules'], ['trackers', 'Trackers and side systems']]],
]
async function paintNav(active) {
  const [inv, { run }] = await Promise.all([get('workday/customer-invoices.json'), latestRun()])
  const counts = { '': inv.data.length, monitor: run ? run.summary.FAIL + run.summary.HOLD : '' }
  document.getElementById('nav').innerHTML = NAV.map(([g, links]) => `<div class="grp">${g}</div>` +
    links.map(([r, l]) => `<a href="#/${r}" class="${active === r ? 'active' : ''}">${l}${counts[r] !== undefined && counts[r] !== '' ? `<span class="n">${counts[r]}</span>` : ''}</a>`).join('')).join('') +
    `<div class="grp">Order management</div><a href="../poms/index.html">POMS ↗</a><a href="../erp/index.html">ORBIS ERP ↗</a>`
}
async function route() {
  const raw = location.hash.replace(/^#\/?/, '')
  const [head, ...rest] = raw.split('/')
  const key = ROUTES[head] ? head : ''
  const arg = rest.length ? decodeURIComponent(rest.join('/')) : null
  paintNav({ invoice: '', customer: 'customers' }[head] ?? key)
  view.innerHTML = '<div class="loading">Loading…</div>'
  try { await ROUTES[key](arg) } catch (e) {
    view.innerHTML = `<div class="panel"><div class="pb"><b>Could not load this record.</b><p class="note">${esc(e.message)}. <a href="#/">Back to customer invoices</a>.</p></div></div>`
  }
}
document.getElementById('globalsearch').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { const q = e.target.value.trim(); if (/^CI-/i.test(q)) location.hash = `#/invoice/${q.toUpperCase()}`; else if (/^C-/i.test(q)) location.hash = `#/customer/${q.toUpperCase()}`; else { location.hash = '#/'; setTimeout(() => { const i = view.querySelector('.toolbar input'); if (i) { i.value = q; i.dispatchEvent(new Event('input')) } }, 300) } }
})
window.addEventListener('hashchange', route)
route()

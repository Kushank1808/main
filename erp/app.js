/* ORBIS ERP — static single-page client over the JSON API in ../api.
   Each screen is a small config: where to fetch, which columns to show, and how
   to render the detail. Adding an object means adding one entry to ROUTES. */
const API = '../api'
const view = document.getElementById('view')
const cache = new Map()

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]))
const num = (n, dp = 2) =>
  n === null || n === undefined || n === '' ? '' : Number(n).toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp })
const int = (n) => (n === null || n === undefined ? '' : Number(n).toLocaleString('en-US'))
const dash = (v) => (v === null || v === undefined || v === '' ? '<span class="v empty-val">—</span>' : null)
const title = (s) => String(s ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

async function get(path) {
  if (cache.has(path)) return cache.get(path)
  const r = await fetch(`${API}/${path}`, { cache: 'no-store' })
  if (!r.ok) throw new Error(`${r.status} ${path}`)
  const j = await r.json()
  cache.set(path, j)
  return j
}

/* ------------------------------- rendering -------------------------------- */
const kv = (rows) =>
  `<div class="kv">${rows
    .map(([l, v, cls = '']) => `<div class="row"><label>${l}</label>${dash(v) || `<div class="v ${cls}">${v}</div>`}</div>`)
    .join('')}</div>`

const card = (heading, body) => `<div class="card"><h2>${heading}</h2><div class="body">${body}</div></div>`
const cardTable = (heading, html) => `<div class="card"><h2>${heading}</h2><div class="scroll">${html}</div></div>`

function table(cols, rows) {
  if (!rows.length) return '<div class="empty">Nothing to show.</div>'
  const head = cols.map((c) => `<th class="${c.num ? 'num' : ''}">${c.label}</th>`).join('')
  const body = rows
    .map(
      (r) =>
        `<tr>${cols
          .map((c) => `<td class="${c.num ? 'num' : ''} ${c.wrap ? 'wrap' : ''}">${c.render ? c.render(r) : esc(r[c.key] ?? '')}</td>`)
          .join('')}</tr>`
    )
    .join('')
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`
}

const addr = (a) =>
  !a ? '' : `<div class="addr">${[a.name, a.address_1, a.address_2, a.address_3, a.address_4,
    `${a.city ?? ''} ${a.state ?? ''} ${a.postal_code ?? ''}`.trim(), a.country]
    .filter((x) => x && x !== '-').map(esc).join('\n')}</div>`

const chip = (text, kind = 'neutral') => `<span class="chip ${kind}">${esc(text)}</span>`
const statusChip = (s) => {
  const k = { ACTIVE: 'ok', OPEN: 'ok', CLOSED: 'neutral', BOOKED: 'neutral', EXPIRED: 'bad',
    AWAITING_BILLING: 'warn', PENDING_VALIDATION: 'warn' }[s] || 'neutral'
  return chip(title(s), k)
}
const link = (route, id, text) => `<a href="#/${route}/${encodeURIComponent(id)}">${esc(text ?? id)}</a>`
const docLinks = (docs) =>
  !docs || !docs.length
    ? '<div class="empty">No documents attached.</div>'
    : `<div class="doc-list">${docs
        .map(
          (d) => `<div class="doc">
            <div><a href="../${d.url}" target="_blank" rel="noopener">${esc(d.title)}</a>
              <div class="meta">${esc(d.document_id)} · ${(d.size_bytes / 1024).toFixed(0)} KB</div></div>
            <span class="pdf">PDF</span></div>`
        )
        .join('')}</div>`

/* toolbar with client-side search over the rows already loaded */
function searchable(rows, cols, placeholder, heading) {
  const id = 'q' + Math.random().toString(36).slice(2, 7)
  setTimeout(() => {
    const input = document.getElementById(id)
    if (!input) return
    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase()
      const hit = q ? rows.filter((r) => JSON.stringify(r).toLowerCase().includes(q)) : rows
      document.getElementById(id + '-t').innerHTML = table(cols, hit)
      document.getElementById(id + '-c').textContent = `${hit.length} of ${rows.length} rows`
    })
  }, 0)
  return `<div class="toolbar">
      <input id="${id}" placeholder="${placeholder}">
      <span class="spacer"></span><span class="count" id="${id}-c">${rows.length} rows</span>
    </div>
    <div class="card"><h2>${heading}</h2><div class="scroll" id="${id}-t">${table(cols, rows)}</div></div>`
}

function page(crumbs, heading, sub, html) {
  view.innerHTML = `<div class="crumbs">${crumbs}</div><h1>${heading}</h1>
    ${sub ? `<div class="page-sub">${sub}</div>` : ''}${html}`
  window.scrollTo(0, 0)
}
const home = '<a href="#/">Home</a>'

function tabs(defs) {
  const id = 't' + Math.random().toString(36).slice(2, 7)
  setTimeout(() => {
    const host = document.getElementById(id)
    if (!host) return
    host.parentElement.querySelectorAll('.tab').forEach((b, i) =>
      b.addEventListener('click', () => {
        host.parentElement.querySelectorAll('.tab').forEach((x) => x.classList.remove('active'))
        b.classList.add('active')
        host.innerHTML = defs[i][1]()
      })
    )
  }, 0)
  return `<div class="tabs">${defs.map(([l], i) => `<button class="tab ${i === 0 ? 'active' : ''}">${l}</button>`).join('')}</div>
    <div id="${id}">${defs[0][1]()}</div>`
}

/* ================================ screens ================================= */
async function dashboard() {
  const [idx, drafts, orders] = await Promise.all([get('index.json'), get('billing-drafts.json'), get('sales-orders.json')])
  const c = idx.counts
  const pending = drafts.data.length
  const value = drafts.data.reduce((s, d) => s + d.total_payable, 0)
  const held = orders.data.filter((o) => o.on_hold).length
  const awaiting = orders.data.filter((o) => o.status === 'AWAITING_BILLING').length

  page(home, 'Order-to-cash overview', 'Everything upstream of invoice generation, as held in ORBIS.',
    `<div class="tiles">
      <div class="tile"><div class="l">Sales orders</div><div class="v">${c.sales_orders}</div><div class="s">${c.order_lines} lines</div></div>
      <div class="tile"><div class="l">Awaiting billing</div><div class="v">${awaiting}</div><div class="s">shipped, not invoiced</div></div>
      <div class="tile"><div class="l">Billing drafts</div><div class="v">${pending}</div><div class="s">pending validation</div></div>
      <div class="tile"><div class="l">Draft value</div><div class="v">${num(value, 0)}</div><div class="s">mixed currency</div></div>
      <div class="tile ${held ? 'alert' : ''}"><div class="l">Orders on hold</div><div class="v">${held}</div><div class="s">not billable</div></div>
      <div class="tile"><div class="l">Documents</div><div class="v">${c.documents}</div><div class="s">contracts, POs, DNs</div></div>
    </div>
    ${card('About this system',
      `<p class="note">ORBIS holds the commercial truth that an invoice is built from: the contract that fixes
       price and terms, the customer PO that authorises spend, the sales order that captures what was asked for,
       and the delivery that records what actually shipped. Billing drafts are the pre-invoice artefact —
       what the billing desk intends to invoice, before anyone checks it.</p>
       <p class="note">Every screen is backed by a JSON endpoint under <span class="mono">api/</span> and every
       contract, PO, order and delivery has a source PDF under <span class="mono">docs/</span>.</p>`)}
    ${cardTable('Billing drafts pending validation', table(DRAFT_COLS, drafts.data.slice(0, 10)))}`)
}

const DRAFT_COLS = [
  { label: 'Draft', key: 'draft_number', render: (r) => link('draft', r.draft_number) },
  { label: 'Proposed invoice', key: 'proposed_invoice_number' },
  { label: 'Status', key: 'status', render: (r) => statusChip(r.status) },
  { label: 'Sales order', key: 'sales_order', render: (r) => link('order', r.sales_order) },
  { label: 'Order status', key: 'order_status', render: (r) => statusChip(r.order_status) + (r.order_on_hold ? ' ' + chip('hold', 'bad') : '') },
  { label: 'Invoiced on', key: 'order_invoiced_date', render: (r) => (r.order_invoiced_date ? `${esc(r.order_invoiced_date)} ${chip('duplicate risk', 'bad')}` : '—') },
  { label: 'Customer PO', key: 'customer_po_number', render: (r) => (r.customer_po_number ? link('po', r.customer_po_number) : chip('missing', 'bad')) },
  { label: 'Contract', key: 'contract_number', render: (r) => link('contract', r.contract_number) },
  { label: 'Delivery', key: 'delivery_number', render: (r) => (r.delivery_number ? link('delivery', r.delivery_number) : '—') },
  { label: 'Customer', key: 'customer_name' },
  { label: 'Bill-to', key: 'bill_to_name' },
  { label: 'Bill-to city/state', key: 'bill_to_city', render: (r) => `${esc(r.bill_to_city)}, ${esc(r.bill_to_state)} ${esc(r.bill_to_postal_code)}` },
  { label: 'Ship-to', key: 'ship_to_name' },
  { label: 'Ship-to city/state', key: 'ship_to_city', render: (r) => `${esc(r.ship_to_city)}, ${esc(r.ship_to_state)} ${esc(r.ship_to_postal_code)}` },
  { label: 'Invoice date', key: 'invoice_date' },
  { label: 'Prepared on', key: 'prepared_on' },
  { label: 'Billing type', key: 'billing_type' },
  { label: 'Terms', key: 'payment_terms' },
  { label: 'Incoterms', key: 'incoterms' },
  { label: 'Tax code', key: 'tax_code' },
  { label: 'Treatment', key: 'tax_treatment', render: (r) => esc(title(r.tax_treatment)) },
  { label: 'Tax rate', key: 'tax_rate', num: true, render: (r) => `${num(r.tax_rate, 2)}%` },
  { label: 'Exemption cert', key: 'exemption_certificate', render: (r) => esc(r.exemption_certificate ?? '—') },
  { label: 'Tax reg', key: 'customer_tax_registration' },
  { label: 'Lines', key: 'line_count', num: true },
  { label: 'Total qty', key: 'total_quantity', num: true, render: (r) => int(r.total_quantity) },
  { label: 'Ccy', key: 'currency' },
  { label: 'Goods', key: 'goods_subtotal', num: true, render: (r) => num(r.goods_subtotal) },
  { label: 'Surcharge', key: 'surcharge_total', num: true, render: (r) => num(r.surcharge_total) },
  { label: 'Freight', key: 'freight_total', num: true, render: (r) => num(r.freight_total) },
  { label: 'Net subtotal', key: 'net_subtotal', num: true, render: (r) => num(r.net_subtotal) },
  { label: 'Tax amt', key: 'tax_amount', num: true, render: (r) => num(r.tax_amount) },
  { label: 'Total payable', key: 'total_payable', num: true, render: (r) => `<b>${num(r.total_payable)}</b>` },
  { label: 'Operating unit', key: 'operating_unit' },
  { label: 'Prepared by', key: 'prepared_by' },
]

/* Flat line-level view: one row per draft line, every header field on the row.
   ref_ columns are joined from the source objects and can be toggled off. */
function csvDownload(rows, filename) {
  const cols = Object.keys(rows[0] ?? {})
  const cell = (v) => {
    const t = v === null || v === undefined ? '' : String(v)
    return /[",\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t
  }
  const csv = [cols.join(','), ...rows.map((r) => cols.map((c) => cell(r[c])).join(','))].join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function draftLines() {
  const payload = await get('billing-draft-lines.json')
  const rows = payload.data
  const allKeys = Object.keys(rows[0] ?? {})
  const refKeys = allKeys.filter((k) => k.startsWith('ref_'))
  // line-level fields first: this table is read line by line, not header by header
  const FIRST = ['draft_number', 'line', 'item_number', 'item_description', 'item_class', 'line_type',
    'uom', 'quantity_to_bill', 'unit_price', 'line_amount', 'line_tax_code', 'line_tax_rate',
    'line_tax_amount', 'line_total_incl_tax', 'line_source', 'line_source_reference',
    'sales_order', 'customer_po_number', 'delivery_number', 'contract_number', 'customer_name',
    'invoice_date', 'currency', 'payment_terms', 'incoterms', 'tax_code', 'tax_treatment', 'tax_rate']
  const rank = (k) => (FIRST.indexOf(k) === -1 ? FIRST.length + allKeys.indexOf(k) : FIRST.indexOf(k))
  const coreKeys = allKeys.filter((k) => !k.startsWith('ref_')).sort((a, b) => rank(a) - rank(b))
  const NUMERIC = /quantity|price|amount|total|rate|pct|subtotal|limit|count/
  const colFor = (k) => ({
    label: title(k.replace(/^ref_/, '')),
    key: k,
    num: NUMERIC.test(k),
    render:
      k === 'draft_number' ? (r) => link('draft', r.draft_number)
      : k === 'sales_order' ? (r) => link('order', r.sales_order)
      : /quantity|count/.test(k) ? (r) => (r[k] === null || r[k] === undefined ? '—' : int(r[k]))
      : NUMERIC.test(k) ? (r) => (r[k] === null || r[k] === undefined ? '—' : num(r[k], /rate|pct|price/.test(k) ? 4 : 2))
      : (r) => esc(r[k] ?? '—'),
  })

  let showRef = false
  let filtered = rows
  const paint = () => {
    const cols = (showRef ? [...coreKeys, ...refKeys] : coreKeys).map(colFor)
    document.getElementById('flatTable').innerHTML = table(cols, filtered)
    document.getElementById('flatCount').textContent =
      `${filtered.length} of ${rows.length} lines · ${cols.length} columns`
  }

  page(`${home} › <a href="#/drafts">Billing drafts</a> › Lines`, 'Billing draft lines',
    'One row per draft line with the full header denormalised onto it — the shape a validation run consumes.',
    `<p class="note">Columns prefixed <span class="mono">ref_</span> are joined from the contract, purchase
      order, sales order, delivery and tax rules. They are what the draft <em>should</em> agree with, not part
      of the draft — turn them off to see the draft exactly as the billing desk stated it.
      Endpoint: <span class="mono">api/billing-draft-lines.json</span>.</p>
     <div class="toolbar">
       <input id="flatQ" placeholder="Search draft, order, item, customer">
       <label style="display:inline-flex;align-items:center;gap:7px;flex:0 0 auto;white-space:nowrap"><input type="checkbox" id="flatRef"> Show reference columns</label>
       <button class="tab" id="flatCsv" style="border:1px solid var(--line);border-radius:3px;padding:6px 11px">Download CSV</button>
       <span class="spacer"></span><span class="count" id="flatCount"></span>
     </div>
     <div class="card"><h2>Draft lines</h2><div class="scroll" id="flatTable"></div></div>`)

  document.getElementById('flatQ').addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase()
    filtered = q ? rows.filter((r) => JSON.stringify(r).toLowerCase().includes(q)) : rows
    paint()
  })
  document.getElementById('flatRef').addEventListener('change', (e) => {
    showRef = e.target.checked
    paint()
  })
  document.getElementById('flatCsv').addEventListener('click', () => csvDownload(filtered, 'orbis-billing-draft-lines.csv'))
  paint()
}

async function draftList() {
  const d = await get('billing-drafts.json')
  page(`${home} › Billing drafts`, 'Billing drafts', 'Pre-invoice drafts awaiting validation against contract, PO, order and delivery.',
    searchable(d.data, DRAFT_COLS, 'Search draft, order, PO or customer', 'Billing drafts'))
}

async function draftDetail(id) {
  const d = (await get(`billing-drafts/${id}.json`)).data
  const t = d.totals
  const header = kv([
    ['Draft number', esc(d.draft_number)], ['Proposed invoice', esc(d.proposed_invoice_number)],
    ['Status', statusChip(d.status)], ['Billing type', esc(d.billing_type)],
    ['Sales order', link('order', d.sales_order)], ['Order status', statusChip(d.order_status)],
    ['Customer PO', d.customer_po_number ? link('po', d.customer_po_number) : ''],
    ['Contract', link('contract', d.contract_number)],
    ['Delivery note', d.delivery_number ? link('delivery', d.delivery_number) : ''],
    ['Customer', link('customer', d.customer_id, d.customer_name)],
    ['Invoice date', esc(d.invoice_date)], ['Prepared by', `${esc(d.prepared_by)} on ${esc(d.prepared_on)}`],
    ['Currency', esc(d.currency)], ['Payment terms', esc(d.payment_terms)],
    ['Incoterms', esc(d.incoterms)], ['Operating unit', esc(d.operating_unit)],
    ['Order invoiced on', d.order_invoiced_date ? `${esc(d.order_invoiced_date)} ${chip('already invoiced', 'bad')}` : ''],
  ])
  const parties = `<div class="kv"><div class="row"><label>Bill to</label><div class="v">${addr(d.bill_to)}</div></div>
      <div class="row"><label>Ship to</label><div class="v">${addr(d.ship_to)}</div></div></div>`
  const taxBlock = kv([
    ['Tax code', esc(d.tax_code)], ['Treatment', esc(title(d.tax_treatment))],
    ['Rate', `${num(d.tax_rate, 2)}%`], ['Customer tax registration', esc(d.customer_tax_registration)],
    ['Exemption certificate', d.exemption_certificate ? esc(d.exemption_certificate) : ''],
    ['Notes', esc(d.notes)],
  ])
  const totals = kv([
    ['Goods subtotal', num(t.goods_subtotal)], ['Surcharges', num(t.surcharge_total)],
    ['Freight', num(t.freight_total)], ['Tax', num(t.tax_amount)],
    ['Total payable', `<b>${num(t.total_payable)} ${esc(t.currency)}</b>`],
  ])
  const lineCols = [
    { label: 'Ln', key: 'line' }, { label: 'Item', key: 'item_number' },
    { label: 'Description', key: 'description', wrap: true },
    { label: 'Type', key: 'line_type', render: (r) => chip(title(r.line_type), r.line_type === 'GOODS' ? 'neutral' : 'warn') },
    { label: 'UOM', key: 'uom' },
    { label: 'Qty to bill', key: 'quantity_to_bill', num: true, render: (r) => int(r.quantity_to_bill) },
    { label: 'Unit price', key: 'unit_price', num: true, render: (r) => num(r.unit_price, 4) },
    { label: 'Amount', key: 'amount', num: true, render: (r) => num(r.amount) },
    { label: 'Tax code', key: 'tax_code' },
    { label: 'Tax amt', key: 'tax_amount', num: true, render: (r) => num(r.tax_amount) },
    { label: 'Source', key: 'source', render: (r) => `${esc(r.source)}${r.source_reference ? ` <span class="count">${esc(r.source_reference)}</span>` : ''}` },
  ]

  page(`${home} › <a href="#/drafts">Billing drafts</a> › ${esc(d.draft_number)}`,
    `Billing draft ${esc(d.draft_number)}`,
    `${esc(d.customer_name)} · proposed invoice ${esc(d.proposed_invoice_number)} · ${num(t.total_payable)} ${esc(t.currency)}`,
    tabs([
      ['Header', () => card('Draft header', header) + card('Bill-to and ship-to', parties)],
      ['Lines', () => cardTable('Draft lines', table(lineCols, d.lines)) + card('Totals', totals)],
      ['Tax', () => card('Tax determination', taxBlock)],
      ['Source documents', () => card('Attached documents', docLinks(d.documents))],
    ]))
}

const ORDER_COLS = [
  { label: 'Order', key: 'order_number', render: (r) => link('order', r.order_number) },
  { label: 'Customer PO', key: 'customer_po_number', render: (r) => link('po', r.customer_po_number) },
  { label: 'Bill-to', key: 'customer_name_bill_to' },
  { label: 'Ship-to', key: 'customer_name_ship_to' },
  { label: 'State (B/S)', key: 'state_bill_to', render: (r) => `${esc(r.state_bill_to)} / ${esc(r.state_ship_to)}` },
  { label: 'Status', key: 'status', render: (r) => statusChip(r.status) + (r.on_hold ? ' ' + chip('hold', 'bad') : '') },
  { label: 'Entered', key: 'entered_date' },
  { label: 'Invoiced', key: 'invoiced_date', render: (r) => esc(r.invoiced_date ?? '—') },
  { label: 'Delivery', key: 'delivery_number', render: (r) => (r.delivery_number ? link('delivery', r.delivery_number) : '—') },
  { label: 'Terms', key: 'payment_terms' },
  { label: 'Tax code', key: 'tax_code' },
  { label: 'Lines', key: 'line_count', num: true },
  { label: 'Order total', key: 'order_total', num: true, render: (r) => `${num(r.order_total)} ${esc(r.currency)}` },
  { label: 'Operating unit', key: 'operating_unit' },
  { label: 'Order taker', key: 'transaction_originator' },
]

async function orderList() {
  const d = await get('sales-orders.json')
  page(`${home} › Sales orders`, 'Sales orders', 'Order headers, lines, shipment status and billing eligibility.',
    searchable(d.data, ORDER_COLS, 'Search order, PO, customer or state', 'Sales orders'))
}

async function orderDetail(id) {
  const o = (await get(`sales-orders/${id}.json`)).data
  const t = o.totals
  const header = kv([
    ['Order number', esc(o.order_number)], ['Order type', esc(o.order_type)],
    ['Order source', esc(o.order_source)], ['Status', statusChip(o.status)],
    ['Customer PO', link('po', o.customer_po_number)], ['Contract', link('contract', o.contract_number)],
    ['Customer', link('customer', o.customer_id, o.customer_id)],
    ['Operating unit', esc(o.operating_unit)], ['Legal entity', esc(o.legal_entity)],
    ['Entered date', esc(o.entered_date)], ['Booked date', esc(o.booked_date)],
    ['Requested ship date', esc(o.requested_ship_date)],
    ['Invoiced date', o.invoiced_date ? esc(o.invoiced_date) : ''],
    ['Price list', esc(o.price_list)], ['Currency', esc(o.currency)],
    ['Payment terms', esc(o.payment_terms)], ['Incoterms', esc(o.incoterms)],
    ['Freight terms', esc(title(o.freight_terms))],
    ['Order taker', esc(o.transaction_originator)],
    ['Caller', `${esc(o.caller_name)}<br>${esc(o.caller_email)}<br>${esc(o.caller_phone)}`],
  ])
  const parties = `<div class="kv"><div class="row"><label>Bill to</label><div class="v">${addr(o.bill_to)}</div></div>
      <div class="row"><label>Ship to</label><div class="v">${addr(o.ship_to)}</div></div></div>`
  const lineCols = [
    { label: 'Ln', key: 'line_number' }, { label: 'Item', key: 'item_number' },
    { label: 'Description', key: 'description', wrap: true },
    { label: 'Type', key: 'line_type', render: (r) => chip(title(r.line_type), r.line_type === 'GOODS' ? 'neutral' : 'warn') },
    { label: 'UOM', key: 'uom' },
    { label: 'Ordered', key: 'ordered_quantity', num: true, render: (r) => int(r.ordered_quantity) },
    { label: 'Shipped', key: 'shipped_quantity', num: true,
      render: (r) => (r.shipped_quantity < r.ordered_quantity ? `<b>${int(r.shipped_quantity)}</b>` : int(r.shipped_quantity)) },
    { label: 'List price', key: 'unit_list_price', num: true, render: (r) => num(r.unit_list_price, 2) },
    { label: 'Contract price', key: 'contract_price', num: true, render: (r) => num(r.contract_price, 2) },
    { label: 'Selling price', key: 'unit_selling_price', num: true, render: (r) => num(r.unit_selling_price, 4) },
    { label: 'Extended', key: 'extended_amount', num: true, render: (r) => num(r.extended_amount) },
    { label: 'Tax code', key: 'tax_code' },
    { label: 'Tax rate', key: 'tax_rate', num: true, render: (r) => `${num(r.tax_rate, 2)}%` },
    { label: 'Tax amt', key: 'tax_amount', num: true, render: (r) => num(r.tax_amount) },
    { label: 'Revenue account', key: 'revenue_account' },
  ]
  const holdRows = o.holds.length
    ? table([{ label: 'Hold', key: 'hold_name' }, { label: 'Applied', key: 'applied_on' },
             { label: 'By', key: 'applied_by' },
             { label: 'Released', key: 'released', render: (r) => (r.released ? chip(`released ${r.released_on ?? ''}`, 'ok') : chip('active', 'bad')) }], o.holds)
    : '<div class="empty">No holds on this order.</div>'

  page(`${home} › <a href="#/orders">Sales orders</a> › ${esc(o.order_number)}`,
    `Sales order ${esc(o.order_number)}`,
    `${esc(o.customer_name_bill_to)} · ${esc(o.status)} · ${num(t.order_total)} ${esc(o.currency)}`,
    tabs([
      ['Header', () => card('Order header', header) + card('Bill-to and ship-to', parties)],
      ['Lines', () => cardTable('Order lines', table(lineCols, o.lines)) +
        card('Order totals', kv([['Goods', num(t.goods_amount)], ['Surcharges', num(t.surcharge_amount)],
          ['Freight', num(t.freight_amount)], ['Tax', num(t.tax_amount)],
          ['Order total', `<b>${num(t.order_total)} ${esc(o.currency)}</b>`]]))],
      ['Tax and charges', () => card('Tax determination', kv([
        ['Tax code', esc(o.tax_code)], ['Treatment', esc(title(o.tax_treatment))],
        ['Customer tax registration', esc(o.tax_registration_customer)],
        ['Exemption certificate', o.exemption_certificate ? esc(o.exemption_certificate) : ''],
        ['Freight terms', esc(title(o.freight_terms))], ['Incoterms', esc(o.incoterms)]]))],
      ['Shipping', () => card('Delivery', kv([
        ['Delivery note', o.delivery_number ? link('delivery', o.delivery_number) : ''],
        ['Requested ship date', esc(o.requested_ship_date)],
        ['Ship-to site', esc(o.ship_to.site_use_id)]]))],
      ['Holds', () => cardTable('Order holds', holdRows)],
      ['Documents', () => card('Attached documents', docLinks(o.documents))],
    ]))
}

async function contractList() {
  const d = await get('contracts.json')
  const cols = [
    { label: 'Contract', key: 'contract_number', render: (r) => link('contract', r.contract_number) },
    { label: 'Type', key: 'contract_type', render: (r) => esc(title(r.contract_type)) },
    { label: 'Customer', key: 'customer_name' },
    { label: 'Status', key: 'status', render: (r) => statusChip(r.status) },
    { label: 'Effective', key: 'effective_from', render: (r) => `${esc(r.effective_from)} → ${esc(r.effective_to)}` },
    { label: 'Ccy', key: 'currency' },
    { label: 'Price list', key: 'price_list' },
    { label: 'Discount', key: 'discount_pct', num: true, render: (r) => `${num(r.discount_pct, 1)}%` },
    { label: 'Terms', key: 'payment_terms' }, { label: 'Incoterms', key: 'incoterms' },
    { label: 'Freight', key: 'freight_terms', render: (r) => esc(title(r.freight_terms)) },
    { label: 'Tax treatment', key: 'tax_treatment', render: (r) => esc(title(r.tax_treatment)) },
    { label: 'PO required', key: 'po_required', render: (r) => (r.po_required ? chip('yes', 'ok') : chip('no', 'neutral')) },
    { label: 'Surcharges', key: 'surcharge_allowed', render: (r) => (r.surcharge_allowed ? chip('allowed', 'ok') : chip('prohibited', 'bad')) },
  ]
  page(`${home} › Contracts`, 'Contracts', 'The commercial source of truth for price, terms, tax treatment and what may be billed.',
    searchable(d.data, cols, 'Search contract or customer', 'Contracts'))
}

async function contractDetail(id) {
  const c = (await get(`contracts/${id}.json`)).data
  const header = kv([
    ['Contract number', esc(c.contract_number)], ['Type', esc(title(c.contract_type))],
    ['Customer', link('customer', c.customer_id, c.customer_name)], ['Status', statusChip(c.status)],
    ['Effective from', esc(c.effective_from)], ['Effective to', esc(c.effective_to)],
    ['Currency', esc(c.currency)], ['Price list', esc(c.price_list)],
    ['Discount', `${num(c.discount_pct, 1)}%`], ['Payment terms', esc(c.payment_terms)],
    ['Incoterms', esc(c.incoterms)], ['Freight terms', esc(title(c.freight_terms))],
    ['Billing rule', esc(title(c.billing_rule))], ['Tax treatment', esc(title(c.tax_treatment))],
    ['Customer PO required', c.po_required ? chip('yes', 'ok') : chip('no', 'neutral')],
    ['Surcharges', c.surcharge_allowed ? chip('allowed', 'ok') : chip('prohibited', 'bad')],
    ['Price tolerance', `${num(c.price_tolerance_pct, 2)}%`], ['Quantity tolerance', `${num(c.qty_tolerance_pct, 2)}%`],
    ['Signed (customer)', esc(c.signed_by_customer)], ['Signed (supplier)', esc(c.signed_by_supplier)],
  ])
  const priceCols = [
    { label: 'Item', key: 'item_number' }, { label: 'UOM', key: 'uom' },
    { label: 'List price', key: 'list_price', num: true, render: (r) => num(r.list_price) },
    { label: 'Discount', key: 'discount_pct', num: true, render: (r) => `${num(r.discount_pct, 1)}%` },
    { label: 'Contract price', key: 'contract_price', num: true, render: (r) => `<b>${num(r.contract_price)}</b>` },
    { label: 'Ccy', key: 'currency' },
    { label: 'Effective', key: 'effective_from', render: (r) => `${esc(r.effective_from)} → ${esc(r.effective_to)}` },
  ]
  page(`${home} › <a href="#/contracts">Contracts</a> › ${esc(c.contract_number)}`,
    `Contract ${esc(c.contract_number)}`, `${esc(c.customer_name)} · ${esc(title(c.contract_type))}`,
    tabs([
      ['Terms', () => card('Contract header', header) +
        card('Clauses', c.clauses.map((x, i) => `<p class="clause">${i + 1}. ${esc(x)}</p>`).join(''))],
      ['Price list', () => cardTable(`Agreed prices — ${esc(c.price_list)}`, table(priceCols, c.price_list_lines))],
      ['Orders', () => cardTable('Orders under this contract',
        table([{ label: 'Order', key: 'o', render: (r) => link('order', r.o) }], c.orders.map((o) => ({ o }))))],
      ['Documents', () => card('Attached documents', docLinks(c.documents))],
    ]))
}

async function poList() {
  const d = await get('purchase-orders.json')
  const cols = [
    { label: 'PO number', key: 'po_number', render: (r) => link('po', r.po_number) },
    { label: 'Customer', key: 'customer_name' },
    { label: 'Contract', key: 'contract_number', render: (r) => link('contract', r.contract_number) },
    { label: 'PO date', key: 'po_date' }, { label: 'Valid to', key: 'valid_to' },
    { label: 'Status', key: 'status', render: (r) => statusChip(r.status) },
    { label: 'Ccy', key: 'currency' },
    { label: 'Authorised', key: 'po_amount_limit', num: true, render: (r) => num(r.po_amount_limit) },
    { label: 'Released', key: 'released_amount', num: true, render: (r) => num(r.released_amount) },
    { label: 'Sales order', key: 'sales_order', render: (r) => link('order', r.sales_order) },
    { label: 'Buyer', key: 'buyer_name' },
  ]
  page(`${home} › Purchase orders`, 'Customer purchase orders', 'Customer authority to be billed: validity window and approved value.',
    searchable(d.data, cols, 'Search PO, customer or order', 'Customer purchase orders'))
}

async function poDetail(id) {
  const p = (await get(`purchase-orders/${id}.json`)).data
  const over = p.released_amount > p.po_amount_limit
  const header = kv([
    ['PO number', esc(p.po_number)], ['Customer', link('customer', p.customer_id, p.customer_name)],
    ['Contract', link('contract', p.contract_number)], ['Sales order', link('order', p.sales_order)],
    ['PO date', esc(p.po_date)], ['Valid from', esc(p.valid_from)],
    ['Valid to', `${esc(p.valid_to)} ${p.status === 'EXPIRED' ? chip('expired', 'bad') : ''}`],
    ['Status', statusChip(p.status)], ['Currency', esc(p.currency)],
    ['Authorised value', num(p.po_amount_limit)],
    ['Released against PO', `${num(p.released_amount)} ${over ? chip('over authority', 'bad') : ''}`],
    ['Payment terms', esc(p.payment_terms)], ['Incoterms', esc(p.incoterms)],
    ['Buyer', `${esc(p.buyer_name)}<br>${esc(p.buyer_email)}`],
  ])
  const cols = [
    { label: 'Ln', key: 'po_line' }, { label: 'Item', key: 'item_number' },
    { label: 'Description', key: 'description', wrap: true }, { label: 'UOM', key: 'uom' },
    { label: 'Qty', key: 'quantity', num: true, render: (r) => int(r.quantity) },
    { label: 'Unit price', key: 'unit_price', num: true, render: (r) => num(r.unit_price, 4) },
    { label: 'Amount', key: 'amount', num: true, render: (r) => num(r.amount) },
  ]
  page(`${home} › <a href="#/pos">Purchase orders</a> › ${esc(p.po_number)}`,
    `Purchase order ${esc(p.po_number)}`, `${esc(p.customer_name)} · authorised ${num(p.po_amount_limit)} ${esc(p.currency)}`,
    tabs([
      ['Header', () => card('PO header', header)],
      ['Lines', () => cardTable('PO lines', table(cols, p.lines))],
      ['Documents', () => card('Attached documents', docLinks(p.documents))],
    ]))
}

async function deliveryList() {
  const d = await get('deliveries.json')
  const cols = [
    { label: 'Delivery', key: 'delivery_number', render: (r) => link('delivery', r.delivery_number) },
    { label: 'Sales order', key: 'sales_order', render: (r) => link('order', r.sales_order) },
    { label: 'Customer', key: 'customer_id', render: (r) => link('customer', r.customer_id) },
    { label: 'Ship date', key: 'ship_date' }, { label: 'POD date', key: 'proof_of_delivery_date' },
    { label: 'Carrier', key: 'carrier' }, { label: 'Waybill', key: 'waybill' },
    { label: 'Incoterms', key: 'incoterms' },
  ]
  page(`${home} › Deliveries`, 'Deliveries', 'What actually shipped — the quantity basis for delivery-based billing.',
    searchable(d.data, cols, 'Search delivery, order or waybill', 'Deliveries'))
}

async function deliveryDetail(id) {
  const d = (await get(`deliveries/${id}.json`)).data
  const header = kv([
    ['Delivery note', esc(d.delivery_number)], ['Sales order', link('order', d.sales_order)],
    ['Customer', link('customer', d.customer_id)], ['Ship date', esc(d.ship_date)],
    ['Proof of delivery', esc(d.proof_of_delivery_date)], ['Carrier', esc(d.carrier)],
    ['Waybill', esc(d.waybill)], ['Incoterms', esc(d.incoterms)],
    ['Gross weight', `${num(d.gross_weight_kg)} kg`], ['Ship from', esc(d.ship_from)],
  ])
  const cols = [
    { label: 'Ln', key: 'delivery_line' }, { label: 'Item', key: 'item_number' }, { label: 'UOM', key: 'uom' },
    { label: 'Ordered', key: 'ordered_quantity', num: true, render: (r) => int(r.ordered_quantity) },
    { label: 'Shipped', key: 'shipped_quantity', num: true, render: (r) => `<b>${int(r.shipped_quantity)}</b>` },
    { label: 'Backordered', key: 'backordered_quantity', num: true,
      render: (r) => (r.backordered_quantity ? `<span class="chip warn">${int(r.backordered_quantity)}</span>` : '0') },
  ]
  page(`${home} › <a href="#/deliveries">Deliveries</a> › ${esc(d.delivery_number)}`,
    `Delivery ${esc(d.delivery_number)}`, `Order ${esc(d.sales_order)} · shipped ${esc(d.ship_date)}`,
    tabs([
      ['Header', () => card('Delivery header', header) + card('Ship to', addr(d.ship_to))],
      ['Lines', () => cardTable('Shipped lines', table(cols, d.lines))],
      ['Documents', () => card('Attached documents', docLinks(d.documents))],
    ]))
}

async function customerList() {
  const d = await get('customers.json')
  const cols = [
    { label: 'Customer', key: 'customer_id', render: (r) => link('customer', r.customer_id) },
    { label: 'Name', key: 'customer_name' }, { label: 'Class', key: 'customer_class' },
    { label: 'Country', key: 'country' }, { label: 'Ccy', key: 'currency' },
    { label: 'Tax code', key: 'tax_code' }, { label: 'Terms', key: 'payment_terms' },
    { label: 'Credit limit', key: 'credit_limit', num: true, render: (r) => num(r.credit_limit, 0) },
    { label: 'Collector', key: 'collector' }, { label: 'Operating unit', key: 'operating_unit' },
  ]
  page(`${home} › Customers`, 'Customer master', 'Bill-to and ship-to sites, tax registration and credit terms.',
    searchable(d.data, cols, 'Search customer', 'Customers'))
}

async function customerDetail(id) {
  const c = (await get(`customers/${id}.json`)).data
  const header = kv([
    ['Customer ID', esc(c.customer_id)], ['Name', esc(c.customer_name)],
    ['Class', esc(c.customer_class)], ['Country', esc(c.country)], ['Currency', esc(c.currency)],
    ['Operating unit', esc(c.operating_unit)], ['Contract', link('contract', c.contract_number)],
    ['Tax code', esc(c.tax_code)], ['Tax registration', esc(c.tax_registration)],
    ['Exemption certificate', c.exemption_certificate ? esc(c.exemption_certificate) : ''],
    ['Credit limit', num(c.credit_limit, 0)], ['Payment terms', esc(c.payment_terms)],
    ['Collector', esc(c.collector)],
    ['Contact', `${esc(c.contact_name)}<br>${esc(c.contact_email)}<br>${esc(c.contact_phone)}`],
  ])
  const sites = `<div class="kv">
      <div class="row"><label>Bill-to site<br><span class="count">${esc(c.bill_to.site_use_id)}</span></label><div class="v">${addr(c.bill_to)}</div></div>
      <div class="row"><label>Ship-to site<br><span class="count">${esc(c.ship_to.site_use_id)}</span></label><div class="v">${addr(c.ship_to)}</div></div></div>`
  page(`${home} › <a href="#/customers">Customers</a> › ${esc(c.customer_id)}`,
    esc(c.customer_name), `${esc(c.customer_id)} · ${esc(c.customer_class)}`,
    tabs([
      ['Profile', () => card('Customer header', header) + card('Sites', sites)],
      ['Orders', () => cardTable('Orders', table([{ label: 'Order', key: 'o', render: (r) => link('order', r.o) }], c.orders.map((o) => ({ o }))))],
    ]))
}

async function itemList() {
  const [items, prices] = await Promise.all([get('items.json'), get('price-list.json')])
  const itemCols = [
    { label: 'Item', key: 'item_number' }, { label: 'Description', key: 'description', wrap: true },
    { label: 'Class', key: 'item_class' }, { label: 'Type', key: 'line_type' },
    { label: 'UOM', key: 'uom' },
    { label: 'List price', key: 'list_price', num: true, render: (r) => num(r.list_price) },
    { label: 'Taxable', key: 'taxable', render: (r) => (r.taxable ? chip('yes', 'ok') : chip('no', 'neutral')) },
    { label: 'HS code', key: 'hs_code' }, { label: 'Operating unit', key: 'operating_unit' },
  ]
  const priceCols = [
    { label: 'Price list', key: 'price_list' },
    { label: 'Contract', key: 'contract_number', render: (r) => link('contract', r.contract_number) },
    { label: 'Item', key: 'item_number' },
    { label: 'List price', key: 'list_price', num: true, render: (r) => num(r.list_price) },
    { label: 'Discount', key: 'discount_pct', num: true, render: (r) => `${num(r.discount_pct, 1)}%` },
    { label: 'Contract price', key: 'contract_price', num: true, render: (r) => `<b>${num(r.contract_price)}</b>` },
    { label: 'Ccy', key: 'currency' },
  ]
  page(`${home} › Items`, 'Item master and price lists', 'List prices and the contract price each customer is entitled to.',
    tabs([
      ['Items', () => cardTable('Item master', table(itemCols, items.data))],
      ['Price list lines', () => cardTable('Contract price lists', table(priceCols, prices.data))],
    ]))
}

async function taxList() {
  const d = await get('tax-rules.json')
  const cols = [
    { label: 'Tax code', key: 'tax_code' }, { label: 'Jurisdiction', key: 'jurisdiction' },
    { label: 'Rate', key: 'rate', num: true, render: (r) => `${num(r.rate, 2)}%` },
    { label: 'Treatment', key: 'treatment', render: (r) => esc(title(r.treatment)) },
    { label: 'Basis', key: 'basis', wrap: true },
    { label: 'Certificate required', key: 'requires_certificate', render: (r) => (r.requires_certificate ? chip('yes', 'warn') : chip('no', 'neutral')) },
  ]
  page(`${home} › Tax rules`, 'Tax rules', 'The rate and treatment an invoice line must carry for each jurisdiction.',
    cardTable('Tax rules', table(cols, d.data)))
}

async function documentList() {
  const d = await get('documents.json')
  const cols = [
    { label: 'Document', key: 'title', render: (r) => `<a href="../${r.url}" target="_blank" rel="noopener">${esc(r.title)}</a>` },
    { label: 'Type', key: 'document_type', render: (r) => esc(title(r.document_type)) },
    { label: 'Reference', key: 'reference' },
    { label: 'Related object', key: 'related_object', render: (r) => esc(title(r.related_object)) },
    { label: 'Date', key: 'document_date' },
    { label: 'Size', key: 'size_bytes', num: true, render: (r) => `${(r.size_bytes / 1024).toFixed(0)} KB` },
    { label: 'ID', key: 'document_id' },
  ]
  page(`${home} › Documents`, 'Document repository', 'Every contract, PO, order acknowledgement and delivery note as a PDF.',
    searchable(d.data, cols, 'Search document, reference or type', 'Documents'))
}

async function integration() {
  const idx = await get('index.json')
  const pkgs = await get('validation-packages.json')
  const rows = Object.entries(idx.endpoints).map(([k, v]) => ({ k: title(k), v }))
  const cols = [
    { label: 'Resource', key: 'k' },
    { label: 'Path', key: 'v', render: (r) => `<a href="../${r.v.replace(/\{[^}]+\}/, '')}" class="mono">${esc(r.v)}</a>` },
  ]
  page(`${home} › Integration`, 'API integration',
    'Read-only JSON over static hosting. No authentication, no rate limits, CORS open to any origin.',
    `<p class="note">External tools should start at
      <span class="mono">api/validation-packages/{draft_number}.json</span> — it returns a billing draft
      together with its sales order, purchase order, contract and price list, delivery, customer,
      tax rules, item master and the URLs of all four source PDFs. One request instead of six.</p>
     ${cardTable('Connection notes', table([
        { label: 'Topic', key: 'k' }, { label: 'Detail', key: 'v', wrap: true },
      ], Object.entries(idx.integration_notes).map(([k, v]) => ({ k: title(k), v }))))}
     ${cardTable('Endpoints', table(cols, rows))}
     ${cardTable('Validation packages', table([
        { label: 'Draft', key: 'draft_number', render: (r) => link('draft', r.draft_number) },
        { label: 'Package', key: 'url', render: (r) => `<a href="../${r.url}" class="mono">${esc(r.url)}</a>` },
        { label: 'Sales order', key: 'sales_order' },
        { label: 'Documents', key: 'document_count', num: true },
        { label: 'Total payable', key: 'total_payable', num: true, render: (r) => `${num(r.total_payable)} ${esc(r.currency)}` },
      ], pkgs.data))}`)
}

async function fieldMap() {
  const d = await get('field-map.json')
  const cols = [
    { label: 'Invoice field', key: 'invoice_field' },
    { label: 'Category', key: 'category' },
    { label: 'Severity', key: 'severity', render: (r) => chip(r.severity, r.severity === 'critical' ? 'bad' : r.severity === 'high' ? 'warn' : 'neutral') },
    { label: 'Authoritative source', key: 'authoritative_source', wrap: true },
    { label: 'Precedence', key: 'precedence', wrap: true, render: (r) => r.precedence.map((p) => chip(title(p))).join(' ') },
    { label: 'Compared against', key: 'compare_to', wrap: true },
    { label: 'Match rule', key: 'match', wrap: true },
  ]
  page(`${home} › Field lineage`, 'Invoice field lineage',
    'For a billing validation tool: every field that goes onto an invoice, where its authoritative value lives, and how to compare it.',
    `<p class="note">Read this as the specification for the validation rule set. Precedence matters —
     where two sources disagree, the leftmost wins.</p>${cardTable('Field lineage', table(cols, d.data))}`)
}

/* ================================= routing =============================== */
const ROUTES = {
  '': dashboard,
  drafts: draftList, draft: draftDetail, draftlines: draftLines,
  orders: orderList, order: orderDetail,
  contracts: contractList, contract: contractDetail,
  pos: poList, po: poDetail,
  deliveries: deliveryList, delivery: deliveryDetail,
  customers: customerList, customer: customerDetail,
  items: itemList, tax: taxList, documents: documentList, fields: fieldMap, integration,
}

const NAV = [
  ['Billing', [['drafts', 'Billing drafts'], ['draftlines', 'Draft lines (flat)'], ['fields', 'Invoice field lineage']]],
  ['Order management', [['orders', 'Sales orders'], ['deliveries', 'Deliveries'], ['pos', 'Customer POs']]],
  ['Commercial', [['contracts', 'Contracts'], ['customers', 'Customers'], ['items', 'Items and prices']]],
  ['Reference', [['tax', 'Tax rules'], ['documents', 'Documents'], ['integration', 'API integration']]],
]

function paintNav(active) {
  document.getElementById('nav').innerHTML =
    `<a href="#/" class="${active === '' ? 'active' : ''}">Overview</a>` +
    NAV.map(([group, links]) =>
      `<div class="nav-group">${group}</div>` +
      links.map(([r, label]) => `<a href="#/${r}" class="${active === r ? 'active' : ''}">${label}</a>`).join('')
    ).join('')
}

async function route() {
  const raw = location.hash.replace(/^#\/?/, '')
  const [head, ...rest] = raw.split('/')
  const key = ROUTES[head] ? head : ''
  const arg = rest.length ? decodeURIComponent(rest.join('/')) : null
  paintNav(['draft', 'order', 'contract', 'po', 'delivery', 'customer'].includes(head)
    ? { draft: 'drafts', order: 'orders', contract: 'contracts', po: 'pos', delivery: 'deliveries', customer: 'customers' }[head]
    : key)
  view.innerHTML = '<div class="loading">Loading…</div>'
  try {
    await ROUTES[key](arg)
  } catch (e) {
    view.innerHTML = `<div class="card"><div class="body"><b>Could not load this record.</b>
      <p class="note">${esc(e.message)}. Check the reference in the address bar, or
      <a href="#/">return to the overview</a>.</p></div></div>`
  }
}

window.addEventListener('hashchange', route)
route()

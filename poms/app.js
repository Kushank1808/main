/* POMS — static client over ../api/poms and ../api/workday (to show linked invoices). */
const API = '../api'
const view = document.getElementById('view')
const cache = new Map()
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]))
const num = (n, dp = 2) => (n == null || n === '' ? '' : Number(n).toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp }))
const title = (s) => String(s ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
const pill = (t, k = '') => `<span class="pill ${k}">${esc(t)}</span>`
const wd = (i) => `<a href="../workday/index.html#/invoice/${encodeURIComponent(i)}" target="_blank" rel="noopener">${esc(i)} ↗</a>`
async function get(p, optional = false) {
  if (cache.has(p)) return cache.get(p)
  const r = await fetch(`${API}/${p}`, { cache: 'no-store' })
  if (!r.ok) { if (optional) return null; throw new Error(`${r.status} ${p}`) }
  const j = await r.json(); cache.set(p, j); return j
}
const card = (h, body, c = '') => `<div class="card"><h2>${h}${c ? `<span class="c">${c}</span>` : ''}</h2>${body}</div>`
const kv = (rows) => `<div class="kv">${rows.map(([l, v]) => `<div><label>${l}</label><div class="v">${v === '' || v == null ? '<span style="color:#b5b0a9">—</span>' : v}</div></div>`).join('')}</div>`
function table(cols, rows) {
  if (!rows.length) return '<div class="empty">Nothing to show.</div>'
  return `<div class="scroll"><table><thead><tr>${cols.map((c) => `<th class="${c.num ? 'num' : ''}">${c.label}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${cols.map((c) => `<td class="${c.num ? 'num' : ''}">${c.render ? c.render(r) : esc(r[c.key] ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`
}
const statusPill = (s) => pill(title(s), { HANDOVER_COMPLETED: 'ok', AWAITING_HANDOVER: 'warn', PAID: 'ok', ON_ACCOUNT: 'acc', FINANCED: '' }[s] || '')
const COLS = (byInv) => [
  { label: 'Order', key: 'order_number', render: (r) => `<a href="#/order/${r.order_number}">${esc(r.order_number)}</a>` },
  { label: 'Market', key: 'market' }, { label: 'Company', key: 'company' }, { label: 'Model', key: 'model' }, { label: 'MY', key: 'model_year' }, { label: 'Colour', key: 'exterior_colour' },
  { label: 'VIN', key: 'vin', render: (r) => `<span class="mono">${esc(r.vin)}</span>` },
  { label: 'Buyer', key: 'buyer_name' }, { label: 'Financing', key: 'financing_type', render: (r) => title(r.financing_type) }, { label: 'Financing partner', key: 'financing_partner' },
  { label: 'Plate', key: 'license_plate' }, { label: 'Status', key: 'order_status', render: (r) => statusPill(r.order_status) }, { label: 'Handover', key: 'handover_date' },
  { label: 'Base price', key: 'base_price', num: true, render: (r) => num(r.base_price) }, { label: 'Fees', key: 'f', num: true, render: (r) => num(r.fees.reduce((s, f) => s + f.amount, 0)) },
  { label: 'Gross taxable', key: 'gross_taxable_amount', num: true, render: (r) => num(r.gross_taxable_amount) }, { label: 'VAT', key: 'vat_amount', num: true, render: (r) => num(r.vat_amount) },
  { label: 'Total', key: 'total_price', num: true, render: (r) => `<b>${num(r.total_price)}</b>` }, { label: 'Ccy', key: 'currency' }, { label: 'Payment', key: 'payment_status', render: (r) => statusPill(r.payment_status) },
  { label: 'Workday invoices', key: 'w', render: (r) => r.workday_invoices.map((i) => `${wd(i)} ${byInv.get(i) ? pill(byInv.get(i).status, { PASS: 'ok', FAIL: 'bad', HOLD: 'warn' }[byInv.get(i).status]) : ''}`).join('<br>') },
]
let market = 'ALL'
async function list() {
  const [o, run] = await Promise.all([get('poms/orders.json'), get('validation-runs/latest.json', true)])
  const byInv = new Map((run?.results ?? []).map((r) => [r.invoice_number, r]))
  const rows = o.data.filter((r) => market === 'ALL' || r.company === market)
  const id = 'q' + Math.random().toString(36).slice(2, 6)
  setTimeout(() => {
    view.querySelectorAll('[data-m]').forEach((b) => b.addEventListener('click', () => { market = b.dataset.m; list() }))
    const i = document.getElementById(id); i.addEventListener('input', () => { const q = i.value.toLowerCase(); const hit = q ? rows.filter((r) => JSON.stringify(r).toLowerCase().includes(q)) : rows; document.getElementById(id + 't').innerHTML = table(COLS(byInv), hit); document.getElementById(id + 'c').textContent = `${hit.length} of ${rows.length} orders` })
  }, 0)
  view.innerHTML = `<div class="crumbs">POMS</div><h1>Vehicle orders</h1><p class="lead">The commercial truth an invoice must agree with: buyer, financing partner, VIN, licence plate, base price, fees and the total the customer agreed to. Workday invoices link back here.</p>
    <div class="tiles"><div class="tile"><div class="l">Orders</div><div class="v">${o.data.length}</div></div><div class="tile"><div class="l">Handover completed</div><div class="v">${o.data.filter((r) => r.order_status === 'HANDOVER_COMPLETED').length}</div></div><div class="tile"><div class="l">Leasing / loan financed</div><div class="v">${o.data.filter((r) => r.financing_partner).length}</div></div><div class="tile"><div class="l">On account payments</div><div class="v">${o.data.filter((r) => r.payment_status === 'ON_ACCOUNT').length}</div></div></div>
    <div class="toolbar"><input id="${id}" placeholder="Search order, VIN, buyer, plate…"><div class="seg">${['ALL', 'SE21', 'NO21', 'PT21', 'DK21'].map((m) => `<button data-m="${m}" class="${market === m ? 'on' : ''}">${m === 'ALL' ? 'All markets' : m}</button>`).join('')}</div><span class="count" id="${id}c">${rows.length} orders</span></div>
    ${card('Orders', `<div id="${id}t">${table(COLS(byInv), rows)}</div>`)}`
}
async function detail(n) {
  const [o, run] = await Promise.all([get(`poms/orders/${n}.json`).then((x) => x.data), get('validation-runs/latest.json', true)])
  const byInv = new Map((run?.results ?? []).map((r) => [r.invoice_number, r]))
  const price = `<div class="price"><span>${esc(o.model)} base price</span><span>${num(o.base_price)}</span>${o.paint_amount ? `<span>Exterior colour ${esc(o.exterior_colour)}</span><span>${num(o.paint_amount)}</span>` : `<span>Exterior colour ${esc(o.exterior_colour)}</span><span>0.00</span>`}
    ${o.options.map((x) => `<span>${esc(x.description)}</span><span>${num(x.amount)}</span>`).join('')}${o.fees.map((x) => `<span>${esc(x.description)} <span class="pill warn">fee</span></span><span>${num(x.amount)}</span>`).join('')}
    ${o.discount_amount ? `<span>Discount</span><span>(${num(o.discount_amount)})</span>` : ''}<span class="t">Gross taxable amount</span><span class="t">${num(o.gross_taxable_amount)}</span><span>VAT ${num(o.vat_rate, 0)}%</span><span>${num(o.vat_amount)}</span><span class="t">Total price</span><span class="t">${num(o.total_price)} ${esc(o.currency)}</span></div>`
  view.innerHTML = `<div class="crumbs"><a href="#/">POMS</a> › ${esc(o.order_number)}</div><h1>Order ${esc(o.order_number)}</h1><p class="lead">${esc(o.model)} · ${esc(o.buyer_name)} · ${esc(o.market)} · ${statusPill(o.order_status)}</p>
    ${card('Order', kv([['Order number', `<b>${esc(o.order_number)}</b>`], ['Market / company', `${esc(o.market)} · ${esc(o.company)}`], ['Model', `${esc(o.model)} (${esc(o.model_code)}) MY${o.model_year}`], ['Exterior colour', esc(o.exterior_colour)], ['VIN', `<span class="mono">${esc(o.vin)}</span>`], ['Licence plate', o.license_plate ? `<b>${esc(o.license_plate)}</b>` : ''],
      ['Buyer', `${esc(o.buyer_name)} <span class="mono">${esc(o.buyer_customer_id)}</span>`], ['Financing', title(o.financing_type)], ['Financing partner', o.financing_partner ? `${esc(o.financing_partner)} <span class="mono">${esc(o.financing_partner_id)}</span>` : ''],
      ['Order date', esc(o.order_date)], ['Handover date', esc(o.handover_date)], ['Payment status', statusPill(o.payment_status)], ['Last updated', esc(o.poms_last_updated)]]))}
    ${card('Price breakdown', price)}
    ${card('Workday invoices for this order', o.workday_invoices.length ? table([{ label: 'Invoice', key: 'i', render: (r) => wd(r) }, { label: 'Validation', key: 'v', render: (r) => (byInv.get(r) ? pill(byInv.get(r).status, { PASS: 'ok', FAIL: 'bad', HOLD: 'warn' }[byInv.get(r).status]) + ' ' + (byInv.get(r).rules_failed || []).join(', ') : pill('not run')) }], o.workday_invoices) : '<div class="empty">Not yet invoiced in Workday.</div>')}`
  window.scrollTo(0, 0)
}
async function route() {
  const [head, arg] = location.hash.replace(/^#\/?/, '').split('/')
  view.innerHTML = '<div class="loading">Loading…</div>'
  try { if (head === 'order' && arg) await detail(decodeURIComponent(arg)); else await list() } catch (e) { view.innerHTML = `<div class="card"><div class="empty"><b>Could not load.</b> ${esc(e.message)} — <a href="#/">back to orders</a></div></div>` }
}
window.addEventListener('hashchange', route); route()

/* ORBIS Insight — a single analytics sheet over the ORBIS JSON model.
   Selections at the top govern every object below, the way a Qlik sheet does. */
const API = '../api'
const FX = { USD: 1, EUR: 1.09 }        // everything is charted in USD equivalent
const board = document.getElementById('board')

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]))
const usd = (n) => n * 1
const num0 = (n) => Math.round(n).toLocaleString('en-US')
const compact = (n) =>
  Math.abs(n) >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : Math.abs(n) >= 1e3 ? `${(n / 1e3).toFixed(0)}K` : n.toFixed(0)
const title = (s) => String(s ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

const state = { ou: new Set(), cust: new Set(), status: new Set() }
let model = null

async function get(p) {
  const r = await fetch(`${API}/${p}`, { cache: 'no-store' })
  if (!r.ok) throw new Error(`${r.status} ${p}`)
  return r.json()
}

async function load() {
  const [orders, drafts, customers, deliveries] = await Promise.all([
    get('sales-orders.json'), get('billing-drafts.json'), get('customers.json'), get('deliveries.json'),
  ])
  const custName = Object.fromEntries(customers.data.map((c) => [c.customer_id, c.customer_name]))
  const podByOrder = Object.fromEntries(deliveries.data.map((d) => [d.sales_order, d.proof_of_delivery_date]))

  model = {
    orders: orders.data.map((o) => ({
      ...o,
      customer_name: custName[o.customer_id] ?? o.customer_id,
      value_usd: o.order_total * (FX[o.currency] ?? 1),
      week: weekOf(o.entered_date),
      pod: podByOrder[o.order_number] ?? null,
    })),
    drafts: drafts.data.map((d) => ({
      ...d,
      value_usd: d.total_payable * (FX[d.currency] ?? 1),
      goods_usd: d.goods_subtotal * (FX[d.currency] ?? 1),
      tax_usd: d.tax_amount * (FX[d.currency] ?? 1),
    })),
    ous: [...new Set(orders.data.map((o) => o.operating_unit))],
    custs: [...new Set(orders.data.map((o) => custName[o.customer_id] ?? o.customer_id))].sort(),
    statuses: [...new Set(orders.data.map((o) => o.status))].sort(),
  }
  document.getElementById('fxNote').textContent = 'Values in USD equivalent · EUR converted at 1.09'
  paintFilters()
  render()
}

function weekOf(iso) {
  const d = new Date(iso + 'T00:00:00Z')
  const day = (d.getUTCDay() + 6) % 7
  d.setUTCDate(d.getUTCDate() - day)
  return d.toISOString().slice(0, 10)
}

/* -------------------------------- filters --------------------------------- */
function chipRow(hostId, values, set, labelFn = (v) => v) {
  const host = document.getElementById(hostId)
  host.innerHTML = values
    .map((v) => `<button class="chip ${set.has(v) ? 'on' : ''}" data-v="${esc(v)}">${esc(labelFn(v))}</button>`)
    .join('')
  host.querySelectorAll('.chip').forEach((b) =>
    b.addEventListener('click', () => {
      const v = b.dataset.v
      set.has(v) ? set.delete(v) : set.add(v)
      paintFilters()
      render()
    })
  )
}

function paintFilters() {
  chipRow('fOu', model.ous, state.ou, (v) => (v.includes('USD') ? 'US Life Sciences (USD)' : 'EU Industrial (EUR)'))
  chipRow('fCust', model.custs, state.cust)
  chipRow('fStatus', model.statuses, state.status, title)
}

document.getElementById('clearSel').addEventListener('click', () => {
  state.ou.clear()
  state.cust.clear()
  state.status.clear()
  paintFilters()
  render()
})

function selectedOrders() {
  return model.orders.filter(
    (o) =>
      (!state.ou.size || state.ou.has(o.operating_unit)) &&
      (!state.cust.size || state.cust.has(o.customer_name)) &&
      (!state.status.size || state.status.has(o.status))
  )
}

/* --------------------------------- charts --------------------------------- */
function hBar(rows, colour = 'var(--a1)') {
  if (!rows.length) return '<div class="sub">No data in this selection.</div>'
  const max = Math.max(...rows.map((r) => r.value)) || 1
  const rowH = 26
  const h = rows.length * rowH + 6
  const labelW = 190
  return `<svg viewBox="0 0 700 ${h}" role="img">
    ${rows
      .map((r, i) => {
        const y = i * rowH
        const w = Math.max(2, (r.value / max) * (700 - labelW - 70))
        return `<text class="bar-label" x="0" y="${y + 15}">${esc(r.label.slice(0, 28))}</text>
          <rect x="${labelW}" y="${y + 4}" width="${w}" height="15" rx="2" fill="${colour}" opacity="0.85"></rect>
          <text class="val-label" x="${labelW + w + 8}" y="${y + 16}">${compact(r.value)}</text>`
      })
      .join('')}
  </svg>`
}

function lineChart(points) {
  if (points.length < 2) return '<div class="sub">Not enough periods in this selection.</div>'
  const w = 700
  const h = 210
  const pad = { l: 44, r: 12, t: 10, b: 26 }
  const max = Math.max(...points.map((p) => p.value)) * 1.12 || 1
  const x = (i) => pad.l + (i * (w - pad.l - pad.r)) / (points.length - 1)
  const y = (v) => h - pad.b - (v / max) * (h - pad.t - pad.b)
  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(' ')
  const area = `${path} L${x(points.length - 1).toFixed(1)},${h - pad.b} L${x(0).toFixed(1)},${h - pad.b} Z`
  const ticks = [0, 0.5, 1].map((f) => f * max)
  return `<svg viewBox="0 0 ${w} ${h}" role="img">
    ${ticks.map((t) => `<line class="grid-line" x1="${pad.l}" x2="${w - pad.r}" y1="${y(t)}" y2="${y(t)}"></line>
      <text class="axis" x="0" y="${y(t) + 3}">${compact(t)}</text>`).join('')}
    <path d="${area}" fill="var(--a1)" opacity="0.13"></path>
    <path d="${path}" fill="none" stroke="var(--a1)" stroke-width="2"></path>
    ${points.map((p, i) => `<circle cx="${x(i)}" cy="${y(p.value)}" r="3" fill="var(--a1)"></circle>`).join('')}
    ${points.map((p, i) =>
      i % Math.ceil(points.length / 6) === 0
        ? `<text class="axis" x="${x(i)}" y="${h - 8}" text-anchor="middle">${p.label.slice(5)}</text>`
        : ''
    ).join('')}
  </svg>`
}

function donut(slices) {
  const total = slices.reduce((s, x) => s + x.value, 0)
  if (!total) return '<div class="sub">No data in this selection.</div>'
  const r = 66
  const cx = 90
  const cy = 90
  let a0 = -Math.PI / 2
  const arcs = slices
    .filter((s) => s.value > 0)
    .map((s) => {
      const a1 = a0 + (s.value / total) * Math.PI * 2
      const large = a1 - a0 > Math.PI ? 1 : 0
      const p = `M${cx + r * Math.cos(a0)},${cy + r * Math.sin(a0)} A${r},${r} 0 ${large} 1 ${cx + r * Math.cos(a1)},${cy + r * Math.sin(a1)}`
      a0 = a1
      return `<path d="${p}" fill="none" stroke="${s.colour}" stroke-width="26"></path>`
    })
    .join('')
  return `<div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">
      <svg viewBox="0 0 180 180" style="width:180px;flex:0 0 180px">${arcs}
        <text x="90" y="86" text-anchor="middle" class="val-label" style="font-size:15px;font-weight:600">${compact(total)}</text>
        <text x="90" y="102" text-anchor="middle" class="axis">USD equiv.</text></svg>
      <div class="legend" style="flex-direction:column;gap:7px">
        ${slices.map((s) => `<span><i style="background:${s.colour}"></i>${esc(s.label)} — ${compact(s.value)}
          <span class="axis">(${total ? ((s.value / total) * 100).toFixed(1) : 0}%)</span></span>`).join('')}
      </div></div>`
}

/* --------------------------------- sheet ---------------------------------- */
function render() {
  const orders = selectedOrders()
  const keys = new Set(orders.map((o) => o.order_number))
  const drafts = model.drafts.filter((d) => keys.has(d.sales_order))

  const orderValue = orders.reduce((s, o) => s + o.value_usd, 0)
  const draftValue = drafts.reduce((s, d) => s + d.value_usd, 0)
  const held = orders.filter((o) => o.on_hold)
  const awaiting = orders.filter((o) => o.status === 'AWAITING_BILLING')
  const noPo = drafts.filter((d) => !d.customer_po_number).length
  const lag = orders
    .filter((o) => o.pod)
    .map((o) => (new Date(o.pod) - new Date(o.entered_date)) / 86400000)
  const avgLag = lag.length ? lag.reduce((a, b) => a + b, 0) / lag.length : 0

  const byCustomer = groupSum(orders, (o) => o.customer_name, (o) => o.value_usd).slice(0, 10)
  const byWeek = groupSum(orders, (o) => o.week, (o) => o.value_usd).sort((a, b) => a.label.localeCompare(b.label))
  const byTax = groupSum(drafts, (d) => title(d.tax_treatment), (d) => d.value_usd)
  const mix = [
    { label: 'Goods', value: sum(drafts, (d) => d.goods_usd), colour: 'var(--a1)' },
    { label: 'Tax', value: sum(drafts, (d) => d.tax_usd), colour: 'var(--a4)' },
    {
      label: 'Surcharge and freight',
      value: sum(drafts, (d) => d.value_usd - d.goods_usd - d.tax_usd),
      colour: 'var(--a2)',
    },
  ]

  board.innerHTML = `
    <div class="kpis">
      ${kpi('Orders in selection', orders.length, `${model.orders.length} in model`)}
      ${kpi('Order value', compact(orderValue), 'USD equivalent')}
      ${kpi('Awaiting billing', awaiting.length, 'shipped, not invoiced')}
      ${kpi('Draft value', compact(draftValue), `${drafts.length} drafts`, 'good')}
      ${kpi('Drafts without a PO', noPo, 'cannot be invoiced', noPo ? 'alert' : '')}
      ${kpi('Orders on hold', held.length, compact(sum(held, (o) => o.value_usd)) + ' blocked', held.length ? 'alert' : '')}
      ${kpi('Order to POD', avgLag.toFixed(1), 'average days')}
    </div>

    <div class="row two">
      ${viz('Order value by customer', 'Top 10 in the current selection', hBar(byCustomer))}
      ${viz('Order value by week entered', 'Week commencing', lineChart(byWeek))}
    </div>

    <div class="row two">
      ${viz('Draft value by tax treatment', 'What the billing desk intends to invoice', hBar(byTax, 'var(--a3)'))}
      ${viz('What makes up the drafts', 'Goods against tax and recoveries', donut(mix))}
    </div>

    ${viz('Billing drafts in this selection', 'Click through to the ERP for the full draft',
      `<div class="scroll"><table>
        <thead><tr><th>Draft</th><th>Order</th><th>Customer</th><th>PO</th><th>Invoice date</th>
        <th>Tax treatment</th><th class="num">Goods</th><th class="num">Tax</th><th class="num">Total payable</th><th>Ccy</th></tr></thead>
        <tbody>${drafts
          .map(
            (d) => `<tr>
            <td><a href="../erp/index.html#/draft/${encodeURIComponent(d.draft_number)}" style="color:var(--a1);text-decoration:none">${esc(d.draft_number)}</a></td>
            <td>${esc(d.sales_order)}</td><td>${esc(d.customer_name)}</td>
            <td>${d.customer_po_number ? esc(d.customer_po_number) : '<span class="tag" style="color:var(--bad);border-color:#5c2626">missing</span>'}</td>
            <td>${esc(d.invoice_date)}</td>
            <td><span class="tag ${d.tax_treatment === 'REVERSE_CHARGE' ? 'rc' : d.tax_treatment === 'EXEMPT' ? 'ex' : 'tx'}">${esc(title(d.tax_treatment))}</span></td>
            <td class="num">${num0(d.goods_subtotal)}</td><td class="num">${num0(d.tax_amount)}</td>
            <td class="num">${num0(d.total_payable)}</td><td>${esc(d.currency)}</td></tr>`
          )
          .join('') || '<tr><td colspan="10" style="color:var(--muted);padding:26px">No drafts in this selection.</td></tr>'}
        </tbody></table></div>`)}
  `
}

const sum = (rows, f) => rows.reduce((s, r) => s + f(r), 0)
function groupSum(rows, keyFn, valFn) {
  const m = new Map()
  rows.forEach((r) => m.set(keyFn(r), (m.get(keyFn(r)) ?? 0) + valFn(r)))
  return [...m.entries()].map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value)
}
const kpi = (l, v, s, tone = '') => `<div class="kpi ${tone}"><div class="l">${l}</div><div class="v">${v}</div><div class="s">${s}</div></div>`
const viz = (h, sub, body) => `<div class="viz"><h3>${h}</h3><div class="sub">${sub}</div>${body}</div>`

load().catch((e) => {
  board.innerHTML = `<div class="loading">Could not load the model: ${esc(e.message)}</div>`
})

// Chronicle — dashboard JavaScript
// All visualizations use raw Canvas 2D, zero dependencies.

const API = "";
const COLORS = {
  blue: "#58a6ff", green: "#3fb950", red: "#f85149",
  purple: "#bc8cff", orange: "#d29922", cyan: "#39d2c0",
  gray: "#8b949e", muted: "#6e7681",
};
const HEAT_COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"];

let state = {
  stats: null, authors: [], files: [], timeline: {}, heatmap: null,
  network: null, trend: {}, milestones: [], extensions: {},
  directories: {}, hourly: null,
};

// ============ Utility ============
async function fetchJSON(url) {
  const r = await fetch(url);
  return r.json();
}

function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = (canvas.dataset.height || 250) * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  return { ctx, w: rect.width, h: canvas.dataset.height || 250 };
}

function formatNum(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toString();
}

// ============ Tab switching ============
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
    // Re-render charts that need canvas sizing
    setTimeout(() => renderTabCharts(tab.dataset.tab), 50);
  });
});

function renderTabCharts(tab) {
  if (tab === "overview") { renderMonthlyChart(); renderHourlyChart(); renderExtensionsChart(); }
  if (tab === "heatmap") renderHeatmap();
  if (tab === "network") renderNetwork();
  if (tab === "files") { renderBubbles(); renderDirectories(); }
  if (tab === "trend") renderLOCChart();
}

// ============ Stats Overview ============
function renderStats() {
  const s = state.stats;
  if (!s || !s.summary) return;
  const p = s.summary;
  const grid = document.getElementById("stats-grid");
  const cards = [
    { label: "Commits", value: p.total_commits, cls: "blue" },
    { label: "Contributors", value: p.authors, cls: "purple" },
    { label: "Files Touched", value: p.files_touched, cls: "cyan" },
    { label: "Active Days", value: p.active_days, cls: "orange" },
    { label: "Additions", value: p.total_additions, cls: "green", fmt: true },
    { label: "Deletions", value: p.total_deletions, cls: "red", fmt: true },
    { label: "Net Lines", value: p.net_lines, cls: p.net_lines >= 0 ? "green" : "red", fmt: true },
    { label: "Avg/Commit", value: p.avg_lines_per_commit, cls: "" },
  ];
  grid.innerHTML = cards.map(c => `
    <div class="stat-card">
      <div class="stat-label">${c.label}</div>
      <div class="stat-value ${c.cls}">${c.fmt ? formatNum(c.value) : c.value}</div>
    </div>
  `).join("");
}

// ============ Bar Chart (monthly commits) ============
function renderMonthlyChart() {
  const canvas = document.getElementById("chart-monthly");
  if (!canvas) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const data = state.timeline.monthly || {};
  const entries = Object.entries(data).slice(-24);
  if (!entries.length) { ctx.fillStyle = "#6e7681"; ctx.fillText("No data", w/2-20, h/2); return; }

  const padL = 40, padR = 10, padT = 10, padB = 30;
  const cw = w - padL - padR, ch = h - padT - padB;
  const maxV = Math.max(...entries.map(e => e[1].commits), 1);
  const bw = cw / entries.length * 0.7;
  const gap = cw / entries.length * 0.3;

  // Grid
  ctx.strokeStyle = "#30363d"; ctx.lineWidth = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = padT + ch * i / 4;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
    ctx.fillStyle = "#8b949e"; ctx.font = "10px sans-serif"; ctx.textAlign = "right";
    ctx.fillText(Math.round(maxV * (1 - i/4)), padL - 5, y + 3);
  }

  // Bars
  entries.forEach(([label, d], i) => {
    const x = padL + i * (bw + gap) + gap / 2;
    const bh = (d.commits / maxV) * ch;
    const y = padT + ch - bh;
    const grad = ctx.createLinearGradient(x, y, x, padT + ch);
    grad.addColorStop(0, "#58a6ff"); grad.addColorStop(1, "#1f6feb");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(x, y, bw, bh, [2, 2, 0, 0]);
    ctx.fill();
    // X labels (every 3rd)
    if (i % 3 === 0 || i === entries.length - 1) {
      ctx.fillStyle = "#8b949e"; ctx.font = "9px sans-serif"; ctx.textAlign = "center";
      ctx.fillText(label.slice(2), x + bw/2, h - 10);
    }
  });
}

// ============ Hourly Distribution ============
function renderHourlyChart() {
  const canvas = document.getElementById("chart-hourly");
  if (!canvas || !state.hourly) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const data = state.hourly.hourly || {};
  const values = Array.from({length: 24}, (_, i) => data[i] || 0);
  const maxV = Math.max(...values, 1);

  const padL = 30, padR = 10, padT = 10, padB = 25;
  const cw = w - padL - padR, ch = h - padT - padB;

  // Area fill
  ctx.beginPath();
  ctx.moveTo(padL, padT + ch);
  values.forEach((v, i) => {
    const x = padL + (i / 23) * cw;
    const y = padT + ch - (v / maxV) * ch;
    if (i === 0) ctx.lineTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.lineTo(padL + cw, padT + ch);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, padT, 0, padT + ch);
  grad.addColorStop(0, "rgba(88,166,255,0.3)"); grad.addColorStop(1, "rgba(88,166,255,0.02)");
  ctx.fillStyle = grad; ctx.fill();

  // Line
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = padL + (i / 23) * cw;
    const y = padT + ch - (v / maxV) * ch;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#58a6ff"; ctx.lineWidth = 1.5; ctx.stroke();

  // X labels
  ctx.fillStyle = "#8b949e"; ctx.font = "9px sans-serif"; ctx.textAlign = "center";
  [0, 6, 12, 18, 23].forEach(h => {
    ctx.fillText(h + ":00", padL + (h / 23) * cw, h - 8);
  });
}

// ============ Extensions Donut ============
function renderExtensionsChart() {
  const canvas = document.getElementById("chart-extensions");
  if (!canvas) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const exts = state.extensions || {};
  const entries = Object.entries(exts).slice(0, 8);
  const total = entries.reduce((s, [, v]) => s + v.commits, 0);
  if (!total) return;

  const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 20, ir = r * 0.55;
  const palette = [COLORS.blue, COLORS.green, COLORS.purple, COLORS.orange, COLORS.cyan, COLORS.red, "#a371f7", "#f778ba"];
  let start = -Math.PI / 2;

  entries.forEach(([ext, v], i) => {
    const angle = (v.commits / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(cx, cy, r, start, start + angle);
    ctx.arc(cx, cy, ir, start + angle, start, true);
    ctx.closePath();
    ctx.fillStyle = palette[i % palette.length];
    ctx.fill();
    start += angle;
  });

  // Center text
  ctx.fillStyle = "#e6edf3"; ctx.font = "bold 18px sans-serif"; ctx.textAlign = "center";
  ctx.fillText(total, cx, cy - 2);
  ctx.fillStyle = "#8b949e"; ctx.font = "10px sans-serif";
  ctx.fillText("commits", cx, cy + 14);

  // Legend
  const legendX = 10, legendY = 10;
  entries.forEach(([ext, v], i) => {
    const ly = legendY + i * 16;
    ctx.fillStyle = palette[i % palette.length];
    ctx.fillRect(legendX, ly, 8, 8);
    ctx.fillStyle = "#8b949e"; ctx.font = "10px sans-serif"; ctx.textAlign = "left";
    ctx.fillText(`${ext} (${v.commits})`, legendX + 12, ly + 8);
  });
}

// ============ Heatmap ============
function renderHeatmap() {
  const canvas = document.getElementById("chart-heatmap");
  if (!canvas || !state.heatmap || !state.heatmap.weeks) return;
  const weeks = state.heatmap.weeks;
  const cellSize = 13, cellGap = 3;
  const cols = weeks.length;
  const rows = 7;
  const w = cols * (cellSize + cellGap) + 60;
  const h = rows * (cellSize + cellGap) + 40;
  canvas.style.height = h + "px";
  canvas.dataset.height = h;
  const { ctx } = setupCanvas(canvas);

  const offsetX = 50, offsetY = 20;
  // Day labels
  ctx.fillStyle = "#8b949e"; ctx.font = "9px sans-serif"; ctx.textAlign = "right";
  ["Mon", "Wed", "Fri"].forEach((d, i) => {
    ctx.fillText(d, offsetX - 5, offsetY + (i * 2 + 1) * (cellSize + cellGap) + cellSize);
  });

  weeks.forEach((week, wi) => {
    week.forEach((cell, di) => {
      const x = offsetX + wi * (cellSize + cellGap);
      const y = offsetY + di * (cellSize + cellGap);
      ctx.fillStyle = HEAT_COLORS[cell.level];
      ctx.beginPath();
      ctx.roundRect(x, y, cellSize, cellSize, 2);
      ctx.fill();
    });
    // Month labels
    if (wi % 4 === 0) {
      const firstDate = week[0].date;
      if (firstDate) {
        const month = firstDate.substring(5, 7);
        ctx.fillStyle = "#8b949e"; ctx.font = "9px sans-serif"; ctx.textAlign = "center";
        ctx.fillText(month, x + cellSize / 2, offsetY - 5);
      }
    }
  });
}

// ============ Force-Directed Network ============
let networkNodes = [], networkEdges = [], networkAnimId = null;

function initNetwork() {
  if (!state.network || !state.network.nodes) return;
  const canvas = document.getElementById("chart-network");
  const rect = canvas.getBoundingClientRect();
  const w = rect.width, h = 400;
  canvas.dataset.height = h;

  const nodes = state.network.nodes.map((n, i) => ({
    ...n,
    x: w / 2 + (Math.random() - 0.5) * 200,
    y: h / 2 + (Math.random() - 0.5) * 200,
    vx: 0, vy: 0,
    radius: Math.max(5, Math.min(25, Math.sqrt(n.commits) * 2)),
  }));
  const edges = state.network.edges.map(e => ({
    source: nodes.find(n => n.id === e.source),
    target: nodes.find(n => n.id === e.target),
    weight: e.weight,
  })).filter(e => e.source && e.target);

  networkNodes = nodes;
  networkEdges = edges;
}

function renderNetwork() {
  if (!state.network) return;
  if (networkNodes.length === 0) initNetwork();
  if (networkAnimId) cancelAnimationFrame(networkAnimId);

  const canvas = document.getElementById("chart-network");
  const { ctx, w, h } = setupCanvas(canvas);

  // Network info
  const info = document.getElementById("network-info");
  if (info && state.network) {
    info.innerHTML = `
      <div class="metric"><strong>${state.network.node_count}</strong> authors</div>
      <div class="metric"><strong>${state.network.edge_count}</strong> connections</div>
      <div class="metric"><strong>${state.clusters ? state.clusters.length : 0}</strong> clusters</div>
    `;
  }

  // Mouse drag
  let dragging = null;
  canvas.onmousedown = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    for (const n of networkNodes) {
      if (Math.hypot(n.x - mx, n.y - my) < n.radius + 5) { dragging = n; break; }
    }
  };
  canvas.onmousemove = (e) => {
    if (!dragging) return;
    const rect = canvas.getBoundingClientRect();
    dragging.x = e.clientX - rect.left;
    dragging.y = e.clientY - rect.top;
    dragging.vx = 0; dragging.vy = 0;
  };
  canvas.onmouseup = () => { dragging = null; };

  const palette = [COLORS.blue, COLORS.green, COLORS.purple, COLORS.orange, COLORS.cyan, COLORS.red];
  let iter = 0;

  function tick() {
    // Force simulation
    for (let step = 0; step < 2; step++) {
      // Repulsion
      for (let i = 0; i < networkNodes.length; i++) {
        for (let j = i + 1; j < networkNodes.length; j++) {
          const a = networkNodes[i], b = networkNodes[j];
          let dx = b.x - a.x, dy = b.y - a.y;
          let dist = Math.hypot(dx, dy) || 1;
          const force = 800 / (dist * dist);
          const fx = (dx / dist) * force, fy = (dy / dist) * force;
          a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
        }
      }
      // Attraction (edges)
      for (const e of networkEdges) {
        let dx = e.target.x - e.source.x, dy = e.target.y - e.source.y;
        let dist = Math.hypot(dx, dy) || 1;
        const force = (dist - 100) * 0.01 * Math.sqrt(e.weight);
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        e.source.vx += fx; e.source.vy += fy;
        e.target.vx -= fx; e.target.vy -= fy;
      }
      // Center gravity
      for (const n of networkNodes) {
        n.vx += (w / 2 - n.x) * 0.005;
        n.vy += (h / 2 - n.y) * 0.005;
      }
      // Apply
      for (const n of networkNodes) {
        if (n === dragging) continue;
        n.vx *= 0.85; n.vy *= 0.85;
        n.x += n.vx; n.y += n.vy;
        n.x = Math.max(n.radius, Math.min(w - n.radius, n.x));
        n.y = Math.max(n.radius, Math.min(h - n.radius, n.y));
      }
    }

    // Draw
    ctx.clearRect(0, 0, w, h);
    // Edges
    for (const e of networkEdges) {
      ctx.beginPath();
      ctx.moveTo(e.source.x, e.source.y);
      ctx.lineTo(e.target.x, e.target.y);
      ctx.strokeStyle = `rgba(88,166,255,${0.1 + Math.min(0.4, e.weight * 0.05)})`;
      ctx.lineWidth = Math.min(3, Math.sqrt(e.weight));
      ctx.stroke();
    }
    // Nodes
    networkNodes.forEach((n, i) => {
      const color = palette[i % palette.length];
      // Glow
      ctx.beginPath(); ctx.arc(n.x, n.y, n.radius + 4, 0, Math.PI * 2);
      ctx.fillStyle = color + "22"; ctx.fill();
      // Node
      ctx.beginPath(); ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fillStyle = color; ctx.fill();
      ctx.strokeStyle = "#0d1117"; ctx.lineWidth = 1.5; ctx.stroke();
      // Label
      if (n.radius > 8) {
        ctx.fillStyle = "#e6edf3"; ctx.font = "10px sans-serif"; ctx.textAlign = "center";
        const name = n.name.length > 12 ? n.name.slice(0, 10) + ".." : n.name;
        ctx.fillText(name, n.x, n.y + n.radius + 12);
      }
    });

    iter++;
    if (iter < 300) networkAnimId = requestAnimationFrame(tick);
  }
  tick();
}

// ============ Bubble Chart (files) ============
function renderBubbles() {
  const canvas = document.getElementById("chart-bubbles");
  if (!canvas) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const topFiles = state.files.slice(0, 30);
  if (!topFiles.length) return;

  // Simple packed bubbles
  const bubbles = topFiles.map((f, i) => ({
    ...f,
    radius: Math.max(4, Math.min(35, Math.sqrt(f.commits) * 4)),
    x: w / 2 + (Math.random() - 0.5) * (w - 80),
    y: h / 2 + (Math.random() - 0.5) * (h - 40),
  }));

  // Packing iterations
  for (let iter = 0; iter < 100; iter++) {
    for (let i = 0; i < bubbles.length; i++) {
      for (let j = i + 1; j < bubbles.length; j++) {
        const a = bubbles[i], b = bubbles[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        let dist = Math.hypot(dx, dy) || 1;
        const minDist = a.radius + b.radius + 2;
        if (dist < minDist) {
          const push = (minDist - dist) / 2;
          const fx = (dx / dist) * push, fy = (dy / dist) * push;
          a.x -= fx; a.y -= fy; b.x += fx; b.y += fy;
        }
      }
    }
    // Center
    for (const b of bubbles) {
      b.x += (w / 2 - b.x) * 0.02;
      b.y += (h / 2 - b.y) * 0.02;
      b.x = Math.max(b.radius, Math.min(w - b.radius, b.x));
      b.y = Math.max(b.radius, Math.min(h - b.radius, b.y));
    }
  }

  const palette = [COLORS.blue, COLORS.green, COLORS.purple, COLORS.orange, COLORS.cyan];
  bubbles.forEach((b, i) => {
    const color = palette[i % palette.length];
    ctx.beginPath(); ctx.arc(b.x, b.y, b.radius + 3, 0, Math.PI * 2);
    ctx.fillStyle = color + "18"; ctx.fill();
    ctx.beginPath(); ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
    ctx.fillStyle = color + "88"; ctx.fill();
    ctx.strokeStyle = color; ctx.lineWidth = 1; ctx.stroke();
    if (b.radius > 10) {
      ctx.fillStyle = "#e6edf3"; ctx.font = "9px sans-serif"; ctx.textAlign = "center";
      const name = b.path.split("/").pop();
      ctx.fillText(name.length > 10 ? name.slice(0, 8) + ".." : name, b.x, b.y + 3);
    }
  });
}

// ============ Directory Horizontal Bars ============
function renderDirectories() {
  const canvas = document.getElementById("chart-directories");
  if (!canvas) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const dirs = Object.entries(state.directories || {}).slice(0, 12);
  if (!dirs.length) return;

  const maxV = Math.max(...dirs.map(([, v]) => v.commits), 1);
  const barH = Math.min(20, (h - 20) / dirs.length - 4);
  const padL = 100;

  dirs.forEach(([name, v], i) => {
    const y = 10 + i * (barH + 6);
    const bw = ((v.commits / maxV) * (w - padL - 20));
    // Label
    ctx.fillStyle = "#8b949e"; ctx.font = "11px sans-serif"; ctx.textAlign = "right";
    const shortName = name.length > 14 ? name.slice(0, 12) + ".." : name;
    ctx.fillText(shortName, padL - 8, y + barH / 2 + 4);
    // Bar
    const grad = ctx.createLinearGradient(padL, y, padL + bw, y);
    grad.addColorStop(0, "#bc8cff"); grad.addColorStop(1, "#8957e5");
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.roundRect(padL, y, bw, barH, 3); ctx.fill();
    // Value
    ctx.fillStyle = "#e6edf3"; ctx.font = "10px sans-serif"; ctx.textAlign = "left";
    ctx.fillText(v.commits, padL + bw + 6, y + barH / 2 + 4);
  });
}

// ============ LOC Trend Line Chart ============
function renderLOCChart() {
  const canvas = document.getElementById("chart-loc");
  if (!canvas) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const data = state.trend || {};
  const entries = Object.entries(data);
  if (!entries.length) return;

  const padL = 60, padR = 20, padT = 20, padB = 40;
  const cw = w - padL - padR, ch = h - padT - padB;
  const locs = entries.map(([, v]) => v.estimated_loc);
  const minV = Math.min(...locs, 0);
  const maxV = Math.max(...locs, 1);
  const range = maxV - minV || 1;

  // Grid
  ctx.strokeStyle = "#30363d"; ctx.lineWidth = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = padT + ch * i / 4;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
    ctx.fillStyle = "#8b949e"; ctx.font = "10px sans-serif"; ctx.textAlign = "right";
    ctx.fillText(formatNum(maxV - range * i / 4), padL - 5, y + 3);
  }

  // Area
  ctx.beginPath();
  entries.forEach(([label, v], i) => {
    const x = padL + (i / Math.max(entries.length - 1, 1)) * cw;
    const y = padT + ch - ((v.estimated_loc - minV) / range) * ch;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  const lastX = padL + cw;
  ctx.lineTo(lastX, padT + ch); ctx.lineTo(padL, padT + ch); ctx.closePath();
  const grad = ctx.createLinearGradient(0, padT, 0, padT + ch);
  grad.addColorStop(0, "rgba(63,185,80,0.25)"); grad.addColorStop(1, "rgba(63,185,80,0.02)");
  ctx.fillStyle = grad; ctx.fill();

  // Line
  ctx.beginPath();
  entries.forEach(([label, v], i) => {
    const x = padL + (i / Math.max(entries.length - 1, 1)) * cw;
    const y = padT + ch - ((v.estimated_loc - minV) / range) * ch;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#3fb950"; ctx.lineWidth = 2; ctx.stroke();

  // X labels
  ctx.fillStyle = "#8b949e"; ctx.font = "9px sans-serif"; ctx.textAlign = "center";
  const step = Math.max(1, Math.floor(entries.length / 8));
  entries.forEach(([label], i) => {
    if (i % step === 0 || i === entries.length - 1) {
      const x = padL + (i / Math.max(entries.length - 1, 1)) * cw;
      ctx.save(); ctx.translate(x, h - 15); ctx.rotate(-0.5);
      ctx.fillText(label, 0, 0); ctx.restore();
    }
  });
}

// ============ Tables ============
function renderAuthorsTable(sortBy) {
  const tbody = document.querySelector("#authors-table tbody");
  if (!tbody) return;
  const sorted = [...state.authors].sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0));
  tbody.innerHTML = sorted.map((a, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${a.name}</strong><br><small style="color:#6e7681">${a.email}</small></td>
      <td>${a.commits}</td>
      <td class="additions">+${a.additions.toLocaleString()}</td>
      <td class="deletions">-${a.deletions.toLocaleString()}</td>
      <td class="${a.net_lines >= 0 ? 'net-pos' : 'net-neg'}">${a.net_lines >= 0 ? '+' : ''}${a.net_lines.toLocaleString()}</td>
      <td>${a.files_touched}</td>
      <td>${a.active_days}</td>
      <td style="font-size:11px">${(a.first_commit || '').slice(0, 10)}</td>
      <td style="font-size:11px">${(a.last_commit || '').slice(0, 10)}</td>
    </tr>
  `).join("");
}

function renderFilesTable() {
  const tbody = document.querySelector("#files-table tbody");
  if (!tbody) return;
  tbody.innerHTML = state.files.slice(0, 100).map((f, i) => `
    <tr>
      <td>${i + 1}</td>
      <td class="file-path" title="${f.path}">${f.path}</td>
      <td>${f.commits}</td>
      <td class="additions">+${f.additions.toLocaleString()}</td>
      <td class="deletions">-${f.deletions.toLocaleString()}</td>
      <td>${f.total_changes.toLocaleString()}</td>
      <td>${f.churn}</td>
      <td>${f.authors_count}</td>
    </tr>
  `).join("");
}

function renderTimelineTable(granularity) {
  const tbody = document.querySelector("#timeline-table tbody");
  if (!tbody) return;
  const data = state.timeline[granularity] || {};
  const entries = Object.entries(data).reverse();
  tbody.innerHTML = entries.map(([period, d]) => `
    <tr>
      <td><strong>${period}</strong></td>
      <td>${d.commits}</td>
      <td class="additions">+${d.additions.toLocaleString()}</td>
      <td class="deletions">-${d.deletions.toLocaleString()}</td>
      <td class="${d.net >= 0 ? 'net-pos' : 'net-neg'}">${d.net >= 0 ? '+' : ''}${d.net.toLocaleString()}</td>
      <td>${d.authors}</td>
      <td>${d.files}</td>
    </tr>
  `).join("");
}

function renderMilestonesTable() {
  const tbody = document.querySelector("#milestones-table tbody");
  if (!tbody) return;
  tbody.innerHTML = (state.milestones || []).slice(0, 50).map(m => `
    <tr>
      <td style="font-size:11px">${(m.date || '').slice(0, 10)}</td>
      <td><code>${m.sha}</code></td>
      <td>${m.author}</td>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis" title="${m.subject}">${m.subject}</td>
      <td class="additions">+${m.additions.toLocaleString()}</td>
      <td class="deletions">-${m.deletions.toLocaleString()}</td>
      <td>${m.files_changed}</td>
    </tr>
  `).join("");
}

function renderTopAuthorsList() {
  const container = document.getElementById("top-authors-list");
  if (!container) return;
  const maxCommits = Math.max(...state.authors.map(a => a.commits), 1);
  container.innerHTML = state.authors.slice(0, 10).map((a, i) => `
    <div class="list-item">
      <span class="list-rank">${i + 1}</span>
      <span class="list-name" title="${a.name} <${a.email}>">${a.name}</span>
      <div class="list-bar-container"><div class="list-bar" style="width:${(a.commits / maxCommits * 100)}%"></div></div>
      <span class="list-value">${a.commits}</span>
    </div>
  `).join("");
}

// ============ Data Loading ============
async function loadAllData() {
  try {
    const [stats, authors, files, timeline, heatmap, network, trend, milestones, extensions, directories, hourly] = await Promise.all([
      fetchJSON(API + "/api/stats"),
      fetchJSON(API + "/api/authors"),
      fetchJSON(API + "/api/files?limit=200"),
      fetchJSON(API + "/api/timeline?granularity=monthly"),
      fetchJSON(API + "/api/heatmap"),
      fetchJSON(API + "/api/network"),
      fetchJSON(API + "/api/trend"),
      fetchJSON(API + "/api/milestones"),
      fetchJSON(API + "/api/extensions"),
      fetchJSON(API + "/api/directories"),
      fetchJSON(API + "/api/hourly"),
    ]);
    state.stats = stats;
    state.authors = authors;
    state.files = files;
    state.timeline.monthly = timeline;
    state.heatmap = heatmap;
    state.network = network;
    state.trend = trend;
    state.milestones = milestones;
    state.extensions = extensions;
    state.directories = directories;
    state.hourly = hourly;
    if (network && network.clusters) state.clusters = network.clusters;

    renderStats();
    renderTopAuthorsList();
    renderMonthlyChart();
    renderHourlyChart();
    renderExtensionsChart();
    renderHeatmap();
    renderAuthorsTable("commits");
    renderFilesTable();
    renderTimelineTable("monthly");
    renderMilestonesTable();
    initNetwork();
  } catch (e) {
    console.error("Failed to load data:", e);
  }
}

// Event listeners
document.getElementById("btn-refresh")?.addEventListener("click", async () => {
  await fetchJSON(API + "/api/refresh");
  networkNodes = []; networkEdges = [];
  loadAllData();
});

document.getElementById("author-sort")?.addEventListener("change", (e) => {
  renderAuthorsTable(e.target.value);
});

document.getElementById("timeline-granularity")?.addEventListener("change", (e) => {
  renderTimelineTable(e.target.value);
});

document.querySelectorAll('input[name="heatmap-range"]').forEach(radio => {
  radio.addEventListener("change", () => renderHeatmap());
});

// Initial load
loadAllData();
window.addEventListener("resize", () => {
  renderTabCharts(document.querySelector(".tab.active").dataset.tab);
});

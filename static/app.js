/* =====================================================
   VOYARA — app.js (plain JS, no frameworks)
   - Same backend endpoints as before
   - No chatbot
   - Multi-step planner, animated map, registration extras,
     auto-login, day-wise budget cards, transport suggestions
   ===================================================== */

const API_BASE = "";

// Static curated list of major Indian cities for origin
const ORIGIN_CITIES = [
  "Pune",
  "Mumbai",
  "Delhi",
  "Bangalore",
  "Hyderabad",
  "Chennai",
  "Kolkata",
  "Ahmedabad",
  "Jaipur",
];

// Add your group names here — they show up automatically in About Us.
const CREDITS = ["Pratik", "Samiksha", "Manasi", "Chaitanya"]

// vibe → emoji mapping (used in chips & icons)
const VIBE_EMOJI = {
  adventure: "🪂",
  scenic: "🏞️",
  cultural: "🎭",
  historical: "🏛️",
  relaxed: "🌴",
  foodie: "🍜",
  nature: "🌿",
  spiritual: "🪷",
  urban: "🌆",
  offbeat: "🗺️",
};

// Words that replace boring "rest" labels
const REST_WORDS = [
  "Explore",
  "Discover",
  "Wander",
  "Recharge",
  "Relax",
  "Bond with locals",
  "People-watch",
  "Café break",
  "Slow stroll",
  "Sunset chase",
  "Local market run",
];

let state = {
  me: null,
  destinations: [],
  vibes: [],
  selectedVibes: [],
  tripId: null,
  itinerary: null,
  zoneDoodles: new Map(),
  budget: null,
  activeTab: "home",
  authMode: "login",
  step: 1,
  planContext: {
    from: "generated",
    destination_id: null,
    destination_name: null,
    start_date: null,
    end_date: null,
  },
};

const el = (id) => document.getElementById(id);

const show = (id, on) => {
  const n = el(id);
  if (n) n.style.display = on ? "block" : "none";
};

async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`);
  return data;
}

function setError(node, msg) {
  if (!node) return;
  if (!msg) {
    node.style.display = "none";
    node.textContent = "";
    return;
  }
  node.style.display = "block";
  node.textContent = msg;
}

function setStatus(node, html) {
  if (!node) return;
  if (!html) {
    node.style.display = "none";
    node.innerHTML = "";
    return;
  }
  node.style.display = "flex";
  node.innerHTML = html;
}

function toast(msg) {
  alert(msg);
}

function setTab(tab) {
  state.activeTab = tab;
  document
    .querySelectorAll(".tab")
    .forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  show("tab-home", tab === "home");
  show("tab-trips", tab === "trips");
  show("tab-about",tab === "about");
}

function monthNameFromDateStr(d) {
  if (!d) return "";
  const dt = new Date(d);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toLocaleString(undefined, { month: "long" });
}

const DEST_QUOTES = {
  1: "Strawberries, viewpoints, and main-character energy.",
  2: "Snow air, café walks, 'one more viewpoint' vibes.",
  3: "Salt hair, fort stories, sunsets that hit different.",
  5: "Backwaters, beach days, slow mornings with good food.",
};
const DEST_BADGE = {
  1: "Hill station",
  2: "Mountains",
  3: "Coast",
  5: "Backwaters",
};
const DEST_IMG = {
  1: "static/img/mahabaleshwar.jpg",
  2: "static/img/manali.jpg",
  3: "static/img/konkan.jpg",
  5: "static/img/kerala.jpg",
};

function topDestinations() {
  const wanted = [1, 2, 3, 5];
  const byId = new Map(
    state.destinations.map((d) => [Number(d.destination_id), d]),
  );
  const picked = wanted.map((id) => byId.get(id)).filter(Boolean);
  if (picked.length) return picked.slice(0, 4);
  return state.destinations.slice(0, 4);
}

function renderDestCards() {
  const wrap = el("dest-grid");
  if (!wrap) return;
  wrap.innerHTML = "";
  topDestinations().forEach((d, i) => {
    const id = Number(d.destination_id);
    const card = document.createElement("div");
    card.className = "dest-card";
    card.setAttribute("data-testid", `dest-card-${id}`);
    const img = DEST_IMG[id] || "";
    card.innerHTML = `
      <div class="dest-photo" ${img ? `style="background-image:url('${img}')"` : ""}></div>
      <div class="dest-overlay"></div>
      ${DEST_BADGE[id] ? `<div class="dest-badge">${DEST_BADGE[id]}</div>` : ""}
      <div class="dest-meta">
        <div class="dest-name">${d.name}</div>
        <div class="dest-quote">${DEST_QUOTES[id] || "A place you'll remember for a long time."}</div>
      </div>`;
    card.addEventListener("click", () => {
      openPlannerModal();
      const sel = el("destination");
      if (sel) sel.value = String(id);
      refreshTravelTerminalOptions();
    });
    wrap.appendChild(card);
  });
}

/* ============== TERMINALS / TRANSPORT ============== */

function terminalOptionsForDestination(destination_id, travel_mode) {
  const id = Number(destination_id);
  if (travel_mode === "car")
    return [{ id: "", label: "— driving in (no terminal) —" }];

  const flights = {
    1: [{ id: 102, label: "Pune Airport (PNQ) — nearest" }],
    2: [{ id: 103, label: "Bhuntar / Kullu Airport (KUU)" }],
    3: [{ id: 106, label: "Sindhudurg Airport (SDW)" }],
    5: [{ id: 107, label: "Cochin International Airport (COK)" }],
  };
  const trains = {
    1: [{ id: 101, label: "Wathar Station — closest to Mahabaleshwar" }],
    2: [{ id: 104, label: "Joginder Nagar Station (nearest)" }],
    3: [{ id: 105, label: "Ratnagiri Railway Station" }],
    5: [{ id: 108, label: "Ernakulam Junction (ERS)" }],
  };
  if (travel_mode === "flight")
    return flights[id] || [{ id: "", label: "— pick later —" }];
  if (travel_mode === "train")
    return trains[id] || [{ id: "", label: "— pick later —" }];
  return [{ id: "", label: "— pick later —" }];
}

function fillSelect(selectId, options, selectedVal) {
  const sel = el(selectId);
  if (!sel) return;
  sel.innerHTML = "";
  options.forEach((o) => {
    const opt = document.createElement("option");
    opt.value = String(o.id);
    opt.textContent = o.label;
    if (selectedVal !== undefined && String(o.id) === String(selectedVal))
      opt.selected = true;
    sel.appendChild(opt);
  });
}

function refreshTravelTerminalOptions() {
  const destSel = el("destination");
  const modeSel = el("travel_mode");
  if (!destSel || !modeSel) return;
  const opts = terminalOptionsForDestination(
    Number(destSel.value),
    modeSel.value,
  );
  fillSelect("arrival_terminal_id", opts);
  fillSelect("departure_terminal_id", opts);
}

function transportSuggestionsFor(destination_id, origin_city, travel_mode) {
  const id = Number(destination_id);
  const base = {
    1: {
      air: ["Pune Airport (PNQ)"],
      rail: ["Wathar Station"],
      road: ["Mumbai-Pune Expy → NH965"],
    },
    2: {
      air: ["Bhuntar / Kullu Airport (KUU)"],
      rail: ["Joginder Nagar"],
      road: ["Chandigarh → NH3"],
    },
    3: {
      air: ["Sindhudurg Airport (SDW)"],
      rail: ["Ratnagiri / Kankavli"],
      road: ["NH66 coastal drive"],
    },
    5: {
      air: ["Cochin International (COK)", "Trivandrum (TRV)"],
      rail: ["Ernakulam Jn (ERS)", "Trivandrum Central"],
      road: ["NH66 → state highways"],
    },
  }[id] || { air: [], rail: [], road: [] };

  const out = [];
  if (travel_mode === "flight" || travel_mode === "car") {
    base.air.forEach((a, i) => {
      out.push({
        kind: "flight",
        title: `${origin_city || "Your city"} → ${a}`,
        sub: `Indigo / Vistara · 2 stops max · ${["non-stop", "1 stop", "fastest"][i % 3]}`,
        price: `₹${4500 + i * 700}–${6800 + i * 900} pp`,
        href: "#",
      });
    });
  }
  if (travel_mode === "train" || travel_mode === "car") {
    base.rail.forEach((r, i) => {
      out.push({
        kind: "train",
        title: `${origin_city || "Your city"} → ${r}`,
        sub: `IRCTC · ${["sleeper / 3A", "2A / 3A", "Tatkal available"][i % 3]} · overnight`,
        price: `₹${850 + i * 300}–${1800 + i * 350} pp`,
        href: "#",
      });
    });
  }
  if (travel_mode === "car") {
    base.road.forEach((r) => {
      out.push({
        kind: "road",
        title: `Drive: ${origin_city || "Your city"} → ${r}`,
        sub: "Self-drive · stops on the way · pet-friendly",
        price: "₹3000–₹5500 fuel",
        href: "#",
      });
    });
  }
  return out.slice(0, 6);
}

function transportIcon(kind) {
  if (kind === "flight")
    return `<svg viewBox="0 0 24 24" fill="none"><path d="M2 16l20-7-9 13-2-6-6-2-3-2z" stroke="#e76f51" stroke-width="2" stroke-linejoin="round"/></svg>`;
  if (kind === "train")
    return `<svg viewBox="0 0 24 24" fill="none"><rect x="5" y="3" width="14" height="14" rx="3" stroke="#2a9d8f" stroke-width="2"/><circle cx="9" cy="13" r="1.4" fill="#2a9d8f"/><circle cx="15" cy="13" r="1.4" fill="#2a9d8f"/><path d="M7 17l-2 4M17 17l2 4" stroke="#2a9d8f" stroke-width="2" stroke-linecap="round"/></svg>`;
  return `<svg viewBox="0 0 24 24" fill="none"><path d="M3 13l2-5a3 3 0 0 1 3-2h8a3 3 0 0 1 3 2l2 5v5h-3v-2H6v2H3z" stroke="#264653" stroke-width="2" stroke-linejoin="round"/><circle cx="7.5" cy="16.5" r="1.5" fill="#264653"/><circle cx="16.5" cy="16.5" r="1.5" fill="#264653"/></svg>`;
}

function renderTransport() {
  const card = el("transport-card");
  const wrap = el("transport-suggestions");
  if (!wrap || !card) return;
  const dest =
    state.planContext.destination_id ||
    state.destinations.find((d) => d.name === state.itinerary?.destination)
      ?.destination_id;
  const origin =
    state.planContext.origin_city || el("origin_city")?.value || "";
  const mode =
    state.planContext.travel_mode || el("travel_mode")?.value || "car";
  const sugg = transportSuggestionsFor(dest, origin, mode);
  if (!sugg.length) {
    card.style.display = "none";
    return;
  }
  card.style.display = "";
  wrap.innerHTML = sugg
    .map(
      (s) => `
    <a class="transport-pill" href="${s.href}" target="_blank" rel="noreferrer" data-testid="transport-pill-${s.kind}">
      <span class="ic">${transportIcon(s.kind)}</span>
      <span class="meta">
        <b>${s.title}</b>
        <span>${s.sub}</span>
        <span class="price">${s.price}</span>
      </span>
    </a>`,
    )
    .join("");
}

/* ============== MAP ============== */

const DAY_COLORS = ["#e76f51", "#2a9d8f", "#f4a261", "#5b4872", "#3a7ca5"];

function schematicMapSvg(destination_id) {
  const id = Number(destination_id);
  const wrap = (zones, name) => {
    return `
      <svg id="voyara-map" viewBox="0 0 540 300" width="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(38,70,83,.06)" stroke-width="1"/>
          </pattern>
        </defs>
        <rect x="6" y="6" width="528" height="288" rx="22" fill="#fff5e3" stroke="rgba(38,70,83,.12)"/>
        <rect x="6" y="6" width="528" height="288" rx="22" fill="url(#grid)"/>
        <text x="20" y="32" fill="rgba(38,70,83,.55)" font-size="11" font-weight="700" letter-spacing="2">${name.toUpperCase()}</text>
        ${zones}
        <path id="route-path" class="route-line" d="" />
        <circle id="route-marker" class="move-marker" cx="-100" cy="-100" r="9" />
      </svg>`;
  };
  if (id === 1)
    return wrap(
      `
    <g><path id="zone-3" class="zone-shape" d="M70 200 Q120 150 200 170 Q190 245 110 250 Q75 235 70 200Z"/><text class="zone-label" x="118" y="208">Venna</text><circle id="zc-3" cx="135" cy="210" r="4" fill="#264653"/></g>
    <g><path id="zone-1" class="zone-shape" d="M210 180 Q260 140 320 170 Q325 240 270 250 Q220 240 210 180Z"/><text class="zone-label" x="248" y="208">Town</text><circle id="zc-1" cx="265" cy="210" r="4" fill="#264653"/></g>
    <g><path id="zone-2" class="zone-shape" d="M220 95 Q275 60 335 90 Q340 145 290 155 Q235 145 220 95Z"/><text class="zone-label" x="262" y="120">Panchgani</text><circle id="zc-2" cx="280" cy="120" r="4" fill="#264653"/></g>
    <g><path id="zone-4" class="zone-shape" d="M340 175 Q395 115 470 150 Q485 230 410 250 Q355 230 340 175Z"/><text class="zone-label" x="384" y="200">Ridge</text><circle id="zc-4" cx="405" cy="200" r="4" fill="#264653"/></g>
  `,
      "Mahabaleshwar",
    );
  if (id === 2)
    return wrap(
      `
    <g><path id="zone-5" class="zone-shape" d="M70 195 Q120 155 180 175 Q175 245 120 250 Q78 240 70 195Z"/><text class="zone-label" x="100" y="210">Town</text><circle id="zc-5" cx="125" cy="210" r="4" fill="#264653"/></g>
    <g><path id="zone-8" class="zone-shape" d="M175 155 Q210 125 260 140 Q265 195 225 210 Q185 198 175 155Z"/><text class="zone-label" x="194" y="170">Old</text><circle id="zc-8" cx="220" cy="170" r="4" fill="#264653"/></g>
    <g><path id="zone-6" class="zone-shape" d="M250 110 Q300 80 350 105 Q360 160 315 175 Q265 160 250 110Z"/><text class="zone-label" x="276" y="130">Solang</text><circle id="zc-6" cx="305" cy="130" r="4" fill="#264653"/></g>
    <g><path id="zone-7" class="zone-shape" d="M360 85 Q420 55 470 95 Q485 145 430 165 Q370 150 360 85Z"/><text class="zone-label" x="396" y="110">Rohtang</text><circle id="zc-7" cx="420" cy="115" r="4" fill="#264653"/></g>
  `,
      "Manali",
    );
  if (id === 3)
    return wrap(
      `
    <path d="M115 60 C140 110, 130 180, 145 235" fill="none" stroke="rgba(58,124,165,.35)" stroke-width="14" stroke-linecap="round"/>
    <g><path id="zone-9" class="zone-shape" d="M155 185 Q190 145 245 170 Q245 235 190 250 Q160 235 155 185Z"/><text class="zone-label" x="174" y="200">Tarkarli</text><circle id="zc-9" cx="200" cy="205" r="4" fill="#264653"/></g>
    <g><path id="zone-10" class="zone-shape" d="M240 140 Q290 110 340 140 Q345 195 300 210 Q250 195 240 140Z"/><text class="zone-label" x="263" y="160">Fort</text><circle id="zc-10" cx="290" cy="170" r="4" fill="#264653"/></g>
    <g><path id="zone-11" class="zone-shape" d="M270 215 Q325 180 380 205 Q385 260 325 270 Q275 260 270 215Z"/><text class="zone-label" x="290" y="230">Ganpatipule</text><circle id="zc-11" cx="325" cy="235" r="4" fill="#264653"/></g>
    <g><path id="zone-12" class="zone-shape" d="M320 105 Q370 70 420 100 Q428 150 385 165 Q338 150 320 105Z"/><text class="zone-label" x="345" y="125">Ratnagiri</text><circle id="zc-12" cx="378" cy="130" r="4" fill="#264653"/></g>
  `,
      "Konkan Coast",
    );
  if (id === 5)
    return wrap(
      `
    <path d="M105 50 C115 110, 105 170, 120 235" fill="none" stroke="rgba(42,157,143,.35)" stroke-width="14" stroke-linecap="round"/>
    <g><path id="zone-17" class="zone-shape" d="M150 185 Q195 145 250 170 Q253 235 195 250 Q155 235 150 185Z"/><text class="zone-label" x="166" y="205">Alleppey</text><circle id="zc-17" cx="195" cy="210" r="4" fill="#264653"/></g>
    <g><path id="zone-18" class="zone-shape" d="M255 110 Q315 75 370 105 Q377 160 325 175 Q270 160 255 110Z"/><text class="zone-label" x="285" y="132">Munnar</text><circle id="zc-18" cx="320" cy="135" r="4" fill="#264653"/></g>
    <g><path id="zone-19" class="zone-shape" d="M265 195 Q325 160 385 185 Q390 250 325 260 Q270 250 265 195Z"/><text class="zone-label" x="290" y="215">Thekkady</text><circle id="zc-19" cx="325" cy="220" r="4" fill="#264653"/></g>
    <g><path id="zone-20" class="zone-shape" d="M395 170 Q435 135 475 160 Q495 215 445 240 Q400 225 395 170Z"/><text class="zone-label" x="412" y="196">Kovalam</text><circle id="zc-20" cx="442" cy="200" r="4" fill="#264653"/></g>
  `,
      "Kerala",
    );
  return `<svg viewBox="0 0 520 280" width="100%"><rect x="6" y="6" width="508" height="268" rx="22" fill="#fff5e3" stroke="rgba(38,70,83,.12)"/><text x="20" y="40" fill="#6f6253" font-size="14">Map not set for this destination yet</text></svg>`;
}

function highlightMapZones(destination_id, days) {
  const mapWrap = el("dest-map");
  if (!mapWrap) return;
  mapWrap.innerHTML = schematicMapSvg(destination_id);

  const legend = el("legend");
  if (legend) legend.innerHTML = "";

  const ordered = (days || [])
    .slice()
    .sort((a, b) => a.day_number - b.day_number);
  const points = [];

  ordered.forEach((dz, idx) => {
    const color = DAY_COLORS[idx % DAY_COLORS.length];
    const shape = mapWrap.querySelector(`#zone-${dz.zone_id}`);
    if (shape) {
      shape.setAttribute("fill", hexAlpha(color, 0.18));
      shape.setAttribute("stroke", color);
      shape.setAttribute("stroke-width", "3");
      shape.style.color = color;
      shape.style.opacity = "0.25"; // dim until lit by animation
    }
    const center = mapWrap.querySelector(`#zc-${dz.zone_id}`);
    if (center)
      points.push({
        shape,
        x: parseFloat(center.getAttribute("cx")),
        y: parseFloat(center.getAttribute("cy")),
        color,
        day: dz.day_number,
        name: dz.zone_name,
      });

    if (legend) {
      const leg = document.createElement("div");
      leg.className = "leg";
      leg.innerHTML = `<span class="dot" style="background:${color}"></span> Day ${dz.day_number}: ${dz.zone_name || "Zone " + dz.zone_id}`;
      legend.appendChild(leg);
    }
  });

  animateRoute(points);
}

function hexAlpha(hex, a) {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function animateRoute(points) {
  const map = el("dest-map")?.querySelector("svg");
  if (!map || points.length === 0) return;
  const path = map.querySelector("#route-path");
  const marker = map.querySelector("#route-marker");
  if (!path || !marker) return;

  // build path d
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const p1 = points[i - 1],
      p2 = points[i];
    const cx = (p1.x + p2.x) / 2;
    const cy = Math.min(p1.y, p2.y) - 30;
    d += ` Q ${cx} ${cy}, ${p2.x} ${p2.y}`;
  }
  path.setAttribute("d", d);
  path.classList.add("draw");

  // step through points sequentially (light each zone), then move marker along
  const totalMs = 4500;
  const perStep = totalMs / points.length;

  // reset state
  points.forEach((p) => {
    if (p.shape) p.shape.style.opacity = "0.25";
  });
  marker.setAttribute("cx", points[0].x);
  marker.setAttribute("cy", points[0].y);
  marker.style.opacity = "0";

  let i = 0;
  marker.style.opacity = "1";
  const lightNext = () => {
    if (i >= points.length) return;
    const p = points[i];
    if (p.shape) {
      p.shape.style.transition = "opacity .5s ease, fill .5s ease";
      p.shape.style.opacity = "1";
      p.shape.classList.add("lit");
    }
    marker.setAttribute("fill", "#fff");
    marker.setAttribute("stroke", p.color);
    // animate marker move
    if (i > 0) {
      const prev = points[i - 1];
      animateMarker(marker, prev.x, prev.y, p.x, p.y, perStep * 0.7);
    } else {
      marker.setAttribute("cx", p.x);
      marker.setAttribute("cy", p.y);
    }
    i++;
    setTimeout(lightNext, perStep);
  };
  lightNext();
}

function animateMarker(marker, x1, y1, x2, y2, dur) {
  const start = performance.now();
  function frame(t) {
    const k = Math.min(1, (t - start) / dur);
    const ease = 1 - Math.pow(1 - k, 3);
    marker.setAttribute("cx", x1 + (x2 - x1) * ease);
    marker.setAttribute(
      "cy",
      y1 + (y2 - y1) * ease - 18 * Math.sin(Math.PI * ease),
    ); // slight arc
    if (k < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* ============== DAYS / ITINERARY ============== */

function timeToMins(s) {
  if (!s) return 0;
  const m = String(s)
    .trim()
    .match(/^(\d+):(\d+)\s*(AM|PM)$/i);
  if (!m) return 0;
  let h = parseInt(m[1], 10);
  const mins = parseInt(m[2], 10);
  const p = m[3].toUpperCase();
  if (p === "PM" && h !== 12) h += 12;
  if (p === "AM" && h === 12) h = 0;
  return h * 60 + mins;
}
function normalizeTime(t) {
  if (!t) return t;
  if (String(t).length === 5) return String(t) + ":00";
  return t;
}

function slotIcon(type) {
  switch ((type || "").toLowerCase()) {
    case "attraction":
      return `<svg viewBox="0 0 24 24" fill="none"><path d="M12 2l2.6 6.5L22 9.6l-5.5 4.7L18 22l-6-3.5L6 22l1.5-7.7L2 9.6l7.4-1.1L12 2z" fill="currentColor"/></svg>`;
    case "meal":
      return `<svg viewBox="0 0 24 24" fill="none"><path d="M7 3v8a3 3 0 0 0 3 3v7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M7 3v6M11 3v6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M17 3c2 1 3 4 3 8s-3 4-3 4v7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    case "travel":
      return `<svg viewBox="0 0 24 24" fill="none"><path d="M3 17l4-4-4-4M21 7l-4 4 4 4M7 13h10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    case "sleep":
      return `<svg viewBox="0 0 24 24" fill="none"><path d="M21 13.5A9 9 0 0 1 10.5 3a7 7 0 1 0 10.5 10.5z" fill="currentColor"/></svg>`;
    case "rest":
    default:
      return `<svg viewBox="0 0 24 24" fill="none"><path d="M5 12c0-4 3-7 7-7s7 3 7 7-3 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M12 8v4l3 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`;
  }
}

function restWord(seedKey) {
  // deterministic-ish pick using seed so same slot keeps same word
  let h = 0;
  for (let i = 0; i < seedKey.length; i++)
    h = (h * 31 + seedKey.charCodeAt(i)) | 0;
  return REST_WORDS[Math.abs(h) % REST_WORDS.length];
}

function renderDays() {
  const wrap = el("days");
  wrap.innerHTML = "";
  const itin = state.itinerary;
  if (!itin || !itin.days) {
    wrap.innerHTML = "<div class='muted'>Generate an itinerary first.</div>";
    return;
  }
  const days = itin.days.slice().sort((a, b) => a.day_number - b.day_number);

  for (const day of days) {
    const budgetDay = state.budget?.days?.find(
      (d) => d.day_number === day.day_number,
    );
    const card = document.createElement("div");
    card.className = "day-card";
    card.setAttribute("data-testid", `day-card-${day.day_number}`);

    const totalText = budgetDay ? `₹${budgetDay.total}` : "—";
    const cats = budgetDay ? Object.entries(budgetDay.categories) : [];
    const breakdown = cats.length
      ? cats.map(([k, v]) => `<span class="bcat">${k}: ₹${v}</span>`).join("")
      : "";

    const items = (day.schedule || [])
      .slice()
      .sort((a, b) => timeToMins(a.start_time) - timeToMins(b.start_time));
    const tlRows = items
      .map((item, idx) => {
        const type = (item.slot_type || "block").toLowerCase();
        let labelName = item.attraction || item.notes || type;
        let typeLabel = type;
        if (type === "rest") {
          const word = restWord(`${day.day_number}-${idx}-${item.start_time}`);
          labelName = word;
          typeLabel = "free time";
        }
        const meal = item.meal_type ? ` · ${item.meal_type}` : "";
        return `
        <div class="tl-row">
          <div class="tl-icon ${type}">${slotIcon(type)}</div>
          <div class="tl-meta">
            <div class="tl-time">${item.start_time} → ${item.end_time}</div>
            <div class="tl-type">${typeLabel}${meal}</div>
            <div class="tl-name">${labelName}</div>
            ${item.notes && item.notes !== labelName ? `<div class="tl-notes">${item.notes}</div>` : ""}
          </div>
        </div>`;
      })
      .join("");

    card.innerHTML = `
      <div class="day-head">
        <div>
          <div class="day-title">Day ${day.day_number}</div>
          <span class="day-zone">📍 ${day.zone_name || ""}</span>
        </div>
      </div>
      <div class="day-budget-card" data-testid="day-budget-${day.day_number}">
        <div>
          <div class="lbl">Day ${day.day_number} budget</div>
          <div class="val">${totalText}</div>
        </div>
        <div class="muted small">spent across food, stay, travel & extras</div>
        ${breakdown ? `<div class="breakdown">${breakdown}</div>` : ""}
      </div>
      <div class="timeline">${tlRows}</div>
    `;
    wrap.appendChild(card);
  }
}

/* ============== TRIPS LIST ============== */

function renderSavedTrips(trips) {
  const wrap = el("mytrips-grid");
  if (!wrap) return;
  wrap.innerHTML = "";
  if (!trips || !trips.length) {
    wrap.innerHTML =
      "<div class='muted' style='padding:14px;'>No saved trips yet. Save a plan and it'll show up here.</div>";
    return;
  }
  trips.forEach((t, i) => {
    const id = Number(t.destination_id);
    const card = document.createElement("div");
    card.className = "trip-card";
    card.setAttribute("data-testid", `trip-card-${t.trip_id}`);
    const img = DEST_IMG[id] || "";
    card.innerHTML = `
      <div class="dest-photo" ${img ? `style="background-image:url('${img}')"` : ""}>
        <div class="dest-overlay"></div>
        ${DEST_BADGE[id] ? `<div class="dest-badge">${DEST_BADGE[id]}</div>` : ""}
      </div>
      <div class="inner">
        <div class="title">${t.destination_name}</div>
        <div class="sub">${t.start_date} → ${t.end_date}</div>
        <div class="sub hand">"${DEST_QUOTES[id] || "you saved this for a reason"}"</div>
        <div class="actions"><button class="btn pop secondary" data-testid="trip-open-${t.trip_id}">Open</button></div>
      </div>`;
    card
      .querySelector("button")
      .addEventListener("click", () => openTrip(t.trip_id, true, "saved"));
    wrap.appendChild(card);
  });
}

/* ============== VIBES ============== */

function pickVibeChips() {
  const wrap = el("vibes-wrap");
   if (!wrap) return; 
  wrap.innerHTML = "";

  state.vibes.forEach((v) => {
    const chip = document.createElement("div");
    chip.className =
      "vibe-chip" + (state.selectedVibes.includes(v) ? " on" : "");
    chip.setAttribute("data-testid", `vibe-chip-${v}`);
    chip.innerHTML = `<span class="v-emoji">${VIBE_EMOJI[v] || "✨"}</span><span>${v}</span>`;
    chip.addEventListener("click", () => {
      const sel = new Set(state.selectedVibes);
      if (sel.has(v)) sel.delete(v);
      else {
        if (sel.size >= 4) return;
        sel.add(v);
      }
      state.selectedVibes = Array.from(sel);
      pickVibeChips();
    });
    wrap.appendChild(chip);
  });
}

/* ============== ORIGIN CITIES & CREDITS ============== */

function fillOriginCityDropdown() {
  const sel = el("origin_city");
  if (!sel) return;
  sel.innerHTML = "";
  ORIGIN_CITIES.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    sel.appendChild(opt);
  });
  // user's own registered city, if available
  const own =
    (state.me && state.me.profile && state.me.profile.city) ||
    localStorage.getItem("voyara.city");
  if (own) {
    if (!ORIGIN_CITIES.includes(own)) {
      const opt = document.createElement("option");
      opt.value = own;
      opt.textContent = `${own} (yours)`;
      sel.prepend(opt);
    } else {
      sel.value = own;
    }
  }

  // also fill datalist for register form
  const dl = el("city-list");
  if (dl) {
    dl.innerHTML = "";
    ORIGIN_CITIES.forEach((c) => {
      const o = document.createElement("option");
      o.value = c;
      dl.appendChild(o);
    });
  }
}

function renderCredits() {
  const row = el("credits-row");
  if (!row) return;
  row.innerHTML = CREDITS.map(
    (c) => `<span class="credit-chip">${c}</span>`,
  ).join("");
}

/* ============== LOAD DATA ============== */

async function loadDestinations() {
  const data = await api("/api/destinations");
  state.destinations = data.destinations || [];
  const sel = el("destination");
  if (!sel) return;
  sel.innerHTML = "";
  state.destinations.forEach((d) => {
    const opt = document.createElement("option");
    opt.value = d.destination_id;
    opt.textContent = d.name;
    sel.appendChild(opt);
  });
  renderDestCards();
  refreshTravelTerminalOptions();
}

async function loadVibes() {
  const data = await api("/api/vibes");
  state.vibes = data.vibes || [];
  pickVibeChips();
}

async function refreshMe() {
  let data = null;
  try {
    data = await api("/api/auth/me");
  } catch (_) {
    data = null;
  }
  state.me = data && data.user_id ? data : null;
  if (el("me-pill")) el("me-pill").textContent = state.me ? state.me.email : "";

  if (!state.me) {
    show("auth-page", true);
    show("app-shell", false);
    return;
  }
  show("auth-page", false);
  show("app-shell", true);
  setTab("home");
  fillOriginCityDropdown();
  renderCredits();
  await Promise.all([loadDestinations(), loadVibes(), refreshSavedTrips()]);
}

async function refreshSavedTrips() {
  try {
    const data = await api("/api/me/trips");
    renderSavedTrips(data.trips || []);
  } catch (_) {
    renderSavedTrips([]);
  }
}

/* ============== AUTH ============== */

function setAuthMode(mode) {
  state.authMode = mode;
  document
    .querySelectorAll(".auth-tab")
    .forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
  show("register-extras", mode === "register");
  el("primary-auth-btn").textContent =
    mode === "register" ? "Create my account" : "Log in";
  el("auth-title").textContent =
    mode === "register" ? "Let's get you started." : "Welcome back, traveller.";
  el("auth-sub").innerHTML =
    mode === "register"
      ? "Tell us a little about you — we use this to personalise origin cities and trip cards."
      : "Try demo: <b>test@example.com</b> + <b>password</b>";
  setError(el("auth-error"), "");
  setStatus(el("auth-status"), "");
}

async function doAuth() {
  const email = el("email").value.trim();
  const password = el("password").value;
  const node = el("auth-error");
  const status = el("auth-status");
  setError(node, "");

  if (!email || !password) {
    setError(node, "Email & password are needed.");
    return;
  }

  if (state.authMode === "register") {
    const name = el("reg-name").value.trim();
    const username = el("reg-username").value.trim();
    const age = parseInt(el("reg-age").value, 10) || null;
    const city = el("reg-city").value.trim();
    if (!name || !username) {
      setError(node, "Name and username are needed.");
      return;
    }

    setStatus(status, `<span class="spinner"></span> Creating your account…`);

    try {
      // send extras alongside; backend ignores unknown fields cleanly
      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          name,
          username,
          age,
          city,
          origin_city: city,
        }),
      });

      // persist locally for UI use (origin city default, etc.)
      localStorage.setItem(
        "voyara.profile",
        JSON.stringify({ name, username, age, city }),
      );
      if (city) localStorage.setItem("voyara.city", city);

      // step 1: registered
      setStatus(
        status,
        `<span class="spinner"></span> Registered ✓ — logging you in…`,
      );

      await new Promise((r) => setTimeout(r, 700));

      // step 2: auto login
      try {
        await api("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      } catch (_) {
        // some backends auto-login on register; ignore login errors if already logged in
      }

      setStatus(
        status,
        `<span class="spinner"></span> Almost there… opening your dashboard.`,
      );
      await new Promise((r) => setTimeout(r, 500));
      setStatus(status, "");
      await refreshMe();
    } catch (e) {
      setStatus(status, "");
      setError(node, e.message);
    }
  } else {
    setStatus(status, `<span class="spinner"></span> Logging in…`);
    try {
      await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setStatus(status, "");
      await refreshMe();
    } catch (e) {
      setStatus(status, "");
      setError(node, e.message);
    }
  }
}

async function logout() {
  try {
    await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
  } catch (_) {}
  state = {
    ...state,
    me: null,
    tripId: null,
    itinerary: null,
    zoneDoodles: new Map(),
    budget: null,
  };
  setAuthMode("login");
  await refreshMe();
}

/* ============== STEPPER ============== */

function setStep(n) {
  state.step = Math.max(1, Math.min(3, n));
  document
    .querySelectorAll(".step")
    .forEach((s) =>
      s.classList.toggle("on", Number(s.dataset.step) === state.step),
    );
  document
    .querySelectorAll(".step-panel")
    .forEach((p) =>
      p.classList.toggle("on", Number(p.dataset.panel) === state.step),
    );
  el("prev-step").style.visibility = state.step === 1 ? "hidden" : "visible";
  el("next-step").style.display = state.step < 3 ? "" : "none";
  el("plan-btn").style.display = state.step === 3 ? "" : "none";
}

/* ============== PLAN ============== */

async function planTrip() {
  const node = el("planner-error");
  setError(node, "");
  const destination_id = parseInt(el("destination").value, 10);
  const start_date = el("start_date").value;
  const end_date = el("end_date").value;
  const num_people = parseInt(el("num_people").value, 10);
  const travel_mode = el("travel_mode").value;
  const accommodation_type = el("accommodation_type").value;
  const wake_time = normalizeTime(el("wake_time").value);
  const sleep_time = normalizeTime(el("sleep_time").value);
  const meals_per_day = parseInt(el("meals_per_day").value, 10);
  const origin_city = el("origin_city").value.trim();
  const flexibility = el("flexibility").value;
  const arrival_terminal_id = el("arrival_terminal_id")?.value || null;
  const departure_terminal_id = el("departure_terminal_id")?.value || null;
  const vibes = state.selectedVibes.slice();

  if (!vibes.length) {
    setStep(3);
    setError(node, "Pick at least 1 vibe.");
    return;
  }
  if (!start_date || !end_date) {
    setStep(1);
    setError(node, "Choose start and end dates.");
    return;
  }

  const priority_order = ["exploring", "meals", "rest", "sleep"];
  el("plan-btn").innerHTML =
    `<span class="spinner" style="width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;"></span> Building your trip…`;

  try {
    const create = await api("/api/trips/create", {
      method: "POST",
      body: JSON.stringify({
        destination_id,
        start_date,
        end_date,
        num_people,
        travel_mode,
        accommodation_type,
        origin_city,
        vibes,
        priority_order,
        sleep_time,
        wake_time,
        meals_per_day,
        flexibility,
        arrival_terminal_id: arrival_terminal_id
          ? Number(arrival_terminal_id)
          : null,
        departure_terminal_id: departure_terminal_id
          ? Number(departure_terminal_id)
          : null,
      }),
    });
    state.tripId = create.trip_id;
    const itinerary = await api(`/api/trips/${state.tripId}/generate`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    state.itinerary = itinerary;

    state.planContext = {
      from: "generated",
      destination_id,
      destination_name:
        state.destinations.find(
          (d) => Number(d.destination_id) === destination_id,
        )?.name || itinerary.destination,
      start_date,
      end_date,
      origin_city,
      travel_mode,
    };

    try {
      const doodles = await api(`/api/trips/${state.tripId}/zone-doodles`);
      state.zoneDoodles = new Map(
        (doodles.zone_doodles || []).map((x) => [x.zone_id, x.primary_tag]),
      );
    } catch (_) {}
    try {
      state.budget = await api(`/api/trips/${state.tripId}/budget`);
    } catch (_) {
      state.budget = null;
    }

    openPlanScreen();
  } catch (e) {
    setError(node, e.message);
  } finally {
    el("plan-btn").innerHTML =
      `<span>Plan it for me</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 2l3 7 7 .8-5 4.7 1.4 7L12 18l-6.4 3.5L7 14.5 2 9.8l7-.8L12 2z" fill="currentColor"/></svg>`;
  }
}

async function openTrip(trip_id, ready, from = "saved") {
  state.tripId = trip_id;
  try {
    if (!ready)
      await api(`/api/trips/${trip_id}/generate`, {
        method: "POST",
        body: JSON.stringify({}),
      });
    const itinerary = await api(`/api/trips/${trip_id}/itinerary`, {
      method: "GET",
    });
    state.itinerary = itinerary;
    try {
      const doodles = await api(`/api/trips/${trip_id}/zone-doodles`);
      state.zoneDoodles = new Map(
        (doodles.zone_doodles || []).map((x) => [x.zone_id, x.primary_tag]),
      );
    } catch (_) {}
    try {
      state.budget = await api(`/api/trips/${trip_id}/budget`);
    } catch (_) {
      state.budget = null;
    }
    state.planContext = {
      from,
      destination_id:
        state.destinations.find((d) => d.name === itinerary.destination)
          ?.destination_id || null,
      destination_name: itinerary.destination,
      start_date: null,
      end_date: null,
      origin_city: el("origin_city")?.value || "",
      travel_mode: el("travel_mode")?.value || "car",
    };
    openPlanScreen();
  } catch (e) {
    toast(`Could not open trip: ${e.message}`);
  }
}

function openModal(id, on) {
  show(id, on);
}
function openPlannerModal() {
  setStep(1);
  openModal("planner-modal", true);
}
function closePlannerModal() {
  openModal("planner-modal", false);
}

function renderQuickStats() {
  const wrap = el("quick-stats");
  if (!wrap) return;
  const itin = state.itinerary;
  if (!itin) {
    wrap.innerHTML = "";
    return;
  }
  const days = itin.days?.length || 0;
  const stops = (itin.days || []).reduce(
    (acc, d) =>
      acc +
      (d.schedule || []).filter((s) => s.slot_type === "attraction").length,
    0,
  );
  const meals = (itin.days || []).reduce(
    (acc, d) =>
      acc + (d.schedule || []).filter((s) => s.slot_type === "meal").length,
    0,
  );
  const acc = itin.accommodation?.name || "TBD";
  wrap.innerHTML = `
    <div class="qstat"><span>Days</span><b>${days}</b></div>
    <div class="qstat"><span>Attractions</span><b>${stops}</b></div>
    <div class="qstat"><span>Meal stops</span><b>${meals}</b></div>
    <div class="qstat"><span>Stay</span><b>${acc}</b></div>`;
}

function renderBudgetBreakdown() {
  const wrap = el("budget-breakdown");
  if (!wrap) return;
  if (!state.budget) {
    wrap.innerHTML = "";
    return;
  }
  const totals = {};
  (state.budget.days || []).forEach((d) => {
    Object.entries(d.categories || {}).forEach(([k, v]) => {
      totals[k] = (totals[k] || 0) + Number(v || 0);
    });
  });
  wrap.innerHTML = Object.entries(totals)
    .map(
      ([k, v]) => `
    <div class="bbar"><span class="name">${k}</span><span class="amt">₹${v}</span></div>`,
    )
    .join("");
}

function openPlanScreen() {
  closePlannerModal();
  openModal("plan-screen", true);
  openModal("day-screen", false);

  const month = monthNameFromDateStr(state.planContext.start_date);
  const destName =
    state.planContext.destination_name ||
    state.itinerary?.destination ||
    "Trip";
  el("plan-title").textContent = `${month ? month + " in " : ""}${destName}`;
  el("plan-sub").textContent =
    state.planContext.start_date && state.planContext.end_date
      ? `${state.planContext.start_date} → ${state.planContext.end_date}`
      : "saved plan · ready when you are";

  const destination_id =
    state.planContext.destination_id ||
    state.destinations.find((d) => d.name === destName)?.destination_id ||
    1;
  highlightMapZones(destination_id, state.itinerary?.days || []);

  const total = state.budget?.total_trip_budget;
  el("budget-total").textContent = total ? `₹${total}` : "—";
  renderBudgetBreakdown();
  renderQuickStats();
  renderTransport();

  const saveBtn = el("save-plan");
  if (saveBtn)
    saveBtn.style.display =
      state.planContext.from === "generated" ? "" : "none";
}

function openDayScreen() {
  openModal("day-screen", true);
  renderDays();
}

async function savePlan() {
  if (!state.tripId) return;
  try {
    await api(`/api/trips/${state.tripId}/save`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    toast("Saved to your trips ✓");
    await refreshSavedTrips();
    state.planContext.from = "saved";
    openPlanScreen();
  } catch (e) {
    toast(e.message);
  }
}

/* ============== EVENTS ============== */

document
  .querySelectorAll(".auth-tab")
  .forEach((b) =>
    b.addEventListener("click", () => setAuthMode(b.dataset.mode)),
  );
el("primary-auth-btn")?.addEventListener("click", doAuth);
[el("email"), el("password")].forEach(
  (n) =>
    n &&
    n.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doAuth();
    }),
);

el("logout-btn")?.addEventListener("click", logout);
el("plan-btn")?.addEventListener("click", planTrip);
el("open-planner")?.addEventListener("click", openPlannerModal);
el("next-step")?.addEventListener("click", () => setStep(state.step + 1));
el("prev-step")?.addEventListener("click", () => setStep(state.step - 1));

document.querySelectorAll("[data-close]").forEach((node) => {
  node.addEventListener("click", () => {
    const what = node.dataset.close;
    if (what === "planner") closePlannerModal();
    if (what === "plan") openModal("plan-screen", false);
    if (what === "days") openModal("day-screen", false);
  });
});

document.querySelectorAll(".tab").forEach((b) => {
  b.addEventListener("click", () => {
    setTab(b.dataset.tab);
    if (b.dataset.tab === "trips") refreshSavedTrips();
  });
});

el("travel_mode")?.addEventListener("change", () => {
  refreshTravelTerminalOptions();
});
el("destination")?.addEventListener("change", () => {
  refreshTravelTerminalOptions();
});

el("open-days")?.addEventListener("click", openDayScreen);
el("save-plan")?.addEventListener("click", savePlan);
el("replay-map")?.addEventListener("click", () => {
  const destination_id =
    state.planContext.destination_id ||
    state.destinations.find((d) => d.name === state.itinerary?.destination)
      ?.destination_id ||
    1;
  highlightMapZones(destination_id, state.itinerary?.days || []);
});

el("profile-btn")?.addEventListener("click", (e) => {
  e.stopPropagation();
  const m = el("profile-menu");
  m.style.display = m.style.display === "none" ? "" : "none";
});
document.addEventListener("click", (e) => {
  const prof = document.querySelector(".profile");
  if (prof && !prof.contains(e.target)) {
    const m = el("profile-menu");
    if (m) m.style.display = "none";
  }
});

// init
fillOriginCityDropdown();
renderCredits();
setAuthMode("login");
refreshMe().catch((err) => {
  console.error(err);
  show("auth-page", true);
});

const API_BASE = "";

let state = {
  me: null,
  destinations: [],
  vibes: [],
  selectedVibes: [],
  tripId: null,
  itinerary: null,
  zoneDoodles: new Map(), // zone_id -> primary_tag
  budget: null,
  activeTab: "home",
  planContext: {
    from: "generated", // generated | saved
    destination_id: null,
    destination_name: null,
    start_date: null,
    end_date: null,
  },
};

function el(id) {
  return document.getElementById(id);
}

async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = data && data.error ? data.error : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

function setError(node, msg) {
  if (!msg) {
    node.style.display = "none";
    node.textContent = "";
    return;
  }
  node.style.display = "block";
  node.textContent = msg;
}

function toast(msg) {
  // simple, human-ish
  alert(msg);
}

function show(id, on) {
  const node = el(id);
  if (!node) return;
  node.style.display = on ? "" : "none";
}

function setTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll(".tab").forEach(b => {
    b.classList.toggle("on", b.dataset.tab === tab);
  });
  show("tab-home", tab === "home");
  show("tab-trips", tab === "trips");
  show("tab-about", tab === "about");
}

function monthNameFromDateStr(d) {
  if (!d) return "";
  const dt = new Date(d);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toLocaleString(undefined, { month: "long" });
}

const DEST_QUOTES = {
  1: "Strawberries, viewpoints, and a little main-character energy.",
  2: "Snow air + cafe walks + ‘let’s do one more viewpoint’.",
  3: "Salt hair, fort stories, and sunsets that hit different.",
  5: "Backwaters, beach days, and slow mornings with good food.",
};

function destVariantClass(destination_id) {
  const m = { 1: "variant1", 2: "variant2", 3: "variant3", 5: "variant4" };
  return m[destination_id] || "variant1";
}

function topDestinations() {
  const wanted = [1, 2, 3, 5]; // popular cards
  const byId = new Map(state.destinations.map(d => [Number(d.destination_id), d]));
  const picked = wanted.map(id => byId.get(id)).filter(Boolean);
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
    const variant = ["", "variant2", "variant3", "variant4"][i % 4];
    const imgMap = {
      1: "/static/img/mahabaleshwar.jpg",
      2: "/static/img/manali.jpg",
      3: "/static/img/konkan.jpg",
      5: "/static/img/kerala.jpg",
    };
    const img = imgMap[id] || "";
    card.innerHTML = `
      <div class="dest-photo ${variant}" ${img ? `style="background-image:url('${img}')"` : ""}></div>
      <div class="dest-overlay"></div>
      <div class="dest-meta">
        <div class="dest-name">${d.name}</div>
        <div class="dest-quote">${DEST_QUOTES[id] || "A place you’ll remember for a long time."}</div>
      </div>
    `;
    card.addEventListener("click", () => {
      openPlannerModal();
      const sel = el("destination");
      if (sel) sel.value = String(id);
      refreshTravelTerminalOptions();
    });
    wrap.appendChild(card);
  });
}

function terminalOptionsForDestination(destination_id, travel_mode) {
  const id = Number(destination_id);
  if (travel_mode === "car") return [{ id: "", label: "— (car trip: no terminal) —" }];

  const options = {
    1: [
      { id: 101, label: "Wathar Station (station) — Mahabaleshwar area" },
      { id: 102, label: "Pune Airport (airport) — nearest" },
    ],
    2: [
      { id: 103, label: "Bhuntar Airport (airport)" },
      { id: 104, label: "Joginder Nagar Station (station)" },
    ],
    3: [
      { id: 105, label: "Ratnagiri Railway Station (station)" },
      { id: 106, label: "Sindhudurg Airport (airport)" },
    ],
    5: [
      { id: 107, label: "Cochin International Airport (airport)" },
      { id: 108, label: "Ernakulam Junction (station)" },
    ],
  };

  return (options[id] || [{ id: "", label: "— pick later —" }]);
}

function fillSelect(selectId, options) {
  const sel = el(selectId);
  if (!sel) return;
  sel.innerHTML = "";
  options.forEach(o => {
    const opt = document.createElement("option");
    opt.value = String(o.id);
    opt.textContent = o.label;
    sel.appendChild(opt);
  });
}

function refreshTravelTerminalOptions() {
  const destSel = el("destination");
  const modeSel = el("travel_mode");
  if (!destSel || !modeSel) return;
  const destination_id = Number(destSel.value);
  const travel_mode = modeSel.value;
  const opts = terminalOptionsForDestination(destination_id, travel_mode);
  fillSelect("arrival_terminal_id", opts);
  fillSelect("departure_terminal_id", opts);
  if (travel_mode === "car") {
    el("arrival_terminal_id").value = "";
    el("departure_terminal_id").value = "";
  }
}

function doodleSvgForTag(tag, colorA, colorB) {
  const t = (tag || "scenic").toLowerCase();
  const palette = {
    adventure: ["#ff6b6b", "#ffd93d"],
    nature: ["#21f3a5", "#35d0ff"],
    foodie: ["#ffb703", "#ff6b6b"],
    spiritual: ["#7c5cff", "#35d0ff"],
    cultural: ["#35d0ff", "#7c5cff"],
    historical: ["#ffd93d", "#7c5cff"],
    relaxed: ["#35d0ff", "#21f3a5"],
    urban: ["#7c5cff", "#ff4d6d"],
    offbeat: ["#ff4d6d", "#21f3a5"],
    scenic: ["#35d0ff", "#7c5cff"],
  };
  const [a, b] = palette[t] || [colorA || "#35d0ff", colorB || "#7c5cff"];

  // “Doodle” style is intentionally simple (not too perfect).
  if (t === "foodie") {
    return `
      <svg width="42" height="42" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M18 7v10c0 2 2 3 3 3s3-1 3-3V7" stroke="${a}" stroke-width="3" stroke-linecap="round"/>
        <path d="M26 10h4" stroke="${b}" stroke-width="3" stroke-linecap="round"/>
        <path d="M18 17c-1 5-5 12-5 18" stroke="${b}" stroke-width="3" stroke-linecap="round"/>
        <path d="M24 17c1 5 5 12 5 18" stroke="${b}" stroke-width="3" stroke-linecap="round"/>
        <circle cx="21" cy="31" r="2.2" fill="${a}"/>
      </svg>
    `;
  }
  if (t === "nature") {
    return `
      <svg width="42" height="42" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 35c0-10 7-14 13-16C33 28 29 35 21 35Z" stroke="${a}" stroke-width="3" stroke-linejoin="round"/>
        <path d="M21 35c0-10-7-14-13-16C9 28 13 35 21 35Z" stroke="${b}" stroke-width="3" stroke-linejoin="round"/>
        <path d="M21 35V14" stroke="${a}" stroke-width="3" stroke-linecap="round"/>
        <path d="M18 18c-2-1-3-3-3-6" stroke="${b}" stroke-width="3" stroke-linecap="round"/>
      </svg>
    `;
  }
  if (t === "adventure") {
    return `
      <svg width="42" height="42" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M7 30l8-14 6 10 6-18 8 22" stroke="${a}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M12 30h18" stroke="${b}" stroke-width="3" stroke-linecap="round"/>
      </svg>
    `;
  }

  // Default: simple landmark-ish doodle
  return `
    <svg width="42" height="42" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M13 30h16" stroke="${a}" stroke-width="3" stroke-linecap="round"/>
      <path d="M15 30l6-16 6 16" stroke="${b}" stroke-width="3" stroke-linejoin="round"/>
      <path d="M18 14h6" stroke="${a}" stroke-width="3" stroke-linecap="round"/>
      <circle cx="21" cy="28" r="2.2" fill="${a}"/>
    </svg>
  `;
}

const DAY_COLORS = ["#41f1c2", "#3ad7ff", "#ffcc66", "#ff4d7d", "#b58bff"];

function schematicMapSvg(destination_id) {
  const id = Number(destination_id);
  // These are intentionally “schematic”, not accurate geography.
  // Each zone shape has id="zone-<zone_id>" so we can highlight.
  if (id === 1) {
    // Mahabaleshwar zones: 1,2,3,4
    return `
      <svg viewBox="0 0 520 280" width="100%" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="500" height="260" rx="22" fill="rgba(0,0,0,.14)" stroke="rgba(255,255,255,.14)"/>
        <path d="M65 210 C130 140, 180 120, 230 80" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="3" stroke-linecap="round"/>
        <path d="M230 80 C300 60, 360 80, 430 140" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="3" stroke-linecap="round"/>
        <g>
          <path id="zone-3" d="M70 170 Q120 120 190 140 Q175 215 105 225 Q75 210 70 170Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
          <text x="118" y="178" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Venna</text>
        </g>
        <g>
          <path id="zone-1" d="M200 150 Q245 110 300 140 Q305 210 250 225 Q205 210 200 150Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
          <text x="238" y="178" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Town</text>
        </g>
        <g>
          <path id="zone-2" d="M210 75 Q265 45 320 70 Q325 120 280 130 Q230 120 210 75Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
          <text x="252" y="95" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Panchgani</text>
        </g>
        <g>
          <path id="zone-4" d="M330 150 Q380 95 450 130 Q470 205 400 225 Q345 210 330 150Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
          <text x="374" y="176" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Ridge</text>
        </g>
      </svg>
    `;
  }

  if (id === 2) {
    // Manali zones: 5,6,7,8
    return `
      <svg viewBox="0 0 520 280" width="100%" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="500" height="260" rx="22" fill="rgba(0,0,0,.14)" stroke="rgba(255,255,255,.14)"/>
        <path d="M90 210 C160 160, 210 130, 270 95 C330 60, 390 70, 445 110" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="3" stroke-linecap="round"/>
        <path id="zone-5" d="M70 175 Q120 135 170 155 Q170 220 115 230 Q78 220 70 175Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="96" y="190" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Town</text>
        <path id="zone-8" d="M165 135 Q200 105 245 120 Q250 170 215 190 Q175 178 165 135Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="183" y="150" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Old</text>
        <path id="zone-6" d="M240 95 Q290 60 335 85 Q345 140 300 155 Q255 140 240 95Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="266" y="110" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Solang</text>
        <path id="zone-7" d="M350 70 Q405 40 450 75 Q470 125 420 145 Q360 130 350 70Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="386" y="92" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Rohtang</text>
      </svg>
    `;
  }

  if (id === 3) {
    // Konkan zones: 9,10,11,12
    return `
      <svg viewBox="0 0 520 280" width="100%" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="500" height="260" rx="22" fill="rgba(0,0,0,.14)" stroke="rgba(255,255,255,.14)"/>
        <path d="M110 70 C130 110, 120 160, 135 205" fill="none" stroke="rgba(58,215,255,.25)" stroke-width="10" stroke-linecap="round"/>
        <path id="zone-9" d="M150 165 Q185 125 235 150 Q235 215 185 230 Q155 215 150 165Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="170" y="185" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Tarkarli</text>
        <path id="zone-10" d="M230 120 Q280 90 325 120 Q330 175 285 190 Q240 175 230 120Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="250" y="140" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Fort</text>
        <path id="zone-11" d="M260 185 Q315 150 370 175 Q372 230 315 240 Q265 230 260 185Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="285" y="205" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Ganpatipule</text>
        <path id="zone-12" d="M310 85 Q360 55 410 80 Q418 130 375 145 Q328 130 310 85Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="335" y="105" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Ratnagiri</text>
      </svg>
    `;
  }

  if (id === 5) {
    // Kerala zones: 17,18,19,20
    return `
      <svg viewBox="0 0 520 280" width="100%" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="500" height="260" rx="22" fill="rgba(0,0,0,.14)" stroke="rgba(255,255,255,.14)"/>
        <path d="M105 60 C115 115, 105 160, 120 220" fill="none" stroke="rgba(65,241,194,.18)" stroke-width="10" stroke-linecap="round"/>
        <path id="zone-17" d="M145 165 Q190 130 245 150 Q248 215 190 230 Q150 215 145 165Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="162" y="185" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Alleppey</text>
        <path id="zone-18" d="M250 95 Q310 60 365 90 Q372 145 320 160 Q265 145 250 95Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="280" y="112" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Munnar</text>
        <path id="zone-19" d="M260 175 Q320 140 380 165 Q385 230 320 240 Q265 230 260 175Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="285" y="195" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Thekkady</text>
        <path id="zone-20" d="M390 150 Q430 115 470 140 Q488 195 440 220 Q395 205 390 150Z" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.18)" stroke-width="2"/>
        <text x="405" y="176" fill="rgba(255,255,255,.85)" font-size="14" font-weight="800">Kovalam</text>
      </svg>
    `;
  }

  // fallback
  return `
    <svg viewBox="0 0 520 280" width="100%" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="10" width="500" height="260" rx="22" fill="rgba(0,0,0,.14)" stroke="rgba(255,255,255,.14)"/>
      <text x="30" y="60" fill="rgba(255,255,255,.75)" font-size="16" font-weight="800">Map not set for this destination yet</text>
    </svg>
  `;
}

function highlightMapZones(destination_id, itineraryDays) {
  const mapWrap = el("dest-map");
  if (!mapWrap) return;
  mapWrap.innerHTML = schematicMapSvg(destination_id);

  const legend = el("legend");
  if (legend) legend.innerHTML = "";

  const dayToZone = (itineraryDays || []).slice().sort((a,b)=>a.day_number-b.day_number).map(d => ({
    day: d.day_number,
    zone_id: d.zone_id,
    zone_name: d.zone_name,
  }));

  dayToZone.forEach((dz, idx) => {
    const color = DAY_COLORS[(dz.day - 1) % DAY_COLORS.length];
    const shape = mapWrap.querySelector(`#zone-${dz.zone_id}`);
    if (shape) {
      shape.setAttribute("fill", color + "33");
      shape.setAttribute("stroke", color);
      shape.setAttribute("stroke-width", "3");
    }

    if (legend) {
      const leg = document.createElement("div");
      leg.className = "leg";
      leg.innerHTML = `<span class="dot" style="background:${color}"></span> Day ${dz.day}: ${dz.zone_name || ("Zone " + dz.zone_id)}`;
      legend.appendChild(leg);
    }
  });
}

function renderDays() {
  const daysWrap = el("days");
  daysWrap.innerHTML = "";
  const itinerary = state.itinerary;
  if (!itinerary || !itinerary.days) {
    daysWrap.innerHTML = "<div class='muted'>Generate an itinerary first.</div>";
    return;
  }

  const days = itinerary.days.slice().sort((a, b) => a.day_number - b.day_number);

  for (const day of days) {
    const zoneId = day.zone_id;
    const tag = state.zoneDoodles.get(zoneId) || "scenic";
    const budgetDay = state.budget?.days?.find(d => d.day_number === day.day_number);

    const card = document.createElement("div");
    card.className = "day-card";

    const totalText = budgetDay ? `Estimated: ₹${budgetDay.total}` : "Estimated: (loading…)";
    const cats = budgetDay ? Object.entries(budgetDay.categories) : [];
    const catBadges = cats.length
      ? cats.map(([k, v]) => `<span class="badge">${k}: ₹${v}</span>`).join("")
      : "";

    card.innerHTML = `
      <div class="day-head">
        <div>
          <div class="day-title">Day ${day.day_number}: ${day.zone_name || ""}</div>
          <div class="muted" style="margin-top:4px">${totalText}</div>
        </div>
      </div>
      <div class="timeline">
        ${(day.schedule || []).slice().sort((a,b)=>timeToMins(a.start_time)-timeToMins(b.start_time)).map(item => {
          const type = item.slot_type || "block";
          const labelName = item.attraction || item.notes || type;
          const meal = item.meal_type ? ` (${item.meal_type})` : "";
          return `
            <div class="tl-row">
              <div class="tl-time">${item.start_time} → ${item.end_time}</div>
              <div class="tl-type">${type}${meal}</div>
              <div class="tl-name">${labelName}</div>
              <div class="tl-notes">${item.notes ? item.notes : ""}</div>
            </div>
          `;
        }).join("")}
      </div>
      <div class="muted" style="margin-top:10px;">${catBadges ? "Budget: " + cats.map(([k,v]) => `${k} ₹${v}`).join(" • ") : ""}</div>
    `;

    daysWrap.appendChild(card);
  }
}

function timeToMins(timeStr) {
  // "6:30 AM" => minutes.
  if (!timeStr) return 0;
  const m = String(timeStr).trim().match(/^(\d+):(\d+)\s*(AM|PM)$/i);
  if (!m) return 0;
  let h = parseInt(m[1], 10);
  const mins = parseInt(m[2], 10);
  const period = m[3].toUpperCase();
  if (period === "PM" && h !== 12) h += 12;
  if (period === "AM" && h === 12) h = 0;
  return h * 60 + mins;
}

function normalizeTime(t) {
  // Convert "HH:MM" -> "HH:MM:00" (MySQL TIME-friendly).
  if (!t) return t;
  if (String(t).length === 5) return String(t) + ":00";
  return t;
}

function renderSavedTrips(trips) {
  const wrap = el("mytrips-grid");
  if (!wrap) return;
  wrap.innerHTML = "";
  if (!trips || trips.length === 0) {
    wrap.innerHTML = "<div class='muted'>No saved trips yet. Save a plan and it’ll show up here.</div>";
    return;
  }

  trips.forEach((t, i) => {
    const id = Number(t.destination_id);
    const card = document.createElement("div");
    card.className = "trip-card";
    const variant = ["", "variant2", "variant3", "variant4"][i % 4];
    const imgMap = {
      1: "/static/img/mahabaleshwar.jpg",
      2: "/static/img/manali.jpg",
      3: "/static/img/konkan.jpg",
      5: "/static/img/kerala.jpg",
    };
    const img = imgMap[id] || "";
    card.innerHTML = `
      <div class="dest-photo ${variant}" ${img ? `style="background-image:url('${img}')"` : ""}></div>
      <div class="inner">
        <div class="title">${t.destination_name}</div>
        <div class="sub">${t.start_date} → ${t.end_date}</div>
        <div class="sub">“${DEST_QUOTES[id] || "you saved this for a reason"}”</div>
        <div class="actions">
          <button class="btn">Open</button>
        </div>
      </div>
    `;
    card.querySelector("button").addEventListener("click", () => openTrip(t.trip_id, true, "saved"));
    wrap.appendChild(card);
  });
}

function pickVibeChips() {
  const wrap = el("vibes-wrap");
  wrap.innerHTML = "";
  state.vibes.forEach(v => {
    const row = document.createElement("label");
    row.style.flexDirection = "row";
    row.style.alignItems = "center";
    row.style.gap = "10px";
    row.style.padding = "8px 10px";
    row.style.border = "1px solid rgba(255,255,255,.10)";
    row.style.borderRadius = "12px";
    row.style.background = "rgba(255,255,255,.03)";
    row.style.cursor = "pointer";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = v;
    cb.checked = state.selectedVibes.includes(v);

    cb.addEventListener("change", () => {
      const selected = new Set(state.selectedVibes);
      if (cb.checked) {
        if (selected.size >= 4) {
          cb.checked = false;
          return;
        }
        selected.add(v);
      } else {
        selected.delete(v);
      }
      state.selectedVibes = Array.from(selected);
    });

    const txt = document.createElement("div");
    txt.textContent = v;
    txt.style.color = "rgba(255,255,255,.85)";
    txt.style.fontWeight = "800";

    row.appendChild(cb);
    row.appendChild(txt);
    wrap.appendChild(row);
  });
}

async function loadDestinations() {
  const data = await api("/api/destinations");
  state.destinations = data.destinations || [];
  const sel = el("destination");
  sel.innerHTML = "";
  state.destinations.forEach(d => {
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
  const data = await api("/api/auth/me");
  state.me = data.user_id ? data : null;
  if (el("me-pill")) el("me-pill").textContent = state.me ? `${state.me.email}` : "";

  if (!state.me) {
    show("auth-page", true);
    show("app-shell", false);
    return;
  }

  show("auth-page", false);
  show("app-shell", true);
  setTab("home");

  await Promise.all([loadDestinations(), loadVibes(), refreshSavedTrips()]);
}

async function refreshSavedTrips() {
  const data = await api("/api/me/trips");
  renderSavedTrips(data.trips || []);
}

async function doLogin(kind) {
  const email = el("email").value.trim();
  const password = el("password").value;
  const node = el("auth-error");
  setError(node, "");

  try {
    const res = await api(
      kind === "login" ? "/api/auth/login" : "/api/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }
    );
    await refreshMe();
    return res;
  } catch (e) {
    setError(node, e.message);
    return null;
  }
}

async function logout() {
  await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
  state = { ...state, me: null, tripId: null, itinerary: null, zoneDoodles: new Map(), budget: null };
  await refreshMe();
}

function getSelectedVibes() {
  return state.selectedVibes.slice();
}

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

  const vibes = getSelectedVibes();
  if (!vibes.length) {
    setError(node, "Pick at least 1 vibe.");
    return;
  }
  if (!start_date || !end_date) {
    setError(node, "Choose start and end dates.");
    return;
  }

  // Basic priority order (backend expects JSON list).
  const priority_order = ["exploring", "meals", "rest", "sleep"];

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
        arrival_terminal_id: arrival_terminal_id ? Number(arrival_terminal_id) : null,
        departure_terminal_id: departure_terminal_id ? Number(departure_terminal_id) : null,
      }),
    });

    const trip_id = create.trip_id;
    state.tripId = trip_id;

    const itinerary = await api(`/api/trips/${trip_id}/generate`, { method: "POST", body: JSON.stringify({}) });
    state.itinerary = itinerary;
    state.planContext = {
      from: "generated",
      destination_id,
      destination_name: state.destinations.find(d => Number(d.destination_id) === destination_id)?.name || itinerary.destination,
      start_date,
      end_date,
    };

    // Doodles derived from zone tags (no images stored).
    const doodles = await api(`/api/trips/${trip_id}/zone-doodles`);
    state.zoneDoodles = new Map((doodles.zone_doodles || []).map(x => [x.zone_id, x.primary_tag]));

    // Budget estimate per day (rough but usable).
    const budget = await api(`/api/trips/${trip_id}/budget`);
    state.budget = budget;

    openPlanScreen();
  } catch (e) {
    setError(node, e.message);
  }
}

async function openTrip(trip_id, itinerary_ready, from = "saved") {
  state.tripId = trip_id;

  try {
    if (!itinerary_ready) {
      await api(`/api/trips/${trip_id}/generate`, { method: "POST", body: JSON.stringify({}) });
    }

    const itinerary = await api(`/api/trips/${trip_id}/itinerary`, { method: "GET" });
    state.itinerary = itinerary;

    const doodles = await api(`/api/trips/${trip_id}/zone-doodles`);
    state.zoneDoodles = new Map((doodles.zone_doodles || []).map(x => [x.zone_id, x.primary_tag]));

    const budget = await api(`/api/trips/${trip_id}/budget`);
    state.budget = budget;

    state.planContext = {
      from,
      destination_id: state.destinations.find(d => d.name === itinerary.destination)?.destination_id || null,
      destination_name: itinerary.destination,
      start_date: null,
      end_date: null,
    };

    openPlanScreen();
  } catch (e) {
    toast(`Could not open trip: ${e.message}`);
  }
}

function addChatMsg(text, kind) {
  const log = el("chat-log");
  const div = document.createElement("div");
  div.className = `msg ${kind}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function initChatUI() {
  el("chat-log").innerHTML = "";
  addChatMsg("Hey bestie. Tell me where you wanna go ✨ (chat wiring later).", "bot");
}

async function onChatSend() {
  const input = el("chat-text");
  const text = (input.value || "").trim();
  if (!text) return;
  input.value = "";

  addChatMsg(text, "user");
  addChatMsg("Not wired yet. For now, use the form above (destination + vibes) and hit “Plan Trip”.", "bot");
}

function openModal(id, on) {
  show(id, on);
}

function openPlannerModal() {
  openModal("planner-modal", true);
}

function closePlannerModal() {
  openModal("planner-modal", false);
}

function openPlanScreen() {
  closePlannerModal();
  openModal("plan-screen", true);
  openModal("day-screen", false);

  const title = el("plan-title");
  const sub = el("plan-sub");
  const month = monthNameFromDateStr(state.planContext.start_date);
  const destName = state.planContext.destination_name || state.itinerary?.destination || "Trip";
  if (title) title.textContent = `${month ? month + " " : ""}${destName} trip`;
  if (sub) sub.textContent = state.planContext.start_date && state.planContext.end_date ? `${state.planContext.start_date} → ${state.planContext.end_date}` : "saved plan";

  const destination_id = state.planContext.destination_id || state.destinations.find(d => d.name === destName)?.destination_id || 1;
  highlightMapZones(destination_id, state.itinerary?.days || []);

  const total = state.budget?.total_trip_budget;
  const bt = el("budget-total");
  if (bt) bt.textContent = total ? `₹${total}` : "—";

  const saveBtn = el("save-plan");
  if (saveBtn) {
    saveBtn.style.display = state.planContext.from === "generated" ? "" : "none";
  }
}

function openDayScreen() {
  openModal("day-screen", true);
  renderDays();
}

async function savePlan() {
  if (!state.tripId) return;
  try {
    await api(`/api/trips/${state.tripId}/save`, { method: "POST", body: JSON.stringify({}) });
    toast("Saved.");
    await refreshSavedTrips();
    state.planContext.from = "saved";
    openPlanScreen();
  } catch (e) {
    toast(e.message);
  }
}

// Events
el("login-btn").addEventListener("click", () => doLogin("login"));
el("register-btn").addEventListener("click", () => doLogin("register"));
el("logout-btn").addEventListener("click", logout);
el("plan-btn").addEventListener("click", planTrip);
el("open-planner").addEventListener("click", openPlannerModal);

document.querySelectorAll("[data-close]").forEach(node => {
  node.addEventListener("click", () => {
    const what = node.dataset.close;
    if (what === "planner") closePlannerModal();
    if (what === "plan") openModal("plan-screen", false);
    if (what === "days") openModal("day-screen", false);
    if (what === "chat") openModal("chat-modal", false);
  });
});

document.querySelectorAll(".tab").forEach(b => {
  b.addEventListener("click", () => {
    setTab(b.dataset.tab);
    if (b.dataset.tab === "trips") refreshSavedTrips();
  });
});

el("travel_mode").addEventListener("change", refreshTravelTerminalOptions);
el("destination").addEventListener("change", refreshTravelTerminalOptions);

el("open-days").addEventListener("click", openDayScreen);
el("save-plan").addEventListener("click", savePlan);

// Profile menu toggle
el("profile-btn").addEventListener("click", () => {
  const m = el("profile-menu");
  m.style.display = m.style.display === "none" ? "" : "none";
});
document.addEventListener("click", (e) => {
  const prof = document.querySelector(".profile");
  if (!prof) return;
  if (!prof.contains(e.target)) {
    const m = el("profile-menu");
    if (m) m.style.display = "none";
  }
});

el("open-bot").addEventListener("click", () => openModal("chat-modal", true));
el("chat-send").addEventListener("click", onChatSend);
el("chat-text").addEventListener("keydown", (e) => {
  if (e.key === "Enter") onChatSend();
});

initChatUI();

refreshMe().catch(err => {
  console.error(err);
  show("auth-page", true);
});


/* Cards for the ha-vehicle integration:
 *   vehicle-info-card      mileage, consumption, monthly costs and service status
 *   vehicle-activity-card  timeline of refuels, charges and services, with linked files
 *   vehicle-entry-card     add a refuel, charge or completed service (with receipt upload)
 */


// ---------------------------------------------------------------------------------------------
// translations (English is the fallback; the language follows Home Assistant's user language)
// ---------------------------------------------------------------------------------------------
const I18N = {
  en: {
    selectVehicle: "Select a vehicle.",
    notFound: "Vehicle not found ({id}).",
    "status.overdue": "Overdue", "status.due_soon": "Due soon", "status.ok": "OK", "status.unknown": "Not tracked yet",
    dayUnit: "d", today: "today", inDays: "in {n} d", daysOverdue: "{n} d overdue", kmLeft: "{n} km left", kmOverdue: "{n} km overdue",
    consumption: "Consumption", costsMonth: "Costs this month", thisMonth: "this month",
    fuel: "Fuel", charging: "Charging", service: "Service", nothingDue: "Nothing due.",
    noItems: "No service items yet. Add them on the integration page.",
    activityTitle: "{vehicle} · Activity", entryTitle: "{vehicle} · Add entry",
    all: "All", refuels: "Refuels", charges: "Charges",
    refuel: "Refuel", charge: "Charge",
    refuelLine: "Refuel · {amount} L", chargeLine: "Charge · {amount} kWh", serviceDone: "{name} · done",
    showMore: "Show more", noActivity: "No activity yet.", openFile: "Open file", edit: "Edit",
    save: "Save", cancel: "Cancel", delete: "Delete", confirmDelete: "Delete this entry? This cannot be undone.",
    date: "Date", liters: "Liters", energyKwh: "Energy (kWh)", priceL: "Price per L", priceKwh: "Price per kWh",
    odometerKm: "Odometer (km)", odometerOptional: "Odometer (km, optional)", cost: "Cost",
    receipt: "Receipt", receiptOptional: "Receipt (optional)", attachFile: "Attach file", replaceFile: "Replace", removeFile: "Remove", openFile2: "Open",
    receiptAttached: "Receipt attached",
    photoFile: "Photo / file", scan: "Scan with AI", uploading: "Uploading…", uploadFailed: "Upload failed",
    reading: "Reading receipt…", checkValues: "Please check the values", nothingReadable: "Nothing readable found", scanFailed: "Scan failed",
    saving: "Saving…", saved: "Saved", failed: "Failed", addRefuel: "Add refuel", addCharge: "Add charge", markDone: "Mark as done",
    serviceItem: "Service item", currently: "Currently: {text}", total: "Total: {value}", last: "last: {value}", current: "current: {value}",
    nothingToAdd: "Nothing to add for this vehicle.", removeTip: "Remove",
    // editors
    vehicle: "Vehicle", layout: "Layout", layoutNormal: "Normal", layoutCompact: "Compact", layoutMinimal: "Minimal",
    header: "Header", statistics: "Statistics", serviceItems: "Service items", showTheseTypes: "Show these types", list: "List", showTheseTabs: "Show these tabs",
    showTitle: "Show title", titleEmpty: "Title (empty = vehicle name)", titleAuto: "Title (empty = automatic)", icon: "Icon", showOdometer: "Show mileage",
    showConsumption: "Show consumption", showCosts: "Show costs this month", showCostSplit: "Show the split (fuel / charging / service)",
    showServices: "Show service items", serviceLayout: "Service item layout", layoutAuto: "Automatic (by layout)", layoutList: "List (two lines)", layoutRows: "One line each", layoutChips: "Chips",
    serviceFilter: "Which service items", filterAll: "All items", filterAttention: "Only overdue or due soon", maxServices: "Maximum number of items (0 = all)", showHeadings: "Show the 'Service' heading",
    optRefuels: "Refuels", optCharges: "Charges", optService: "Service", entries: "Entries shown (more via 'Show more')", showFilters: "Show filter chips",
    groupByMonth: "Group by month", showCostsPerEntry: "Show costs", showFiles: "Show links to receipts and invoices", allowEdit: "Allow editing and deleting entries",
    tabRefuel: "Refuel", tabCharge: "Charge", tabService: "Service",
  },
  de: {
    selectVehicle: "Bitte ein Fahrzeug auswählen.",
    notFound: "Fahrzeug nicht gefunden ({id}).",
    "status.overdue": "Überfällig", "status.due_soon": "Bald fällig", "status.ok": "OK", "status.unknown": "Noch nicht erfasst",
    dayUnit: "T", today: "heute", inDays: "in {n} T", daysOverdue: "{n} T überfällig", kmLeft: "noch {n} km", kmOverdue: "{n} km überfällig",
    consumption: "Verbrauch", costsMonth: "Kosten diesen Monat", thisMonth: "diesen Monat",
    fuel: "Kraftstoff", charging: "Laden", service: "Service", nothingDue: "Nichts fällig.",
    noItems: "Noch keine Service-Einträge. Lege sie auf der Integrationsseite an.",
    activityTitle: "{vehicle} · Aktivität", entryTitle: "{vehicle} · Eintrag hinzufügen",
    all: "Alle", refuels: "Tanken", charges: "Laden",
    refuel: "Tanken", charge: "Laden",
    refuelLine: "Tanken · {amount} L", chargeLine: "Laden · {amount} kWh", serviceDone: "{name} · erledigt",
    showMore: "Mehr anzeigen", noActivity: "Noch keine Aktivität.", openFile: "Datei öffnen", edit: "Bearbeiten",
    save: "Speichern", cancel: "Abbrechen", delete: "Löschen", confirmDelete: "Diesen Eintrag löschen? Das lässt sich nicht rückgängig machen.",
    date: "Datum", liters: "Liter", energyKwh: "Energie (kWh)", priceL: "Preis pro L", priceKwh: "Preis pro kWh",
    odometerKm: "Kilometerstand (km)", odometerOptional: "Kilometerstand (km, optional)", cost: "Kosten",
    receipt: "Beleg", receiptOptional: "Beleg (optional)", attachFile: "Datei anhängen", replaceFile: "Ersetzen", removeFile: "Entfernen", openFile2: "Öffnen",
    receiptAttached: "Beleg angehängt",
    photoFile: "Foto / Datei", scan: "Mit KI scannen", uploading: "Lade hoch…", uploadFailed: "Hochladen fehlgeschlagen",
    reading: "Lese Beleg…", checkValues: "Bitte die Werte prüfen", nothingReadable: "Nichts Lesbares gefunden", scanFailed: "Scan fehlgeschlagen",
    saving: "Speichere…", saved: "Gespeichert", failed: "Fehlgeschlagen", addRefuel: "Tanken eintragen", addCharge: "Laden eintragen", markDone: "Als erledigt markieren",
    serviceItem: "Service-Eintrag", currently: "Aktuell: {text}", total: "Summe: {value}", last: "zuletzt: {value}", current: "aktuell: {value}",
    nothingToAdd: "Für dieses Fahrzeug gibt es nichts hinzuzufügen.", removeTip: "Entfernen",
    vehicle: "Fahrzeug", layout: "Darstellung", layoutNormal: "Normal", layoutCompact: "Kompakt", layoutMinimal: "Minimal",
    header: "Kopfzeile", statistics: "Statistik", serviceItems: "Service-Einträge", showTheseTypes: "Diese Arten anzeigen", list: "Liste", showTheseTabs: "Diese Reiter anzeigen",
    showTitle: "Titel anzeigen", titleEmpty: "Titel (leer = Fahrzeugname)", titleAuto: "Titel (leer = automatisch)", icon: "Symbol", showOdometer: "Kilometerstand anzeigen",
    showConsumption: "Verbrauch anzeigen", showCosts: "Kosten diesen Monat anzeigen", showCostSplit: "Aufteilung anzeigen (Kraftstoff / Laden / Service)",
    showServices: "Service-Einträge anzeigen", serviceLayout: "Darstellung der Service-Einträge", layoutAuto: "Automatisch (je nach Darstellung)", layoutList: "Liste (zwei Zeilen)", layoutRows: "Eine Zeile pro Eintrag", layoutChips: "Chips",
    serviceFilter: "Welche Service-Einträge", filterAll: "Alle", filterAttention: "Nur überfällige oder bald fällige", maxServices: "Maximale Anzahl (0 = alle)", showHeadings: "Überschrift „Service“ anzeigen",
    optRefuels: "Tanken", optCharges: "Laden", optService: "Service", entries: "Angezeigte Einträge (mehr über „Mehr anzeigen“)", showFilters: "Filter-Chips anzeigen",
    groupByMonth: "Nach Monat gruppieren", showCostsPerEntry: "Kosten anzeigen", showFiles: "Links zu Belegen und Rechnungen anzeigen", allowEdit: "Bearbeiten und Löschen erlauben",
    tabRefuel: "Tanken", tabCharge: "Laden", tabService: "Service",
  },
};

const tr = (hass, key, vars = {}) => {
  const lang = String(hass?.locale?.language || hass?.language || "en").split("-")[0];
  const text = I18N[lang]?.[key] ?? I18N.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
};

// ---------------------------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------------------------
const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const STATUS_ORDER = { overdue: 0, due_soon: 1, ok: 2, unknown: 3 };
const STATUS_COLOR = {
  overdue: "var(--error-color, #db4437)",
  due_soon: "var(--warning-color, #ffa600)",
  ok: "var(--success-color, #43a047)",
  unknown: "var(--secondary-text-color)",
};
const KIND_COLOR = { fuel: "#fb8c00", charge: "#43a047", service: "#03a9f4" };
const KIND_ICON = { fuel: "mdi:gas-station", charge: "mdi:ev-station", service: "mdi:car-wrench" };

const downscale = async (file, max = 1600) => {
  if (!file.type.startsWith("image/")) return file;
  try {
    const bmp = await createImageBitmap(file);
    const scale = Math.min(1, max / Math.max(bmp.width, bmp.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bmp.width * scale);
    canvas.height = Math.round(bmp.height * scale);
    canvas.getContext("2d").drawImage(bmp, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    return blob ? new File([blob], "receipt.jpg", { type: "image/jpeg" }) : file;
  } catch (_) {
    return file; // formats the browser cannot decode are sent unchanged
  }
};

const callResponse = async (hass, service, data) =>
  (await hass.callWS({ type: "call_service", domain: "vehicle", service, service_data: data, return_response: true })).response;

const uploadReceipt = async (hass, file) => {
  const body = new FormData();
  body.append("file", await downscale(file));
  const resp = await hass.fetchWithAuth("/api/file_upload", { method: "POST", body });
  if (!resp.ok) throw new Error(`Upload failed (${resp.status})`);
  const { file_id } = await resp.json();
  return (await callResponse(hass, "upload_receipt", { file: file_id })).receipt;
};

const aiAvailable = (hass) =>
  !!hass.services?.ai_task?.generate_data && Object.keys(hass.states).some((id) => id.startsWith("ai_task."));

const scanReceipt = async (hass, receipt, kind) => (await callResponse(hass, "scan_receipt", { receipt, kind })).values || {};

const openReceipt = async (hass, receipt) => {
  const win = window.open("", "_blank"); // open synchronously to avoid popup blockers
  try {
    const { path } = await hass.callWS({ type: "auth/sign_path", path: `/api/vehicle/receipt/${receipt}`, expires: 120 });
    if (win) win.location.href = path;
    else window.open(path, "_blank");
  } catch (err) {
    if (win) win.close();
    window.alert(err?.message || "Could not open the file");
  }
};

// A card is configured with the vehicle's device (`device`, chosen in the editor) or, in YAML,
// with any entity of the vehicle (`entity`, e.g. its odometer sensor).
const vehicleDeviceId = (hass, config) => config.device || hass.entities?.[config.entity]?.device_id;

const findVehicle = (hass, config) => {
  const deviceId = vehicleDeviceId(hass, config);
  const result = { items: [] };
  if (!deviceId) return result;
  for (const [id, e] of Object.entries(hass.entities)) {
    if (e.platform !== "vehicle" || e.device_id !== deviceId) continue;
    const state = hass.states[id];
    if (!state || !e.translation_key) continue;
    if (e.translation_key === "service_status") result.items.push(state);
    else result[e.translation_key] = state;
  }
  result.device = hass.devices?.[deviceId];
  return result;
};

const describeConfig = (config) => config.device || config.entity || "?";
const numberOf = (state) => {
  const n = Number(state?.state);
  return state && state.state !== "" && Number.isFinite(n) ? n : null;
};

const SHARED_CSS = `
  [hidden] { display:none !important; }
  ha-card { display:block; padding-bottom:8px; }
  .header { display:flex; align-items:center; gap:8px; padding:16px 16px 4px; }
  .title { font-size:1.2em; font-weight:500; display:flex; align-items:center; gap:8px; flex:1; min-width:0; }
  .odo { font-size:1.4em; font-weight:500; margin-left:auto; }
  small { font-size:.6em; color:var(--secondary-text-color); font-weight:400; }
  .muted { font-size:.85em; color:var(--secondary-text-color); }
  .section { padding:12px 16px 4px; font-size:.8em; text-transform:uppercase; letter-spacing:.06em; color:var(--secondary-text-color); }
  .row { display:flex; align-items:center; gap:12px; padding:6px 16px; min-height:44px; }
  .grow { flex:1; min-width:0; }
  .dot { width:10px; height:10px; border-radius:50%; flex:none; }
  .empty { padding:16px; color:var(--secondary-text-color); }
  .msg { padding:4px 16px; color:var(--secondary-text-color); }
  ha-icon-button { flex:none; }
`;

// ---------------------------------------------------------------------------------------------
// base class: config handling, vehicle lookup, formatting
// ---------------------------------------------------------------------------------------------
class VehicleCardBase extends HTMLElement {
  static get defaults() {
    return {};
  }

  setConfig(config) {
    if (!config.device && !config.entity) throw new Error("Select a vehicle.");
    this._config = { ...this.constructor.defaults, ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  get _ready() {
    return !!(this._config && this._hass && this.shadowRoot);
  }

  _t(key, vars) {
    return tr(this._hass, key, vars);
  }

  _vehicle() {
    return findVehicle(this._hass, this._config);
  }

  _notFound() {
    this.shadowRoot.innerHTML = `<ha-card><div class="empty">${esc(this._t("notFound", { id: describeConfig(this._config) }))}</div></ha-card><style>${SHARED_CSS}</style>`;
  }

  _vehicleName(v) {
    return v.device?.name_by_user || v.device?.name || "Vehicle";
  }

  _fmt(value, digits = 0) {
    if (value === null || value === undefined || value === "unknown" || value === "unavailable") return "–";
    return Number(value).toLocaleString(this._hass.locale?.language, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  _date(iso, options = { month: "short", day: "numeric" }) {
    return new Date(`${iso}T12:00:00`).toLocaleDateString(this._hass.locale?.language, options);
  }

  _itemName(state, v) {
    const prefix = this._vehicleName(v);
    const name = state.attributes.friendly_name || state.entity_id;
    return name.startsWith(prefix + " ") ? name.slice(prefix.length + 1) : name;
  }

  // "−30 d", "24 d · 1,350 km"
  _remainingShort(a) {
    const parts = [];
    const sign = (n) => (n < 0 ? "−" : "");
    if (a.days_remaining !== null && a.days_remaining !== undefined) parts.push(`${sign(a.days_remaining)}${Math.abs(a.days_remaining)} ${this._t("dayUnit")}`);
    if (a.km_remaining !== null && a.km_remaining !== undefined) parts.push(`${sign(a.km_remaining)}${this._fmt(Math.abs(a.km_remaining))} km`);
    return parts.join(" · ");
  }

  // "30 d overdue", "in 24 d · 1,350 km left"
  _remainingLong(a) {
    const parts = [];
    const d = a.days_remaining;
    const km = a.km_remaining;
    if (d !== null && d !== undefined) parts.push(d < 0 ? this._t("daysOverdue", { n: -d }) : d === 0 ? this._t("today") : this._t("inDays", { n: d }));
    if (km !== null && km !== undefined) parts.push(km < 0 ? this._t("kmOverdue", { n: this._fmt(-km) }) : this._t("kmLeft", { n: this._fmt(km) }));
    return parts.join(" · ");
  }

  _sortedItems(v) {
    return [...v.items].sort((a, b) => {
      const d = STATUS_ORDER[a.state] - STATUS_ORDER[b.state];
      return d || (a.attributes.days_remaining ?? 1e9) - (b.attributes.days_remaining ?? 1e9);
    });
  }

  _moreInfo(entityId) {
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig(hass) {
    const odometer = Object.values(hass.entities || {}).find((e) => e.platform === "vehicle" && e.translation_key === "odometer");
    return { device: odometer?.device_id || "" };
  }
}

// ---------------------------------------------------------------------------------------------
// info card
// ---------------------------------------------------------------------------------------------
const INFO_DEFAULTS = {
  layout: "normal", // normal | compact | minimal
  show_title: true,
  icon: "mdi:car",
  show_odometer: true,
  show_consumption: true,
  show_costs: true,
  show_cost_split: true,
  show_services: true,
  service_layout: "auto", // auto | list | rows | chips
  service_filter: "all", // all | attention
  max_services: 0,
  show_headings: true,
};

class VehicleInfoCard extends VehicleCardBase {
  static get defaults() {
    return INFO_DEFAULTS;
  }

  static getConfigElement() {
    return document.createElement("vehicle-info-card-editor");
  }

  getCardSize() {
    return this._config?.layout === "minimal" ? 2 : 4;
  }

  _consumption(v) {
    const out = [];
    const fuel = numberOf(v.fuel_consumption);
    const energy = numberOf(v.energy_consumption);
    if (fuel !== null) out.push({ value: this._fmt(fuel, 1), unit: "L/100 km" });
    if (energy !== null) out.push({ value: this._fmt(energy, 1), unit: "kWh/100 km" });
    return out;
  }

  _costs(v) {
    const month = numberOf(v.monthly_cost) ?? 0;
    const service = numberOf(v.monthly_service_cost) ?? 0;
    const type = v.odometer?.attributes.fuel_type;
    const fuel = Number(v.monthly_cost?.attributes.fuel);
    const energy = Number(v.monthly_cost?.attributes.energy);
    const parts = [];
    if (Number.isFinite(fuel) && Number.isFinite(energy)) {
      parts.push({ label: this._t("fuel"), value: fuel, color: KIND_COLOR.fuel }, { label: this._t("charging"), value: energy, color: KIND_COLOR.charge });
    } else {
      parts.push({ label: type === "electric" ? this._t("charging") : this._t("fuel"), value: month, color: type === "electric" ? KIND_COLOR.charge : KIND_COLOR.fuel });
    }
    parts.push({ label: this._t("service"), value: service, color: KIND_COLOR.service });
    return { total: month + service, parts: parts.filter((p) => p.value > 0) };
  }

  _services(v, cfg, layout) {
    let items = this._sortedItems(v);
    const all = items.length;
    if (cfg.service_filter === "attention") items = items.filter((i) => i.state === "overdue" || i.state === "due_soon");
    if (Number(cfg.max_services) > 0) items = items.slice(0, Number(cfg.max_services));
    if (!cfg.show_services || !all) return "";
    const shape = cfg.service_layout === "auto" ? (layout === "minimal" ? "chips" : "rows") : cfg.service_layout;
    const heading = cfg.show_headings && shape !== "chips" ? `<div class="section">${esc(this._t("service"))}</div>` : "";
    if (!items.length) return `${heading}<div class="empty">${esc(this._t("nothingDue"))}</div>`;
    const color = (s) => STATUS_COLOR[s.state] || STATUS_COLOR.unknown;
    const attrs = (s) => `data-entity="${esc(s.entity_id)}"`;
    if (shape === "chips") {
      return `<div class="chips">${items
        .map((s) => `<span class="chip" ${attrs(s)}><span class="dot" style="background:${color(s)}"></span>${esc(this._itemName(s, v))} <span class="muted">${esc(this._remainingShort(s.attributes).split(" · ")[0])}</span></span>`)
        .join("")}</div>`;
    }
    if (shape === "list") {
      return `${heading}${items
        .map(
          (s) => `<div class="row tap" ${attrs(s)}><span class="dot" style="background:${color(s)}"></span>
            <div class="grow"><div>${esc(this._itemName(s, v))}</div><div class="muted">${esc(this._remainingLong(s.attributes) || this._t("status." + s.state))}</div></div></div>`
        )
        .join("")}`;
    }
    return `${heading}${items
      .map(
        (s) => `<div class="crow tap" ${attrs(s)}><span class="dot" style="background:${color(s)}"></span><div class="grow">${esc(this._itemName(s, v))}</div>
          <div class="muted ${s.state === "overdue" ? "bad" : ""}">${esc(this._remainingShort(s.attributes) || this._t("status." + s.state))}</div></div>`
      )
      .join("")}`;
  }

  _render() {
    if (!this._ready) return;
    const cfg = this._config;
    const v = this._vehicle();
    if (!v.odometer) return this._notFound();
    const layout = cfg.layout;
    const currency = this._hass.config?.currency || "";
    const title = cfg.title || this._vehicleName(v);
    const cons = cfg.show_consumption ? this._consumption(v) : [];
    const costs = cfg.show_costs ? this._costs(v) : null;
    const consText = cons.map((c) => `<b>${esc(c.value)}</b> <small>${esc(c.unit)}</small>`).join(" &nbsp;·&nbsp; ");
    const titleHtml = cfg.show_title ? `<div class="title">${cfg.icon ? `<ha-icon icon="${esc(cfg.icon)}"></ha-icon>` : ""}<span>${esc(title)}</span></div>` : `<div class="title"></div>`;
    const odoHtml = cfg.show_odometer ? `<div class="odo">${this._fmt(v.odometer.state)} <small>km</small></div>` : "";
    let body = "";

    if (layout === "minimal") {
      const bits = [cons.map((c) => `${c.value} ${c.unit}`).join(" · "), costs ? `${this._fmt(costs.total, 2)} ${currency}` : ""].filter(Boolean).join(" · ");
      const right = [cfg.show_odometer ? `<span class="odo small">${this._fmt(v.odometer.state)}</span> km` : "", bits].filter(Boolean).join("<br>");
      body = `<div class="header">${titleHtml}${right ? `<div class="muted right">${right}</div>` : ""}</div>${this._services(v, cfg, layout)}`;
    } else if (layout === "compact") {
      const line = [
        cons.length ? `<span class="cs"><ha-icon icon="mdi:gauge"></ha-icon>${consText}</span>` : "",
        costs ? `<span class="cs"><ha-icon icon="mdi:cash-multiple"></ha-icon><b>${this._fmt(costs.total, 2)}</b> <small>${esc(currency)} ${esc(this._t("thisMonth"))}</small></span>` : "",
      ].filter(Boolean).join("");
      body = `<div class="header">${titleHtml}${odoHtml}</div>${line ? `<div class="sline">${line}</div>` : ""}${this._services(v, cfg, layout)}`;
    } else {
      const rows = [];
      if (cons.length) {
        rows.push(`<div class="stat"><div class="gi"><ha-icon icon="mdi:gauge"></ha-icon></div><div class="grow"><div class="gn">${esc(this._t("consumption"))}</div><div class="main">${consText}</div></div></div>`);
      }
      if (costs) {
        const split = cfg.show_cost_split && costs.parts.length > 1;
        const bar = split ? `<div class="bar">${costs.parts.map((p) => `<span style="flex:${p.value};background:${p.color}"></span>`).join("")}</div>` : "";
        const legend = split
          ? `<div class="splits">${costs.parts.map((p) => `<span class="sp"><span class="dot s" style="background:${p.color}"></span>${p.label} <b>${this._fmt(p.value, 2)} ${esc(currency)}</b></span>`).join("")}</div>`
          : "";
        rows.push(`<div class="stat"><div class="gi"><ha-icon icon="mdi:cash-multiple"></ha-icon></div><div class="grow"><div class="gn">${esc(this._t("costsMonth"))}</div><div class="main"><b>${this._fmt(costs.total, 2)}</b> <small>${esc(currency)}</small></div>${bar}${legend}</div></div>`);
      }
      body = `<div class="header">${titleHtml}${odoHtml}</div>${rows.join("")}${this._services(v, cfg, layout)}`;
    }

    this.shadowRoot.innerHTML = `<ha-card>${body}</ha-card><style>${SHARED_CSS}${this._css()}</style>`;
    this.shadowRoot.querySelectorAll("[data-entity]").forEach((el) => el.addEventListener("click", () => this._moreInfo(el.dataset.entity)));
  }

  _css() {
    return `
      .header .odo.small, .right .odo.small { font-size:1.1em; font-weight:500; color:var(--primary-text-color); margin:0; }
      .right { text-align:right; line-height:1.4; }
      .stat { display:flex; align-items:flex-start; gap:12px; padding:6px 16px; }
      .gi { width:28px; height:28px; border-radius:8px; background:var(--secondary-background-color,#f1f1f1); display:flex; align-items:center; justify-content:center; color:var(--secondary-text-color); flex:none; }
      .gi ha-icon { --mdc-icon-size:18px; }
      .gn { font-size:.75em; text-transform:uppercase; letter-spacing:.06em; color:var(--secondary-text-color); margin-bottom:2px; }
      .main { font-size:1.05em; }
      .bar { display:flex; gap:2px; height:6px; border-radius:3px; overflow:hidden; margin:6px 0 4px; }
      .bar span { display:block; }
      .splits { display:flex; flex-wrap:wrap; gap:2px 14px; font-size:.8em; color:var(--secondary-text-color); }
      .sp { display:inline-flex; align-items:center; gap:5px; }
      .sp b { color:var(--primary-text-color); font-weight:500; }
      .dot.s { width:8px; height:8px; }
      .sline { display:flex; flex-wrap:wrap; align-items:center; gap:4px 16px; padding:2px 16px 6px; }
      .cs { display:inline-flex; align-items:center; gap:5px; }
      .cs ha-icon { --mdc-icon-size:18px; color:var(--secondary-text-color); }
      .crow { display:flex; align-items:center; gap:10px; padding:3px 16px; min-height:30px; }
      .crow .bad { color:var(--error-color,#db4437); }
      .tap { cursor:pointer; }
      .chips { display:flex; flex-wrap:wrap; gap:6px; padding:4px 16px 8px; }
      .chip { display:inline-flex; align-items:center; gap:6px; border:1px solid var(--divider-color,#e0e0e0); border-radius:16px; padding:3px 10px 3px 8px; font-size:.85em; cursor:pointer; }
    `;
  }
}

// ---------------------------------------------------------------------------------------------
// activity card
// ---------------------------------------------------------------------------------------------
const ACTIVITY_DEFAULTS = {
  show_title: true,
  icon: "mdi:timeline-clock-outline",
  show_refuels: true,
  show_charges: true,
  show_service: true,
  show_filters: true,
  group_by_month: true,
  show_costs: true,
  show_files: true,
  allow_edit: true,
  entries: 8,
};

class VehicleActivityCard extends VehicleCardBase {
  static get defaults() {
    return ACTIVITY_DEFAULTS;
  }

  static getConfigElement() {
    return document.createElement("vehicle-activity-card-editor");
  }

  getCardSize() {
    return 6;
  }

  setConfig(config) {
    this._filter = "all";
    this._extra = 0;
    this._editing = null;
    this._signature = null;
    super.setConfig(config);
  }

  _enabledKinds() {
    const c = this._config;
    return { fuel: c.show_refuels, charge: c.show_charges, service: c.show_service };
  }

  _title(e) {
    if (e.kind === "fuel") return this._t("refuelLine", { amount: this._fmt(e.amount, 1) });
    if (e.kind === "charge") return this._t("chargeLine", { amount: this._fmt(e.amount, 1) });
    return esc(this._t("serviceDone", { name: e.name }));
  }

  _subtitle(e) {
    const unit = e.kind === "charge" ? "kWh" : "L";
    const parts = [this._date(e.date)];
    if (e.price != null) parts.push(`${this._fmt(e.price, 3)} ${esc(this._hass.config?.currency || "")}/${unit}`);
    if (e.odometer != null) parts.push(`${this._fmt(e.odometer)} km`);
    return parts.join(" · ");
  }

  _rowHtml(e, cfg, currency) {
    return `<div class="row" data-id="${esc(e.id)}">
      <div class="ic" style="background:${KIND_COLOR[e.kind]}22;color:${KIND_COLOR[e.kind]}"><ha-icon icon="${KIND_ICON[e.kind]}"></ha-icon></div>
      <div class="grow"><div>${this._title(e)}</div><div class="muted">${this._subtitle(e)}</div></div>
      ${cfg.show_costs && e.cost != null ? `<div class="amount">${this._fmt(e.cost, 2)} ${esc(currency)}</div>` : ""}
      ${cfg.show_files ? (e.receipt ? `<ha-icon-button class="file" data-receipt="${esc(e.receipt)}" title="${esc(this._t("openFile"))}"><ha-icon icon="mdi:paperclip"></ha-icon></ha-icon-button>` : `<span class="nofile"></span>`) : ""}
      ${cfg.allow_edit ? `<ha-icon-button class="edit" data-id="${esc(e.id)}" title="${esc(this._t("edit"))}"><ha-icon icon="mdi:pencil-outline"></ha-icon></ha-icon-button>` : ""}
    </div>`;
  }

  _editHtml(e, currency) {
    const t = (k, v) => esc(this._t(k, v));
    const field = (label, name, value, step, extra = "") =>
      `<label><span class="lt">${label}</span><input name="${name}" type="${name === "date" ? "date" : "number"}" ${name === "date" ? "" : `step="${step}" min="0" inputmode="decimal"`} value="${esc(value ?? "")}" ${extra}></label>`;
    const fields =
      e.kind === "service"
        ? `${field(t("date"), "date", e.date)}${field(t("odometerKm"), "odometer", e.odometer, "0.1")}${field(`${t("cost")} (${esc(currency)})`, "cost", e.cost, "0.01")}`
        : `${field(t("date"), "date", e.date)}${field(e.kind === "charge" ? t("energyKwh") : t("liters"), "amount", e.amount, "0.01")}
           ${field(`${e.kind === "charge" ? t("priceKwh") : t("priceL")} (${esc(currency)})`, "price", e.price, "0.001")}${field(t("odometerOptional"), "odometer", e.odometer, "0.1")}`;
    const receiptRow = `<div class="drop ${e.receipt ? "has" : ""}">
        <ha-icon icon="mdi:paperclip" class="clip"></ha-icon>
        <div class="grow rname muted">${e.receipt ? t("receiptAttached") : t("receiptOptional")}</div>
        ${e.receipt ? `<button type="button" class="btn" data-act="open">${t("openFile2")}</button>` : ""}
        <button type="button" class="btn" data-act="pick">${e.receipt ? t("replaceFile") : t("attachFile")}</button>
        ${e.receipt ? `<button type="button" class="btn" data-act="remove">${t("removeFile")}</button>` : ""}
      </div>`;
    return `<div class="editor" data-id="${esc(e.id)}">
      <div class="etitle">${this._title(e)}</div>
      <form>${fields}${receiptRow}
        <div class="actions"><button type="button" class="btn danger" data-act="delete"><ha-icon icon="mdi:delete-outline"></ha-icon>${t("delete")}</button>
          <span class="status"></span>
          <span class="grow"></span><button type="button" class="btn" data-act="cancel">${t("cancel")}</button><button type="submit" class="btn primary">${t("save")}</button></div>
      </form></div>`;
  }

  _render() {
    if (!this._ready) return;
    const cfg = this._config;
    const v = this._vehicle();
    if (!v.odometer) return this._notFound();
    // the state changes constantly; only redraw when something shown here changed, and never
    // while an entry is being edited (that would throw away what has been typed)
    if (this._editing) return;
    const currency = this._hass.config?.currency || "";
    const signature = JSON.stringify([v.odometer.attributes.activity, cfg, this._filter, this._extra, currency, this._hass.locale?.language, this._vehicleName(v)]);
    if (signature === this._signature) return;
    this._signature = signature;

    const enabled = this._enabledKinds();
    const all = (v.odometer.attributes.activity || []).filter((e) => enabled[e.kind]);
    const present = ["fuel", "charge", "service"].filter((k) => all.some((e) => e.kind === k));
    if (this._filter !== "all" && !present.includes(this._filter)) this._filter = "all";
    const filtered = all.filter((e) => this._filter === "all" || e.kind === this._filter);
    const limit = Math.max(1, Number(cfg.entries) || 8) + this._extra;
    const shown = filtered.slice(0, limit);
    const title = cfg.title || this._t("activityTitle", { vehicle: this._vehicleName(v) });
    const chipLabel = { all: this._t("all"), fuel: this._t("refuels"), charge: this._t("charges"), service: this._t("service") };

    let list = "";
    if (!shown.length) {
      list = `<div class="empty">${esc(this._t("noActivity"))}</div>`;
    } else if (cfg.group_by_month) {
      let month = "";
      for (const e of shown) {
        const m = this._date(e.date, { month: "long", year: "numeric" });
        if (m !== month) {
          month = m;
          list += `<div class="section">${esc(m)}</div>`;
        }
        list += this._rowHtml(e, cfg, currency);
      }
    } else {
      list = shown.map((e) => this._rowHtml(e, cfg, currency)).join("");
    }
    const filters =
      cfg.show_filters && present.length > 1
        ? `<div class="chips">${["all", ...present].map((k) => `<span class="fchip ${k === this._filter ? "on" : ""}" data-filter="${k}">${esc(chipLabel[k])}</span>`).join("")}</div>`
        : "";
    const more = filtered.length > shown.length ? `<div class="more" data-more>${esc(this._t("showMore"))}</div>` : "";

    this.shadowRoot.innerHTML = `<ha-card>
      ${cfg.show_title ? `<div class="header"><div class="title">${cfg.icon ? `<ha-icon icon="${esc(cfg.icon)}"></ha-icon>` : ""}<span>${esc(title)}</span></div></div>` : ""}
      ${filters}${list}${more}</ha-card><style>${SHARED_CSS}${this._css()}</style>`;

    this.shadowRoot.querySelectorAll("[data-filter]").forEach((el) =>
      el.addEventListener("click", () => {
        this._filter = el.dataset.filter;
        this._extra = 0;
        this._render();
      })
    );
    this.shadowRoot.querySelectorAll(".file").forEach((el) => el.addEventListener("click", () => openReceipt(this._hass, el.dataset.receipt)));
    this.shadowRoot.querySelectorAll("button.edit, ha-icon-button.edit").forEach((el) =>
      el.addEventListener("click", () => this._startEdit(el.dataset.id, all.find((e) => e.id === el.dataset.id)))
    );
    const moreEl = this.shadowRoot.querySelector("[data-more]");
    if (moreEl) {
      moreEl.addEventListener("click", () => {
        this._extra += Math.max(1, Number(cfg.entries) || 8);
        this._render();
      });
    }
  }

  // ---- editing -----------------------------------------------------------------------------
  _startEdit(id, entry) {
    if (!entry) return;
    this._editing = { id, entry, receipt: undefined, removeReceipt: false };
    const row = this.shadowRoot.querySelector(`.row[data-id="${CSS.escape(id)}"]`);
    if (!row) return;
    const currency = this._hass.config?.currency || "";
    row.outerHTML = this._editHtml(entry, currency);
    const editor = this.shadowRoot.querySelector(".editor");
    this._picker = document.createElement("input");
    this._picker.type = "file";
    this._picker.accept = "image/*,application/pdf";
    this._picker.hidden = true;
    this._picker.addEventListener("change", () => this._pickFile());
    editor.appendChild(this._picker);
    editor.querySelector("form").addEventListener("submit", (ev) => {
      ev.preventDefault();
      this._save();
    });
    editor.querySelectorAll("[data-act]").forEach((el) => el.addEventListener("click", () => this._action(el.dataset.act)));
  }

  _status(text, cls = "") {
    const el = this.shadowRoot.querySelector(".editor .status");
    if (el) {
      el.className = `status ${cls}`;
      el.textContent = text;
    }
  }

  _endEdit() {
    this._editing = null;
    this._signature = null;
    this._render();
  }

  async _action(act) {
    const edit = this._editing;
    if (!edit) return;
    const root = this.shadowRoot.querySelector(".editor");
    if (act === "cancel") return this._endEdit();
    if (act === "open") return openReceipt(this._hass, edit.receipt || edit.entry.receipt);
    if (act === "pick") return this._picker.click();
    if (act === "remove") {
      edit.removeReceipt = true;
      edit.receipt = undefined;
      root.querySelector(".drop").classList.remove("has");
      root.querySelector(".rname").textContent = this._t("receiptOptional");
      root.querySelectorAll('[data-act="open"], [data-act="remove"]').forEach((el) => (el.hidden = true));
      return;
    }
    if (act === "delete") {
      if (!window.confirm(this._t("confirmDelete"))) return;
      this._status(this._t("saving"));
      try {
        await this._hass.callService("vehicle", "delete_activity", { entity_id: this._vehicle().odometer.entity_id, activity_id: edit.id });
        this._endEdit();
      } catch (err) {
        this._status(err?.message || this._t("failed"), "err");
      }
    }
  }

  async _pickFile() {
    const file = this._picker.files[0];
    this._picker.value = "";
    if (!file || !this._editing) return;
    const root = this.shadowRoot.querySelector(".editor");
    root.querySelector(".rname").textContent = this._t("uploading");
    try {
      this._editing.receipt = await uploadReceipt(this._hass, file);
      this._editing.removeReceipt = false;
      root.querySelector(".rname").textContent = file.name;
      root.querySelector(".drop").classList.add("has");
    } catch (err) {
      root.querySelector(".rname").textContent = this._editing.entry.receipt ? this._t("receiptAttached") : this._t("receiptOptional");
      this._status(err?.message || this._t("uploadFailed"), "err");
    }
  }

  async _save() {
    const edit = this._editing;
    const q = (n) => this.shadowRoot.querySelector(`.editor [name=${n}]`);
    const data = { entity_id: this._vehicle().odometer.entity_id, activity_id: edit.id, date: q("date").value };
    for (const name of ["amount", "price", "odometer", "cost"]) {
      const input = q(name);
      if (input && input.value !== "") data[name] = Number(input.value);
    }
    if (edit.receipt) data.receipt = edit.receipt;
    else if (edit.removeReceipt) data.remove_receipt = true;
    this._status(this._t("saving"));
    try {
      await this._hass.callService("vehicle", "update_activity", data);
      this._endEdit();
    } catch (err) {
      this._status(err?.message || this._t("failed"), "err");
    }
  }

  _css() {
    return `
      .ic { width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex:none; }
      .ic ha-icon { --mdc-icon-size:20px; }
      .amount { font-weight:500; text-align:right; white-space:nowrap; }
      .nofile { width:40px; flex:none; margin-left:-12px; }
      .file, .edit { --mdc-icon-button-size:40px; color:var(--secondary-text-color); margin:-8px -8px -8px -12px; }
      .chips { display:flex; flex-wrap:wrap; gap:8px; padding:8px 16px 4px; }
      .fchip { border:1px solid var(--divider-color,#e0e0e0); border-radius:16px; padding:4px 12px; font-size:.85em; cursor:pointer; }
      .fchip.on { background:var(--primary-color,#03a9f4); color:var(--text-primary-color,#fff); border-color:transparent; }
      .more { padding:8px 16px; color:var(--primary-color,#03a9f4); font-weight:500; font-size:.9em; cursor:pointer; }
      .editor { margin:6px 8px; padding:8px 8px 4px; border:1px solid var(--divider-color,#e0e0e0); border-radius:12px; background:var(--secondary-background-color,#fafafa); }
      .etitle { padding:4px 8px; font-weight:500; }
      form { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px 12px; padding:6px 8px 8px; align-items:start; }
      label { display:flex; flex-direction:column; gap:4px; font-size:.8em; color:var(--secondary-text-color); min-width:0; }
      .lt { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-height:1.2em; }
      input { font:inherit; font-size:1rem; padding:8px; border-radius:6px; color:var(--primary-text-color); background:var(--card-background-color,#fff); border:1px solid var(--divider-color,#ccc); min-width:0; width:100%; box-sizing:border-box; }
      input:focus { outline:2px solid var(--primary-color); outline-offset:-1px; }
      input[type=number] { -moz-appearance:textfield; appearance:textfield; }
      input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
      .drop { grid-column:1 / -1; display:flex; align-items:center; gap:8px; flex-wrap:wrap; border:1.5px dashed var(--divider-color,#bdbdbd); border-radius:10px; padding:8px 10px; }
      .drop.has { border-style:solid; border-color:var(--primary-color,#03a9f4); }
      .drop .clip { color:var(--secondary-text-color); --mdc-icon-size:20px; }
      .rname { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .actions { grid-column:1 / -1; display:flex; align-items:center; gap:8px; }
      .btn { font:inherit; font-size:.9em; cursor:pointer; border-radius:6px; border:1px solid var(--divider-color,#ccc); background:transparent; color:var(--primary-text-color); padding:6px 12px; display:inline-flex; align-items:center; gap:6px; }
      .btn ha-icon { --mdc-icon-size:18px; }
      .btn.primary { background:var(--primary-color,#03a9f4); color:var(--text-primary-color,#fff); border-color:transparent; padding:8px 16px; font-weight:500; }
      .btn.danger { color:var(--error-color,#db4437); border-color:var(--error-color,#db4437); }
      .status.err { color:var(--error-color,#db4437); }
    `;
  }
}

// ---------------------------------------------------------------------------------------------
// entry card: add a refuel, charge or completed service
// ---------------------------------------------------------------------------------------------
const ENTRY_DEFAULTS = {
  show_title: true,
  icon: "mdi:plus-circle-outline",
  show_refuel: true,
  show_charge: true,
  show_service: true,
};

const TAB_INFO = {
  fuel: { label: "tabRefuel", icon: "mdi:gas-station" },
  charge: { label: "tabCharge", icon: "mdi:ev-station" },
  service: { label: "tabService", icon: "mdi:car-wrench" },
};

class VehicleEntryCard extends VehicleCardBase {
  static get defaults() {
    return ENTRY_DEFAULTS;
  }

  static getConfigElement() {
    return document.createElement("vehicle-entry-card-editor");
  }

  getCardSize() {
    return 5;
  }

  setConfig(config) {
    this._built = false;
    this._tab = null;
    super.setConfig(config);
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._ready) return;
    const tabs = this._availableTabs();
    if (!this._built || tabs.join() !== this._tabsKey) this._build();
    else this._hints();
  }

  _render() {
    if (this._ready) this._build();
  }

  _availableTabs() {
    const v = this._vehicle();
    const type = v.odometer?.attributes.fuel_type;
    const c = this._config;
    const tabs = [];
    if (type && type !== "electric" && c.show_refuel) tabs.push("fuel");
    if (type && (type === "electric" || type === "hybrid") && c.show_charge) tabs.push("charge");
    if (v.items.length && c.show_service) tabs.push("service");
    return tabs;
  }

  _build() {
    const v = this._vehicle();
    if (!v.odometer) return this._notFound();
    const tabs = this._availableTabs();
    this._tabsKey = tabs.join();
    this._built = true;
    if (!tabs.includes(this._tab)) this._tab = tabs[0] || null;
    const cfg = this._config;
    const title = cfg.title || this._t("entryTitle", { vehicle: this._vehicleName(v) });
    this._receipt = null;

    const tabBar =
      tabs.length > 1
        ? `<div class="tabs">${tabs.map((t) => `<div class="tab ${t === this._tab ? "on" : ""}" data-tab="${t}"><ha-icon icon="${TAB_INFO[t].icon}"></ha-icon>${esc(this._t(TAB_INFO[t].label))}</div>`).join("")}</div>`
        : "";
    this.shadowRoot.innerHTML = `<ha-card>
      ${cfg.show_title ? `<div class="header"><div class="title">${cfg.icon ? `<ha-icon icon="${esc(cfg.icon)}"></ha-icon>` : ""}<span>${esc(title)}</span></div></div>` : ""}
      ${tabBar}
      ${this._tab ? this._form(v) : `<div class="empty">${esc(this._t("nothingToAdd"))}</div>`}
    </ha-card><style>${SHARED_CSS}${this._css()}</style>`;
    this._wire();
    this._hints();
  }

  _form(v) {
    const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    const t = this._tab;
    const files = `<div class="drop">
        <ha-icon icon="mdi:paperclip" class="clip"></ha-icon>
        <div class="grow"><div class="rname muted">${esc(this._t("receiptOptional"))}</div></div>
        <button type="button" class="btn scan" hidden><ha-icon icon="mdi:text-recognition"></ha-icon>${esc(this._t("scan"))}</button>
        <button type="button" class="btn pick"><ha-icon icon="mdi:camera-outline"></ha-icon>${esc(this._t("photoFile"))}</button>
        <button type="button" class="btn drop-x" hidden title="${esc(this._t("removeTip"))}"><ha-icon icon="mdi:close"></ha-icon></button>
      </div>`;
    if (t === "service") {
      const options = this._sortedItems(v).map((s) => `<option value="${esc(s.entity_id)}">${esc(this._itemName(s, v))}</option>`).join("");
      return `<form>
        <label class="full"><span class="lt">${esc(this._t("serviceItem"))}</span><select name="item">${options}</select></label>
        <div class="full muted item-state"></div>
        <label><span class="lt">${esc(this._t("date"))}</span><input name="date" type="date" value="${today}" required></label>
        <label><span class="lt">${esc(this._t("odometerKm"))}</span><input name="odometer" type="number" step="0.1" min="0" inputmode="decimal"></label>
        <label class="full"><span class="lt">${esc(this._t("cost"))} <span class="cur"></span></span><input name="cost" type="number" step="0.01" min="0" inputmode="decimal"></label>
        ${files}
        <div class="actions"><span class="status"></span><button type="submit" class="btn primary">${esc(this._t("markDone"))}</button></div>
      </form>`;
    }
    const charge = t === "charge";
    return `<form>
      <label><span class="lt">${esc(this._t("date"))}</span><input name="date" type="date" value="${today}" required></label>
      <label><span class="lt">${esc(charge ? this._t("energyKwh") : this._t("liters"))}</span><input name="amount" type="number" step="0.01" min="0" inputmode="decimal" required></label>
      <label><span class="lt">${esc(charge ? this._t("priceKwh") : this._t("priceL"))} <span class="cur"></span></span><input name="price" type="number" step="0.001" min="0" inputmode="decimal" required></label>
      <label><span class="lt">${esc(this._t("odometerOptional"))}</span><input name="odometer" type="number" step="0.1" min="0" inputmode="decimal"></label>
      ${files}
      <div class="total muted"></div>
      <div class="actions"><span class="status"></span><button type="submit" class="btn primary">${esc(charge ? this._t("addCharge") : this._t("addRefuel"))}</button></div>
    </form>`;
  }

  _wire() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-tab]").forEach((el) =>
      el.addEventListener("click", () => {
        this._tab = el.dataset.tab;
        this._build();
      })
    );
    const form = root.querySelector("form");
    if (!form) return;
    this._picker = document.createElement("input");
    this._picker.type = "file";
    this._picker.accept = "image/*,application/pdf";
    this._picker.hidden = true;
    this._picker.addEventListener("change", () => this._pick());
    root.appendChild(this._picker);
    root.querySelector(".pick").addEventListener("click", () => this._picker.click());
    root.querySelector(".scan").addEventListener("click", () => this._scan());
    root.querySelector(".drop-x").addEventListener("click", () => this._clearReceipt());
    form.addEventListener("input", () => this._hints());
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      this._submit();
    });
  }

  _q(sel) {
    return this.shadowRoot.querySelector(sel);
  }

  _status(text, cls = "") {
    const el = this._q(".status");
    if (!el) return;
    el.className = `status ${cls}`;
    el.textContent = text;
  }

  _clearReceipt() {
    this._receipt = null;
    this._q(".rname").textContent = this._t("receiptOptional");
    this._q(".scan").hidden = true;
    this._q(".drop-x").hidden = true;
    this._q(".drop").classList.remove("has");
  }

  async _pick() {
    const file = this._picker.files[0];
    this._picker.value = "";
    if (!file) return;
    this._receipt = null;
    this._q(".rname").textContent = this._t("uploading");
    try {
      this._receipt = await uploadReceipt(this._hass, file);
      this._q(".rname").textContent = file.name;
      this._q(".drop").classList.add("has");
      this._q(".drop-x").hidden = false;
      this._q(".scan").hidden = !aiAvailable(this._hass);
    } catch (err) {
      this._q(".rname").textContent = this._t("receiptOptional");
      this._status(err?.message || this._t("uploadFailed"), "err");
    }
  }

  async _scan() {
    if (!this._receipt) return;
    this._status(this._t("reading"));
    try {
      const v = await scanReceipt(this._hass, this._receipt, this._tab);
      const set = (name, value) => {
        const input = this._q(`[name=${name}]`);
        if (input && value !== undefined && value !== null && value !== "") input.value = value;
      };
      if (this._tab === "service") {
        set("date", v.date);
        set("odometer", v.odometer);
        set("cost", v.cost);
      } else {
        const charge = this._tab === "charge";
        let amount = v[charge ? "kwh" : "liters"];
        let price = v[charge ? "price_per_kwh" : "price_per_liter"];
        if (!price && amount && v.total_cost) price = Math.round((v.total_cost / amount) * 1000) / 1000;
        if (!amount && price && v.total_cost) amount = Math.round((v.total_cost / price) * 100) / 100;
        set("date", v.date);
        set("amount", amount);
        set("price", price);
        set("odometer", v.odometer);
      }
      this._hints();
      this._status(Object.keys(v).length ? this._t("checkValues") : this._t("nothingReadable"));
    } catch (err) {
      this._status(err?.message || this._t("scanFailed"), "err");
    }
  }

  _hints() {
    if (!this._built || !this._tab) return;
    const v = this._vehicle();
    const currency = this._hass.config?.currency || "";
    this.shadowRoot.querySelectorAll(".cur").forEach((el) => (el.textContent = currency ? `(${currency})` : ""));
    const odo = this._q("[name=odometer]");
    if (odo) odo.placeholder = v.odometer?.state && !isNaN(v.odometer.state) ? this._t("current", { value: Math.round(v.odometer.state) }) : "";
    if (this._tab === "service") {
      const select = this._q("[name=item]");
      const state = this._hass.states[select.value];
      const text = state ? this._remainingLong(state.attributes) || this._t("status." + state.state) : "";
      this._q(".item-state").textContent = text ? this._t("currently", { text }) : "";
      return;
    }
    const charge = this._tab === "charge";
    const last = (charge ? v.energy_price : v.fuel_price)?.state;
    const price = this._q("[name=price]");
    price.placeholder = last && !isNaN(last) ? this._t("last", { value: last }) : "";
    const total = Number(this._q("[name=amount]").value) * Number(price.value);
    this._q(".total").textContent = total > 0 ? this._t("total", { value: `${total.toFixed(2)} ${currency}` }) : "";
  }

  async _submit() {
    const hass = this._hass;
    const v = this._vehicle();
    const value = (n) => this._q(`[name=${n}]`)?.value ?? "";
    this._status(this._t("saving"));
    try {
      if (this._tab === "service") {
        const data = { entity_id: value("item"), date: value("date") };
        if (value("odometer") !== "") data.odometer = Number(value("odometer"));
        if (value("cost") !== "") data.cost = Number(value("cost"));
        if (this._receipt) data.receipt = this._receipt;
        await hass.callService("vehicle", "complete_service", data);
      } else {
        const charge = this._tab === "charge";
        const data = {
          entity_id: v.odometer.entity_id,
          date: value("date"),
          [charge ? "kwh" : "liters"]: Number(value("amount")),
          [charge ? "price_per_kwh" : "price_per_liter"]: Number(value("price")),
        };
        if (value("odometer") !== "") data.odometer = Number(value("odometer"));
        if (this._receipt) data.receipt = this._receipt;
        await hass.callService("vehicle", charge ? "add_charge" : "add_fuel", data);
        this._q("[name=amount]").value = "";
      }
      this._q("[name=odometer]").value = "";
      if (this._q("[name=cost]")) this._q("[name=cost]").value = "";
      this._clearReceipt();
      this._hints();
      this._status(this._t("saved"), "ok");
      const el = this._q(".status");
      setTimeout(() => {
        if (el.textContent === this._t("saved")) el.textContent = "";
      }, 4000);
    } catch (err) {
      this._status(err?.message || this._t("failed"), "err");
    }
  }

  _css() {
    return `
      .tabs { display:flex; border-bottom:1px solid var(--divider-color,#e0e0e0); margin-top:8px; }
      .tab { flex:1; text-align:center; padding:12px 0; font-weight:500; font-size:.9em; color:var(--secondary-text-color); display:flex; gap:6px; align-items:center; justify-content:center; cursor:pointer; }
      .tab.on { color:var(--primary-color,#03a9f4); box-shadow:inset 0 -2px 0 var(--primary-color,#03a9f4); }
      .tab ha-icon { --mdc-icon-size:18px; }
      form { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; padding:12px 16px 8px; }
      form { align-items:start; }
      label { display:flex; flex-direction:column; gap:4px; font-size:.8em; color:var(--secondary-text-color); min-width:0; }
      .lt { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-height:1.2em; }
      input[type=number] { -moz-appearance:textfield; appearance:textfield; }
      input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
      input, select { font:inherit; font-size:1rem; padding:8px; border-radius:6px; color:var(--primary-text-color); background:var(--secondary-background-color,#f5f5f5); border:1px solid var(--divider-color,#ccc); min-width:0; width:100%; box-sizing:border-box; }
      input:focus, select:focus { outline:2px solid var(--primary-color); outline-offset:-1px; }
      .full, .total, .actions, .drop { grid-column:1 / -1; }
      .drop { display:flex; align-items:center; gap:8px; flex-wrap:wrap; border:1.5px dashed var(--divider-color,#bdbdbd); border-radius:10px; padding:8px 10px; }
      .drop.has { border-style:solid; border-color:var(--primary-color,#03a9f4); }
      .drop .clip { color:var(--secondary-text-color); --mdc-icon-size:20px; }
      .rname { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .actions { display:flex; justify-content:space-between; align-items:center; gap:12px; }
      .btn { font:inherit; font-size:.9em; cursor:pointer; border-radius:6px; border:1px solid var(--divider-color,#ccc); background:transparent; color:var(--primary-text-color); padding:6px 10px; display:inline-flex; align-items:center; gap:6px; }
      .btn ha-icon { --mdc-icon-size:18px; }
      .btn.scan { color:var(--primary-color,#03a9f4); border-color:var(--primary-color,#03a9f4); }
      .btn.primary { background:var(--primary-color,#03a9f4); color:var(--text-primary-color,#fff); border-color:transparent; padding:9px 18px; font-weight:500; }
      .status.ok { color:var(--success-color,#43a047); }
      .status.err { color:var(--error-color,#db4437); }
    `;
  }
}

// ---------------------------------------------------------------------------------------------
// editors
// ---------------------------------------------------------------------------------------------
class VehicleCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    else this._render();
  }

  get _defaults() {
    return {};
  }

  _data() {
    // YAML cards may use `entity`; show (and, once edited, save) the vehicle instead
    const { entity, ...rest } = this._config;
    const device = rest.device || this._hass.entities?.[entity]?.device_id;
    return { ...this._defaults, ...(device ? { ...rest, device } : this._config) };
  }

  _schema() {
    return [];
  }

  _labels() {
    return {};
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        // only store what differs from the defaults, so the card YAML stays short
        const config = { ...ev.detail.value };
        for (const [key, value] of Object.entries(this._defaults)) {
          if (JSON.stringify(config[key]) === JSON.stringify(value)) delete config[key];
        }
        for (const key of Object.keys(config)) if (config[key] === "" || config[key] === undefined) delete config[key];
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._data();
    this._form.schema = this._schema();
    this._form.computeLabel = (s) => this._labels()[s.name] || s.name;
  }
}

const BOOL = { boolean: {} };
const DEVICE = { name: "device", required: true, selector: { device: { integration: "vehicle" } } };
const group = (title, schema) => ({ type: "expandable", name: "", title, flatten: true, schema });
const num = (min, max) => ({ number: { min, max, step: 1, mode: "box" } });
const choice = (options) => ({ select: { mode: "dropdown", options } });

class VehicleInfoCardEditor extends VehicleCardEditor {
  get _defaults() {
    return INFO_DEFAULTS;
  }

  _schema() {
    const t = (key) => tr(this._hass, key);
    return [
      DEVICE,
      { name: "layout", selector: choice([{ value: "normal", label: t("layoutNormal") }, { value: "compact", label: t("layoutCompact") }, { value: "minimal", label: t("layoutMinimal") }]) },
      group(t("header"), [{ name: "show_title", selector: BOOL }, { name: "title", selector: { text: {} } }, { name: "icon", selector: { icon: {} } }, { name: "show_odometer", selector: BOOL }]),
      group(t("statistics"), [{ name: "show_consumption", selector: BOOL }, { name: "show_costs", selector: BOOL }, { name: "show_cost_split", selector: BOOL }]),
      group(t("serviceItems"), [
        { name: "show_services", selector: BOOL },
        { name: "service_layout", selector: choice([{ value: "auto", label: t("layoutAuto") }, { value: "list", label: t("layoutList") }, { value: "rows", label: t("layoutRows") }, { value: "chips", label: t("layoutChips") }]) },
        { name: "service_filter", selector: choice([{ value: "all", label: t("filterAll") }, { value: "attention", label: t("filterAttention") }]) },
        { name: "max_services", selector: num(0, 50) },
        { name: "show_headings", selector: BOOL },
      ]),
    ];
  }

  _labels() {
    const t = (key) => tr(this._hass, key);
    return {
      device: t("vehicle"), layout: t("layout"), show_title: t("showTitle"), title: t("titleEmpty"), icon: t("icon"), show_odometer: t("showOdometer"),
      show_consumption: t("showConsumption"), show_costs: t("showCosts"), show_cost_split: t("showCostSplit"),
      show_services: t("showServices"), service_layout: t("serviceLayout"), service_filter: t("serviceFilter"),
      max_services: t("maxServices"), show_headings: t("showHeadings"),
    };
  }
}

class VehicleActivityCardEditor extends VehicleCardEditor {
  get _defaults() {
    return ACTIVITY_DEFAULTS;
  }

  _schema() {
    const t = (key) => tr(this._hass, key);
    return [
      DEVICE,
      group(t("header"), [{ name: "show_title", selector: BOOL }, { name: "title", selector: { text: {} } }, { name: "icon", selector: { icon: {} } }]),
      group(t("showTheseTypes"), [{ name: "show_refuels", selector: BOOL }, { name: "show_charges", selector: BOOL }, { name: "show_service", selector: BOOL }]),
      group(t("list"), [
        { name: "entries", selector: num(1, 40) },
        { name: "show_filters", selector: BOOL },
        { name: "group_by_month", selector: BOOL },
        { name: "show_costs", selector: BOOL },
        { name: "show_files", selector: BOOL },
        { name: "allow_edit", selector: BOOL },
      ]),
    ];
  }

  _labels() {
    const t = (key) => tr(this._hass, key);
    return {
      device: t("vehicle"), show_title: t("showTitle"), title: t("titleAuto"), icon: t("icon"),
      show_refuels: t("optRefuels"), show_charges: t("optCharges"), show_service: t("optService"),
      entries: t("entries"), show_filters: t("showFilters"), group_by_month: t("groupByMonth"),
      show_costs: t("showCostsPerEntry"), show_files: t("showFiles"), allow_edit: t("allowEdit"),
    };
  }
}

class VehicleEntryCardEditor extends VehicleCardEditor {
  get _defaults() {
    return ENTRY_DEFAULTS;
  }

  _schema() {
    const t = (key) => tr(this._hass, key);
    return [
      DEVICE,
      group(t("header"), [{ name: "show_title", selector: BOOL }, { name: "title", selector: { text: {} } }, { name: "icon", selector: { icon: {} } }]),
      group(t("showTheseTabs"), [{ name: "show_refuel", selector: BOOL }, { name: "show_charge", selector: BOOL }, { name: "show_service", selector: BOOL }]),
    ];
  }

  _labels() {
    const t = (key) => tr(this._hass, key);
    return {
      device: t("vehicle"), show_title: t("showTitle"), title: t("titleAuto"), icon: t("icon"),
      show_refuel: t("tabRefuel"), show_charge: t("tabCharge"), show_service: t("tabService"),
    };
  }
}

// ---------------------------------------------------------------------------------------------
// registration
// ---------------------------------------------------------------------------------------------
// Home Assistant's frontend swaps window.customElements for a scoped-registry polyfill while it
// boots. When this file is served from the service worker cache it can run *before* that swap,
// and elements defined on the old registry are then invisible to the dashboard ("Custom element
// doesn't exist"). So define the elements only once the frontend itself is up.
const defineAll = () => {
  const elements = {
    "vehicle-info-card": VehicleInfoCard,
    "vehicle-info-card-editor": VehicleInfoCardEditor,
    "vehicle-activity-card": VehicleActivityCard,
    "vehicle-activity-card-editor": VehicleActivityCardEditor,
    "vehicle-entry-card": VehicleEntryCard,
    "vehicle-entry-card-editor": VehicleEntryCardEditor,
  };
  for (const [tag, cls] of Object.entries(elements)) {
    if (!customElements.get(tag)) customElements.define(tag, cls);
  }
};
if (customElements.get("home-assistant")) defineAll();
else customElements.whenDefined("home-assistant").then(defineAll);

window.customCards = window.customCards || [];
for (const card of [
  { type: "vehicle-info-card", name: "Vehicle info", description: "Mileage, consumption, monthly costs and service status of a vehicle." },
  { type: "vehicle-activity-card", name: "Vehicle activity", description: "Timeline of refuels, charges and services with links to receipts and invoices." },
  { type: "vehicle-entry-card", name: "Vehicle: add entry", description: "Add a refuel, charge or completed service, with receipt upload." },
]) {
  if (!window.customCards.some((c) => c.type === card.type)) window.customCards.push(card);
}

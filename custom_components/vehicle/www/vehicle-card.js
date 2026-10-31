/* Vehicle overview card for the ha-vehicle integration. */
const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const STATUS_ORDER = { overdue: 0, due_soon: 1, ok: 2, unknown: 3 };
const STATUS_COLOR = {
  overdue: "var(--error-color, #db4437)",
  due_soon: "var(--warning-color, #ffa600)",
  ok: "var(--success-color, #43a047)",
  unknown: "var(--secondary-text-color)",
};
const STATUS_LABEL = { overdue: "Overdue", due_soon: "Due soon", ok: "OK", unknown: "Not tracked yet" };

class VehicleCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Select an entity of your vehicle (e.g. its odometer).");
    this._config = { show_stats: true, show_log: true, ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 5;
  }

  static getConfigElement() {
    return document.createElement("vehicle-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.entities || {}).find(
      (id) => hass.entities[id].platform === "vehicle" && hass.entities[id].translation_key === "odometer"
    );
    return { entity: entity || "" };
  }

  _vehicleEntities() {
    const hass = this._hass;
    const reg = hass.entities?.[this._config.entity];
    const result = { items: [] };
    if (!reg?.device_id) return result;
    for (const [id, e] of Object.entries(hass.entities)) {
      if (e.device_id !== reg.device_id || e.platform !== "vehicle") continue;
      const state = hass.states[id];
      if (!state) continue;
      if (e.translation_key === "service_status") result.items.push(state);
      else if (e.translation_key) result[e.translation_key] = state;
    }
    result.device = hass.devices?.[reg.device_id];
    return result;
  }

  _fmt(value, digits = 0) {
    if (value === null || value === undefined || value === "unknown" || value === "unavailable") return "–";
    return Number(value).toLocaleString(this._hass.locale?.language, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  _remaining(a) {
    const parts = [];
    const d = a.days_remaining;
    const km = a.km_remaining;
    if (d !== null && d !== undefined) parts.push(d < 0 ? `${-d} d overdue` : d === 0 ? "today" : `in ${d} d`);
    if (km !== null && km !== undefined) parts.push(km < 0 ? `${this._fmt(-km)} km overdue` : `${this._fmt(km)} km left`);
    return parts.join(" · ");
  }

  _render() {
    if (!this._config || !this._hass || !this.shadowRoot) return;
    const cfg = this._config;
    const hass = this._hass;
    const v = this._vehicleEntities();
    const odo = v.odometer;
    if (!odo) {
      this.shadowRoot.innerHTML = `<ha-card><div class="empty">Vehicle entities not found for ${esc(cfg.entity)}.</div></ha-card>${this._style()}`;
      return;
    }
    const title = cfg.title || v.device?.name_by_user || v.device?.name || "Vehicle";
    const currency = hass.config?.currency || "";

    const items = [...v.items].sort((a, b) => {
      const d = STATUS_ORDER[a.state] - STATUS_ORDER[b.state];
      if (d) return d;
      return (a.attributes.days_remaining ?? 1e9) - (b.attributes.days_remaining ?? 1e9);
    });
    const prefix = v.device?.name_by_user || v.device?.name || "";
    const itemName = (s) => {
      const n = s.attributes.friendly_name || s.entity_id;
      return prefix && n.startsWith(prefix + " ") ? n.slice(prefix.length + 1) : n;
    };

    const stat = (label, value) => `<div class="stat"><span class="v">${value}</span><span class="l">${esc(label)}</span></div>`;
    const stats = [];
    if (v.fuel_consumption) stats.push(stat("Fuel", `${this._fmt(v.fuel_consumption.state, 1)} <small>L/100km</small>`));
    if (v.energy_consumption) stats.push(stat("Energy", `${this._fmt(v.energy_consumption.state, 1)} <small>kWh/100km</small>`));
    if (v.fuel_price) stats.push(stat("Fuel price", `${this._fmt(v.fuel_price.state, 3)} <small>${esc(currency)}/L</small>`));
    if (v.energy_price) stats.push(stat("Energy price", `${this._fmt(v.energy_price.state, 3)} <small>${esc(currency)}/kWh</small>`));
    if (v.cost_per_km) stats.push(stat("Cost/km", `${this._fmt(v.cost_per_km.state, 3)} <small>${esc(currency)}</small>`));
    if (v.monthly_cost) stats.push(stat("This month", `${this._fmt(v.monthly_cost.state, 2)} <small>${esc(currency)}</small>`));

    const log = (odo.attributes.recent_log || []).slice(0, 5);
    const logRows = log
      .map((e) => {
        const unit = e.kind === "charge" ? "kWh" : "L";
        const cost = e.cost != null ? `${this._fmt(e.cost, 2)} ${esc(currency)}` : "";
        const price = e.price != null ? `${this._fmt(e.price, 3)}/${e.kind === "charge" ? "kWh" : "L"}` : "";
        const km = e.odometer != null ? `${this._fmt(e.odometer)} km` : "";
        return `<div class="log"><ha-icon icon="${e.kind === "charge" ? "mdi:ev-station" : "mdi:gas-station"}"></ha-icon>
          <span class="grow">${esc(e.date)} · ${this._fmt(e.amount, 1)} ${unit}</span><span class="muted">${[price, cost, km].filter(Boolean).join(" · ")}</span></div>`;
      })
      .join("");

    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="header">
          <div class="title"><ha-icon icon="mdi:car"></ha-icon>${esc(title)}</div>
          <div class="odo">${this._fmt(odo.state)} <small>km</small></div>
        </div>
        ${cfg.show_stats && stats.length ? `<div class="stats">${stats.join("")}</div>` : ""}
        <div class="section">Service</div>
        ${
          items.length
            ? items
                .map(
                  (s) => `<div class="item">
              <span class="dot" style="background:${STATUS_COLOR[s.state] || STATUS_COLOR.unknown}"></span>
              <div class="grow"><div>${esc(itemName(s))}</div>
              <div class="muted">${esc(this._remaining(s.attributes) || STATUS_LABEL[s.state] || s.state)}</div></div>
              <ha-icon-button class="done" data-entity="${esc(s.entity_id)}" title="Mark as done"><ha-icon icon="mdi:check"></ha-icon></ha-icon-button>
            </div>`
                )
                .join("")
            : `<div class="empty">No service items yet. Add them on the integration page.</div>`
        }
        ${cfg.show_log && logRows ? `<div class="section">Recent refuels &amp; charges</div>${logRows}` : ""}
      </ha-card>${this._style()}`;

    this.shadowRoot.querySelectorAll(".done").forEach((btn) =>
      btn.addEventListener("click", () => {
        const id = btn.dataset.entity;
        if (window.confirm("Mark this service item as done today?")) {
          hass.callService("vehicle", "complete_service", { entity_id: id });
        }
      })
    );
  }

  _style() {
    return `<style>
      ha-card { padding-bottom: 8px; }
      .header { display:flex; justify-content:space-between; align-items:baseline; padding:16px 16px 4px; }
      .title { display:flex; align-items:center; gap:8px; font-size:1.2em; font-weight:500; }
      .odo { font-size:1.4em; font-weight:500; }
      small { font-size:.6em; color:var(--secondary-text-color); font-weight:400; }
      .stats { display:flex; flex-wrap:wrap; gap:8px 20px; padding:4px 16px 8px; }
      .stat { display:flex; flex-direction:column; }
      .stat .v { font-weight:500; }
      .stat .l, .muted { font-size:.85em; color:var(--secondary-text-color); }
      .section { padding:12px 16px 4px; font-size:.8em; text-transform:uppercase; letter-spacing:.06em; color:var(--secondary-text-color); }
      .item, .log { display:flex; align-items:center; gap:12px; padding:4px 16px; min-height:40px; }
      .grow { flex:1; min-width:0; }
      .dot { width:10px; height:10px; border-radius:50%; flex:none; }
      .empty { padding:16px; color:var(--secondary-text-color); }
      .log ha-icon { --mdc-icon-size:18px; color:var(--secondary-text-color); }
    </style>`;
  }
}

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

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: ev.detail.value }, bubbles: true, composed: true })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      { name: "entity", required: true, selector: { entity: { integration: "vehicle", domain: "sensor" } } },
      { name: "title", selector: { text: {} } },
      { name: "show_stats", selector: { boolean: {} } },
      { name: "show_log", selector: { boolean: {} } },
    ];
    this._form.computeLabel = (s) =>
      ({ entity: "Vehicle (any sensor, e.g. odometer)", title: "Title", show_stats: "Show statistics", show_log: "Show recent refuels" })[s.name] || s.name;
  }
}

customElements.define("vehicle-card", VehicleCard);
customElements.define("vehicle-card-editor", VehicleCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "vehicle-card",
  name: "Vehicle",
  description: "Odometer, service status, consumption and recent refuels of a vehicle.",
});

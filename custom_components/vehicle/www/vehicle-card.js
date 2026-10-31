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

const findVehicle = (hass, entityId) => {
  const reg = hass.entities?.[entityId];
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
};

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
    return findVehicle(this._hass, this._config.entity);
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
      .item, .log { display:flex; align-items:center; flex-wrap:wrap; gap:4px 12px; padding:4px 16px; min-height:40px; }
      .grow { flex:1; min-width:120px; }
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

  _schema() {
    return [
      { name: "entity", required: true, selector: { entity: { integration: "vehicle", domain: "sensor" } } },
      { name: "title", selector: { text: {} } },
      { name: "show_stats", selector: { boolean: {} } },
      { name: "show_log", selector: { boolean: {} } },
    ];
  }

  _labels() {
    return { entity: "Vehicle (any sensor, e.g. odometer)", title: "Title", show_stats: "Show statistics", show_log: "Show recent refuels" };
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
    this._form.schema = this._schema();
    this._form.computeLabel = (s) => this._labels()[s.name] || s.name;
  }
}

class VehicleLogCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Select an entity of your vehicle (e.g. its odometer).");
    this._config = config;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._built = false;
    if (this._hass) this._build();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    else this._hints();
  }

  getCardSize() {
    return 4;
  }

  static getConfigElement() {
    return document.createElement("vehicle-log-card-editor");
  }

  static getStubConfig(hass) {
    return VehicleCard.getStubConfig(hass);
  }

  _fuelType() {
    return findVehicle(this._hass, this._config.entity).odometer?.attributes.fuel_type;
  }

  _build() {
    const v = findVehicle(this._hass, this._config.entity);
    if (!v.odometer) {
      this.shadowRoot.innerHTML = `<ha-card><div class="empty">Vehicle entities not found for ${esc(this._config.entity)}.</div></ha-card>${this._style()}`;
      return;
    }
    this._built = true;
    const type = v.odometer.attributes.fuel_type;
    this._kind = type === "electric" ? "charge" : "fuel";
    const title = this._config.title || `Add ${type === "electric" ? "charge" : type === "hybrid" ? "fuel or charge" : "refuel"}`;
    const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);

    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="header"><div class="title"><ha-icon icon="mdi:gas-station"></ha-icon>${esc(title)}</div></div>
        ${type === "hybrid" ? `<div class="tabs"><button data-kind="fuel" class="active">Fuel</button><button data-kind="charge">Charge</button></div>` : ""}
        <form>
          <label>Date<input name="date" type="date" value="${today}" required></label>
          <label><span class="amount-label"></span><input name="amount" type="number" step="0.01" min="0" inputmode="decimal" required></label>
          <label><span class="price-label"></span><input name="price" type="number" step="0.001" min="0" inputmode="decimal" required></label>
          <label>Odometer (km, optional)<input name="odometer" type="number" step="0.1" min="0" inputmode="decimal"></label>
          <div class="total muted"></div>
          <div class="actions"><span class="status"></span><button type="submit" class="primary">Add</button></div>
        </form>
      </ha-card>${this._style()}`;

    const root = this.shadowRoot;
    this._price = root.querySelector("[name=price]");
    this._amount = root.querySelector("[name=amount]");
    this._odo = root.querySelector("[name=odometer]");
    root.querySelectorAll(".tabs button").forEach((b) =>
      b.addEventListener("click", () => {
        this._kind = b.dataset.kind;
        root.querySelectorAll(".tabs button").forEach((x) => x.classList.toggle("active", x === b));
        this._price.value = "";
        this._hints();
      })
    );
    [this._amount, this._price].forEach((i) => i.addEventListener("input", () => this._hints()));
    root.querySelector("form").addEventListener("submit", (ev) => {
      ev.preventDefault();
      this._submit();
    });
    this._hints();
  }

  _hints() {
    if (!this._built) return;
    const v = findVehicle(this._hass, this._config.entity);
    const charge = this._kind === "charge";
    const unit = charge ? "kWh" : "L";
    const currency = this._hass.config?.currency || "";
    const root = this.shadowRoot;
    root.querySelector(".amount-label").textContent = charge ? "Energy (kWh)" : "Liters";
    root.querySelector(".price-label").textContent = `Price per ${unit} (${currency})`;
    const last = (charge ? v.energy_price : v.fuel_price)?.state;
    this._price.placeholder = last && !isNaN(last) ? `last: ${last}` : "";
    const odo = v.odometer?.state;
    this._odo.placeholder = odo && !isNaN(odo) ? `current: ${Math.round(odo)}` : "";
    const total = Number(this._amount.value) * Number(this._price.value);
    root.querySelector(".total").textContent = total > 0 ? `Total: ${total.toFixed(2)} ${currency}` : "";
  }

  async _submit() {
    const root = this.shadowRoot;
    const status = root.querySelector(".status");
    const charge = this._kind === "charge";
    const data = {
      entity_id: this._config.entity,
      date: root.querySelector("[name=date]").value,
      [charge ? "kwh" : "liters"]: Number(this._amount.value),
      [charge ? "price_per_kwh" : "price_per_liter"]: Number(this._price.value),
    };
    if (this._odo.value !== "") data.odometer = Number(this._odo.value);
    status.className = "status";
    status.textContent = "Saving…";
    try {
      await this._hass.callService("vehicle", charge ? "add_charge" : "add_fuel", data);
      status.className = "status ok";
      status.textContent = "Saved";
      this._amount.value = "";
      this._odo.value = "";
      this._hints();
      setTimeout(() => { if (status.textContent === "Saved") status.textContent = ""; }, 4000);
    } catch (err) {
      status.className = "status err";
      status.textContent = err?.message || "Failed";
    }
  }

  _style() {
    return `<style>
      .header { padding:16px 16px 4px; }
      .title { display:flex; align-items:center; gap:8px; font-size:1.2em; font-weight:500; }
      .empty { padding:16px; color:var(--secondary-text-color); }
      .muted { font-size:.85em; color:var(--secondary-text-color); }
      form { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; padding:8px 16px 16px; }
      label { display:flex; flex-direction:column; gap:4px; font-size:.85em; color:var(--secondary-text-color); }
      input { font:inherit; font-size:1rem; padding:8px; border-radius:6px; color:var(--primary-text-color);
        background:var(--secondary-background-color, #f5f5f5); border:1px solid var(--divider-color, #ccc); min-width:0; width:100%; box-sizing:border-box; }
      input:focus { outline:2px solid var(--primary-color); outline-offset:-1px; }
      .total, .actions { grid-column:1 / -1; }
      .actions { display:flex; justify-content:space-between; align-items:center; gap:12px; }
      button { font:inherit; cursor:pointer; border-radius:6px; border:1px solid var(--divider-color, #ccc);
        background:transparent; color:var(--primary-text-color); padding:8px 16px; }
      button.primary { background:var(--primary-color); color:var(--text-primary-color, #fff); border-color:transparent; }
      .tabs { display:flex; gap:8px; padding:8px 16px 0; }
      .tabs button.active { background:var(--primary-color); color:var(--text-primary-color, #fff); border-color:transparent; }
      .status.ok { color:var(--success-color, #43a047); }
      .status.err { color:var(--error-color, #db4437); }
    </style>`;
  }
}

class VehicleLogCardEditor extends VehicleCardEditor {
  _schema() {
    return [
      { name: "entity", required: true, selector: { entity: { integration: "vehicle", domain: "sensor" } } },
      { name: "title", selector: { text: {} } },
    ];
  }

  _labels() {
    return { entity: "Vehicle (any sensor, e.g. odometer)", title: "Title" };
  }
}

customElements.define("vehicle-card", VehicleCard);
customElements.define("vehicle-card-editor", VehicleCardEditor);
customElements.define("vehicle-log-card", VehicleLogCard);
customElements.define("vehicle-log-card-editor", VehicleLogCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "vehicle-card",
  name: "Vehicle",
  description: "Odometer, service status, consumption and recent refuels of a vehicle.",
});
window.customCards.push({
  type: "vehicle-log-card",
  name: "Vehicle: add fuel / charge",
  description: "Form to log a refuel or charging session with price per unit.",
});

class BlomsterMaintenanceCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      title: "Underhållshistorik",
      empty_text: "Inget underhåll har registrerats ännu.",
      max_rows: 20,
      show_delete: true,
      ...config,
    };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return 5; }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _formatDate(value) {
    if (!value) return "Aldrig registrerat";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("sv-SE", {
      year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    }).format(date);
  }

  _formatNumber(value, unit) {
    if (value === null || value === undefined) return "–";
    const formatted = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1 }).format(value);
    return `${formatted}${unit ? ` ${unit}` : ""}`;
  }

  _entityIds() {
    if (Array.isArray(this._config.entities) && this._config.entities.length) return this._config.entities;
    return Object.entries(this._hass?.states || {})
      .filter(([entityId, state]) => entityId.startsWith("sensor.") && state.attributes?.item_id && Array.isArray(state.attributes?.history))
      .map(([entityId]) => entityId);
  }

  _collectRows() {
    const rows = [];
    for (const entityId of this._entityIds()) {
      const state = this._hass?.states?.[entityId];
      if (!state) continue;
      const name = state.attributes.friendly_name || entityId;
      const itemId = state.attributes.item_id;
      const history = Array.isArray(state.attributes.history) ? state.attributes.history : [];
      let previousMeterValue = null;
      let previousMeterUnit = null;
      for (const event of history) {
        let meterDelta = null;
        if (
          previousMeterValue !== null && event.meter_value !== null && event.meter_value !== undefined &&
          (!previousMeterUnit || !event.meter_unit || previousMeterUnit === event.meter_unit)
        ) {
          meterDelta = Math.max(0, Number(event.meter_value) - Number(previousMeterValue));
        }
        rows.push({ ...event, meter_delta: meterDelta, name, itemId, entityId });
        if (event.meter_value !== null && event.meter_value !== undefined) {
          previousMeterValue = event.meter_value;
          previousMeterUnit = event.meter_unit || null;
        }
      }
    }
    rows.sort((a, b) => new Date(b.performed_at) - new Date(a.performed_at));
    return rows.slice(0, Number(this._config.max_rows) || 20);
  }

  async _deleteEvent(itemId, eventId, name) {
    if (!itemId || !eventId) return;
    if (!confirm(`Ta bort underhållsposten för ${name}?`)) return;
    try {
      await this._hass.callService("blomster_maintenance", "delete_maintenance", { item_id: itemId, event_id: eventId });
    } catch (error) {
      alert(`Det gick inte att ta bort posten: ${error?.message || error}`);
    }
  }

  _bindActions() {
    this.shadowRoot.querySelectorAll("button[data-event-id]").forEach((button) => {
      button.addEventListener("click", () => this._deleteEvent(button.dataset.itemId, button.dataset.eventId, button.dataset.name));
    });
  }

  _render() {
    if (!this.shadowRoot || !this._hass || !this._config) return;
    const rows = this._collectRows();
    const actionHeader = this._config.show_delete ? "<th>Åtgärd</th>" : "";
    const colspan = this._config.show_delete ? 6 : 5;
    const body = rows.length
      ? rows.map((event) => `
          <tr>
            <td>${this._escape(this._formatDate(event.performed_at))}</td>
            <td>${this._escape(event.name)}</td>
            <td class="meter">${this._escape(this._formatNumber(event.meter_value, event.meter_unit))}</td>
            <td class="meter">${this._escape(this._formatNumber(event.meter_delta, event.meter_unit))}</td>
            <td>${this._escape(event.note || "–")}</td>
            ${this._config.show_delete ? `<td class="action"><button type="button" data-item-id="${this._escape(event.itemId)}" data-event-id="${this._escape(event.event_id)}" data-name="${this._escape(event.name)}">Ta bort</button></td>` : ""}
          </tr>`).join("")
      : `<tr><td colspan="${colspan}" class="empty">${this._escape(this._config.empty_text)}</td></tr>`;

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { overflow: hidden; }
        .header { padding: 20px 20px 12px; font-size: 24px; font-weight: 400; }
        .wrap { overflow-x: auto; padding: 0 16px 16px; }
        table { width: 100%; border-collapse: collapse; min-width: 760px; }
        th { text-align: left; font-size: 13px; color: var(--secondary-text-color); padding: 10px 12px; border-bottom: 1px solid var(--divider-color); }
        td { padding: 12px; border-bottom: 1px solid var(--divider-color); vertical-align: top; }
        tbody tr:last-child td { border-bottom: 0; }
        .meter, th:nth-child(3), th:nth-child(4) { text-align: right; white-space: nowrap; }
        td:first-child { white-space: nowrap; }
        .action { text-align: right; white-space: nowrap; }
        button { border: 0; border-radius: 8px; padding: 7px 10px; cursor: pointer; background: var(--error-color); color: white; font: inherit; }
        .empty { text-align: center; color: var(--secondary-text-color); padding: 24px 12px; }
      </style>
      <ha-card>
        <div class="header">${this._escape(this._config.title)}</div>
        <div class="wrap"><table><thead><tr>
          <th>Datum</th><th>Underhåll</th><th>Mätarvärde</th><th>Diff</th><th>Anteckning</th>${actionHeader}
        </tr></thead><tbody>${body}</tbody></table></div>
      </ha-card>`;
    this._bindActions();
  }
}

class BlomsterMaintenanceManagerCard extends HTMLElement {
  setConfig(config) {
    this._config = { title: "Underhåll", ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot?.activeElement) this._render();
  }

  getCardSize() { return 7; }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  _items() {
    return Object.entries(this._hass?.states || {})
      .filter(([entityId, state]) => entityId.startsWith("sensor.") && state.attributes?.item_id && Array.isArray(state.attributes?.history))
      .map(([entityId, state]) => ({ entityId, state }))
      .sort((a, b) => (a.state.attributes.friendly_name || a.entityId).localeCompare(b.state.attributes.friendly_name || b.entityId, "sv"));
  }

  _numericSensors() {
    return Object.entries(this._hass?.states || {})
      .filter(([entityId, state]) => entityId.startsWith("sensor.") && !Number.isNaN(Number(state.state)) && !state.attributes?.item_id)
      .sort((a, b) => (a[1].attributes.friendly_name || a[0]).localeCompare(b[1].attributes.friendly_name || b[0], "sv"));
  }

  _slug(name) {
    return name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "underhall";
  }

  _uniqueId(name) {
    const used = new Set(this._items().map(({ state }) => state.attributes.item_id));
    const base = this._slug(name);
    if (!used.has(base)) return base;
    let index = 2;
    while (used.has(`${base}_${index}`)) index += 1;
    return `${base}_${index}`;
  }

  _status(state) {
    const attrs = state.attributes;
    if (!attrs.registered) return "Aldrig registrerat";
    if (attrs.next_due) {
      const due = new Date(attrs.next_due);
      return `${attrs.status === "overdue" ? "Försenat" : "Nästa"}: ${new Intl.DateTimeFormat("sv-SE", { dateStyle: "medium" }).format(due)}`;
    }
    if (attrs.remaining !== null && attrs.remaining !== undefined && attrs.meter_entity) {
      const meter = this._hass.states[attrs.meter_entity];
      const unit = meter?.attributes?.unit_of_measurement || "";
      return `${new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1 }).format(Math.max(0, attrs.remaining))}${unit ? ` ${unit}` : ""} kvar`;
    }
    return "Registrerat";
  }

  async _record(itemId, name) {
    if (!confirm(`Registrera utfört underhåll: ${name}?`)) return;
    try {
      await this._hass.callService("blomster_maintenance", "record_maintenance", { item_id: itemId, name });
    } catch (error) {
      alert(`Det gick inte att registrera underhållet: ${error?.message || error}`);
    }
  }

  async _create() {
    const name = this.shadowRoot.querySelector("#name")?.value.trim();
    const mode = this.shadowRoot.querySelector("#mode")?.value;
    const value = Number(this.shadowRoot.querySelector("#interval")?.value);
    if (!name || !Number.isFinite(value) || value <= 0) {
      alert("Fyll i namn och ett intervall större än 0.");
      return;
    }
    const data = { item_id: this._uniqueId(name), name, interval_value: value };
    if (mode === "time") {
      data.interval_type = this.shadowRoot.querySelector("#time-unit")?.value || "months";
    } else {
      const meterEntity = this.shadowRoot.querySelector("#meter")?.value;
      if (!meterEntity) {
        alert("Välj en mätare/sensor.");
        return;
      }
      data.interval_type = "meter";
      data.meter_entity = meterEntity;
    }
    try {
      await this._hass.callService("blomster_maintenance", "configure_item", data);
      this._render();
    } catch (error) {
      alert(`Det gick inte att skapa underhållsobjektet: ${error?.message || error}`);
    }
  }

  _bind() {
    this.shadowRoot.querySelectorAll("button[data-record]").forEach((button) => {
      button.addEventListener("click", () => this._record(button.dataset.itemId, button.dataset.name));
    });
    this.shadowRoot.querySelector("#create")?.addEventListener("click", () => this._create());
    this.shadowRoot.querySelector("#mode")?.addEventListener("change", () => this._render());
  }

  _render() {
    if (!this.shadowRoot || !this._hass || !this._config) return;
    const items = this._items();
    const previousMode = this.shadowRoot.querySelector("#mode")?.value || "time";
    const sensors = this._numericSensors();
    const itemHtml = items.length ? items.map(({ state }) => {
      const name = state.attributes.friendly_name || state.attributes.item_id;
      return `<div class="item">
        <div><strong>${this._escape(name)}</strong><div class="status">${this._escape(this._status(state))}</div></div>
        <button type="button" data-record data-item-id="${this._escape(state.attributes.item_id)}" data-name="${this._escape(name)}">Registrera utfört</button>
      </div>`;
    }).join("") : `<div class="empty">Inga underhållsobjekt ännu.</div>`;

    const meterOptions = sensors.map(([entityId, state]) => {
      const name = state.attributes.friendly_name || entityId;
      const unit = state.attributes.unit_of_measurement ? ` · ${state.attributes.unit_of_measurement}` : "";
      return `<option value="${this._escape(entityId)}">${this._escape(`${name}${unit}`)}</option>`;
    }).join("");

    this.shadowRoot.innerHTML = `
      <style>
        .header { padding: 20px 20px 8px; font-size: 24px; }
        .items, .create { padding: 8px 20px 20px; }
        .item { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:12px 0; border-bottom:1px solid var(--divider-color); }
        .status { color:var(--secondary-text-color); font-size:13px; margin-top:4px; }
        button { border:0; border-radius:10px; padding:9px 12px; cursor:pointer; background:var(--primary-color); color:white; font:inherit; }
        .create { border-top:1px solid var(--divider-color); display:grid; grid-template-columns:2fr 1fr 1fr 2fr auto; gap:10px; align-items:end; }
        label { display:flex; flex-direction:column; gap:5px; color:var(--secondary-text-color); font-size:12px; }
        input, select { box-sizing:border-box; width:100%; min-height:40px; padding:8px; border:1px solid var(--divider-color); border-radius:8px; background:var(--card-background-color); color:var(--primary-text-color); }
        .empty { color:var(--secondary-text-color); padding:8px 0; }
        @media (max-width:800px) { .create { grid-template-columns:1fr 1fr; } .wide { grid-column:1 / -1; } }
      </style>
      <ha-card>
        <div class="header">${this._escape(this._config.title)}</div>
        <div class="items">${itemHtml}</div>
        <div class="create">
          <label class="wide">Namn<input id="name" type="text" placeholder="T.ex. Service värmepump"></label>
          <label>Typ<select id="mode"><option value="time" ${previousMode === "time" ? "selected" : ""}>Tid</option><option value="meter" ${previousMode === "meter" ? "selected" : ""}>Mätare</option></select></label>
          <label>Intervall<input id="interval" type="number" min="1" step="1" value="1"></label>
          ${previousMode === "time" ? `<label>Enhet<select id="time-unit"><option value="days">Dagar</option><option value="weeks">Veckor</option><option value="months" selected>Månader</option><option value="years">År</option></select></label>` : `<label class="wide">Mätare/sensor<select id="meter"><option value="">Välj sensor…</option>${meterOptions}</select></label>`}
          <button id="create" type="button">Lägg till</button>
        </div>
      </ha-card>`;
    this._bind();
  }
}

customElements.define("blomster-maintenance-card", BlomsterMaintenanceCard);
customElements.define("blomster-maintenance-manager-card", BlomsterMaintenanceManagerCard);

window.customCards = window.customCards || [];
window.customCards.push(
  { type: "blomster-maintenance-card", name: "Blomster underhållshistorik", description: "Visar all registrerad underhållshistorik dynamiskt.", preview: true },
  { type: "blomster-maintenance-manager-card", name: "Blomster underhåll", description: "Skapar underhållsobjekt och registrerar utfört underhåll.", preview: true },
);

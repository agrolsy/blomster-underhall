class BlomsterMaintenanceCard extends HTMLElement {
  setConfig(config) {
    if (!config.entities || !Array.isArray(config.entities) || config.entities.length === 0) {
      throw new Error("Du måste ange minst en entitet");
    }
    this._config = {
      title: "Underhållshistorik",
      empty_text: "Inget underhåll har registrerats ännu.",
      max_rows: 20,
      ...config,
    };
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 5;
  }

  _formatDate(value) {
    if (!value) return "Aldrig registrerat";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("sv-SE", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  _formatMeter(event) {
    if (event.meter_value === null || event.meter_value === undefined) return "–";
    const value = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1 }).format(event.meter_value);
    return `${value}${event.meter_unit ? ` ${event.meter_unit}` : ""}`;
  }

  _collectRows() {
    const rows = [];
    for (const entityId of this._config.entities) {
      const state = this._hass?.states?.[entityId];
      if (!state) continue;
      const name = state.attributes.friendly_name || entityId;
      const history = Array.isArray(state.attributes.history) ? state.attributes.history : [];
      for (const event of history) {
        rows.push({ ...event, name, entityId });
      }
    }
    rows.sort((a, b) => new Date(b.performed_at) - new Date(a.performed_at));
    return rows.slice(0, Number(this._config.max_rows) || 20);
  }

  _render() {
    if (!this.shadowRoot || !this._hass || !this._config) return;
    const rows = this._collectRows();
    const body = rows.length
      ? rows.map((event) => `
          <tr>
            <td>${this._formatDate(event.performed_at)}</td>
            <td>${event.name}</td>
            <td class="meter">${this._formatMeter(event)}</td>
            <td>${event.note || "–"}</td>
          </tr>`).join("")
      : `<tr><td colspan="4" class="empty">${this._config.empty_text}</td></tr>`;

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { overflow: hidden; }
        .header { padding: 20px 20px 12px; font-size: 24px; font-weight: 400; }
        .wrap { overflow-x: auto; padding: 0 16px 16px; }
        table { width: 100%; border-collapse: collapse; min-width: 560px; }
        th { text-align: left; font-size: 13px; color: var(--secondary-text-color); padding: 10px 12px; border-bottom: 1px solid var(--divider-color); }
        td { padding: 12px; border-bottom: 1px solid var(--divider-color); vertical-align: top; }
        tbody tr:last-child td { border-bottom: 0; }
        .meter { text-align: right; white-space: nowrap; }
        th:nth-child(3) { text-align: right; }
        td:first-child { white-space: nowrap; }
        .empty { text-align: center; color: var(--secondary-text-color); padding: 24px 12px; }
        @media (max-width: 600px) {
          .header { font-size: 21px; }
          th, td { padding: 10px 8px; }
        }
      </style>
      <ha-card>
        <div class="header">${this._config.title}</div>
        <div class="wrap">
          <table>
            <thead>
              <tr>
                <th>Datum</th>
                <th>Underhåll</th>
                <th>Mätarvärde</th>
                <th>Anteckning</th>
              </tr>
            </thead>
            <tbody>${body}</tbody>
          </table>
        </div>
      </ha-card>`;
  }
}

customElements.define("blomster-maintenance-card", BlomsterMaintenanceCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "blomster-maintenance-card",
  name: "Blomster underhållshistorik",
  description: "Visar registrerat underhåll i en riktig tabell.",
  preview: true,
});

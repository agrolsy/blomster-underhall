class BlomsterMaintenanceCard extends HTMLElement {
  setConfig(config) {
    if (!config.entities || !Array.isArray(config.entities) || config.entities.length === 0) {
      throw new Error("Du måste ange minst en entitet");
    }
    this._config = {
      title: "Underhållshistorik",
      empty_text: "Inget underhåll har registrerats ännu.",
      max_rows: 20,
      show_delete: true,
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
      const itemId = state.attributes.item_id;
      const history = Array.isArray(state.attributes.history) ? state.attributes.history : [];
      for (const event of history) {
        rows.push({ ...event, name, itemId, entityId });
      }
    }
    rows.sort((a, b) => new Date(b.performed_at) - new Date(a.performed_at));
    return rows.slice(0, Number(this._config.max_rows) || 20);
  }

  async _deleteEvent(itemId, eventId, name) {
    if (!itemId || !eventId) {
      alert("Posten saknar ett unikt ID och kan inte tas bort. Ladda om integrationen först.");
      return;
    }
    if (!confirm(`Ta bort underhållsposten för ${name}?`)) return;

    try {
      await this._hass.callService("blomster_maintenance", "delete_maintenance", {
        item_id: itemId,
        event_id: eventId,
      });
    } catch (error) {
      alert(`Det gick inte att ta bort posten: ${error?.message || error}`);
    }
  }

  _bindActions() {
    this.shadowRoot.querySelectorAll("button[data-event-id]").forEach((button) => {
      button.addEventListener("click", () => {
        this._deleteEvent(
          button.dataset.itemId,
          button.dataset.eventId,
          button.dataset.name,
        );
      });
    });
  }

  _render() {
    if (!this.shadowRoot || !this._hass || !this._config) return;
    const rows = this._collectRows();
    const actionHeader = this._config.show_delete ? "<th>Åtgärd</th>" : "";
    const colspan = this._config.show_delete ? 5 : 4;
    const body = rows.length
      ? rows.map((event) => `
          <tr>
            <td>${this._escape(this._formatDate(event.performed_at))}</td>
            <td>${this._escape(event.name)}</td>
            <td class="meter">${this._escape(this._formatMeter(event))}</td>
            <td>${this._escape(event.note || "–")}</td>
            ${this._config.show_delete ? `<td class="action"><button type="button" data-item-id="${this._escape(event.itemId)}" data-event-id="${this._escape(event.event_id)}" data-name="${this._escape(event.name)}">Ta bort</button></td>` : ""}
          </tr>`).join("")
      : `<tr><td colspan="${colspan}" class="empty">${this._escape(this._config.empty_text)}</td></tr>`;

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { overflow: hidden; }
        .header { padding: 20px 20px 12px; font-size: 24px; font-weight: 400; }
        .wrap { overflow-x: auto; padding: 0 16px 16px; }
        table { width: 100%; border-collapse: collapse; min-width: 650px; }
        th { text-align: left; font-size: 13px; color: var(--secondary-text-color); padding: 10px 12px; border-bottom: 1px solid var(--divider-color); }
        td { padding: 12px; border-bottom: 1px solid var(--divider-color); vertical-align: top; }
        tbody tr:last-child td { border-bottom: 0; }
        .meter { text-align: right; white-space: nowrap; }
        th:nth-child(3) { text-align: right; }
        td:first-child { white-space: nowrap; }
        .action { text-align: right; white-space: nowrap; }
        button { border: 0; border-radius: 8px; padding: 7px 10px; cursor: pointer; background: var(--error-color); color: var(--text-primary-color, white); font: inherit; }
        button:hover { filter: brightness(0.95); }
        .empty { text-align: center; color: var(--secondary-text-color); padding: 24px 12px; }
        @media (max-width: 600px) {
          .header { font-size: 21px; }
          th, td { padding: 10px 8px; }
        }
      </style>
      <ha-card>
        <div class="header">${this._escape(this._config.title)}</div>
        <div class="wrap">
          <table>
            <thead>
              <tr>
                <th>Datum</th>
                <th>Underhåll</th>
                <th>Mätarvärde</th>
                <th>Anteckning</th>
                ${actionHeader}
              </tr>
            </thead>
            <tbody>${body}</tbody>
          </table>
        </div>
      </ha-card>`;
    this._bindActions();
  }
}

customElements.define("blomster-maintenance-card", BlomsterMaintenanceCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "blomster-maintenance-card",
  name: "Blomster underhållshistorik",
  description: "Visar registrerat underhåll i en tabell och kan ta bort felaktiga poster.",
  preview: true,
});

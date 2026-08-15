# Blomster Underhåll

Home Assistant-integration för en digital servicebok med underhållsintervall, mätarställningar, historik, kostnader och påminnelser.

## Dynamiska underhållsobjekt

Dashboardkortet `custom:blomster-maintenance-manager-card` kan skapa nya underhållsobjekt direkt i Home Assistant utan kod- eller YAML-ändringar.

För varje nytt objekt anger du:

- namn
- om intervallet baseras på tid eller en mätare/sensor
- intervallvärde
- för tid: dagar, veckor, månader eller år
- för mätare: valfri numerisk Home Assistant-sensor

Månader och år räknas kalenderbaserat. För mätarbaserade objekt hämtas enheten från den valda sensorn.

När objektet har skapats får det automatiskt en underhållssensor, problemindikering och kvitteringsknapp. Managerkortet visar också en knapp för att registrera utfört underhåll. Historikkortet hittar alla objekt dynamiskt.

## Inbyggda objekt

Integrationen har fortsatt bakåtkompatibelt stöd för:

- Luba-knivar
- Vattenfilter kol (`water_filter`, tidigare Vattenfilter)
- Vattenfilter bomull (`water_filter_cotton`)

Det befintliga `water_filter`-ID:t behålls så tidigare historik fortsätter höra till kolfiltret.

## Historik och mätardiff

`custom:blomster-maintenance-card` visar bland annat:

- datum
- underhållsobjekt
- mätarvärde vid utfört underhåll
- diff mot föregående registrering för samma objekt
- anteckning

Första registreringen saknar tidigare mätvärde och visar därför `–` som diff.

## Tjänster

### `blomster_maintenance.configure_item`

Skapar eller uppdaterar ett underhållsobjekt. Viktiga fält är `item_id`, `name`, `interval_type`, `interval_value` och vid mätarbaserat underhåll `meter_entity`.

Stödda intervalltyper:

- `days`
- `weeks`
- `months`
- `years`
- `meter`
- äldre kompatibilitetstyper: `liters`, `hours`, `starts`

### `blomster_maintenance.record_maintenance`

Registrerar utfört underhåll. Om objektet har en konfigurerad mätarentitet sparas dess aktuella värde och enhet tillsammans med händelsen.

### `blomster_maintenance.delete_maintenance`

Tar bort en enskild historikhändelse via `item_id` och `event_id`.

### `blomster_maintenance.acknowledge_maintenance`

Kvitterar den aktuella underhållsvarningen för ett objekt.

## Installation

Installera integrationen via HACS eller kopiera `custom_components/blomster_maintenance` till Home Assistants `custom_components`-katalog och starta om Home Assistant.

Kortresursen registreras automatiskt när Lovelace körs i storage mode. Vid YAML-hanterade resurser behöver `/blomster_maintenance/blomster-maintenance-card.js` läggas till som JavaScript-modul manuellt.

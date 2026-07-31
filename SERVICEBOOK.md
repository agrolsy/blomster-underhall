# Digital servicebok

Version 0.4.0 utökar Blomster Underhåll till en servicebok för husets komponenter.

## Skapa eller uppdatera ett objekt

Kör `blomster_maintenance.configure_item` och ange ett stabilt `item_id`. Objektet kan innehålla kategori, placering, tillverkare, modell, serienummer, installationsdatum samt länkar till manual, kvitto och bild.

Serviceintervall stöds för:

- `days`
- `liters`
- `hours`
- `starts`

För mätarbaserade intervall anges även `meter_entity`.

## Registrera underhåll

`blomster_maintenance.record_maintenance` sparar datum, mätarställning, anteckning och kostnad. Tjänsten kan returnera `item_id` och `event_id`, vilket används för säker ångring.

## Status och dashboard

Varje objekts sensor visar metadata, historik, kostnad och beräknad status. `sensor.servicebok` sammanställer:

- försenat underhåll
- kommande underhåll
- senast utfört
- total kostnad för innevarande år

## Påminnelser

Integrationen kontrollerar serviceboken varje timme och skapar stabila Home Assistant-notiser för objekt som aldrig har registrerats, snart behöver service eller är försenade. Samma notis-ID återanvänds så att dubletter inte skapas.

## Dokument

Manualer, kvitton och bilder lagras som lokala eller externa URL:er. Själva filerna kan därför ligga exempelvis under Home Assistants `/local/`-katalog eller i annan vald lagring.

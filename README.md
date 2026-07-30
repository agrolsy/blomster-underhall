# Blomster Underhåll

En egen Home Assistant-integration för husets underhåll, servicehistorik och mätarbaserade påminnelser.

Första testversionen hanterar:

- egen beständig total för vattenförbrukning
- vattenfilterbyten med sparad mätarställning
- Mammotion Luba-blad med 150 timmars bytesintervall
- både bladens användningstid och Mammotions egen slitagevarning

## Vattenförbrukning

Grohe-entiteten som ska användas är dagsförbrukningen:

```text
sensor.garage_vattenmatare_water_consumption
```

Den återställs dagligen. Integrationen sparar därför en egen total och lägger till förändringen i dagsvärdet. Ett lägre värde tolkas som att en ny dag har börjat.

Mätaren installerades den 6 juli 2026, men Home Assistant saknar hela historiken. Grohe-appen visade därför den korrekta baslinjen:

```text
14 839 L
```

Efter installation ska tjänsten `blomster_maintenance.set_water_baseline` köras en gång med `14839`. Tjänsten sparar samtidigt Grohes aktuella dagsvärde så att dagens förbrukning inte dubbelräknas.

Integrationen skapar:

```text
sensor.ackumulerad_vattenforbrukning
```

## Mammotion Luba-blad

Följande entiteter används:

```text
sensor.garden_hugo_ii_luba_vpqnssl9_bladanvandningstid
sensor.garden_hugo_ii_luba_vpqnssl9_bladslitagevarningstid
```

Bladen ska bytas efter 150 timmars användning. Integrationen skapar:

```text
sensor.luba_blad_aterstaende_tid
binary_sensor.luba_blad_behover_bytas
```

Varningen blir aktiv när antingen användningstiden når 150 timmar eller Mammotions egen slitagevarning är aktiv.

## Underhållshistorik

Tjänsten `blomster_maintenance.record_maintenance` sparar datum, anteckning och aktuell ackumulerad vattenförbrukning. Datan lagras lokalt med Home Assistants Store-API under `.storage` och följer med vanliga Home Assistant-backuper.

Exempel för vattenfilter:

```yaml
action: blomster_maintenance.record_maintenance
data:
  item_id: vattenfilter
  name: Vattenfilter
  note: Nytt filter monterat 30 juli 2026. Intervall ännu okänt.
```

## Installation via HACS

1. Öppna HACS.
2. Gå till Integrations.
3. Öppna menyn och välj Custom repositories.
4. Lägg till:

   ```text
   https://github.com/agrolsy/blomster-underhall
   ```

5. Välj kategorin Integration.
6. Installera Blomster Underhåll.
7. Starta om Home Assistant.
8. Gå till Inställningar → Enheter och tjänster → Lägg till integration.
9. Sök efter Blomster Underhåll.

Vid konfiguration används:

```text
Grohe dagsförbrukning:
sensor.garage_vattenmatare_water_consumption

Installationsdatum:
2026-07-06

Bladanvändningstid:
sensor.garden_hugo_ii_luba_vpqnssl9_bladanvandningstid

Bladslitagevarning:
sensor.garden_hugo_ii_luba_vpqnssl9_bladslitagevarningstid

Bytesintervall:
150 timmar
```

## Manuell installation

Kopiera katalogen:

```text
custom_components/blomster_maintenance
```

till:

```text
/config/custom_components/blomster_maintenance
```

Starta sedan om Home Assistant och lägg till integrationen från gränssnittet.

## Status

Detta är version `0.1.0` och ska testas i den aktuella Home Assistant-installationen innan den betraktas som stabil. Nästa steg är dashboardkort, kvitteringsknappar och återkommande notifieringar.

# Blomster Underhåll

En Home Assistant-integration för att samla husets underhåll, servicehistorik och påminnelser på ett ställe.

Integrationen är tänkt att bli husets digitala underhållsregister. Den ska kunna hantera både manuellt registrerade åtgärder och servicebehov som kommer direkt från andra Home Assistant-entiteter.

## Planerade användningsfall

- vattenfilter, baserat på verklig vattenförbrukning
- knivbyte på robotgräsklippare, baserat på Mammotions servicevarning
- ventilationsfilter och annan tidsstyrd service
- underhåll baserat på drifttimmar, mätarställning eller externa varningssensorer
- visning av aktuella underhållsbehov på Home Assistant-dashboarden
- återkommande notifieringar tills en åtgärd har kvitterats
- historik över när en åtgärd utfördes och vilket mätvärde som gällde då

## Vattenförbrukning

Grohe Sense exponerar i detta fall ett dagsvärde som återställs, inte en livstidstotal. Integrationen ska därför:

1. läsa historiska dagsvärden ur Home Assistants Recorder
2. börja från vattenmätarens installationsdatum, 6 juli 2026
3. summera värdeökningar inom varje dag
4. tolka ett lägre värde som en ny dagsperiod
5. skapa en egen beständig totalsensor
6. fortsätta ackumulera förbrukningen live efter historikimporten

Den egna totalsensorn används sedan som mätarställning när exempelvis ett vattenfilter byts.

## Datalagring

Integrationsdata lagras lokalt med Home Assistants Store-API under `.storage`.

Det innebär att datan:

- inte versionshanteras i Git
- följer med vanliga Home Assistant-backuper
- hålls skild från Recorder-databasen
- kan innehålla beständig underhållshistorik även om vanlig tillståndshistorik rensas

## Installation

Projektet är under utveckling och är ännu inte redo för vanlig installation via HACS.

Den planerade strukturen är:

```text
custom_components/
└── blomster_maintenance/
    ├── __init__.py
    ├── config_flow.py
    ├── const.py
    ├── manifest.json
    ├── sensor.py
    ├── services.yaml
    ├── storage.py
    ├── strings.json
    └── translations/
        └── sv.json
```

När en första testbar version finns ska installation kunna ske genom HACS som ett eget repository, eller manuellt genom att kopiera integrationsmappen till:

```text
/config/custom_components/blomster_maintenance
```

Därefter startas Home Assistant om och integrationen läggs till via:

```text
Inställningar → Enheter och tjänster → Lägg till integration
```

## Status

Första implementationen utvecklas initialt i projektet BlomstersSambandscentral och flyttas hit som ett fristående publikt HACS-repository.

När koden har flyttats hit återstår bland annat:

- verifiering mot aktuell Home Assistant-version
- val av exakt Grohe-entitet
- test av historikimport från 6 juli 2026
- registrering av första vattenfilterbytet
- koppling till Mammotions knivbytesvarning
- dashboardkort och notifieringar
- tester och versionshantering för HACS

## Licens

Licens väljs innan den första publika releasen.

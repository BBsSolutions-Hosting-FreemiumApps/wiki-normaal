# Elohim-YHWH Studiebijbel 2026 — conversierapport

Branch: `update-studiebijbel-2026-11-13`.

**Technische controles: geslaagd.**

Publicatie is niet vrijgegeven (`safe_to_publish: false`, `publication_approved: false`). De gebruiker beoordeelt de testversie en geeft afzonderlijk toestemming voor publicatie.

## Bron en herstel

- RTF: `Ai-Elohim-YHWH-Studiebijbel-2026 (3).rtf` (14.092.423 bytes).
- SHA-256: `4cf082bd418517b301240735b4ede690b09f2372e13ca5c1e4aac59b48935392`.
- Het oorspronkelijke bronbestand is ongewijzigd.
- Herstelreferentie van de eerste conversie op 14 november 2026: `89cf53b`; lokale tag `herstel-studiebijbel-2026-11-14-voor-conversie`.
- Elke uitvoering bewaart `baseline-data.tar.gz` en `baseline-manifest.json` vóór de conversie.

## Volledige Bijbel

| Controle | Uitkomst |
|---|---|
| Boeken | 66 |
| Bestaande blokken | 17.402 |
| Nieuwe bronblokken | 405 |
| Verwerkte blokken | 17.807 |
| Oorspronkelijke naamsegmenten behouden | 52.740 / 52.740 |
| Zichtbare naamsegmenten na nieuwe opmaak | 52.749 |
| Naamvoorkomens met dezelfde identiteit | 36.494 / 36.494 |
| Wiki-records | 2.808 |
| Bestaande studienotities | 1.494 |
| RTF-regels precies eenmaal bewaard | 217.428 / 217.428 |
| Tekst- en opmaakafwijkingen tegenover bron | 0 / 0 |
| Structurele fouten | 0 |
| Onzekere oude naamsegmenten | 0 |

Python-regressietests: 100 geslaagd.

Herhaalbaarheid: 94 gegevensbestanden zijn na een tweede volledige conversie byte voor byte identiek.

Alle oorspronkelijke blok-ID’s blijven gelijk. Nieuwe ID’s komen achter de bestaande reeks. De bestaande wiki-records, classificaties, verwijzingen en 1.494 losse studienotities blijven behouden. Naamidentiteiten worden per oorspronkelijke occurrence gekoppeld; gelijke spelling is geen reden om records samen te voegen.

De broncontrole vergelijkt alle tekstregels inclusief interne spaties en tabs, alle niet-lege tekens en de bronopmaak: voor- en achtergrondkleur, vet, cursief, onderstreping en onderstrepingskleur, doorhaling, super/subscript, lettertype en puntgrootte. De huidige RTF gebruikt Times 18pt. Alleen lege buitenregels van een tekstblok worden in de lezer getrimd; de bronkaart bewaart hun bereik.

## Aanvullingen en veranderingen

- 4.995 tekstblokken (veld `x`, inclusief nieuwe blokken) hebben een letterlijke tekst-/regelwijziging; daarvan 2.150 na het normaliseren van witruimte.
- 17.778 tekstblokken hebben gewijzigde bronopmaak. Deze telling omvat de nu expliciet overgenomen bronletters en bronlettergrootte.
- 17.762 blokken hebben nieuwe of opnieuw ingelezen bronkoppen.
- `changes.json` bevat alle oude/nieuwe bodyteksten, gebruikte kleuren en stijlen en de bronkoppen vóór/na de conversie.
- `source-headers.json` onderscheidt nieuwe passages, bestaande ingesprongen citaten, samengevoegde verzen en redactionele overzichten.
- `source-map.json` koppelt ieder uitvoerveld aan het oorspronkelijke RTF-regelbereik.
- `links.json` geeft per oude naamoccurrence de exacte overdrachtsmethode en eventuele onzekerheid.

Nieuwe opmaak kan een klikbare naam over extra stijlsegmenten verdelen. Het aantal volledige naamvoorkomens en hun wiki-ID’s blijft gelijk.

Bestaande chronologische groeperingen blijven intact. Nieuwe, voorheen ontbrekende passages krijgen eigen blokken en hoofdstukken. De delen a–c van Exodus 14:21 worden samen één nieuw blok. Deuteronomium krijgt de ontbrekende bronpassages en hoofdstukken zonder bestaande ID’s te vernummeren.

## Genesis 2 en browser

- Gegevenscontrole Genesis 2: geslaagd.
- Broncontrole Genesis 2: geslaagd.
- Genesis-browsercontrole: geslaagd.
- Volledige testsite browsercontrole: geslaagd.
- De browserregressie controleert alle 66 boeken en de 18 aangevulde Deuteronomium-hoofdstukken, naast 18 Genesis-2-blokken, 13 oorspronkelijke naamsegmenten, alle bijbehorende popups, tekstregels en CSS, toetsenbord, kleurenknop, hoofdstuknavigatie, wiki, legenda en voorwerk.
- Eden blijft `plaats / zeker`. Chawila I behoudt het bestaande ID en de bestaande classificatie; de plaats-/landcontext in Genesis 2:11–12 blijft een redactioneel aandachtspunt, zonder automatische correctie.

## Resterende beoordeling

- Technische controlepunten: 0.
- Beoordeel de tekst- en kleurwijzigingen en de nieuw teruggevonden passages inhoudelijk.
- De bron bevat in Genesis 2:23 zelf donkerblauwe tekst op een zwarte achtergrond. Dit is brongetrouw behouden; de kleurenknop biedt een leesbare weergave zonder bronkleuren. Beoordeel deze bronopmaak redactioneel.
- Nieuwe passages krijgen geen gegokte nieuwe wiki-identiteiten. Bestaande naamkoppelingen zijn beschermd; aanvullende naamindexering kan later met brononderbouwing worden uitgebreid.
- De handmatige Actions-workflow is toegevoegd. GitHub kan registratie op de standaardbranch vereisen om een nieuwe `workflow_dispatch`-workflow te tonen. `main` is daarvoor niet aangepast.

## Herhalen

Zie [de updateprocedure](https://github.com/BBsSolutions-Hosting-FreemiumApps/wiki-normaal/blob/update-studiebijbel-2026-11-13/docs/RTF-UPDATES.md) voor de CLI, bron- en gegevenscontroles, browsercontrole, herstel en de handmatig te starten artifact-workflow.

## Tellingen per boek

| Boek | Bestaand | Verwerkt | Nieuw | Tekst gewijzigd | Opmaak gewijzigd |
|---|---:|---:|---:|---:|---:|
| Genesis | 865 | 865 | 0 | 207 | 865 |
| Exodus | 884 | 885 | 1 | 143 | 885 |
| Leviticus | 544 | 544 | 0 | 11 | 544 |
| Numeri | 772 | 772 | 0 | 45 | 772 |
| Deuteronomium | 118 | 522 | 404 | 430 | 522 |
| Jozua | 411 | 411 | 0 | 30 | 411 |
| Richteren | 463 | 463 | 0 | 37 | 463 |
| Ruth | 63 | 63 | 0 | 1 | 63 |
| 1 Samu-el | 557 | 557 | 0 | 45 | 555 |
| 2 Samu-el | 535 | 535 | 0 | 46 | 535 |
| 1 Koningen | 634 | 634 | 0 | 83 | 633 |
| 2 Koningen | 635 | 635 | 0 | 88 | 627 |
| 1 Kronieken | 565 | 565 | 0 | 77 | 558 |
| 2 Kronieken | 660 | 660 | 0 | 133 | 659 |
| Ezra | 200 | 200 | 0 | 27 | 196 |
| Nehemia | 321 | 321 | 0 | 37 | 316 |
| Esther | 66 | 66 | 0 | 5 | 66 |
| Job | 162 | 162 | 0 | 23 | 162 |
| Psalm | 199 | 199 | 0 | 5 | 199 |
| Spreuken | 764 | 764 | 0 | 25 | 764 |
| Prediker | 191 | 191 | 0 | 50 | 191 |
| Hooglied | 109 | 109 | 0 | 16 | 109 |
| Jesaja | 291 | 291 | 0 | 90 | 291 |
| Jeremia | 726 | 726 | 0 | 51 | 726 |
| Klaagliederen | 144 | 144 | 0 | 0 | 144 |
| Ezechi-el | 401 | 401 | 0 | 13 | 401 |
| Dani-el | 141 | 141 | 0 | 15 | 141 |
| Hosea | 32 | 32 | 0 | 13 | 32 |
| Jo-el | 53 | 53 | 0 | 9 | 53 |
| Amos | 59 | 59 | 0 | 9 | 59 |
| Obadja | 9 | 9 | 0 | 1 | 9 |
| Jona | 31 | 31 | 0 | 2 | 31 |
| Micha | 80 | 80 | 0 | 11 | 80 |
| Nahum | 45 | 45 | 0 | 6 | 45 |
| Habakuk | 50 | 50 | 0 | 6 | 50 |
| Sefanja | 51 | 51 | 0 | 1 | 51 |
| Haggaï | 22 | 22 | 0 | 2 | 22 |
| Zacharia | 119 | 119 | 0 | 10 | 119 |
| Maleachi | 53 | 53 | 0 | 1 | 53 |
| Mattheus | 816 | 816 | 0 | 798 | 816 |
| Markus | 474 | 474 | 0 | 466 | 473 |
| Lukas | 921 | 921 | 0 | 896 | 921 |
| Johannes | 498 | 498 | 0 | 464 | 498 |
| Handelingen | 456 | 456 | 0 | 456 | 456 |
| Romeinen | 329 | 329 | 0 | 45 | 329 |
| 1 Korinthie-ers | 358 | 358 | 0 | 17 | 358 |
| 2 Korinthie-ers | 187 | 187 | 0 | 4 | 187 |
| Galaten | 87 | 87 | 0 | 5 | 87 |
| Efezie-ers | 75 | 75 | 0 | 2 | 75 |
| Filippie-ers | 74 | 74 | 0 | 0 | 74 |
| Kolossers | 60 | 60 | 0 | 0 | 60 |
| 1 Thessalonikers | 53 | 53 | 0 | 3 | 53 |
| 2 Thessalonikers | 30 | 30 | 0 | 0 | 30 |
| 1 Timotheus | 79 | 79 | 0 | 9 | 79 |
| 2 Timotheus | 55 | 55 | 0 | 0 | 55 |
| Titus | 25 | 25 | 0 | 0 | 25 |
| Filémon | 15 | 15 | 0 | 0 | 15 |
| Hebree-en | 195 | 195 | 0 | 9 | 195 |
| Jakobus | 90 | 90 | 0 | 5 | 90 |
| 1 Petrus | 67 | 67 | 0 | 5 | 67 |
| 2 Petrus | 37 | 37 | 0 | 3 | 37 |
| 1 Johannes | 93 | 93 | 0 | 0 | 93 |
| 2 Johannes | 11 | 11 | 0 | 0 | 11 |
| 3 Johannes | 6 | 6 | 0 | 0 | 6 |
| Judas | 17 | 17 | 0 | 1 | 17 |
| Openbaring | 269 | 269 | 0 | 3 | 269 |

## Controlebestanden downloaden

- [Alle rapporten, oude gegevens en volledige wijzigingen (ZIP)](../reports/rtf-2026-11-14/controlebestanden.zip).
- [Conversieoverzicht](../reports/rtf-2026-11-14/conversion.json), [gegevenscontrole](../reports/rtf-2026-11-14/verification.json), [RTF-broncontrole](../reports/rtf-2026-11-14/fidelity.json) en [herhaaltest](../reports/rtf-2026-11-14/idempotence.json).
- [Browsercontrole](../reports/rtf-2026-11-14/browser.json), [100 regressietests](../reports/rtf-2026-11-14/unit-tests.txt) en [schermafbeelding Genesis 2](../reports/rtf-2026-11-14/genesis2.png).

De ZIP bevat onder meer `changes.json` met de volledige oude en nieuwe teksten, gebruikte kleuren en stijlen, `links.json`, `source-map.json`, `source-headers.json` en `baseline-data.tar.gz`.

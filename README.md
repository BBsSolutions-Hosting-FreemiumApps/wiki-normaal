# Elohim YHWH Studiebijbel · Wiki (voorbeeld, niet live)

Statische, wiki-achtige voorbeeldsite van de Elohim YHWH Studiebijbel (v9). In de tekst zijn namen van personen, volken, steden, landen, rivieren, meren, zeeën en regio's aan te tikken; dan opent een popup met wie of wat het is en wat de tekst erover zegt.

Dit is alleen een preview in deze repository. Er is niets gedeployed, GitHub Pages staat niet aan, er is geen live URL en er zijn geen bronbestanden van de bijbel gewijzigd.

## Preview openen

- Open `index.html` rechtstreeks in de browser (dubbelklik, of via `file://`). Dat werkt, want alle data zit in `.js`-bestanden en `fetch` is niet nodig.
- Of start een lokale server in de hoofdmap van deze repository: `python3 -m http.server` en open het adres dat de server toont (standaard http://localhost:8000/).
- Er is geen live URL.

## Inhoud van de site

1. **Lezen** (`#/lees/<boek>/<hoofdstuk>`): de tekst per boek en hoofdstuk, met de originele RTF-kleuren. De knop "Kleuren" zet ze uit of aan. Groepen als "Genesis 1:14 | Genesis 1:15" blijven één blok, net als in de bron. Codes zoals [E], [Y], [§], [!] en [?] tonen hun betekenis als u ze aantikt. Verwijzingen als {2 Kronieken 10:1} zijn klikbaar.
2. **Popup/paneel** (aan de zijkant op desktop, van onderen op mobiel) toont:
   1. soort en zekerheid;
   2. "wie of wat" (koningsprofiel, rol of titel als de tekst die geeft);
   3. feiten uit de tekst ("zoon van", "verwekte", "koning van", generatiemarkeringen, tijdmarkeringen [-3300 / 460]);
   4. koningsprofielen uit de studiebijbel;
   5. toelichtingen [(…)], afwijkende namen [{'…'}] en Hebreeuwse vormen <…>;
   6. belangrijke verzen, letterlijk geciteerd;
   7. alle vindplaatsen met telling per boek;
   8. studynotes die de naam noemen;
   9. waarop de indeling berust.
   Er wordt geen biografie bijgeschreven.
3. **Wiki** (`#/wiki/P|V|S|L|W|R|O|U`): een index per soort met zoeken op naam, schrijfwijze en afwijkende naam. Vaste link per naam: `#/e/<id>`.
4. **Legenda** (`#/legenda`): de kleuren en codes uit Legenda.rtf, met dezelfde kleurwaarden, plus uitleg over hoe de wiki ze gebruikt.
5. **Over** (`#/over`): de bronnen, de tellingen en de uitleg van de zekerheid.

## Kaart met de huidige ligging

Bij drie namen toont de popup, direct onder "wie of wat", een compacte kaart. U ziet de huidige ligging, geen historische reconstructie en geen bijbelse grens. Bij die drie namen, en bij een aantal andere bekende plaatsen, staat daarnaast een foto of een historische kaart. Elke afbeelding heeft een auteur, een licentienaam en een link. Een naam zonder gelicenseerde afbeelding krijgt geen leeg vak. Van personen wordt geen portret getoond.

| Naam | Link | Wat u op de kaart ziet |
|---|---|---|
| Jeruzalem | `#/e/216` | Een speld op de Oude Stad, ingezoomd op dat gebied. Bijschrift: "Huidige ligging van de Oude Stad van Jeruzalem." |
| Egypte | `#/e/137` | Het moderne land als geheel, inclusief de Sinaï, zonder speld in de woestijn. Het bijschrift zegt dat dit de moderne landsgrens is, geen bijbelse grens. |
| Jordaan (de rivier) | `#/e/141` | De huidige loop, van ten noorden van het Meer van Galilea tot de Dode Zee. |

De coördinaten en de lichte omtrek of loop komen van OpenStreetMap, opgezocht via Nominatim op 12 november 2026 (Oude Stad: relatie 5862586, Egypte: relatie 1473947, Jordaan: relatie 2246907). De tegels zijn de standaardkaart van OpenStreetMap. Op de kaart en eronder staat: © [OpenStreetMap-bijdragers](https://www.openstreetmap.org/copyright).

Verwante namen krijgen geen kaart: Egyptenaren, Egyptenaar, Egyptische en de stad Jordaanse. Een naam zonder regel in `data/geo.js` krijgt geen kaart en geen leeg vak. Dat bestand is klein en staat los van de naamgegevens, zodat later meer plaatsen kunnen worden toegevoegd zonder de popup opnieuw te schrijven. Leaflet 1.9.4 (BSD-2-Clause, licentie in `vendor/leaflet/LICENSE`) staat in de repository. De site laadt het lokaal, met relatieve paden, niet via een CDN.

## Bronnen (alleen gelezen)

Deze bestanden zijn bij de bouw alleen gelezen. Ze staan niet in deze repository en zijn niet gewijzigd.

- `/workspace/elohim/v9/Ai-Elohim-YHWH-Studiebijbel-2026.rtf`, voor de kleuren en opmaak per letter. Het bestand telt 213.544 regels, precies even veel als `studiebijbel-v9.txt`, en de tekst is regel voor regel gelijk.
- `/workspace/elohim/kennis-v9/studiebijbel-v9.txt`, voor de tekst en de versstructuur.
- `/workspace/elohim/kennis-v9/studynotes-v9.txt`, met 1494 aantekeningen.
- `/workspace/agency/Legenda.rtf`, `.txt` en `legenda-kleuren-*.png`, voor de kleurbetekenissen.
- `leesversie-v9.txt` is niet gebruikt.
- De SHA-256 van de bronnen is na de bouw ongewijzigd: v9.txt 0e75beb9…, studynotes cbe74c5f…, v9.rtf badab6ba….

## Tellingen (bouw 12-11-2026)

- Tekstblokken (verzen of versgroepen): 17.402
- Geëxtraheerde namen: **2.808** (2.784 plus 24 personen die de studiebijbel zelf uit een gedeelde naam haalt)

| Soort | Aantal | zeker | waarschijnlijk | onzeker |
|---|---|---|---|---|
| Personen | 1.449 | 186 | 507 | 756 |
| Volken/stammen | 255 | 0 | 117 | 138 |
| Steden | 715 | 713 | 0 | 2 |
| Landen | 65 | 12 | 51 | 2 |
| Rivieren/meren/zeeën | 22 | 17 | 4 | 1 |
| Bergen/woestijnen/regio's | 26 | 6 | 17 | 3 |
| Overige plaatsen (o.a. #Plaats in het NT) | 35 | 27 | 4 | 4 |
| Soort onbepaald (vaak 1x-namen) | 241 | 0 | 0 | 241 |

## Hoe de soort bepaald wordt

1. **Legendakleur, per woord uit de RTF.** Dit geeft de "zeker"-gevallen:
   1. zwart vet: stad;
   2. zwart met rode eerste en laatste letter: stad die 1x voorkomt;
   3. zwart cursief: rivier, meer, zee of regio;
   4. oranje beginletter: koningsnaam (een groene achtergrond = Juda, cyaan = Is-ra-el);
   5. magenta beginletter: profetennaam;
   6. lichtblauwe achtergrond: priester;
   7. overige gekleurde achtergronden: markering van stam, volk of koning;
   8. lichtblauw vet in het NT: plaatsaanduiding.
2. **Koningsprofielen** (`[{Koning-…}] nn/nn / Naam`), met de regels eronder (vader, moeder, vrouw, kinderen, profeet, priester).
3. **Context in de zin:** "het land …", "koning van …", "stad …", "rivier …", "berg/woestijn …", "zoon/dochter van …", "verwekte …", een werkwoord na de naam, of een volgnummer (I, II, …).
4. **Een kleine naamlijst als hulp** (bijv. Egypte = land, Jordaan = water, Libanon = regio). In de popup staat dit apart vermeld. Er zijn drie handmatige keuzes: Yiś·rā·'êl als volk (met de legendatekst erbij), Adam als persoon en Farizeeën/Sadduceeën/Grieken als volk.

## Hiaten en onzekerheden

1. De RTF-kleuren onderscheiden landen niet apart, want zwart = alle geografie. Daardoor kan een land dat niet in de naamlijst staat als "stad" verschijnen (bijv. Macedonië of Asia).
2. 756 personen zijn "onzeker". Daar kan ruis tussen zitten, zoals woorden die alleen met een hoofdletter voorkomen.
3. 241 namen hebben de soort "onbepaald". Dat zijn vooral namen die maar 1x voorkomen (rode eerste en laatste letter) in geslachtsregisters.
4. Personen met dezelfde naam worden gescheiden als de studiebijbel dat zelf duidelijk doet, ook zonder volgnummer. Saul blijft op `#/e/380` (zoon van Kis II, koning). Saul* uit Rechobot, de zoon van Simeon I, en Saulus (in Handelingen aangesproken als Saul) hebben een eigen pagina. Hetzelfde geldt voor andere duidelijke naamgenoten, zoals Johannes de Doper, Jozef van Arimatea en Judas Iskariot naast de andere Judas. Onzekere namen zijn niet massaal gesplitst.
5. Feiten komen uit eenvoudige zinspatronen. In de popup is "zoon van", "koning van" en een verwante rol een link naar `#/e/…` als de tekst één persoon of plaats aanwijst. Een keten ("dochter van A / zoon van B") of een naam die na de splitsing nog dubbelzinnig is, blijft gewone tekst. Een datering verschijnt alleen als de studiebijbel die zelf bij de naam zet, bijvoorbeeld de tijdmarkering `[-3300 / 460]` of "1050 voor Christus" bij Saul.
6. Studynotes worden aan een naam gekoppeld als de naam in de aantekening staat, niet via het vers.
7. Godsnamen (Elohim, YHWH, Adonay, Kyrios/Theos …) en afgoden (Baal, Dagon, Molech …) zijn bewust niet als wiki-item opgenomen.
8. Maandnamen (groene achtergrond in de legenda) zijn niet opgenomen.
9. De data is ongeveer 14 MB en wordt per boek geladen.
10. Een versverwijzing die in de bron los op een regel staat (bijv. een tweede "Genesis 5:15" binnen een vers) wordt als apart blok getoond.
11. In `/workspace/elohim/studieb-wiki/` loopt mogelijk vergelijkbaar werk van een andere bot. Daar is niets aangeraakt.

## Bouw

Deze repository bevat alleen de statische preview (`index.html`, `css/`, `js/`, `data/`, `vendor/`). De bouwscripts uit de oorspronkelijke notities (`build/run.sh`, `build/rtfruns.py`, `build/build.py`, `build/stage2.py`, `build/shot.py`) zitten niet in het archief en zijn hier niet toegevoegd. Die scripts lazen alleen de bronnen en schreven naar `build/` en `site/data/`.

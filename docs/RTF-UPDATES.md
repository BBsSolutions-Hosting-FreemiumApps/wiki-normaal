# Studiebijbel bijwerken vanuit RTF

Werkbranch: `update-studiebijbel-2026-11-13`. De converter gebruikt de nieuwe RTF voor tekst en bronopmaak, en de bestaande websitegegevens voor blokindeling en wiki-identiteiten. Gelijk gespelde namen worden niet op naam alleen aan een wiki-ID gekoppeld.

## Herstelpunt en bron

Voor de conversie van 14 november 2026 is lokaal de Git-tag `herstel-studiebijbel-2026-11-14-voor-conversie` gemaakt. Er is ook een lokale archiefkopie van de oude `data/`-map in `/workspace/work/studiebijbel-2026/data-voor-conversie.tar`. Een lokale tag of archiefkopie wordt niet automatisch naar GitHub geüpload.

Controleer voor een volgende update eerst de branch en een schone werkmap. Maak vervolgens een nieuw herstelpunt met een unieke naam:

```sh
git branch --show-current
git status --short
git tag herstel-voor-volgende-rtf-update
mkdir -p work
git archive HEAD data > work/data-voor-update.tar
```

Upload het nieuwe RTF-bestand naar deze testbranch. Bewaar oudere bronversies totdat de nieuwe versie is beoordeeld. De converter schrijft naar een aparte uitvoermap en overschrijft de brongegevens bij deze werkwijze niet. Iedere conversie maakt vóór verwerking automatisch `baseline-data.tar.gz` en `baseline-manifest.json` in de rapportmap. Het archief bevat de volledige oorspronkelijke `data/`-map; het manifest bevat de SHA-256 per bestand.

## Eerst Genesis 2, daarna alle boeken

De opdrachten gebruiken Python 3.10 of nieuwer en de standaardbibliotheek. Externe RTF-programma's zijn voor de converter niet nodig. Voer ze uit vanuit de hoofdmap van de repository:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/convert_rtf.py --source 'Ai-Elohim-YHWH-Studiebijbel-2026 (3).rtf' --baseline . --output work/genesis2 --report-dir work/reports/genesis2 --chapter 'Genesis 2'
python3 tools/verify_conversion.py work/genesis2 --baseline . --report work/reports/genesis2/verification.json
python3 tools/verify_rtf_fidelity.py --source 'Ai-Elohim-YHWH-Studiebijbel-2026 (3).rtf' --site work/genesis2 --source-map work/reports/genesis2/source-map.json --report work/reports/genesis2/fidelity.json --partial
python3 tools/convert_rtf.py --source 'Ai-Elohim-YHWH-Studiebijbel-2026 (3).rtf' --baseline . --output work/testsite --report-dir work/reports/full
python3 tools/verify_conversion.py work/testsite --baseline . --report work/reports/full/verification.json
python3 tools/verify_rtf_fidelity.py --source 'Ai-Elohim-YHWH-Studiebijbel-2026 (3).rtf' --site work/testsite --source-map work/reports/full/source-map.json --report work/reports/full/fidelity.json
python3 tools/report_conversion.py --reports work/reports/full --genesis-reports work/reports/genesis2 --output work/reports/full/EINDRAPPORT.md
```

`--baseline` verwijst naar een bestaande website met een `data/`-map. `--output` krijgt een volledige statische testsite en moet een **nieuwe, nog niet bestaande map** zijn. Binnen de baseline-repository mag die uitsluitend onder `work/` staan. Kies voor een herhaalde uitvoering nieuwe uitvoer- en rapportmappen en pas alle controleopdrachten daarop aan. De converter weigert bestaande uitvoermappen zodat een eerdere testversie behouden blijft.

`--report-dir` krijgt een nieuwe, lege rapportmap, gescheiden van de uitvoermap. Binnen de baseline mag ook deze alleen onder `work/` staan. Dit voorkomt het overschrijven van brongegevens of het hergebruiken van verouderde geslaagde controles. De map ontvangt conversierapporten, bronkoppelingen, wijzigingen, controlelijst en herstelbestanden. Met `--chapter 'Genesis 2'` wordt alleen dat hoofdstuk bijgewerkt; de overige gegevens blijven in de testsite beschikbaar. De brongetrouwheidscontrole krijgt dan `--partial` omdat de rest van de bron in deze tussenstap bewust niet is omgezet. Zonder hoofdstukfilter worden alle 66 boeken verwerkt en controleert de bronverificatie de volledige brondekking.

De bronreferentiekoppen staan als opgemaakte rijen in blokveld `r`; koppen, subkoppen en studienotities direct vóór een passage staan in `pre`; de tekstregels staan in `x`. Voorwerk vóór de eerste passage blijft beschikbaar via **Over → Voorwerk uit de RTF** (`#/bron`). Zo blijft de oorspronkelijke tekst met Unicode, regeleinden en bronopmaak beschikbaar. De brongetrouwheidscontrole vergelijkt tekst en opmaak per teken, waaronder voor- en achtergrondkleur, vet, cursief, onderstreping en onderstrepingskleur, lettertype en lettergrootte; ook Times 18 pt wordt uit de bron overgenomen.

De aangeleverde bron bevat 405 toe te voegen canonieke tekstblokken: 404 in Deuteronomium en één samengevoegd blok voor Exodus 14:21a-c. Nieuwe blok-ID's worden achter de bestaande reeks toegevoegd (`17402` t/m `17806`, samen 17.807 blokken). Daarbij komen 18 hoofdstukken van Deuteronomium beschikbaar die in de oude hoofdstukindex ontbraken. Bestaande blok-ID's, wiki-ID's, wiki-records en studynotes blijven behouden. Deze beschrijving verklaart de aanvulling; de daadwerkelijk verwerkte aantallen en geslaagde controles staan in de rapporten van iedere uitvoering.

Start de testsite bijvoorbeeld met `python3 -m http.server 8000 --directory work/testsite` en open `http://localhost:8000/#/lees/0/2`. Controleer de tekst, kleurenknop, alle naamknoppen, Eden als plaats met zekerheid zeker, naamgenoten en verwijzingen. De rapporten geven aan welke bronpassages, tekst- of kleurwijzigingen en onzekere koppelingen aandacht vragen.

De automatische browserregressie gebruikt Playwright en Chromium. Deze controleert alle 66 boeken, de 18 aangevulde Deuteronomium-hoofdstukken en de 13 oorspronkelijke Genesis-2-naamsegmenten. Met een beschikbare Playwright-installatie en Chromium:

```sh
node tests/browser_conversion.cjs http://localhost:8000/ --report work/reports/full/browser.json --screenshot work/reports/full/genesis2.png --chromium /usr/bin/chromium
python3 tools/report_conversion.py --reports work/reports/full --genesis-reports work/reports/genesis2 --output work/reports/full/EINDRAPPORT.md
```

De browsercontrole is uitgevoerd met Playwright 1.62.1. Een ontbrekende installatie kan lokaal onder `work/` worden geplaatst met `npm install --prefix work/browser-tools --no-save playwright@1.62.1`; gebruik dan `NODE_PATH="$PWD/work/browser-tools/node_modules"` voor het Node-commando. Geef met `--chromium` het werkelijke pad naar de geïnstalleerde Chromium/Chrome-binary. De converter heeft deze browserafhankelijkheden niet nodig. Zonder browserrapport noemt het Markdown-rapport die controle expliciet niet uitgevoerd.

Beoordeel de technische status afzonderlijk van toestemming voor publicatie: conversie zonder fouten, parserwaarschuwingen of onduidelijke koppelingen, plus `passed: true` in zowel `verification.json` als `fidelity.json`, onderbouwt de technische klaarstatus. `conversion.json` houdt `safe_to_publish: false` omdat de gebruiker eerst de testversie beoordeelt en afzonderlijk toestemming moet geven voor publicatie. Een technisch geslaagde run is daarmee geen publicatiebesluit.

## Handmatig via GitHub Actions

De workflow `.github/workflows/rtf-update.yml` heeft uitsluitend `workflow_dispatch`; er is geen automatische push- of publicatietrigger. Kies bij **Run workflow** de branch `update-studiebijbel-2026-11-13` en het RTF-bronpad. Een branchcontrole blokkeert uitvoering op andere branches. De workflow draait regressietests, bouwt eerst Genesis 2 en daarna alle boeken, voert voor beide de dataverificatie én brongetrouwheidscontrole uit, herhaalt de volledige conversie en vergelijkt alle gegevensbestanden byte voor byte. Ook wordt automatisch een Markdown-eindrapport gemaakt. De testsite, rapporten en herstelarchieven blijven als downloadbaar artifact 30 dagen beschikbaar. Bij een fout blijven aangemaakte rapporten beschikbaar. De browsercontrole gebeurt lokaal; de workflow installeert daarvoor geen externe pakketten.

GitHub toont en registreert een nieuwe handmatige workflow doorgaans pas wanneer het workflowbestand ook op de standaardbranch bestaat. In dit project wordt `main` niet aangepast om dat te activeren. Als **Run workflow** voor dit bestand nog niet beschikbaar is, gebruik dan de bovenstaande lokale opdrachten; activering op de standaardbranch is een afzonderlijke, later te beoordelen repositorywijziging. Er is geen GitHub Actions-uitvoering aangetoond alleen doordat het YAML-bestand aanwezig is.

De externe Actions staan vast op volledige commit-SHA's. De workflow heeft alleen `contents: read`, bewaart geen checkout-inloggegevens en bevat geen commit-, push-, merge- of deploystap. De RTF-bron wordt niet in het testsite-artifact gekopieerd.

## Beoordelen, overnemen en herstellen

Beoordeel de gegenereerde site en de rapporten voordat je gegenereerde gegevens in de testbranch overneemt. Bewaar bij overname de nieuwe bron, converter en rapporten samen met de gewijzigde gegevens. Controleer daarna opnieuw de volledige site en de Git-diff. Een merge naar `main` en publicatie van de live website vereisen afzonderlijke toestemming van de gebruiker.

Om alleen de oude Bijbelgegevens terug te zetten, archiveer eerst eventuele nieuwe wijzigingen. Controleer dat het genoemde herstelpunt bestaat (`git show-ref --verify refs/tags/herstel-studiebijbel-2026-11-14-voor-conversie`) en herstel vervolgens uitsluitend de gegevensmap:

```sh
git restore --source herstel-studiebijbel-2026-11-14-voor-conversie -- data
git diff --stat
```

Dit herstelt de `data/`-map naar dat herstelpunt en overschrijft daar eventuele niet-opgeslagen wijzigingen. De afzonderlijke uitvoermappen onder `work/` kunnen ook worden bewaard als vergelijking. Gebruik voor toekomstige updates het herstelpunt dat bij die update hoort.

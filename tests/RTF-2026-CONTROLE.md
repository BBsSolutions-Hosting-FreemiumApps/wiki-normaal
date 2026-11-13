# Studiebijbel 2026 – controle 13 november 2026

## Status
Dit is een **technische nulmeting** in de testbranch, **geen** voltooide RTF-vervanging. De oorspronkelijke 66 JS-boekbestanden zijn bij deze controle niet overschreven. Er is niets samengevoegd naar `main`.

## Nieuwe RTF-bron
- Bestandsnaam: `Ai-Elohim-YHWH-Studiebijbel-2026.rtf`.
- Grootte: **14.092.423 bytes**.
- SHA-256: `4cf082bd418517b301240735b4ede690b09f2372e13ca5c1e4aac59b48935392`.
- De volledige RTF kon worden gelezen en als HTML met oorspronkelijke RTF-opmaak worden geëxporteerd.
- Alle **66 Bijbelboeken** zijn in de aangeleverde bron herkend.
- De automatisch gelezen bron bevat 20.074 mogelijke verseverwijzingregels; daarvan zijn er ook verwijzingen binnen commentaren en gecombineerde passages. Dit aantal is niet hetzelfde als het aantal websiteblokken.

## Bestaande websitegegevens, daadwerkelijk gecontroleerd
- **66/66** `data/b/0.js` t/m `data/b/65.js` leesbaar en JSON-parsebaar.
- **17.402** bestaande tekstblokken.
- **52.740** klikbare naamsegmenten.
- **0** gevonden verwijzingen naar ongeldige stijl-ID's (stijlentabel: 819).
- **0** gevonden verwijzingen naar naam-ID's buiten bereik.
- **24/24** entiteitenbestanden `data/e0.js` t/m `data/e23.js` leesbaar.
- **2.808** wiki-records aanwezig; de record-ID's staan in de juiste bestanden.

## Genesis 2
- **18** bestaande tekstblokken en **13** aangeklikbare naamsegmenten.
- **5 van 5** gecontroleerde Bijbeltekstpassages komen in de bestaande GitHub-data overeen met de nieuwe RTF-tekst.
- **Eden** (naam-ID 1): type **plaats**, zekerheid **zeker**.
- De 13 segmenten en bijbehorende echte records zijn via de regressiepagina te onderzoeken: `tests/genesis2-rtf-regressie.html`.
- **Reviewpunt:** de entiteit `Chawila I` (naam-ID 3) staat als persoon, terwijl Genesis 2:11 spreekt over het **land** Chawila I. Dit is een contextafhankelijke classificatie die niet automatisch gewijzigd is.

## Nog niet afgerond
1. Volledige vers-voor-vers en kleur-voor-kleur vergelijking van de 66 boekbestanden met de nieuwe RTF.
2. Het betrouwbaar overzetten van gewijzigde tekst met behoud van alle reeds gekoppelde namen en wiki-ID's.
3. Eindcontrole na conversie en pas daarna een eventuele merge naar `main`.

**Belangrijk:** nul ongeldige ID's in de bestaande versie bewijst nog niet dat de nieuwe versie in zijn geheel correct is geïmporteerd. De RTF is niet als nieuw bronbestand in deze GitHub-branch opgeslagen.

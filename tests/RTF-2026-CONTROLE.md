# Studiebijbel 2026 — RTF-vervanging (13 november 2026)

Dit is het historische onderzoeksrapport van 13 november. De uitgevoerde conversie en actuele controles staan in [RTF-2026-EINDRAPPORT.md](RTF-2026-EINDRAPPORT.md); de hieronder beschreven onvoltooide converterstatus is door die uitvoering opgevolgd.

## Bevestiging bronbestand
- Bestand in GitHub testbranch: `Ai-Elohim-YHWH-Studiebijbel-2026 (3).rtf`.
- Grootte: **14.092.423 bytes**.
- SHA-256: `4cf082bd418517b301240735b4ede690b09f2372e13ca5c1e4aac59b48935392`.
- Git blob: `138e7a8eb94637ac6a9a84f72d1070bc64a6c34a`.
- Dit blob-ID is identiek aan dat van de eerder ingelezen RTF. Bestand is volledig en leesbaar.

## Structuurcontrole bestaande website
- **66** Bijbelboeken, **17.402** tekstblokken, **52.740** aanklikbare naamsegmenten en **2.808** wiki-records.
- Geen ongeldige kleurstijl-ID's of naam-ID's gevonden in de bestaande gegevens.
- Live-website (`main`) is bij deze controle niet gewijzigd.

## Geautomatiseerde RTF-vergelijking
GitHub Actions workflow: [RTF-vergelijking](https://github.com/BBsSolutions-Hosting-FreemiumApps/wiki-normaal/actions/workflows/rtf-audit.yml).

**Eerste extractie (`unrtf`):**
- 17.385 verzenblokken gekoppeld aan de RTF.
- 13.343 exact overeenkomend.
- 4.042 verschilpunten en 17 nog niet gekoppelde blokken.
- Automatisch ZIP-artifact beschikbaar met de 66-boeken-vergelijking.

**Nauwkeuriger vergelijking met LibreOffice-HTML (controle buiten GitHub):**
- 17.383 van 17.402 blokken gekoppeld.
- **15.185 tekstblokken letterlijk gelijk.**
- **2.198** blokken nog niet letterlijk gelijk.
- Daarvan is bij **1.314** de RTF-tekst langer dan de huidige tekst, vaak doordat een volgende kanttekening of kop aan het vers wordt gehangen (**1.301** hebben herkenbaar zo'n commentaarstart).
- Bij **395** blokken is juist de huidige webtekst langer, onder meer doordat de website meerdere bijbelverzen in één blok samenvoegt.
- **489** verschillen zijn intern en verdienen tekstinhoudelijke beoordeling.
- **19** blokken zijn door deze methode nog niet veilig gekoppeld.

## Technische conclusie
De RTF is correct geüpload, maar kan **niet veilig blind over de huidige gegevensbestanden worden geschreven**. De bestaande website combineert meerdere verzen, aparte commentaren, gekleurde tekstdelen en persistent toegewezen wiki-ID's. Gewone tekstextractie verliest of verplaatst die informatie.

De eerstvolgende technische stap is een converter te valideren die **per bestaande blok-ID** de RTF-opmaak opnieuw inleest, de exacte oorspronkelijke link-ID's behoudt en alle niet automatisch passende blokken expliciet markeert. Deze stap is nog **niet afgerond**. `main` blijft ongewijzigd.

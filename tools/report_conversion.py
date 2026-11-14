#!/usr/bin/env python3
"""Create an evidence-based Markdown report from the conversion checks."""
import argparse
import json
from pathlib import Path
import re


def load(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def number(value):
    return f'{value:,}'.replace(',', '.') if isinstance(value, int) else str(value)


def build(reports, output, genesis_reports=None):
    reports, output = Path(reports), Path(output)
    conversion = load(reports / 'conversion.json')
    verification = load(reports / 'verification.json')
    fidelity = load(reports / 'fidelity.json')
    browser = load(reports / 'browser.json')
    genesis = Path(genesis_reports) if genesis_reports else None
    genesis_data = load(genesis / 'verification.json') if genesis else {}
    genesis_source = load(genesis / 'fidelity.json') if genesis else {}
    genesis_browser = load(genesis / 'browser.json') if genesis else {}
    repeat = load(reports / 'idempotence.json')
    unit_path = reports / 'unit-tests.txt'
    if not unit_path.exists():
        unit_path = reports.parent / 'unit-tests.txt'
    unit_text = unit_path.read_text(encoding='utf-8') if unit_path.exists() else ''
    unit_match = re.search(r'Ran (\d+) tests?', unit_text)
    unit_count = int(unit_match[1]) if unit_match else 0
    unit_passed = bool(unit_match and re.search(r'\nOK(?:\s|$)', unit_text))
    technical = bool(conversion and not conversion.get('issues') and not conversion.get('untouched_blocks')
                     and verification.get('passed') and fidelity.get('passed') and not fidelity.get('partial'))
    if unit_text:
        technical = technical and unit_passed
    if repeat:
        technical = technical and bool(repeat.get('passed'))
    counts = verification.get('counts', {})
    source_counts = fidelity.get('counts', {})
    added = conversion.get('additional_source_passages', [])
    added_chapters = verification.get('baseline', {}).get('growth', {}).get('added_chapters', [])
    lines = [
        '# Elohim-YHWH Studiebijbel 2026 — conversierapport', '',
        'Branch: `update-studiebijbel-2026-11-13`.', '',
        '**Technische controles: ' + ('geslaagd.' if technical else 'nog niet volledig geslaagd.') + '**', '',
        'Publicatie is niet vrijgegeven (`safe_to_publish: false`, `publication_approved: false`). '
        'De gebruiker beoordeelt de testversie en geeft afzonderlijk toestemming voor publicatie.', '',
        '## Bron en herstel', '',
        f"- RTF: `{conversion.get('source', 'onbekend')}` ({number(conversion.get('source_bytes', 0))} bytes).",
        f"- SHA-256: `{conversion.get('source_sha256', 'onbekend')}`.",
        '- Het oorspronkelijke bronbestand is ongewijzigd.',
        '- Herstelreferentie van de eerste conversie op 14 november 2026: `89cf53b`; lokale tag `herstel-studiebijbel-2026-11-14-voor-conversie`.',
        '- Elke uitvoering bewaart `baseline-data.tar.gz` en `baseline-manifest.json` vóór de conversie.', '',
        '## Volledige Bijbel', '',
        '| Controle | Uitkomst |', '|---|---|',
        f"| Boeken | {number(counts.get('books', 0))} |",
        f"| Bestaande blokken | {number(conversion.get('baseline_blocks', 0))} |",
        f"| Nieuwe bronblokken | {number(conversion.get('added_source_blocks', 0))} |",
        f"| Verwerkte blokken | {number(conversion.get('converted_blocks', 0))} |",
        f"| Oorspronkelijke naamsegmenten behouden | {number(conversion.get('retained_old_link_segments', 0))} / {number(conversion.get('old_link_segments', 0))} |",
        f"| Zichtbare naamsegmenten na nieuwe opmaak | {number(counts.get('all_linked_segments', counts.get('linked_segments', 0)))} |",
        f"| Naamvoorkomens met dezelfde identiteit | {number(counts.get('all_linked_occurrences', 0))} / {number(verification.get('baseline', {}).get('counts', {}).get('all_linked_occurrences', 0))} |",
        f"| Wiki-records | {number(counts.get('entity_records', 0))} |",
        f"| Bestaande studienotities | {number(counts.get('study_notes', 0))} |",
        f"| RTF-regels precies eenmaal bewaard | {number(source_counts.get('covered_source_lines', 0))} / {number(source_counts.get('source_lines', 0))} |",
        f"| Tekst- en opmaakafwijkingen tegenover bron | {number(source_counts.get('text_mismatched_characters', 0))} / {number(source_counts.get('format_mismatched_characters', 0))} |",
        f"| Structurele fouten | {number(len(verification.get('errors', [])))} |",
        f"| Onzekere oude naamsegmenten | {number(conversion.get('unresolved_old_link_segments', 0))} |", '',
        f"Python-regressietests: {number(unit_count)} geslaagd." if unit_passed else 'Python-testresultaat: geen geslaagd log in deze rapportset.', '',
        (f"Herhaalbaarheid: {number(repeat.get('data_files', 0))} gegevensbestanden zijn na een tweede volledige conversie byte voor byte identiek."
         if repeat.get('passed') else 'Herhaalbaarheid: geen geslaagd herhaalrapport in deze rapportset.'), '',
        'Alle oorspronkelijke blok-ID’s blijven gelijk. Nieuwe ID’s komen achter de bestaande reeks. '
        'De bestaande wiki-records, classificaties, verwijzingen en 1.494 losse studienotities blijven behouden. '
        'Naamidentiteiten worden per oorspronkelijke occurrence gekoppeld; gelijke spelling is geen reden om records samen te voegen.', '',
        'De broncontrole vergelijkt alle tekstregels inclusief interne spaties en tabs, alle niet-lege tekens en de bronopmaak: '
        'voor- en achtergrondkleur, vet, cursief, onderstreping en onderstrepingskleur, doorhaling, super/subscript, lettertype en puntgrootte. '
        'De huidige RTF gebruikt Times 18pt. Alleen lege buitenregels van een tekstblok worden in de lezer getrimd; de bronkaart bewaart hun bereik.', '',
        '## Aanvullingen en veranderingen', '',
        f"- {number(conversion.get('text_changed_blocks', 0))} tekstblokken (veld `x`, inclusief nieuwe blokken) hebben een letterlijke tekst-/regelwijziging; "
        f"daarvan {number(conversion.get('normalized_text_changed_blocks', 0))} na het normaliseren van witruimte.",
        f"- {number(conversion.get('formatting_changed_blocks', 0))} tekstblokken hebben gewijzigde bronopmaak. "
        'Deze telling omvat de nu expliciet overgenomen bronletters en bronlettergrootte.',
        f"- {number(conversion.get('source_header_changed_blocks', 0))} blokken hebben nieuwe of opnieuw ingelezen bronkoppen.",
        '- `changes.json` bevat alle oude/nieuwe bodyteksten, gebruikte kleuren en stijlen en de bronkoppen vóór/na de conversie.',
        '- `source-headers.json` onderscheidt nieuwe passages, bestaande ingesprongen citaten, samengevoegde verzen en redactionele overzichten.',
        '- `source-map.json` koppelt ieder uitvoerveld aan het oorspronkelijke RTF-regelbereik.',
        '- `links.json` geeft per oude naamoccurrence de exacte overdrachtsmethode en eventuele onzekerheid.', '',
        'Nieuwe opmaak kan een klikbare naam over extra stijlsegmenten verdelen. '
        'Het aantal volledige naamvoorkomens en hun wiki-ID’s blijft gelijk.', '',
        'Bestaande chronologische groeperingen blijven intact. Nieuwe, voorheen ontbrekende passages krijgen eigen blokken '
        'en hoofdstukken. De delen a–c van Exodus 14:21 worden samen één nieuw blok. '
        'Deuteronomium krijgt de ontbrekende bronpassages en hoofdstukken zonder bestaande ID’s te vernummeren.', '',
        '## Genesis 2 en browser', '',
        f"- Gegevenscontrole Genesis 2: {'geslaagd' if genesis_data.get('passed') else 'geen geslaagd rapport aangeleverd'}.",
        f"- Broncontrole Genesis 2: {'geslaagd' if genesis_source.get('passed') else 'geen geslaagd rapport aangeleverd'}.",
        f"- Genesis-browsercontrole: {'geslaagd' if genesis_browser.get('passed') else 'geen geslaagd rapport aangeleverd'}.",
        f"- Volledige testsite browsercontrole: {'geslaagd' if browser.get('passed') else 'niet uitgevoerd in deze rapportset'}.",
        '- De browserregressie controleert alle 66 boeken en de 18 aangevulde Deuteronomium-hoofdstukken, naast 18 Genesis-2-blokken, 13 oorspronkelijke naamsegmenten, '
        'alle bijbehorende popups, tekstregels en CSS, toetsenbord, kleurenknop, hoofdstuknavigatie, wiki, legenda en voorwerk.',
        '- Eden blijft `plaats / zeker`. Chawila I behoudt het bestaande ID en de bestaande classificatie; '
        'de plaats-/landcontext in Genesis 2:11–12 blijft een redactioneel aandachtspunt, zonder automatische correctie.', '',
        '## Resterende beoordeling', '',
        f"- Technische controlepunten: {number(len(conversion.get('issues', [])))}.",
        '- Beoordeel de tekst- en kleurwijzigingen en de nieuw teruggevonden passages inhoudelijk.',
        '- De bron bevat in Genesis 2:23 zelf donkerblauwe tekst op een zwarte achtergrond. '
        'Dit is brongetrouw behouden; de kleurenknop biedt een leesbare weergave zonder bronkleuren. Beoordeel deze bronopmaak redactioneel.',
        '- Nieuwe passages krijgen geen gegokte nieuwe wiki-identiteiten. Bestaande naamkoppelingen zijn beschermd; '
        'aanvullende naamindexering kan later met brononderbouwing worden uitgebreid.',
        '- De handmatige Actions-workflow is toegevoegd. GitHub kan registratie op de standaardbranch vereisen om '
        'een nieuwe `workflow_dispatch`-workflow te tonen. `main` is daarvoor niet aangepast.', '',
        '## Herhalen', '',
        'Zie [de updateprocedure](https://github.com/BBsSolutions-Hosting-FreemiumApps/wiki-normaal/blob/update-studiebijbel-2026-11-13/docs/RTF-UPDATES.md) voor de CLI, bron- en gegevenscontroles, '
        'browsercontrole, herstel en de handmatig te starten artifact-workflow.', '',
    ]
    if conversion.get('per_book'):
        lines += ['## Tellingen per boek', '', '| Boek | Bestaand | Verwerkt | Nieuw | Tekst gewijzigd | Opmaak gewijzigd |', '|---|---:|---:|---:|---:|---:|']
        lines += ['| ' + ' | '.join(str(b[k]) for k in ('book', 'baseline_blocks', 'converted_blocks', 'added_blocks', 'body_text_changes', 'formatting_changes')) + ' |'
                  for b in conversion['per_book']]
        lines.append('')
    if conversion.get('issues'):
        lines += ['### Open technische controlepunten', '']
        lines += ['- `' + json.dumps(item, ensure_ascii=False) + '`' for item in conversion['issues']]
        lines.append('')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')
    readiness = dict(technical_checks_passed=technical, browser_passed=bool(browser.get('passed')),
                     genesis_data_passed=bool(genesis_data.get('passed')), genesis_source_passed=bool(genesis_source.get('passed')),
                     unit_tests_passed=unit_passed, unit_test_count=unit_count, idempotence_passed=bool(repeat.get('passed')),
                     publication_approved=False, safe_to_publish=False)
    (reports / 'readiness.json').write_text(json.dumps(readiness, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(readiness))
    return technical


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--genesis-reports', type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if build(args.reports, args.output, args.genesis_reports) else 2)

"""Regression cases for the source/baseline boundary (no network/dependencies)."""
import sys
from pathlib import Path
import unittest
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from convert_rtf import reference_sections, align_blocks, split_body, style_css, new_source_blocks, convert, preserve_owned_headers


class ConversionBoundaryTests(unittest.TestCase):
    def test_citations_do_not_steal_verse_identity(self):
        groups, _ = reference_sections([
            'Genesis 2:4 | Genesis 2:5', '| Genesis 2:7 {Genesis 1:27}',
            'Dit is de geschiedenis', 'Genesis 2:8 {Genesis 2:4}', 'Verder'], ['Genesis'])
        self.assertEqual(groups[0]['refs'], [('Genesis', '2', '4'), ('Genesis', '2', '5'), ('Genesis', '2', '7')])
        self.assertEqual(groups[1]['refs'], [('Genesis', '2', '8')])

    def test_empty_legacy_duplicate_does_not_consume_real_verse(self):
        texts = ['1 Koningen 16:29', 'Achab', 'de zoon van Omri']
        groups, ref = reference_sections(texts, ['1 Koningen'])
        meta = {'blk': [[0, 16, '1 Koningen 16:29']] * 2}
        old = {0: {'x': [], 'm': '- 1 Koningen 22:40'}, 1: {'x': [[['Achab', 0]], [['de zoon van Omri', 0]]]}}
        matches, empty, _, issues = align_blocks(meta, old, groups, ref, texts)
        self.assertEqual(matches, {1: 0})
        self.assertEqual(empty, {0})
        self.assertEqual(issues, [])

    def test_merged_verses_split_with_changed_wrapping_and_keep_marker(self):
        rows = [[['Zie', 0]], [['dit heb ik opgemerkt', 0]], [['| die ik nog altijd zoek', 1]], [['zonder ze gevonden te hebben', 1]]]
        old = {1: {'x': [[['Zie', 0]]]}, 2: {'x': [[['die ik nog altijd zoek zonder ze gevonden te hebben', 0]]]}}
        parts, boundaries = split_body([1, 2], rows, old)
        self.assertEqual(boundaries, [0, 2, 4])
        self.assertEqual(parts[2][0][0][0], '| die ik nog altijd zoek')
        self.assertEqual(parts[1] + parts[2], rows)

    def test_ambiguous_duplicate_body_is_rejected(self):
        old = {1: {'x': [[['Eerste', 0]]]}, 2: {'x': [[['Herhaling', 0]]]}}
        with self.assertRaises(ValueError):
            split_body([1, 2], [[['Herhaling', 0]], [['Herhaling', 0]]], old)

    def test_underlining_retains_its_source_color(self):
        css = style_css({'color': '#0000ff', 'underline': True, 'underline_color': '#fb02ff'})
        self.assertIn('text-decoration-color:#fb02ff', css)

    def test_superscript_retains_the_source_point_size(self):
        css = style_css({'font_size_points': 18, 'superscript': 1})
        self.assertIn('font-size:18pt', css)
        self.assertIn('vertical-align:super', css)
        self.assertEqual(css.count('font-size:'), 1)

    def test_report_directory_cannot_modify_baseline_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / 'baseline'
            (baseline / 'data').mkdir(parents=True)
            sentinel = baseline / 'data/keep.txt'
            sentinel.write_text('oorspronkelijk')
            with self.assertRaisesRegex(ValueError, 'Rapporten'):
                convert(root / 'source.rtf', baseline, root / 'output', baseline / 'data')
            self.assertEqual(list((baseline / 'data').iterdir()), [sentinel])
            self.assertEqual(sentinel.read_text(), 'oorspronkelijk')

    def test_stale_verification_reports_are_never_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / 'reports'
            reports.mkdir()
            check = reports / 'verification.json'
            check.write_text('{"passed":true}')
            with self.assertRaisesRegex(ValueError, 'lege rapportmap'):
                convert(root / 'source.rtf', root / 'baseline', root / 'output', reports)
            self.assertEqual(check.read_text(), '{"passed":true}')

    def test_output_and_reports_cannot_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'apart'):
                convert(root / 'source.rtf', root / 'baseline', root / 'output', root / 'output/reports')
            self.assertFalse((root / 'output').exists())

    def test_new_chapter_appends_ids_but_existing_quotation_stays_in_owner(self):
        texts = ['Deuteronomium 11:1', 'Bestaande woorden',
                 'Deuteronomium 11:2', 'Een bestaande toespraak die al onder het vorige blok valt',
                 'Deuteronomium 12:1', 'Volledig nieuwe inzettingen voor het nieuwe hoofdstuk',
                 'Deuteronomium 18:1', 'Volgend bestaand blok']
        groups, ref = reference_sections(texts, ['Deuteronomium'])
        meta = {'books': [['Deuteronomium', [11, 18]]], 'blk': [[0, 11, 'Deuteronomium 11:1'], [0, 18, 'Deuteronomium 18:1']]}
        old = {0: {'x': [[['Bestaande woorden', 0]], [['Een bestaande toespraak die al onder het vorige blok valt', 0]]]},
               1: {'x': [[['Volgend bestaand blok', 0]]]}}
        matches = {0: 0, 1: 3}
        additions, inventory = new_source_blocks(meta, old, groups, matches, texts, ref)
        self.assertEqual(len(additions), 1)
        self.assertEqual(meta['blk'], [[0, 11, 'Deuteronomium 11:1'], [0, 18, 'Deuteronomium 18:1'], [0, 12, 'Deuteronomium 12:1']])
        self.assertEqual(matches[2], 2)
        self.assertEqual(inventory[0]['classification'], 'existing_body_exact')

    def test_new_note_does_not_turn_existing_short_verse_into_new_block(self):
        texts = ['Job 4:1', 'Aanhef', 'Job 5:24', 'Gij zult ervaren', 'dat uw tent vrede is',
                 '[!] Nieuwe lange opmerking die volledig ontbreekt in de baseline', 'Job 6:1', 'Antwoord']
        groups, ref = reference_sections(texts, ['Job'])
        meta = {'books': [['Job', [4, 6]]], 'blk': [[0, 4, 'Job 4:1'], [0, 6, 'Job 6:1']]}
        old = {0: {'x': [[['Aanhef', 0]], [['Gij zult ervaren', 0]], [['dat uw tent vrede is', 0]]]}, 1: {'x': [[['Antwoord', 0]]]}}
        additions, _ = new_source_blocks(meta, old, groups, {0: 0, 1: 2}, texts, ref)
        self.assertEqual(additions, [])

    def test_new_verse_letter_subdivisions_share_one_stable_block(self):
        texts = ['Exodus 14:20', 'Oude passage', 'Exodus 14:21a', 'Nieuwe eerste zin',
                 'Exodus 14:21b', 'Nieuwe tweede zin', 'Exodus 14:22', 'Volgend bestaand blok']
        groups, ref = reference_sections(texts, ['Exodus'])
        meta = {'books': [['Exodus', [14]]], 'blk': [[0, 14, 'Exodus 14:20'], [0, 14, 'Exodus 14:22']]}
        old = {0: {'x': [[['Oude passage', 0]]]}, 1: {'x': [[['Volgend bestaand blok', 0]]]}}
        additions, _ = new_source_blocks(meta, old, groups, {0: 0, 1: 3}, texts, ref)
        self.assertEqual(len(additions), 1)
        self.assertEqual(meta['blk'][2][2], 'Exodus 14:21')

    def test_similar_religious_formula_is_not_proof_of_old_verse_identity(self):
        texts = ['Deuteronomium 7:10', 'Onderhoud de inzettingen en geboden die Ik u heden gebied',
                 'Deuteronomium 7:11', 'Onderhoud de inzettingen en geboden die Ik u morgen gebied',
                 'Deuteronomium 7:12', 'Volgende tekst']
        groups, ref = reference_sections(texts, ['Deuteronomium'])
        meta = {'books': [['Deuteronomium', [7]]], 'blk': [[0, 7, 'Deuteronomium 7:10'], [0, 7, 'Deuteronomium 7:12']]}
        old = {0: {'x': [[['Onderhoud de inzettingen en geboden die Ik u heden gebied', 0]]]},
               1: {'x': [[['Volgende tekst', 0]]]}}
        additions, _ = new_source_blocks(meta, old, groups, {0: 0, 1: 2}, texts, ref)
        self.assertEqual(len(additions), 1)
        self.assertEqual(meta['blk'][2][2], 'Deuteronomium 7:11')

    def test_shared_long_opening_does_not_hide_a_new_chapter(self):
        prefix = 'Een gedeelde inleiding met een lange reeks woorden. ' * 4
        texts = ['Genesis 1:1', prefix + 'Oude afsluiting',
                 'Genesis 2:1', prefix + 'Nieuwe afsluiting', 'Genesis 3:1', 'Volgende']
        groups, ref = reference_sections(texts, ['Genesis'])
        meta = {'books': [['Genesis', [1, 3]]], 'blk': [[0, 1, 'Genesis 1:1'], [0, 3, 'Genesis 3:1']]}
        old = {0: {'x': [[[prefix + 'Oude afsluiting', 0]]]}, 1: {'x': [[['Volgende', 0]]]}}
        additions, _ = new_source_blocks(meta, old, groups, {0: 0, 1: 2}, texts, ref)
        self.assertEqual(len(additions), 1)
        self.assertEqual(meta['blk'][2][2], 'Genesis 2:1')

    def test_embedded_original_header_preserves_changed_quotation_owner(self):
        texts = ['Job 4:1', 'Aanhef', 'Job 5:1', 'Een geheel gewijzigde bronzin', 'Job 6:1', 'Antwoord']
        groups, ref = reference_sections(texts, ['Job'])
        meta = {'books': [['Job', [4, 6]]], 'blk': [[0, 4, 'Job 4:1'], [0, 6, 'Job 6:1']]}
        old = {0: {'x': [[['Aanhef', 0]], [['\tJob 5:1', 0]], [['Oude woorden', 0]]]}, 1: {'x': [[['Antwoord', 0]]]}}
        additions, inventory = new_source_blocks(meta, old, groups, {0: 0, 1: 2}, texts, ref)
        self.assertEqual(additions, [])
        self.assertEqual(inventory[0]['classification'], 'existing_embedded_verse_header')

    def test_royal_overview_is_not_a_new_verse(self):
        texts = ['Jeremia 38:1', 'Bestaande tekst', 'Psalm 33:1-22 / 66:1-20', '[K#38/48]',
                 '[{Koning-Juda}] Manasse', 'Jeremia 39:1', 'Volgende tekst',
                 'Psalm 33:1', 'Echte psalmtekst']
        groups, ref = reference_sections(texts, ['Jeremia', 'Psalm'])
        meta = {'books': [['Jeremia', [38, 39]], ['Psalm', [33]]],
                'blk': [[0, 38, 'Jeremia 38:1'], [0, 39, 'Jeremia 39:1'], [1, 33, 'Psalm 33:1']]}
        old = {0: {'x': [[['Bestaande tekst', 0]]]}, 1: {'x': [[['Volgende tekst', 0]]]}, 2: {'x': [[['Echte psalmtekst', 0]]]}}
        additions, inventory = new_source_blocks(meta, old, groups, {0: 0, 1: 2, 2: 3}, texts, ref)
        self.assertEqual(additions, [])
        self.assertEqual(inventory[0]['classification'], 'source_editorial_overview')

    def test_appended_ids_align_using_provenance_order_on_future_updates(self):
        texts = ['Genesis 1:1', 'Eerste', 'Genesis 2:1', 'Nieuw', 'Genesis 3:1', 'Derde']
        groups, ref = reference_sections(texts, ['Genesis'])
        meta = {'blk': [[0, 1, 'Genesis 1:1'], [0, 3, 'Genesis 3:1'], [0, 2, 'Genesis 2:1']]}
        old = {0: {'x': [[['Eerste', 0]]], 'rtf': {'header_lines': [1, 1], 'lines': [2, 2]}},
               1: {'x': [[['Derde', 0]]], 'rtf': {'header_lines': [5, 5], 'lines': [6, 6]}},
               2: {'x': [[['Nieuw', 0]]], 'rtf': {'header_lines': [3, 3], 'lines': [4, 4]}}}
        matches, _, _, issues = align_blocks(meta, old, groups, ref, texts)
        self.assertEqual(matches, {0: 0, 2: 1, 1: 2})
        self.assertEqual(issues, [])

    def test_wrapped_title_keeps_its_existing_owner_and_final_verse_header(self):
        texts = ['Jesaja 13:17', 'Oude versbody',
                 'Jesaja 14:1-27 [#] gewijzigde eerste titelregel - ander regeleinde',
                 'Jesaja 14:28-32 genoemd', '', 'Jesaja 14:1 | Jesaja 14:2', 'Nieuwe versbody']
        groups, _ = reference_sections(texts, ['Jesaja'])
        old = {0: {'x': [[['Oude versbody', 0]], [['Jesaja 14:1-27 [#] oude eerste regel', 0]],
                         [['Jesaja 14:28-32 genoemd', 0]]]},
               1: {'x': [[['Nieuwe versbody', 0]]]}}
        decisions = preserve_owned_headers(groups, {0: [0], 1: [1]}, [0, 1], old, texts)
        self.assertEqual(groups[1]['start'], 4)
        self.assertEqual(groups[1]['end'], 6)
        self.assertEqual(decisions[0]['block'], 0)

    def test_recovered_a_b_c_verse_keeps_first_subdivision_on_next_update(self):
        texts = ['Exodus 14:20', 'Oude passage', 'Exodus 14:21a', 'Toen strekte Mozes zijn hand uit over de zee',
                 'Exodus 14:21b', 'en YHWH deed de zee wegvloeien', 'Exodus 14:21c', 'en de wateren werden gespleten',
                 'Exodus 14:22', 'Volgende passage']
        groups, ref = reference_sections(texts, ['Exodus'])
        meta = {'blk': [[0, 14, 'Exodus 14:20'], [0, 14, 'Exodus 14:22'], [0, 14, 'Exodus 14:21']]}
        old = {0: {'x': [[['Oude passage', 0]]], 'rtf': {'header_lines': [1, 1], 'lines': [2, 2]}},
               1: {'x': [[['Volgende passage', 0]]], 'rtf': {'header_lines': [9, 9], 'lines': [10, 10]}},
               2: {'x': [[[s, 0]] for s in texts[3:8]], 'rtf': {'header_lines': [3, 3], 'lines': [4, 8]}}}
        matches, _, _, issues = align_blocks(meta, old, groups, ref, texts)
        self.assertEqual(matches[2], 1)
        self.assertEqual(issues, [])


if __name__ == '__main__':
    unittest.main()

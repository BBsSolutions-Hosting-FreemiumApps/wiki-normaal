import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from wiki_links import transfer_links


class LinkTransferTests(unittest.TestCase):
    def test_same_spelling_keeps_distinct_identities_and_new_styles(self):
        old = [[["Jozef", 0, 10], [" verwekte ", 0], ["Jozef", 0, 11]]]
        new = [[["Jo", 7], ["zef verwekte Jozef", 8]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(rows, [[["Jo", 7, 10], ["zef", 8, 10],
                                 [" verwekte ", 8], ["Jozef", 8, 11]]])
        self.assertEqual(report["retained_link_segments"], 2)
        self.assertEqual(report["new_link_segments"], 3)

    def test_inserted_paragraph_does_not_move_an_identity_to_another_name(self):
        old = [[["De zoon van ", 0], ["Saul", 0, 380], [" ging naar de stad.", 0]]]
        new = [[["Nieuwe toelichting.", 1]],
               [["De zoon van Saul ging naar de stad.", 2]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 1)
        self.assertEqual([segment for row in rows if row for segment in row
                          if len(segment) > 2], [["Saul", 2, 380]])

    def test_repeated_short_context_is_flagged(self):
        old = [[["Saul", 0, 380], [" Saul", 0, 100]]]
        rows, report = transfer_links(old, [[["Saul Saul Saul", 1]]])
        self.assertEqual(report["retained_link_segments"], 0)
        self.assertEqual(len(report["issues"]), 2)
        self.assertFalse(any(len(segment) > 2 for row in rows for segment in row))

    def test_changed_name_is_reported_without_guessing(self):
        old = [[["Hij sprak met ", 0], ["Saul", 0, 380], [" buiten de stad.", 0]]]
        rows, report = transfer_links(old, [[["Hij sprak met Saulus buiten de stad.", 1]]])
        # A substring inside another spelling is not the same name occurrence.
        self.assertEqual(report["retained_link_segments"], 0)

    def test_style_split_name_is_assessed_as_complete_occurrence(self):
        old = [[["Hij sprak met ", 0], ["Sa", 0, 380], ["ul", 1, 380],
                [" buiten de stad.", 0]]]
        rows, report = transfer_links(old, [[["Hij sprak met Salomo buiten de stad.", 1]]])
        self.assertEqual(report["retained_link_segments"], 0)
        self.assertEqual(report["unresolved_link_segments"], 2)

    def test_deleted_occurrence_is_reported(self):
        old = [[["In het land ", 0], ["Eden", 0, 50], [" stond een boom.", 0]]]
        rows, report = transfer_links(old, [[["In het land stond een boom.", 0]]])
        self.assertEqual(report["unresolved_link_segments"], 1)

    def test_new_ids_are_never_inferred(self):
        old = [[["In het land.", 0]]]
        rows, report = transfer_links(old, [[["In Eden.", 4, 999]]])
        self.assertEqual(rows, [[["In Eden.", 4]]])
        self.assertEqual(report["old_link_segments"], 0)

    def test_gaps_and_empty_rows_stay_intact(self):
        old = [0, [], [["Saul", 0, 380]], None]
        rows, report = transfer_links(old, [0, [], [["Saul", 2]], None])
        self.assertEqual(rows, [0, [], [["Saul", 2, 380]], None])

    def test_line_wrapping_keeps_repeated_names_in_occurrence_order(self):
        old = [[["Jozef", 0, 10], [" verwekte ", 0], ["Jozef", 0, 11]]]
        new = [[["Jozef", 7]], [["verwekte", 8]], 0, [["Jozef", 9]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(rows, [[["Jozef", 7, 10]], [["verwekte", 8]],
                                0, [["Jozef", 9, 11]]])
        self.assertEqual(report["retained_link_segments"], 2)
        self.assertEqual({item["match_method"] for item in report["retained"]},
                         {"whitespace_projection"})

    def test_new_wrapping_and_additional_notes_use_exact_context(self):
        old = [[["De zoon van ", 0], ["Saul", 0, 380],
                [" ging naar de stad en wachtte daar.", 0]]]
        new = [[["De zoon van Saul", 4]],
               [["ging naar de stad en wachtte daar.", 5]],
               [["[#] Nieuwe bronnotitie.", 6]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 1)
        self.assertEqual([segment for row in rows if row for segment in row
                          if len(segment) > 2], [["Saul", 4, 380]])
        self.assertEqual(''.join(segment[0] for row in rows if row for segment in row),
                         ''.join(segment[0] for row in new if row for segment in row))

    def test_whitespace_projection_does_not_link_a_changed_name_prefix(self):
        old = [[["De zoon van ", 0], ["Saul", 0, 380],
                [" ging naar de stad en wachtte daar.", 0]]]
        new = [[["De zoon van Saulus", 4]],
               [["ging naar de stad en wachtte daar.", 5]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 0)

    def test_trailing_linked_space_does_not_hide_changed_name_suffix(self):
        old = [[["De zoon van ", 0], ["Saul ", 0, 380],
                ["ging naar de stad en wachtte daar.", 0]]]
        new = [[["De zoon van Saulus", 4]],
               [["ging naar de stad en wachtte daar.", 5]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 0)

    def test_new_nonbreaking_space_preserves_name_identity(self):
        old = [[["De zoon van ", 0], ["Saul", 0, 380],
                [" ging naar de stad.", 0]]]
        new = [[["De\u00a0zoon\u00a0van\u00a0Saul\u00a0ging\u00a0naar\u00a0de\u00a0stad.", 1]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 1)
        self.assertEqual([segment for row in rows if row for segment in row
                          if len(segment) > 2], [["Saul", 1, 380]])

    def test_unique_complete_short_body_remains_linked_with_added_notes(self):
        old = [[["H", 0, 282], ["ada", 1, 282], ["r", 0, 282]]]
        new = [[["Hadar", 3]], 0, [["[#] Aanvullende bronnotitie.", 4]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 3)
        self.assertEqual(''.join(segment[0] for row in rows if row for segment in row
                                 if len(segment) > 2), "Hadar")

    def test_complete_short_body_with_two_new_occurrences_is_ambiguous(self):
        old = [[["Hadar", 0, 282]]]
        new = [[["Hadar", 3]], [["[#] Hadar wordt opnieuw genoemd.", 4]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 0)

    def test_alias_inserted_after_initial_name_uses_exact_right_context(self):
        old = [[["H", 0, 282], ["ada", 1, 282], ["r", 0, 282]],
               [["Tema", 0]], [["Jetur", 0]], [["Nafis", 0]], [["en Kedema", 0]]]
        new = [[["Genesis 25:15", 0]], [["Hadar [{‘Chadad’}]", 3]],
               [["Tema", 4]], [["Jetur", 4]], [["Nafis", 4]], [["en Kedema", 4]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 3)
        self.assertEqual({item["match_method"] for item in report["retained"]},
                         {"context_projection"})

    def test_reference_annotations_may_change_between_exact_flanks(self):
        old = [[["en Andreas (M4/L2)", 0]],
               [["Filippus ", 0, 2562], ["I", 1, 2562], [" (M5/L5)", 0]],
               [["en Tomas [Didymus] (M8/L8)", 0]]]
        new = [[["en Andreas (M4/Mt2/L2)", 0]],
               [["Filippus I (M5/Mt5/L5)", 3]],
               [["en Tomas [Didymus] (M8/Mt7/L8)", 0]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 2)
        linked = [segment[0] for row in rows if row for segment in row
                  if len(segment) > 2 and segment[2] == 2562]
        self.assertEqual(''.join(linked), 'Filippus I')

    def test_new_alias_quotes_are_not_a_name_extension(self):
        old = [[["Nachson [09/42] verwekte Salmon {", 0], ["Salma", 0, 1146],
                ["} *)", 0]], 0, [["[{6e generatie > Juda}]", 0]]]
        new = [[["Nachson [09/42] verwekte Salmon [{‘Salma’}]", 1]],
               0, [["[{6e generatie > Juda}]", 1]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 1)

    def test_apostrophe_name_extension_stays_unlinked(self):
        old = [[["Hij sprak met ", 0], ["Saul", 0, 380], [" buiten de stad.", 0]]]
        new = [[["Hij sprak met Saul’s buiten de stad.", 1]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report["retained_link_segments"], 0)

    def alias_fixture(self, subject='Taddeus', extra_alias=''):
        old = [[["en Taddeus (M10/L ", 0], ["Judas", 0, 2796],
                [" zoon van ", 0], ["Jakobus", 0, 2543], [")", 0]]]
        new = [[["en " + subject + " (M10/L11) [{‘Judas’}] " + extra_alias
                 + "[Volgens Markus 3:17-18 en Lukas 6:15 is Judas de zoon van Jakobus]", 1]]]
        following_rows = [[["en Simon (M11/L10) de Zeloot", 0]],
                          [["en Judas Iskariot (M12/L12)", 0]]]
        old.extend(following_rows)
        new.extend(following_rows)
        return old, new

    def test_explicit_alias_with_same_subject_and_retained_relative(self):
        old, new = self.alias_fixture()
        rows, report = transfer_links(old, new)
        aliases = [item for item in report['retained'] if item['entity_id'] == 2796]
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0]['match_method'], 'explicit_source_alias')
        text = ''.join(segment[0] for row in rows for segment in row)
        self.assertEqual(text, ''.join(segment[0] for row in new for segment in row))
        linked = [segment for row in rows for segment in row if len(segment) > 2]
        self.assertEqual([(segment[0], segment[2]) for segment in linked],
                         [('Judas', 2796), ('Jakobus', 2543)])
        self.assertEqual(report['unresolved_link_segments'], 0)

    def test_two_explicit_alias_candidates_remain_unresolved(self):
        old, new = self.alias_fixture(extra_alias='[{‘Judas’}] ')
        rows, report = transfer_links(old, new)
        self.assertFalse(any(item['entity_id'] == 2796 for item in report['retained']))
        self.assertTrue(any(item['entity_id'] == 2796 for item in report['issues']))

    def test_homonym_under_another_subject_is_not_the_old_alias(self):
        old, new = self.alias_fixture(subject='Andreas')
        rows, report = transfer_links(old, new)
        self.assertFalse(any(item['entity_id'] == 2796 for item in report['retained']))

    def test_alias_requires_independently_retained_relative_identity(self):
        old, new = self.alias_fixture()
        new = [[[new[0][0][0].replace('Jakobus', 'Jakobus II'), 1]]]
        # The old relative has no matching whole name boundary, so cannot be
        # used as independent identity evidence for the ambiguous alias.
        old[0][3][0] = 'Jozef'
        rows, report = transfer_links(old, new)
        self.assertFalse(any(item['entity_id'] == 2796 for item in report['retained']))

    def relationship_fixture(self, repeat=False, changed_name=False):
        generation = 'Generatiemarkering met uitgebreide vaste tekst ' * 8
        old = [[[generation, 0]], [["[!] [Vader van ", 0],
                                  ["Jonadab ", 0, 1239], ["I", 1, 1239]],
               [["vriend van ", 0], ["Amnon", 0, 1209], ["]", 0]]]
        first_name = 'Jonadab II' if changed_name else 'Jonadab I'
        note = '[!] [Netan-el III is de vader van ' + first_name + ' - vriend van Amnon]'
        new = [[[note, 4]]]
        if repeat:
            new.append([[note, 4]])
        new.append([[generation, 5]])
        return old, new

    def test_unique_relationship_survives_note_reordering(self):
        old, new = self.relationship_fixture()
        rows, report = transfer_links(old, new)
        self.assertEqual(report['unresolved_link_segments'], 0)
        self.assertEqual(report['retained_link_segments'], 3)
        self.assertEqual({item['match_method'] for item in report['retained']},
                         {'explicit_note_relationship'})
        linked = [segment[0] for row in rows if row for segment in row
                  if len(segment) > 2 and segment[2] == 1239]
        self.assertEqual(''.join(linked), 'Jonadab I')

    def test_repeated_relationship_pairs_are_not_disambiguated_by_name(self):
        old, new = self.relationship_fixture(repeat=True)
        rows, report = transfer_links(old, new)
        self.assertEqual(report['retained_link_segments'], 0)

    def test_changed_relationship_member_does_not_keep_old_name_prefix(self):
        old, new = self.relationship_fixture(changed_name=True)
        rows, report = transfer_links(old, new)
        self.assertFalse(any(item['entity_id'] == 1239 for item in report['retained']))

    def reference_fixture(self, new_header):
        body = 'Zij zei tot hem en vroeg naar het levende water. ' * 5
        old = [[[body, 0]], [["\t", 0], ["J", 0, 1574], ["ohannes", 1, 1574],
                                            [" 4:12", 0]],
               [["Zijt Gij meer dan onze vader Jakob?", 0]]]
        new = [[[new_header, 3]], [[body, 4]],
               [["Zijt Gij meer dan onze vader Jakob?", 4]]]
        return old, new

    def test_reference_key_keeps_link_when_reference_moves_into_header(self):
        old, new = self.reference_fixture('Johannes 4:11 | Johannes 4:12')
        rows, report = transfer_links(old, new)
        self.assertEqual(report['retained_link_segments'], 2)
        self.assertEqual({item['match_method'] for item in report['retained']},
                         {'exact_reference_key'})
        self.assertEqual(min(item['new_start'] for item in report['retained']), 16)

    def test_repeated_reference_key_remains_unresolved(self):
        old, new = self.reference_fixture('Johannes 4:12 | Johannes 4:12')
        rows, report = transfer_links(old, new)
        self.assertEqual(report['retained_link_segments'], 0)

    def test_other_verse_reference_does_not_receive_old_link(self):
        old, new = self.reference_fixture('Johannes 4:11 | Johannes 4:13')
        rows, report = transfer_links(old, new)
        self.assertEqual(report['retained_link_segments'], 0)

    def test_internal_space_between_original_style_runs_stays_linked(self):
        old = [[["Herodes ", 0, 5], ["II", 1, 5],
                [" sprak tot het volk.", 0]]]
        new = [[["Herodes II", 4]], [["sprak tot het volk.", 5]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report['retained_link_segments'], 2)
        self.assertEqual(''.join(segment[0] for segment in rows[0]
                                 if len(segment) > 2), 'Herodes II')
        self.assertEqual(report['linked_internal_whitespace_spans'], 1)

    def test_same_id_on_separate_old_occurrences_does_not_bridge_separator(self):
        old = [[["Saul", 0, 380], [" ", 0], ["Saul", 0, 380],
                [" ging door de poort.", 0]]]
        new = [[["Saul  Saul", 1]], [["ging door de poort.", 2]]]
        rows, report = transfer_links(old, new)
        self.assertEqual(report['retained_link_segments'], 2)
        self.assertEqual(report['linked_internal_whitespace_spans'], 0)
        self.assertEqual([segment for segment in rows[0] if len(segment) == 2],
                         [['  ', 1]])

    def test_all_existing_genesis_two_links_survive_style_changes(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "data/b/0.js").read_text().strip()
        book = json.loads(source.split(",", 1)[1][:-2])
        retained = total = 0
        for block_id in book["ch"]["2"]:
            old = book["bl"][str(block_id)]["x"]
            fresh = [row if not isinstance(row, list) else [[segment[0], 100] for segment in row]
                     for row in old]
            rows, report = transfer_links(old, fresh)
            total += report["old_link_segments"]
            retained += report["retained_link_segments"]
        self.assertEqual(total, 13)
        self.assertEqual(retained, total)


if __name__ == "__main__":
    unittest.main()

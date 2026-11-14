"""Safety regressions: bad IDs, same-name identities and accidental data loss."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_conversion import load_callback, verify_site


def write(path, prefix, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prefix + json.dumps(value, ensure_ascii=False) + ");\n", encoding="utf-8")


def make_site(root):
    books = [["Genesis", [1, 2]]] + [[f"Book{i}", []] for i in range(1, 66)]
    meta = {"books": books, "blk": [[0, 1, "Genesis 1:1"], [0, 2, "Genesis 2:1"],
                                     [0, 2, "Genesis 2:2"]],
            "sty": ["color:#000000", "color:#ff0000;font-weight:700"],
            "ents": [["Adam", "P", "z", 1, []], ["Eden", "O", "z", 1, []],
                     ["Adam", "P", "z", 1, []]], "nch": 2,
            "notes": [{"n": 1, "t": "Een bestaande studienotitie", "r": "Genesis 2:1"}]}
    write(root / "data/meta.js", "SBW.gotMeta(", meta)
    blocks = {"0": {"l": "Genesis 1:1", "x": [[["Adam", 0, 0]], 0]},
              "1": {"l": "Genesis 2:1", "x": [[["Eden", 0, 1], [" in de hof", 0]]]},
              "2": {"l": "Genesis 2:2", "x": [[["Adam", 0, 2]]]}}
    for i in range(66):
        write(root / f"data/b/{i}.js", f"SBW.gotBook({i},",
              {"ch": {"1": [0], "2": [1, 2]}, "bl": blocks} if i == 0 else {"ch": {}, "bl": {}})
    entities = {"0": {"n": "Adam", "t": "persoon", "c": "zeker", "o": [0], "nt": [], "q": []},
                "1": {"n": "Eden", "t": "plaats", "c": "zeker", "o": [1], "nt": [0], "q": [[1, "Eden"]]},
                "2": {"n": "Adam", "t": "persoon", "c": "zeker", "o": [2], "nt": [], "q": []}}
    for i in range(2):
        write(root / f"data/e{i}.js", "SBW.gotEnts(",
              {k: e for k, e in entities.items() if int(k) % 2 == i})


class DataVerificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name) / "baseline"
        self.site = Path(self.directory.name) / "candidate"
        make_site(self.base)
        shutil.copytree(self.base, self.site)

    def mutate(self, relative, prefix, function):
        path = self.site / relative
        value = load_callback(path, prefix)
        function(value)
        write(path, prefix, value)

    def codes(self):
        return {e["code"] for e in verify_site(self.site, self.base)["errors"]}

    def append_source_block(self, chapter=3):
        def metadata(meta):
            meta["blk"].append([0, chapter, f"Genesis {chapter}:3"])
            if chapter not in meta["books"][0][1]:
                meta["books"][0][1].append(chapter)
        self.mutate("data/meta.js", "SBW.gotMeta(", metadata)
        def book_data(book):
            book["bl"]["3"] = {"l": f"Genesis {chapter}:3", "x": [[["Nieuwe brontekst", 0]]]}
            chapter_ids = book["ch"].setdefault(str(chapter), [])
            chapter_ids.insert(1 if chapter_ids else 0, 3)
        self.mutate("data/b/0.js", "SBW.gotBook(0,", book_data)

    def test_existing_data_and_legacy_gap_rows_pass(self):
        report = verify_site(self.site, self.base)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["counts"]["linked_segments"], 3)
        self.assertFalse(report["publication_approved"])

    def test_invalid_style_id_is_rejected(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["1"]["x"][0][0].__setitem__(1, 999))
        self.assertIn("style_id", self.codes())

    def test_invalid_entity_id_is_rejected(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["1"]["x"][0][0].__setitem__(2, 999))
        self.assertIn("entity_id", self.codes())

    def test_same_spelling_different_identity_cannot_be_swapped(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["2"]["x"][0][0].__setitem__(2, 0))
        self.assertIn("lost_name_links", self.codes())

    def test_name_split_across_new_style_runs_preserves_identity(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["1"].__setitem__("x", [[["Ed", 0, 1], ["en", 1, 1], [" in de hof", 0]]]))
        report = verify_site(self.site, self.base)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["counts"]["linked_segments"], 4)
        self.assertEqual(report["counts"]["linked_occurrences"], 3)
        self.assertEqual(report["baseline"]["changes"]["style_blocks"], [1])

    def test_cosmetic_segment_split_is_not_a_style_change(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["1"].__setitem__("x", [[["Ed", 0, 1], ["en", 0, 1], [" in de hof", 0]]]))
        report = verify_site(self.site, self.base)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["baseline"]["changes"]["style_blocks"], [])

    def test_missing_block_fails_even_if_remaining_js_is_valid(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,", lambda b: b["bl"].pop("1"))
        self.assertIn("missing_block", self.codes())

    def test_chapter_move_is_rejected(self):
        def move(book):
            book["ch"]["1"].append(book["ch"]["2"].pop(0))
        self.mutate("data/b/0.js", "SBW.gotBook(0,", move)
        self.assertIn("chapter_boundary", self.codes())

    def test_deleted_study_note_is_rejected(self):
        self.mutate("data/meta.js", "SBW.gotMeta(", lambda m: m.__setitem__("notes", []))
        self.assertIn("study_notes_changed", self.codes())

    def test_incorrect_eden_classification_is_rejected(self):
        self.mutate("data/e1.js", "SBW.gotEnts(", lambda e: e["1"].__setitem__("t", "persoon"))
        self.assertIn("eden_classification", self.codes())

    def test_missing_link_may_not_hide_in_plain_text(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,", lambda b: b["bl"]["1"]["x"][0][0].pop())
        self.assertIn("lost_name_links", self.codes())

    def test_javascript_outside_json_callback_is_not_executed_or_accepted(self):
        path = self.site / "data/b/0.js"
        path.write_text(path.read_text() + "alert('unexpected');", encoding="utf-8")
        self.assertIn("book_schema", self.codes())

    def test_new_source_header_and_preface_links_do_not_change_old_body_identities(self):
        def supplement(book):
            book["bl"]["1"]["r"] = [[["Genesis 2:1 ", 0], ["Eden", 1, 1]]]
            book["bl"]["1"]["pre"] = [[["Kopje: ", 1], ["Adam", 0, 0]], 0]
        self.mutate("data/b/0.js", "SBW.gotBook(0,", supplement)
        write(self.site / "data/rtf-extra.js", "SBW.gotRtfExtra(",
              {"title": "Voorwerk", "rows": [[["Adam", 0, 0]], 0]})
        report = verify_site(self.site, self.base)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["counts"]["linked_segments"], 3)
        self.assertEqual(report["counts"]["all_linked_segments"], 6)
        self.assertEqual(report["baseline"]["changes"]["lost_link_occurrences"], [])

    def test_original_body_link_may_move_to_its_own_source_header(self):
        def move(book):
            book["bl"]["1"]["x"][0][0].pop()
            book["bl"]["1"]["r"] = [[["Eden", 0, 1]]]
        self.mutate("data/b/0.js", "SBW.gotBook(0,", move)
        report = verify_site(self.site, self.base)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["counts"]["linked_segments"], 2)
        self.assertEqual(report["counts"]["all_linked_segments"], 3)
        self.assertEqual(report["baseline"]["changes"]["lost_link_occurrences"], [])

    def test_original_body_link_may_move_to_its_own_source_prefix(self):
        def move(book):
            book["bl"]["1"]["x"][0][0].pop()
            book["bl"]["1"]["pre"] = [[["Eden", 0, 1]]]
        self.mutate("data/b/0.js", "SBW.gotBook(0,", move)
        report = verify_site(self.site, self.base)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["baseline"]["changes"]["lost_link_occurrences"], [])

    def test_original_body_link_moved_to_another_block_prefix_is_rejected(self):
        def move(book):
            book["bl"]["1"]["x"][0][0].pop()
            book["bl"]["2"]["pre"] = [[["Eden", 0, 1]]]
        self.mutate("data/b/0.js", "SBW.gotBook(0,", move)
        self.assertIn("lost_name_links", self.codes())

    def test_future_baseline_header_links_are_preserved_too(self):
        path = self.base / "data/b/0.js"
        book = load_callback(path, "SBW.gotBook(0,")
        book["bl"]["1"]["r"] = [[["Adam", 0, 0]]]
        write(path, "SBW.gotBook(0,", book)
        self.assertIn("lost_name_links", self.codes())

    def test_source_header_style_is_validated(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["1"].__setitem__("r", [[["Genesis 2:1", 999]]]))
        self.assertIn("style_id", self.codes())

    def test_source_prefix_name_link_is_validated(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["1"].__setitem__("pre", [[["Naam", 0, 999]]]))
        self.assertIn("entity_id", self.codes())

    def test_source_preface_style_and_names_are_validated(self):
        write(self.site / "data/rtf-extra.js", "SBW.gotRtfExtra(",
              {"title": "Voorwerk", "rows": [[["Naam", 999, 999]]]})
        self.assertIn("style_id", self.codes())
        self.assertIn("entity_id", self.codes())

    def test_converted_metadata_requires_source_preface_file(self):
        self.mutate("data/meta.js", "SBW.gotMeta(", lambda m: m.__setitem__("conversion", {"source": "new.rtf"}))
        self.assertIn("extra_schema", self.codes())

    def test_malformed_source_prefix_rows_are_rejected(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["1"].__setitem__("pre", "plain string is not structured source"))
        self.assertIn("rows_schema", self.codes())

    def test_malformed_segment_text_generates_a_report_instead_of_crashing(self):
        self.mutate("data/b/0.js", "SBW.gotBook(0,",
                    lambda b: b["bl"]["1"].__setitem__("x", [[[123, 0, 1], [456, 0, 1]]]))
        self.assertIn("segment_text", self.codes())

    def test_new_block_and_chapter_may_be_appended_without_changing_old_ids(self):
        self.append_source_block()
        report = verify_site(self.site, self.base)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["baseline"]["changes"]["added_blocks"], [3])
        self.assertEqual(report["baseline"]["changes"]["added_chapters"], [{"book": 0, "chapter": 3}])
        self.assertEqual(report["baseline"]["growth"],
                         {"original_blocks": 3, "candidate_blocks": 4, "added_blocks": 1, "added_chapters": 1})

    def test_new_block_may_be_inserted_between_old_blocks_in_existing_chapter(self):
        self.append_source_block(chapter=2)
        report = verify_site(self.site, self.base)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["baseline"]["changes"]["chapter_lists"], [])

    def test_existing_block_order_cannot_change_when_new_blocks_are_added(self):
        self.append_source_block(chapter=2)
        self.mutate("data/b/0.js", "SBW.gotBook(0,", lambda b: b["ch"].__setitem__("2", [2, 3, 1]))
        self.assertIn("chapter_order_changed", self.codes())

    def test_existing_metadata_ids_cannot_be_overwritten_by_new_source(self):
        self.append_source_block()
        self.mutate("data/meta.js", "SBW.gotMeta(",
                    lambda m: m["blk"][0].__setitem__(2, "Genesis 1:99"))
        self.mutate("data/b/0.js", "SBW.gotBook(0,", lambda b: b["bl"]["0"].__setitem__("l", "Genesis 1:99"))
        self.assertIn("block_identity_changed", self.codes())

    def test_appended_block_must_belong_to_its_declared_chapter(self):
        self.append_source_block(chapter=3)
        self.mutate("data/b/0.js", "SBW.gotBook(0,", lambda b: b["ch"].__setitem__("3", []))
        self.mutate("data/b/0.js", "SBW.gotBook(0,", lambda b: b["ch"]["2"].append(3))
        self.assertIn("chapter_boundary", self.codes())

    def test_existing_chapter_order_cannot_change(self):
        def reorder(meta):
            meta["books"][0][1] = [2, 1]
        self.mutate("data/meta.js", "SBW.gotMeta(", reorder)
        self.mutate("data/b/0.js", "SBW.gotBook(0,", lambda b: b.__setitem__("ch", {"2": [1, 2], "1": [0]}))
        self.assertIn("book_structure_changed", self.codes())

    def test_stale_stats_after_adding_source_blocks_are_rejected(self):
        self.append_source_block()
        self.mutate("data/meta.js", "SBW.gotMeta(", lambda m: m.__setitem__("stats", {"blokken": 3}))
        self.assertIn("block_statistics", self.codes())


if __name__ == "__main__":
    unittest.main()

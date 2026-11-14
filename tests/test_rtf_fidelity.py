"""Independent source/format/coverage regressions with a small known RTF fixture."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_rtf_fidelity import verify


def write_json_callback(path, prefix, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prefix + json.dumps(value) + ');\n', encoding='utf-8')


class RTFFidelityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.rtf'
        self.site = self.root / 'site'
        self.map = self.root / 'source-map.json'
        self.source.write_bytes(br'{\rtf1{\colortbl;\red255\green0\blue0;\red0\green255\blue0;}Title\par (#) comment\par Genesis 2:1\par \par \cf1\b Text\par \ul\ulc2 Note\par}')
        self.meta = dict(books=[['Genesis', [2]]], blk=[[0,2,'Genesis 2:1']],
            sty=['font-size:12pt', 'font-size:12pt;color:#ff0000;font-weight:700', 'font-size:12pt;color:#ff0000;font-weight:700;text-decoration:underline;text-decoration-color:#00ff00'])
        self.book = dict(ch={'2':[0]}, bl={'0':dict(l='Genesis 2:1',
            pre=[[['(#) comment',0]]], r=[[['Genesis 2:1',0]]],
            x=[[['Text',1]],[['Note',2]]])})
        self.records = [dict(block=0, prefix=[1,2],header=[2,3],body=[3,7])]
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        write_json_callback(self.site/'data/meta.js', 'SBW.gotMeta(', self.meta)
        write_json_callback(self.site/'data/b/0.js', 'SBW.gotBook(0,', self.book)
        write_json_callback(self.site/'data/rtf-extra.js', 'SBW.gotRtfExtra(', dict(title='Voorwerk', rows=[[['Title',0]]]))
        self.map.write_text(json.dumps(self.records))

    def check(self, **kwargs):
        self.save()
        return verify(self.source, self.site, self.map, **kwargs)

    def test_complete_fidelity_and_blank_edge_trimming(self):
        report = self.check()
        self.assertTrue(report['passed'], report)
        self.assertEqual(report['counts']['covered_source_lines'], 7)
        self.assertEqual(report['counts']['uncovered_source_lines'], 0)

    def test_missing_comment_fails(self):
        self.book['bl']['0']['pre'] = []
        report = self.check()
        self.assertFalse(report['passed'])
        self.assertIn('character_text', report['error_counts'])

    def test_color_and_underline_color_loss_fail(self):
        self.meta['sty'][2] = 'font-size:12pt;color:#000000;font-weight:700;text-decoration:underline'
        report = self.check()
        self.assertFalse(report['passed'])
        self.assertIn('character_format', report['error_counts'])

    def test_underline_color_checked_even_if_foreground_unchanged(self):
        self.meta['sty'][2] = 'font-size:12pt;color:#ff0000;font-weight:700;text-decoration:underline'
        report = self.check()
        self.assertFalse(report['passed'])
        self.assertIn('character_format', report['error_counts'])

    def test_duplicate_spans_and_duplicate_map_ids_fail(self):
        self.records.append(self.records[0].copy())
        report = self.check()
        self.assertFalse(report['passed'])
        self.assertIn('source_overlap', report['error_counts'])
        self.assertIn('duplicate_map_block', report['error_counts'])

    def test_missing_span_fails_full_but_explicit_partial_reports_gap(self):
        self.records[0]['header'] = None
        self.book['bl']['0']['r'] = []
        report = self.check()
        self.assertFalse(report['passed'])
        self.assertIn('source_gap', report['error_counts'])
        partial = self.check(partial=True)
        self.assertTrue(partial['passed'], partial)
        self.assertEqual(partial['counts']['uncovered_source_lines'], 1)

    def test_internal_whitespace_is_preserved(self):
        self.book['bl']['0']['x'][0] = [['T ext', 1]]
        report = self.check()
        self.assertFalse(report['passed'])
        self.assertIn('line_text', report['error_counts'])
        self.assertNotIn('character_text', report['error_counts'])

    def test_link_splitting_does_not_change_fidelity(self):
        self.book['bl']['0']['x'][0] = [['Te',1,123],['xt',1,123]]
        report = self.check()
        self.assertTrue(report['passed'], report)

    def test_font_size_loss_fails(self):
        self.meta['sty'][1] = self.meta['sty'][1].replace('12pt', '11pt')
        report = self.check()
        self.assertFalse(report['passed'])
        self.assertIn('character_format', report['error_counts'])

    def test_font_family_loss_fails(self):
        raw = self.source.read_bytes().replace(br'{\rtf1', br'{\rtf1{\fonttbl{\f0\froman Times-Roman;}}', 1)
        self.source.write_bytes(raw)
        self.meta['sty'] = [style + ";font-family:'Times',serif" for style in self.meta['sty']]
        self.assertTrue(self.check()['passed'])
        self.meta['sty'][1] = self.meta['sty'][1].replace("'Times'", "'Arial'")
        report = self.check()
        self.assertFalse(report['passed'])
        self.assertIn('character_format', report['error_counts'])


if __name__ == '__main__':
    unittest.main()

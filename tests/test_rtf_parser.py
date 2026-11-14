"""Focused parser regressions; run python3 -m unittest discover -s tests."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from rtf_parser import parse_rtf, parse_rtf_bytes


def text(document):
    return '\n'.join(''.join(run['text'] for run in line) for line in document['lines'])


class RTFParserTests(unittest.TestCase):
    def test_groups_colors_and_escaped_characters(self):
        doc = parse_rtf_bytes(br'{\rtf1{\colortbl;\red255\green0\blue0;}a {\b\cf1 b} c \\ \{\}}')
        self.assertEqual(text(doc), 'a b c \\ {}')
        runs = doc['lines'][0]
        self.assertTrue(runs[1]['style']['bold'])
        self.assertEqual(runs[1]['style']['color'], '#ff0000')
        self.assertFalse(runs[2]['style']['bold'])
        self.assertIsNone(runs[2]['style']['color'])

    def test_unicode_fallback_and_codepage(self):
        doc = parse_rtf_bytes(br"{\rtf1\ansi\ansicpg1252\uc1 caf\u233\'e9 \uc0\u257  \'93x\'94}")
        self.assertEqual(text(doc), 'café ā “x”')

    def test_destinations_fields_and_lines(self):
        doc = parse_rtf_bytes(b'{\\rtf1{\\fonttbl ignored}{\\*\\unknown hidden}a\n{\\field{\\*\\fldinst HYPERLINK secret}{\\fldrslt visible}}\\\nb\\par c\\line d\\tab e}')
        self.assertEqual(text(doc), 'avisible\nb\nc\nd\te')

    def test_unicode_surrogates(self):
        self.assertEqual(text(parse_rtf_bytes(br'{\rtf1\uc0\u-10179\u-8704}')), '😀')

    def test_binary_destinations_do_not_consume_following_text(self):
        self.assertEqual(text(parse_rtf_bytes(br'{\rtf1 A{\pict\bin5 a{}bc}Z}')), 'AZ')

    def test_font_families_variants_default_and_point_size(self):
        doc = parse_rtf_bytes(br'{\rtf1\deff1{\fonttbl{\f0\froman Times-BoldItalic;}{\f1\froman Times New Roman;}{\f2\fswiss Example-Regular;}}\fs22 A {\f0\fs36 B} C\f2 D\plain E}')
        self.assertEqual(doc['fonts'][0]['family'], 'Times')
        self.assertEqual(doc['fonts'][1]['family'], 'Times New Roman')
        self.assertEqual(doc['fonts'][2]['family'], 'Example')
        runs = doc['lines'][0]
        self.assertEqual(runs[0]['style']['font_family'], 'Times New Roman')
        self.assertEqual(runs[0]['style']['font_size_points'], 11)
        self.assertEqual(runs[1]['style']['font_family'], 'Times')
        self.assertEqual(runs[1]['style']['font_size_points'], 18)
        self.assertEqual(runs[-1]['style']['font_family'], 'Times New Roman')
        self.assertEqual(runs[-1]['style']['font_size_points'], 12)

    def test_unicode_font_names_and_hidden_alternate_names(self):
        doc = parse_rtf_bytes(br'{\rtf1{\fonttbl{\f0\fnil{\*\falt Hidden;}B\uc1\u233?ta-Regular;}}Text}')
        self.assertEqual(doc['fonts'][0]['family'], 'Béta')
        self.assertEqual(doc['lines'][0][0]['style']['font_family'], 'Béta')

    def test_unbalanced_groups_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_rtf_bytes(br'{\rtf1 text')

    def test_real_genesis2_has_styled_names(self):
        path = Path(__file__).resolve().parents[1] / 'Ai-Elohim-YHWH-Studiebijbel-2026 (3).rtf'
        if not path.exists():
            self.skipTest('RTF fixture not present')
        doc = parse_rtf(path)
        lines = doc['lines']
        start = next(i for i,line in enumerate(lines) if ''.join(r['text'] for r in line).startswith('Genesis 2:1'))
        end = next(i for i,line in enumerate(lines[start+1:],start+1) if ''.join(r['text'] for r in line).startswith('Genesis 3:1'))
        chapter = '\n'.join(''.join(r['text'] for r in line) for line in lines[start:end])
        self.assertIn('Eden', chapter)
        self.assertIn('Chawila', chapter)
        eden = [r for line in lines[start:end] for r in line if 'Eden' in r['text']]
        self.assertTrue(eden)
        self.assertTrue(any(r['style']['color'] == '#fb0207' and r['style']['bold'] and r['style']['italic'] for r in eden))
        self.assertEqual(doc['unsupported_controls'], {})
        self.assertEqual(doc['fonts'][0]['family'], 'Times')
        self.assertEqual(eden[-1]['style']['font_size_points'], 18)


if __name__ == '__main__':
    unittest.main()

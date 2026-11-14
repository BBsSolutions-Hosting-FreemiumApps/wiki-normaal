#!/usr/bin/env python3
"""Independently compare converted site fields with their exact RTF source spans.

Checks text (including spaces/tabs within lines), visible character formatting,
source coverage and source-map completeness. Does not import the converter and
never modifies source/site data. Exit status 0 is technical fidelity, not release
approval. Use --partial only for an explicitly limited conversion such as Genesis 2.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import re

from rtf_parser import parse_rtf

_FIELDS = {'prefix':'pre', 'header':'r', 'body':'x'}


def _read(path: Path, prefix: str):
    text = path.read_text(encoding='utf-8').strip()
    if not text.startswith(prefix) or not text.endswith(');'):
        raise ValueError(f'Unexpected JavaScript wrapper: {path}')
    return json.loads(text[len(prefix):-2])


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _color(value):
    value = value.lower().strip() if value else None
    if value in (None, 'transparent', 'initial', 'inherit', 'currentcolor', 'auto'):
        return None
    if re.fullmatch(r'#[0-9a-f]{3}', value):
        return '#' + ''.join(c * 2 for c in value[1:])
    match = re.fullmatch(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', value)
    if match:
        return '#%02x%02x%02x' % tuple(map(int, match.groups()))
    return value


def _font_family(value):
    if not value:
        return None
    # CSS font-family is case-insensitive; inspect the requested first family,
    # leaving fallback selection to the browser.
    match = re.match(r'''\s*(?:"((?:\\.|[^"])*)"|'((?:\\.|[^'])*)'|([^,]+))''', value)
    if not match:
        return None
    name = next(part for part in match.groups() if part is not None)
    name = re.sub(r'\\(.)', r'\1', name)
    return ' '.join(name.split()).casefold()


def _font_size(value):
    if value is None:
        return None
    match = re.fullmatch(r'([0-9.]+)\s*(pt|px)', value.strip().lower())
    if match:
        return float(match[1]) * (0.75 if match[2] == 'px' else 1)
    return value


def source_style(style):
    """Compare visible semantics, including source family and point size."""
    underline = bool(style.get('underline'))
    foreground = _color(style.get('color'))
    return (foreground, _color(style.get('background')), bool(style.get('bold')),
            bool(style.get('italic')), underline, bool(style.get('strike')),
            int(style.get('superscript', 0)),
            _color(style.get('underline_color')) or foreground if underline else None,
            _font_family(style.get('font_family')), style.get('font_size_points', 12.0))


def css_style(css):
    properties = dict(item.strip().split(':', 1) for item in css.split(';') if ':' in item)
    properties = {key.strip().lower(): value.strip().lower() for key, value in properties.items()}
    weight = properties.get('font-weight', 'normal')
    bold = weight in ('bold', 'bolder') or (weight.isdigit() and int(weight) >= 600)
    decorations = (properties.get('text-decoration', '') + ' ' + properties.get('text-decoration-line', '')).split()
    underline = 'underline' in decorations
    foreground = _color(properties.get('color'))
    return (foreground, _color(properties.get('background-color', properties.get('background'))),
            bold, properties.get('font-style') in ('italic', 'oblique'), underline,
            'line-through' in decorations,
            {'super':1, 'sub':-1}.get(properties.get('vertical-align'), 0),
            _color(properties.get('text-decoration-color')) or foreground if underline else None,
            _font_family(properties.get('font-family')), _font_size(properties.get('font-size')))


def _source_texts(lines):
    return [''.join(run['text'] for run in line) for line in lines]


def _site_texts(rows):
    return [''.join(segment[0] for segment in row) if row else '' for row in rows]


def _trim_empty(values):
    start, end = 0, len(values)
    while start < end and values[start] == '':
        start += 1
    while end > start and values[end - 1] == '':
        end -= 1
    return values[start:end]


def _source_chars(lines):
    for line_id, line in enumerate(lines):
        for run in line:
            signature = source_style(run['style'])
            for character in run['text']:
                if not character.isspace():
                    yield character, signature, line_id


def _site_chars(rows, styles):
    for line_id, row in enumerate(rows):
        for segment in row or []:
            if not isinstance(segment, list) or len(segment) not in (2, 3) or not isinstance(segment[0], str):
                raise ValueError('Invalid site segment')
            style_id = segment[1]
            if not _integer(style_id) or not 0 <= style_id < len(styles):
                raise ValueError(f'Invalid site style ID: {style_id!r}')
            signature = styles[style_id]
            for character in segment[0]:
                if not character.isspace():
                    yield character, signature, line_id


def verify(source, site, source_map, *, partial=False):
    source, site, source_map = map(Path, (source, site, source_map))
    counts = Counter()
    errors, warnings = [], []
    error_counts = Counter()

    def issue(code, context, detail):
        error_counts[code] += 1
        if len(errors) < 150:
            errors.append(dict(code=code, context=context, detail=detail))

    try:
        document = parse_rtf(source)
        lines = document['lines']
        meta = _read(site / 'data/meta.js', 'SBW.gotMeta(')
        styles = [css_style(style) for style in meta['sty']]
        records = json.loads(source_map.read_text(encoding='utf-8'))
        if not isinstance(records, list):
            raise ValueError('Source map must be a list')
        books = [_read(site / f'data/b/{i}.js', f'SBW.gotBook({i},') for i in range(len(meta['books']))]
        supplement = _read(site / 'data/rtf-extra.js', 'SBW.gotRtfExtra(')
        if not isinstance(supplement.get('rows'), list):
            raise ValueError('RTF supplement requires rows')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        issue('input', 'source/site/map', str(exc))
        return dict(passed=False, partial=partial, errors=errors, error_counts=dict(error_counts),
                    error_count=sum(error_counts.values()), warnings=warnings, counts=dict(counts))
    counts.update(source_lines=len(lines), source_books=len(meta['books']), site_blocks=len(meta['blk']))
    for warning in document.get('warnings', []):
        issue('source_parser_warning', 'RTF', warning)
    coverage_delta = [0] * (len(lines) + 1)

    def cover(start, end):
        coverage_delta[start] += 1
        coverage_delta[end] -= 1

    def compare(context, source_lines, rows, *, body=False):
        if not isinstance(rows, list):
            issue('field_schema', context, 'Formatted rows must be a list')
            return
        try:
            expected_lines, actual_lines = _source_texts(source_lines), _site_texts(rows)
            if body:
                expected_lines, actual_lines = _trim_empty(expected_lines), _trim_empty(actual_lines)
            if expected_lines != actual_lines:
                first = next((i for i, (a, b) in enumerate(zip_longest(expected_lines, actual_lines)) if a != b), 0)
                issue('line_text', context, dict(first_different_line=first,
                      expected_lines=len(expected_lines), actual_lines=len(actual_lines),
                      expected=expected_lines[first][:200] if first < len(expected_lines) else None,
                      actual=actual_lines[first][:200] if first < len(actual_lines) else None))
            text_mismatches, format_mismatches, character_count = 0, 0, 0
            first_text, first_format = None, None
            for source_char, site_char in zip_longest(_source_chars(source_lines), _site_chars(rows, styles)):
                character_count += 1
                if source_char is None or site_char is None or source_char[0] != site_char[0]:
                    text_mismatches += 1
                    if first_text is None:
                        first_text = dict(character=character_count - 1,
                            expected=source_char[0] if source_char else None,
                            actual=site_char[0] if site_char else None)
                elif source_char[1] != site_char[1]:
                    format_mismatches += 1
                    if first_format is None:
                        first_format = dict(character=character_count - 1, text=source_char[0],
                                            expected=source_char[1], actual=site_char[1])
            counts['compared_nonwhitespace_characters'] += character_count
            counts['compared_fields'] += 1
            if text_mismatches:
                counts['text_mismatched_characters'] += text_mismatches
                issue('character_text', context, dict(count=text_mismatches, first=first_text))
            if format_mismatches:
                counts['format_mismatched_characters'] += format_mismatches
                issue('character_format', context, dict(count=format_mismatches, first=first_format))
        except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
            issue('field_schema', context, str(exc))

    preamble_end = len(supplement['rows'])
    if preamble_end > len(lines):
        issue('preamble_span', 'rtf-extra', 'Supplement has more rows than source')
    else:
        cover(0, preamble_end)
        compare('rtf-extra', lines[:preamble_end], supplement['rows'])
    seen = set()
    minimum_span_start = len(lines)
    for record_index, record in enumerate(records):
        context = f'source-map[{record_index}]'
        if not isinstance(record, dict) or not _integer(record.get('block')):
            issue('map_record', context, 'Source map requires an integer block ID')
            continue
        block_id = record['block']
        context = f'block[{block_id}]'
        if block_id in seen:
            issue('duplicate_map_block', context, 'Block occurs more than once in source map')
        seen.add(block_id)
        if not 0 <= block_id < len(meta['blk']):
            issue('map_block', context, 'Unknown block ID')
            continue
        try:
            block = books[meta['blk'][block_id][0]]['bl'][str(block_id)]
        except (IndexError, KeyError, TypeError) as exc:
            issue('map_block', context, str(exc))
            continue
        counts['mapped_blocks'] += 1
        if record.get('legacy_empty') is True:
            counts['legacy_empty_blocks'] += 1
            if any(block.get(field) for field in ('x', 'r', 'pre')):
                issue('legacy_empty', context, 'Legacy-empty block contains source text')
            if any(record.get(field) is not None for field in _FIELDS):
                issue('legacy_empty', context, 'Legacy-empty block must not claim source spans')
            continue
        for source_field, site_field in _FIELDS.items():
            span = record.get(source_field)
            rows = block.get(site_field, [])
            if span is None:
                if rows:
                    issue('unmapped_field', context + '.' + site_field, 'Field has rows but no source span')
                if source_field == 'body':
                    issue('missing_body_span', context, 'Converted block requires a body span')
                continue
            if (not isinstance(span, list) or len(span) != 2 or not all(map(_integer, span))
                    or not 0 <= span[0] <= span[1] <= len(lines)):
                issue('map_span', context + '.' + source_field, f'Invalid source span {span!r}')
                continue
            start, end = span
            minimum_span_start = min(minimum_span_start, start)
            cover(start, end)
            compare(context + '.' + site_field, lines[start:end], rows, body=site_field == 'x')
    if not partial:
        for block_id in set(range(len(meta['blk']))) - seen:
            issue('missing_map_block', f'block[{block_id}]', 'Block not included in full-conversion source map')
        if preamble_end != minimum_span_start:
            issue('preamble_boundary', 'rtf-extra', dict(actual_end=preamble_end, first_map_span=minimum_span_start))
    coverage, uncovered, duplicated = 0, [], []
    for line_id, difference in enumerate(coverage_delta[:-1]):
        coverage += difference
        if coverage == 0:
            counts['uncovered_source_lines'] += 1
            if len(uncovered) < 30:
                uncovered.append(line_id)
        elif coverage == 1:
            counts['covered_source_lines'] += 1
        else:
            counts['multiply_covered_source_lines'] += 1
            if len(duplicated) < 30:
                duplicated.append(line_id)
    if duplicated:
        issue('source_overlap', 'source-map', dict(count=counts['multiply_covered_source_lines'], examples=duplicated))
    if uncovered and not partial:
        issue('source_gap', 'source-map', dict(count=counts['uncovered_source_lines'], examples=uncovered))
    if uncovered and partial:
        warnings.append(dict(code='partial_source_coverage', count=counts['uncovered_source_lines']))
    for key in ('uncovered_source_lines', 'multiply_covered_source_lines', 'text_mismatched_characters', 'format_mismatched_characters'):
        counts.setdefault(key, 0)
    return dict(schema_version=1, passed=not error_counts, partial=partial,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                errors=errors, error_counts=dict(error_counts), error_count=sum(error_counts.values()),
                warnings=warnings, counts=dict(counts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--source-map', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--partial', action='store_true')
    args = parser.parse_args()
    report = verify(args.source, args.site, args.source_map, partial=args.partial)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('passed', 'partial', 'error_count', 'counts')}, ensure_ascii=False))
    return 0 if report['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

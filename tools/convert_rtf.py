#!/usr/bin/env python3
"""Convert an RTF into a reviewable static wiki, retaining existing identities.

Python standard library only. The baseline is read-only; output must be separate.
Every source line is assigned to a block or retained in the source supplement.
No deployment, push or merge is performed by this program.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
import unicodedata

from rtf_parser import parse_rtf
from wiki_links import transfer_links


def read_js(path, prefix):
    text = Path(path).read_text(encoding='utf-8').strip()
    if not text.startswith(prefix) or not text.endswith(');'):
        raise ValueError(f'Onbekend gegevensformaat: {path}')
    return json.loads(text[len(prefix):-2])


def write_js(path, prefix, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(prefix + json.dumps(value, ensure_ascii=False, separators=(',', ':')) + ');\n', encoding='utf-8')


def line_text(line):
    return ''.join(run['text'] for run in line)


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()


def body_key(text):
    return normalize(re.sub(r'^\s*\|\s*', '', text))


def flat(rows):
    return '\n'.join(''.join(s[0] for s in row) if row else '' for row in rows)


def style_css(style):
    parts = []
    if style.get('font_family'):
        family = style['font_family'].replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
        generic = style.get('font_generic', 'serif')
        if generic not in ('serif', 'sans-serif', 'monospace', 'cursive', 'fantasy'):
            generic = 'serif'
        parts.append('font-family:"' + family + '",' + generic)
    if style.get('font_size_points'):
        parts.append('font-size:' + format(style['font_size_points'], 'g') + 'pt')
    if style.get('color'):
        parts.append('color:' + style['color'])
    if style.get('background'):
        parts.append('background:' + style['background'])
    if style.get('bold'):
        parts.append('font-weight:700')
    if style.get('italic'):
        parts.append('font-style:italic')
    decorations = []
    if style.get('underline'):
        decorations.append('underline')
    if style.get('strike'):
        decorations.append('line-through')
    if decorations:
        parts.append('text-decoration:' + ' '.join(decorations))
    if style.get('underline') and style.get('underline_color'):
        parts.append('text-decoration-color:' + style['underline_color'])
    if style.get('superscript'):
        parts.append('vertical-align:' + ('super' if style['superscript'] > 0 else 'sub'))
    return ';'.join(parts)


def reference_sections(texts, books):
    names = '|'.join(re.escape(b) for b in sorted(books, key=len, reverse=True))
    ref = re.compile('(' + names + r')\s+(\d+):(\d+)')
    header = re.compile(r'^\s*(?:\|\s*)?' + ref.pattern)
    groups, active = [], None
    for i, text in enumerate(texts):
        if header.match(text):
            # A citation inside braces is not an additional verse header.
            clean = re.sub(r'\{[^}]*\}|\[[^]]*\]', '', text)
            refs = [m.group(1, 2, 3) for part in clean.split('|') if (m := header.match(part))]
            if active is None:
                active = dict(start=i, end=i + 1, refs=refs)
                groups.append(active)
            else:
                active['end'] = i + 1
                active['refs'].extend(refs)
        elif text.strip():
            active = None
    return groups, ref


def align_blocks(meta, old_blocks, groups, ref, texts):
    """Align occurrences, including reordered references and legacy empty records."""
    old_keys = [ref.match(b[2]).group(1, 2, 3) for b in meta['blk']]
    # Earlier extraction sometimes made an empty record from a subtitle, then
    # the real verse with precisely the same label. It must not steal its body.
    synthetic = set()
    for i in range(len(old_keys) - 1):
        if old_keys[i] == old_keys[i + 1] and not old_blocks[i]['x'] and old_blocks[i + 1]['x']:
            synthetic.add(i)
    old_ids = [i for i in range(len(old_keys)) if i not in synthetic]
    # IDs appended by an earlier update are stable identifiers, not source
    # sequence numbers. Use the previous conversion's source order on reruns.
    if old_ids and all(old_blocks[i].get('rtf', {}).get('header_lines') for i in old_ids):
        old_ids.sort(key=lambda i: (old_blocks[i]['rtf']['header_lines'][0], old_blocks[i]['rtf'].get('lines', [0])[0], i))
    refs = [(key, gi) for gi, g in enumerate(groups) for key in g['refs']]
    matcher = difflib.SequenceMatcher(None, [old_keys[i] for i in old_ids], [r[0] for r in refs], autojunk=False)
    matches = {}
    for op, a, z, b, y in matcher.get_opcodes():
        if op == 'equal':
            matches.update((old_ids[oi], refs[ni][1]) for oi, ni in zip(range(a, z), range(b, y)))
    recovered, issues = [], []
    by_key = defaultdict(set)
    for key, gi in refs:
        by_key[key].add(gi)
    used = set(matches.values())
    for i in old_ids:
        if i in matches:
            continue
        choices = by_key.get(old_keys[i], set()) - used
        if len(choices) == 1:
            gi = next(iter(choices))
            matches[i] = gi
            used.add(gi)
            recovered.append(dict(block=i, reason='unique_reference_reordered', source_line=groups[gi]['start'] + 1))
            continue
        # A profile can cite a parallel book in a later RTF. Restrict fallback
        # to adjacent source groups and require an exact substantial body anchor.
        position = old_ids.index(i)
        prev = next((k for k in reversed(old_ids[:position]) if k in matches), None)
        nxt = next((k for k in old_ids[position + 1:] if k in matches), None)
        lo = max(0, matches[prev] if prev is not None else 0)
        hi = min(len(groups), matches[nxt] + 1 if nxt is not None else len(groups))
        anchors = [body_key(''.join(s[0] for s in row)) for row in old_blocks[i]['x'] if row]
        anchors = [a for a in anchors[:12] if len(a) >= 20]
        candidates = []
        for gi in range(lo, hi):
            if gi in used:
                continue
            end = groups[gi + 1]['start'] if gi + 1 < len(groups) else len(texts)
            body = [body_key(s) for s in texts[groups[gi]['end']:end]]
            count = sum(a in body for a in anchors)
            if anchors and count >= min(3, len(anchors)) and count / len(anchors) >= .75:
                candidates.append(gi)
        if len(candidates) == 1:
            gi = candidates[0]
            matches[i] = gi
            used.add(gi)
            recovered.append(dict(block=i, reason='parallel_reference_exact_body', source_line=groups[gi]['start'] + 1,
                                  old_label=meta['blk'][i][2], source_refs=groups[gi]['refs']))
        else:
            issues.append(dict(kind='unaligned_block', block=i, label=meta['blk'][i][2], candidates=candidates))
    # A chapter overview and its real first verse can share the same ref.
    # Prefer the occurrence with the existing body's exact prefix; the overview
    # then stays in the preceding block, where older wiki occurrences point.
    compact = lambda s: re.sub(r'[\s|]+', '', unicodedata.normalize('NFC', s))
    ordered_ids = sorted(matches, key=lambda i: (matches[i], i))
    for position, i in enumerate(ordered_ids):
        body = compact(flat(old_blocks[i]['x']))
        if len(body) < 25:
            continue
        needle = body[:100]
        first_row = next((compact(''.join(s[0] for s in row)) for row in old_blocks[i]['x'] if row), '')
        current = matches[i]
        lo = matches[ordered_ids[position - 1]] if position else 0
        hi = matches[ordered_ids[position + 1]] if position + 1 < len(ordered_ids) else len(groups) - 1
        scored = []
        for gi in by_key.get(old_keys[i], set()):
            if not lo <= gi <= hi:
                continue
            if gi != current and gi in matches.values():
                continue
            end = groups[gi + 1]['start'] if gi + 1 < len(groups) else len(texts)
            candidate_body = compact('\n'.join(texts[groups[gi]['end']:end]))
            if needle in candidate_body:
                scored.append((2, gi))
            elif len(first_row) >= 25 and first_row in candidate_body:
                # A newly recovered verse can have a/b/c source subdivisions.
                # Its first exact line identifies the first subdivision even
                # when the full old prefix extends into the next header.
                scored.append((1, gi))
        best = max((score for score, _ in scored), default=0)
        choices = [gi for score, gi in scored if score == best]
        if len(choices) == 1 and choices[0] != current:
            matches[i] = choices[0]
            recovered.append(dict(block=i, reason='duplicate_reference_exact_body',
                                  original_source_line=groups[current]['start'] + 1,
                                  source_line=groups[choices[0]]['start'] + 1))
    for i in synthetic:
        recovered.append(dict(block=i, reason='legacy_empty_subtitle_record', follows=i + 1))
    return matches, synthetic, recovered, issues


def new_source_blocks(meta, old_blocks, groups, matches, texts, ref, selected_chapter=None):
    """Find genuinely additional source passages without splitting old text out.

    A header inside an existing quotation can be absent from metadata while its
    whole body is already in an old block. Such text remains in its old owner.
    Only source bodies absent from that owner's text get appended identifiers.
    Every decision is recorded for review; no entity classification is inferred.
    """
    by_group = defaultdict(list)
    for i, gi in matches.items():
        by_group[gi].append(i)
    book_ids = {b[0]: i for i, b in enumerate(meta['books'])}
    inventory, additions = [], []
    owner = None
    last_addition_key = None
    compact_cache = {}
    hidden_headers = {}
    baseline_keys = {ref.match(b[2]).group(1, 2, 3) for b in meta['blk']}
    source_key_counts = Counter(g['refs'][0] for g in groups)
    header_match = re.compile(r'^\s*(?:\|\s*)?' + ref.pattern)

    def compact(text):
        return re.sub(r'[\s|]+', '', unicodedata.normalize('NFC', text))

    for gi, group in enumerate(groups):
        if gi in by_group:
            owner = max(by_group[gi])
            last_addition_key = None
            continue
        if owner is None:
            continue
        end = groups[gi + 1]['start'] if gi + 1 < len(groups) else len(texts)
        body_lines = [s for s in texts[group['end']:end] if s.strip()]
        # Notes and section titles remain source metadata for the existing ID.
        verse_lines = []
        for s in body_lines:
            if re.match(r'^\s*(?:\(#\)|\{\*\}|\[(?:#|!|\?)\]|#)', s):
                break
            verse_lines.append(s)
        body = compact('\n'.join(verse_lines))
        if owner not in compact_cache:
            compact_cache[owner] = compact(flat(old_blocks[owner]['x']))
            hidden_headers[owner] = {m.group(1, 2, 3) for row in old_blocks[owner]['x'] if row
                                     if (m := header_match.match(''.join(s[0] for s in row)))}
        previous = compact_cache[owner]
        old_label = meta['blk'][owner][2]
        old_ref = ref.match(old_label)
        verse_range = re.search(r':(\d+)(?:-(\d+))?$', old_label)
        covered = bool(verse_range) and all(
            r[:2] == old_ref.group(1, 2) and int(verse_range[1]) <= int(r[2]) <= int(verse_range[2] or verse_range[1])
            for r in group['refs'])
        reason = 'existing_combined_reference' if covered else None
        if reason is None and group['refs'][0] in hidden_headers[owner]:
            reason = 'existing_embedded_verse_header'
        header_text = ' '.join(texts[group['start']:group['end']])
        editorial = bool(body_lines) and (
            body_lines[0].lstrip().startswith(('[[[[', '[#]')) or
            any(re.search(r'\[K#\d+/\d+\]|\[\{Koning-', s) for s in body_lines[:3]))
        overview = bool(re.search(r':\d+.*[-/+]', header_text))
        if reason is None and editorial and overview and (group['refs'][0] in baseline_keys or source_key_counts[group['refs'][0]] > 1):
            reason = 'source_editorial_overview'
        if (reason is None and overview and group['refs'][0] in baseline_keys
                and gi + 1 < len(groups) and gi + 1 in by_group
                and groups[gi + 1]['refs'][0] == group['refs'][0]):
            reason = 'source_editorial_overview'
        longest = 0
        fraction = 0
        if reason is None and (not body or not verse_lines):
            reason = 'source_note_or_empty_header'
        if reason is None and body in previous:
            reason = 'existing_body_exact'
        if reason is None and group['refs'][0] == last_addition_key:
            # a/b/c subdivisions of one newly recovered verse remain one block.
            reason = 'additional_verse_subdivision'
        entry = dict(group=gi, source_lines=[group['start'] + 1, end], refs=group['refs'],
                     previous_owner=owner, source_characters=len(body), longest_exact_anchor=longest,
                     matched_fraction=round(fraction, 4), classification=reason or 'additional_source_passage')
        inventory.append(entry)
        if reason is not None:
            continue
        bn, chapter, verse = group['refs'][0]
        if selected_chapter and (bn, int(chapter)) != selected_chapter:
            continue
        bi, chapter = book_ids[bn], int(chapter)
        label = f'{bn} {chapter}:{verse}'
        same = [int(r[2]) for r in group['refs'] if r[:2] == (bn, str(chapter))]
        if same and same == list(range(int(verse), max(same) + 1)) and max(same) > int(verse):
            label += '-' + str(max(same))
        i = len(meta['blk'])
        meta['blk'].append([bi, chapter, label])
        old_blocks[i] = dict(l=label, h=None, s=None, m='', x=[])
        matches[i] = gi
        entry['new_block'] = i
        additions.append(entry)
        last_addition_key = group['refs'][0]
    return additions, inventory


def split_body(ids, rows, old_blocks):
    """Split a combined RTF verse using exact existing line anchors, never ratios."""
    keys = [body_key(''.join(s[0] for s in row)) if row else '' for row in rows]
    boundaries = [0]
    cursor = 0
    for i in ids[1:]:
        old = old_blocks[i]['x']
        anchors = [body_key(''.join(s[0] for s in row)) for row in old if row]
        if not anchors:
            boundaries.append(cursor)
            continue
        # Match an ordered prefix; line wrapping may differ, so use a compact
        # concatenated anchor as a second path, but retain whole source lines.
        anchor = anchors[0]
        choices = [k for k in range(cursor, len(keys)) if keys[k] == anchor]
        if len(choices) != 1:
            # Same characters with new RTF line wrapping: map an exact compact
            # text prefix back to the beginning of its original source row.
            compact, starts = '', []
            for k in range(cursor, len(keys)):
                starts.append((len(compact), k))
                compact += re.sub(r'\s+', '', keys[k])
            needle = re.sub(r'\s+', '', anchor)
            positions = [m.start() for m in re.finditer(re.escape(needle), compact)]
            choices = [k for offset, k in starts if offset in positions]
        if len(choices) != 1:
            raise ValueError(f'Geen unieke splitsing voor blok {i}: {anchor[:90]} ({len(choices)} kandidaten)')
        cursor = choices[0]
        boundaries.append(cursor)
    boundaries.append(len(rows))
    return {i: rows[a:z] for i, a, z in zip(ids, boundaries, boundaries[1:])}, boundaries


def preserve_owned_headers(groups, by_group, ordered, old_blocks, texts):
    """Keep a chapter-title tail in its established preceding block ID.

    A source edit can wrap several old title rows into one. An exact remaining
    tail row still anchors the boundary; never consume the final verse header.
    """
    decisions = []
    for pos, gi in enumerate(ordered[1:], 1):
        owner = by_group[ordered[pos - 1]][-1]
        previous = old_blocks[owner]['x']
        keys = [body_key(''.join(s[0] for s in row)) for row in previous if row][-12:]
        matching = [k for k in range(groups[gi]['start'], groups[gi]['end'] - 1)
                    if body_key(texts[k]) and body_key(texts[k]) in keys]
        if matching:
            start = groups[gi]['start']
            groups[gi]['start'] = max(matching) + 1
            decisions.append(dict(block=owner, reason='leading_header_body_owner',
                                  source_lines=[start + 1, groups[gi]['start']]))
    return decisions


def convert(source, baseline, output, report_dir, chapter=None):
    source, baseline, output, report_dir = map(lambda p: Path(p).resolve(), (source, baseline, output, report_dir))
    if output == baseline or output in baseline.parents:
        raise ValueError('Uitvoer moet een aparte map zijn')
    if baseline in output.parents and output.relative_to(baseline).parts[0] != 'work':
        raise ValueError('Uitvoer binnen de baseline mag uitsluitend in work/ staan')
    if report_dir == baseline or (baseline in report_dir.parents and report_dir.relative_to(baseline).parts[0] != 'work'):
        raise ValueError('Rapporten binnen de baseline mogen uitsluitend in work/ staan')
    if report_dir == output or report_dir in output.parents or output in report_dir.parents:
        raise ValueError('Rapportmap en uitvoermap moeten apart staan')
    if source == report_dir or report_dir in source.parents:
        raise ValueError('De bron mag niet binnen de rapportmap staan')
    if report_dir.exists() and any(report_dir.iterdir()):
        raise ValueError('Kies een nieuwe, lege rapportmap; oude controles mogen niet worden hergebruikt')
    if output.exists():
        raise ValueError(f'Uitvoermap bestaat al; kies een nieuwe map: {output}')
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = {str(p.relative_to(baseline)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((baseline / 'data').rglob('*')) if p.is_file()}
    (report_dir / 'baseline-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    with tarfile.open(report_dir / 'baseline-data.tar.gz', 'w:gz') as archive:
        archive.add(baseline / 'data', arcname='data')
    meta = read_js(baseline / 'data/meta.js', 'SBW.gotMeta(')
    original_meta = copy.deepcopy(meta)
    books = [read_js(baseline / f'data/b/{bi}.js', f'SBW.gotBook({bi},') for bi in range(len(meta['books']))]
    old_blocks = {i: books[b[0]]['bl'][str(i)] for i, b in enumerate(meta['blk'])}
    original_blocks = copy.deepcopy(old_blocks)
    document = parse_rtf(source)
    lines = document['lines']
    texts = [line_text(line) for line in lines]
    groups, ref = reference_sections(texts, [b[0] for b in meta['books']])
    matches, synthetic, recovered, issues = align_blocks(meta, old_blocks, groups, ref, texts)
    chapter_filter = None
    if chapter:
        chapter_match = re.fullmatch(r'(.+) (\d+)', chapter)
        if not chapter_match:
            raise ValueError('--chapter verwacht bijvoorbeeld "Genesis 2"')
        if chapter_match[1] not in [b[0] for b in meta['books']]:
            raise ValueError('Onbekend Bijbelboek: ' + chapter_match[1])
        chapter_filter = (chapter_match[1], int(chapter_match[2]))
    old_count = len(meta['blk'])
    additions, header_inventory = new_source_blocks(meta, old_blocks, groups, matches, texts, ref, chapter_filter)
    for entry in additions:
        i = entry['new_block']
        bi, ch, _ = meta['blk'][i]
        books[bi]['bl'][str(i)] = old_blocks[i]
        original_blocks[i] = copy.deepcopy(old_blocks[i])
        ids = books[bi]['ch'].setdefault(str(ch), [])
        # Insert by source position while retaining every old ID's relative order.
        before = next((j for j, existing in enumerate(ids) if matches.get(existing, -1) > entry['group']), len(ids))
        ids.insert(before, i)
        if ch not in meta['books'][bi][1]:
            chapters = meta['books'][bi][1]
            before_chapter = next((j for j, existing in enumerate(chapters) if existing > ch), len(chapters))
            chapters.insert(before_chapter, ch)
    for bi, book in enumerate(books):
        book['ch'] = {str(ch): book['ch'][str(ch)] for ch in meta['books'][bi][1]}
    meta['stats']['blokken'] = len(meta['blk'])
    # Derived counts follow the existing identity database, including the Eden
    # correction already present in the baseline. No classification is changed.
    type_names = dict(P='persoon', V='volk', S='stad', L='land', W='water', R='regio', O='plaats', U='onbepaald')
    cert_names = dict(z='zeker', w='waarschijnlijk', o='onzeker')
    type_counts, cert_counts = Counter(), Counter()
    per_type = defaultdict(Counter)
    for entity in meta['ents']:
        kind, certainty = type_names[entity[1]], cert_names[entity[2]]
        type_counts[kind] += 1
        cert_counts[certainty] += 1
        per_type[kind][certainty] += 1
    meta['stats'].update(entiteiten=len(meta['ents']), soorten=dict(type_counts), zekerheid=dict(cert_counts),
                         perSoortZekerheid={kind: dict(counts) for kind, counts in per_type.items()})
    style_ids = {css: i for i, css in enumerate(meta['sty'])}

    def rows_for(start, end):
        result = []
        for line in lines[start:end]:
            row = []
            for run in line:
                style = dict(run['style'])
                style['font_generic'] = document.get('fonts', {}).get(style.get('font'), {}).get('generic', 'serif')
                css = style_css(style)
                if css not in style_ids:
                    style_ids[css] = len(meta['sty'])
                    meta['sty'].append(css)
                row.append([run['text'], style_ids[css]])
            result.append(row if row else 0)
        return result

    by_group = defaultdict(list)
    for i, gi in sorted(matches.items()):
        by_group[gi].append(i)
    ordered = sorted(by_group)
    # Consecutive headers may start with a standalone chapter title that was
    # already a linked body row of the preceding block. Keep it there rather
    # than taking it into the next block's reference header.
    recovered.extend(preserve_owned_headers(groups, by_group, ordered, original_blocks, texts))
    # A heading and its accompanying notes belong before the following verse.
    prefix_start = {}
    for pos, gi in enumerate(ordered):
        lower = groups[ordered[pos - 1]]['end'] if pos else 0
        start = groups[gi]['start']
        if pos:
            # A new heading can occur *inside* an existing block, for example
            # before a king's profile. Keep that block's exact body anchors in
            # their original owner, so its occurrence IDs do not migrate.
            previous_ids = by_group[ordered[pos - 1]]
            previous = original_blocks[previous_ids[-1]]['x']
            tail = [body_key(re.sub(r'^\s*(?:\(#\)|\{\*\})\s*', '', ''.join(s[0] for s in row))) for row in previous if row][-12:]
            source_keys = [body_key(re.sub(r'^\s*(?:\(#\)|\{\*\})\s*', '', s)) for s in texts[lower:start]]
            for anchor in reversed(tail):
                positions = [k for k, key in enumerate(source_keys) if key == anchor]
                if anchor and len(positions) == 1:
                    lower += positions[0] + 1
                    break
        markers = [k for k in range(lower, start) if re.match(r'^\s*(?:\(#\)|\{\*\})', texts[k])]
        prefix_start[gi] = markers[-1] if markers else start
        if len(markers) >= 2 and texts[markers[-1]].lstrip().startswith('{*}'):
            prefix_start[gi] = markers[-2]
    selected = set(range(len(meta['blk'])))
    if chapter_filter:
        bi = [b[0] for b in meta['books']].index(chapter_filter[0])
        selected = {i for i, b in enumerate(meta['blk']) if b[0] == bi and b[1] == chapter_filter[1]}
        issues = [item for item in issues if item.get('block') in selected]
    changes, source_map, link_reports = [], [], []
    converted = set()
    for pos, gi in enumerate(ordered):
        ids = by_group[gi]
        if not selected.intersection(ids):
            continue
        group = groups[gi]
        end = prefix_start[ordered[pos + 1]] if pos + 1 < len(ordered) else len(lines)
        body_rows = rows_for(group['end'], end)
        try:
            parts, boundaries = split_body(ids, body_rows, old_blocks)
        except ValueError as error:
            issues.append(dict(kind='ambiguous_body_split', blocks=ids, source_lines=[group['start'] + 1, end], detail=str(error)))
            continue
        # Give each legacy ID its own header when several consecutive source
        # references are combined. The full original header is retained once.
        for ix, i in enumerate(ids):
            if i not in selected:
                continue
            old = original_blocks[i]
            new_rows = parts[i]
            while new_rows and not new_rows[0]:
                new_rows = new_rows[1:]
            while new_rows and not new_rows[-1]:
                new_rows = new_rows[:-1]
            pre_rows = rows_for(prefix_start[gi], group['start']) if ix == 0 else []
            header_rows = rows_for(group['start'], group['end']) if ix == 0 else []
            # Names can move from body lines into a wrapped reference header.
            # Match the complete visible source span of this same stable ID,
            # then restore field boundaries without changing source characters.
            linked_all, link_report = transfer_links(old.get('pre', []) + old.get('r', []) + old['x'],
                                                     pre_rows + header_rows + new_rows)
            pre_end, header_end = len(pre_rows), len(pre_rows) + len(header_rows)
            linked_pre = linked_all[:pre_end]
            linked_header = linked_all[pre_end:header_end]
            linked_rows = linked_all[header_end:]
            block = copy.deepcopy(old)
            block['x'] = linked_rows
            block['r'] = linked_header
            block['pre'] = linked_pre
            # Legacy labels remain stable; source headers carry current markings.
            block['h'] = None
            block['s'] = None
            block['m'] = ''
            block['rtf'] = dict(lines=[group['end'] + boundaries[ix] + 1, group['end'] + boundaries[ix + 1]],
                                header_lines=[group['start'] + 1, group['end']])
            books[meta['blk'][i][0]]['bl'][str(i)] = block
            converted.add(i)
            if len(converted) % 2000 == 0:
                print(f'Verwerkt: {len(converted)}/{len(selected)} blokken', flush=True)
            source_map.append(dict(block=i, prefix=[prefix_start[gi], group['start']] if ix == 0 else None,
                                   header=[group['start'], group['end']] if ix == 0 else None,
                                   body=[group['end'] + boundaries[ix], group['end'] + boundaries[ix + 1]]))
            if link_report.get('issues'):
                issues.extend(dict(kind='wiki_link_review', block=i, detail=item) for item in link_report['issues'])
            link_reports.append(dict(block=i, **link_report))
            old_text, new_text = flat(old['x']), flat(linked_rows)
            old_format = [(s[0], original_meta['sty'][s[1]]) for row in old['x'] if row for s in row]
            new_format = [(s[0], meta['sty'][s[1]]) for row in linked_rows if row for s in row]
            old_headers = {k: old.get(k) for k in ('h', 's', 'm', 'r', 'pre')}
            header_changed = old.get('r', []) != linked_header or old.get('pre', []) != linked_pre
            def styled(rows, styles):
                return [[[s[0], styles[s[1]]] + s[2:] for s in row] if row else 0 for row in rows]
            if old_text != new_text or old_format != new_format or header_changed:
                changes.append(dict(block=i, label=meta['blk'][i][2], text_changed=old_text != new_text,
                                    normalized_text_changed=normalize(old_text) != normalize(new_text),
                                    formatting_changed=old_format != new_format,
                                    source_header_changed=header_changed,
                                    before=old_text, after=new_text, body_scope=True,
                                    source_header_before=old_headers,
                                    source_header_after=dict(pre=styled(linked_pre, meta['sty']), r=styled(linked_header, meta['sty'])),
                                    styles_before=sorted({s[1] for s in old_format}),
                                    styles_after=sorted({s[1] for s in new_format}),
                                    colors_before=sorted(set(re.findall(r'(?:color|background):(#\w{6})', ';'.join(s[1] for s in old_format)))),
                                    colors_after=sorted(set(re.findall(r'(?:color|background):(#\w{6})', ';'.join(s[1] for s in new_format))))))
    for i in sorted(synthetic & selected):
        block = books[meta['blk'][i][0]]['bl'][str(i)]
        block.update(h=None, s=None, m='', pre=[], r=[])
        converted.add(i)
        source_map.append(dict(block=i, legacy_empty=True))
    output.mkdir(parents=True)
    for name in ('index.html', 'js', 'css', 'vendor', 'media', 'data', 'tests'):
        src = baseline / name
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, output / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(src, output / name)
    for bi, book in enumerate(books):
        write_js(output / f'data/b/{bi}.js', f'SBW.gotBook({bi},', book)
    meta['conversion'] = dict(source=source.name, sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                              source_lines=len(lines), converted_blocks=len(converted), review_items=len(issues))
    write_js(output / 'data/meta.js', 'SBW.gotMeta(', meta)
    # Preamble is retained with its original styles and can be read in the site.
    preamble_end = prefix_start[ordered[0]] if ordered else len(lines)
    supplement = dict(title='Voorwerk uit de RTF', rows=rows_for(0, preamble_end))
    write_js(output / 'data/rtf-extra.js', 'SBW.gotRtfExtra(', supplement)
    # rows_for can add preamble-only styles, so write metadata after all rows.
    write_js(output / 'data/meta.js', 'SBW.gotMeta(', meta)
    report = dict(schema_version=1, source=source.name, source_sha256=meta['conversion']['sha256'],
                  source_bytes=source.stat().st_size, source_lines=len(lines), source_header_groups=len(groups),
                  books=len(books), requested_blocks=len(selected), converted_blocks=len(converted),
                  baseline_blocks=old_count, added_source_blocks=len(additions),
                  additional_source_passages=additions,
                  untouched_blocks=sorted(selected - converted), styles_before=len(original_meta['sty']), styles_after=len(meta['sty']),
                  text_changed_blocks=sum(x['text_changed'] for x in changes),
                  normalized_text_changed_blocks=sum(x['normalized_text_changed'] for x in changes),
                  formatting_changed_blocks=sum(x['formatting_changed'] for x in changes),
                  source_header_changed_blocks=sum(x['source_header_changed'] for x in changes),
                  body_change_count_scope='text/format counts concern x; source headers recorded separately per block in changes.json',
                  old_link_segments=sum(x['old_link_segments'] for x in link_reports),
                  retained_old_link_segments=sum(x['retained_link_segments'] for x in link_reports),
                  unresolved_old_link_segments=sum(x['unresolved_link_segments'] for x in link_reports),
                  parser_warnings=document['warnings'], recovered_alignments=recovered, issues=issues,
                  safe_to_publish=False,
                  publication_note='Testversie; afzonderlijke toestemming van de gebruiker vereist voor publicatie.')
    report['per_book'] = [dict(book=name, baseline_blocks=sum(b[0] == bi for b in original_meta['blk']),
                               converted_blocks=sum(meta['blk'][i][0] == bi for i in converted),
                               added_blocks=sum(meta['blk'][a['new_block']][0] == bi for a in additions),
                               body_text_changes=sum(c['text_changed'] and meta['blk'][c['block']][0] == bi for c in changes),
                               formatting_changes=sum(c['formatting_changed'] and meta['blk'][c['block']][0] == bi for c in changes))
                          for bi, (name, _) in enumerate(meta['books'])]
    (report_dir / 'conversion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for filename, value in [('changes.json', changes), ('source-map.json', source_map), ('links.json', link_reports), ('source-headers.json', header_inventory)]:
        (report_dir / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('books', 'requested_blocks', 'converted_blocks', 'untouched_blocks', 'text_changed_blocks', 'formatting_changed_blocks')}, ensure_ascii=False))
    print(f'Controlepunten: {len(issues)}; rapporten: {report_dir}; testsite: {output}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path, required=True)
    parser.add_argument('--chapter')
    args = parser.parse_args()
    report = convert(args.source, args.baseline, args.output, args.report_dir, args.chapter)
    return 2 if report['issues'] or report['untouched_blocks'] or report['parser_warnings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

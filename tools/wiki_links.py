"""Transfer occurrence-specific wiki IDs without looking up names globally.

``transfer_links(old_rows, new_rows)`` returns ``(rows, report)``. Rows use the
website's existing ``[text, style_id, optional_entity_id]`` segment format. New
styles always win; old IDs are copied only onto exactly matching text in the
same block. A changed block requires a unique surrounding text anchor, so two
people sharing a spelling cannot be merged by a name dictionary.

Gap rows may be either ``0`` (the existing files' representation) or ``None``.

Unmapped links are returned as review issues, never silently guessed. Counts
refer to original link segments: one old segment may span several new styles.
"""

from bisect import bisect_left, bisect_right
from difflib import SequenceMatcher
import re
import unicodedata


def _flatten(rows):
    parts, segments, offset = [], [], 0
    for row_index, row in enumerate(rows):
        if isinstance(row, list):
            for segment_index, segment in enumerate(row):
                text = segment[0]
                if not isinstance(text, str):
                    raise ValueError("Segment text must be a string")
                end = offset + len(text)
                segments.append((offset, end, row_index, segment_index, segment))
                parts.append(text)
                offset = end
        parts.append("\n")
        offset += 1
    return "".join(parts), segments


def _unique(text, needle):
    position = text.find(needle)
    return position >= 0 and text.find(needle, position + 1) < 0


def _name_part(character):
    return bool(character) and (character.isalnum()
        or unicodedata.category(character).startswith("M")
        or character in "-'’·ʼ`‘*")


def _neighbor_part(text, position, direction):
    if not 0 <= position < len(text):
        return False
    character = text[position]
    if character == '*':
        return True
    if character in "-'’·ʼ`‘":
        # A quote wrapping an alias is punctuation. The same character between
        # letters is part of the name and must still protect token boundaries.
        while 0 <= position < len(text) and text[position] in "-'’·ʼ`‘":
            position += direction
        return (0 <= position < len(text)
                and (text[position].isalnum()
                     or unicodedata.category(text[position]).startswith('M')))
    return (character.isalnum()
            or unicodedata.category(character).startswith('M'))


def transfer_links(old_rows, new_rows):
    """Copy reliable old link occurrences to new styled rows.

    No IDs are taken from ``new_rows``. Source rows remain untouched. Reports
    include every retained original occurrence and each unresolved occurrence;
    callers can keep the complete original block in a recovery/review archive.
    """
    old_text, old_segments = _flatten(old_rows)
    new_text, new_segments = _flatten(new_rows)
    links = [segment for segment in old_segments if len(segment[4]) > 2]
    # A single name can be split by source formatting. Assess its complete
    # occurrence before copying any piece, otherwise a changed suffix could
    # leave a misleading clickable prefix behind.
    groups = []
    for segment in links:
        if (groups and groups[-1][-1][1] == segment[0]
                and groups[-1][-1][4][2] == segment[4][2]):
            groups[-1].append(segment)
        else:
            groups.append([segment])
    group_bounds = {id(segment): (group[0][0], group[-1][1])
                    for group in groups for segment in group}
    unchanged = old_text == new_text

    def alignment(left, right):
        blocks = ([(0, 0, len(left))] if left == right else
                  [tuple(block) for block in SequenceMatcher(
                      None, left, right, autojunk=False).get_matching_blocks()
                   if block.size])
        return blocks, [block[0] for block in blocks]

    blocks, block_starts = alignment(old_text, new_text)
    compact = None

    def locate(left, right, start, end, matching, starts):
        index = bisect_right(starts, start) - 1
        block = matching[index] if index >= 0 else None
        if block is None or end > block[0] + block[2]:
            return None, "linked_text_changed_or_not_aligned"
        old_start, new_start, length = block
        if left != right:
            # A complete old body occurring exactly once inside this already
            # aligned block is itself an occurrence anchor, even for a short
            # standalone genealogy name. Repeated short names still fail.
            whole_body_anchor = (old_start == 0 and length == len(left)
                                 and _unique(''.join(right.split()),
                                             ''.join(left.split())))
            anchored = False
            # Parallel passages can repeat much more than 48 characters. Grow
            # the exact common context rather than assigning by spelling or by
            # the nearest repeated name.
            for radius in (48, 96, 192, length):
                anchor_start = max(old_start, start - radius)
                anchor_end = min(old_start + length, end + radius)
                anchor = left[anchor_start:anchor_end]
                surrounding = left[anchor_start:start] + left[end:anchor_end]
                if ((len(''.join(surrounding.split())) >= 8 or whole_body_anchor)
                        and _unique(left, anchor) and _unique(right, anchor)):
                    anchored = True
                    break
            if not anchored:
                return None, "ambiguous_or_short_context"
        return (new_start + start - old_start, new_start + end - old_start), None

    def boundary_changed(start, end, target_start, target_end):
        # Existing styled entity runs can include a trailing/leading space.
        # Check the actual name edges rather than allowing that whitespace to
        # conceal an added suffix (for example linked "Saul " -> "Saulus ").
        while start < end and old_text[start].isspace():
            start += 1
        while end > start and old_text[end - 1].isspace():
            end -= 1
        while target_start < target_end and new_text[target_start].isspace():
            target_start += 1
        while target_end > target_start and new_text[target_end - 1].isspace():
            target_end -= 1
        if start == end or target_start == target_end:
            return False
        return ((_name_part(old_text[start])
                 and not _neighbor_part(old_text, start - 1, -1)
                 and _neighbor_part(new_text, target_start - 1, -1))
                or (_name_part(old_text[end - 1])
                    and not _neighbor_part(old_text, end, 1)
                    and _neighbor_part(new_text, target_end, 1)))

    def compact_alignment():
        nonlocal compact
        if compact is None:
            old_offsets = [i for i, character in enumerate(old_text) if not character.isspace()]
            new_offsets = [i for i, character in enumerate(new_text) if not character.isspace()]
            old_compact = ''.join(old_text[i] for i in old_offsets)
            new_compact = ''.join(new_text[i] for i in new_offsets)
            match_blocks, starts = alignment(old_compact, new_compact)
            compact = old_compact, new_compact, old_offsets, new_offsets, match_blocks, starts
        return compact

    def flank_context(left, right, start, end):
        """Locate an unchanged name between unique exact context anchors.

        Inserted source annotations may interrupt the contiguous equal chunk
        at either name edge. Both flanks must still select exactly this old
        occurrence and exactly one new occurrence. A document edge may replace
        one flank only when the opposite exact anchor is substantial.
        """
        needle = left[start:end]
        if not needle:
            return None

        def positions(text):
            return [match.start() for match in re.finditer(
                '(?=' + re.escape(needle) + ')', text)]

        old_positions, new_positions = positions(left), positions(right)
        if len(new_positions) > 40:
            return None

        def anchors(old_context, new_context):
            blocks = SequenceMatcher(None, old_context, new_context,
                                     autojunk=False).get_matching_blocks()
            found = [old_context[block.a:block.a + block.size]
                     for block in blocks if block.size >= 8]
            return sorted(set(found), key=len, reverse=True)[:6]

        def signature(text, position, before, after):
            left_context = text[max(0, position - 192):position]
            right_context = text[position + len(needle):position + len(needle) + 192]
            return ((before is None or before in left_context)
                    and (after is None or after in right_context))

        valid = set()
        for position in new_positions:
            before = ([None] if start == 0 else anchors(
                left[max(0, start - 128):start],
                right[max(0, position - 192):position]))
            after = ([None] if end == len(left) else anchors(
                left[end:end + 128],
                right[position + len(needle):position + len(needle) + 192]))
            for left_anchor in before:
                for right_anchor in after:
                    lengths = len(left_anchor or ''), len(right_anchor or '')
                    if (sum(lengths) < 16
                            or (None in (left_anchor, right_anchor) and max(lengths) < 20)):
                        continue
                    old_candidates = [p for p in old_positions
                                      if signature(left, p, left_anchor, right_anchor)]
                    new_candidates = [p for p in new_positions
                                      if signature(right, p, left_anchor, right_anchor)]
                    if old_candidates == [start] and new_candidates == [position]:
                        valid.add(position)
        if len(valid) == 1:
            position = next(iter(valid))
            return position, position + len(needle)
        return None

    decisions = {}
    assignments, retained, issues = [], [], []
    for occurrence in links:
        start, end, row_index, segment_index, segment = occurrence
        group_start, group_end = group_bounds[id(occurrence)]
        entity = segment[2]
        item = {"row": row_index, "segment": segment_index,
                "entity_id": entity, "text": segment[0],
                "old_start": start, "old_end": end}
        if not segment[0]:
            issues.append(dict(item, reason="empty_link_text"))
            continue
        group_key = group_start, group_end
        if group_key not in decisions:
            target, reason = locate(old_text, new_text, group_start, group_end,
                                    blocks, block_starts)
            method = "exact"
            if target is not None and boundary_changed(group_start, group_end, *target):
                target, reason = None, "linked_name_boundary_changed"
            if target is None and reason != "linked_name_boundary_changed":
                # RTF line wrapping and whitespace are presentation boundaries.
                # Compare the exact remaining characters, then project offsets
                # back to the original untouched source text and source styles.
                left, right, old_offsets, new_offsets, matching, starts = compact_alignment()
                a = bisect_left(old_offsets, group_start)
                z = bisect_left(old_offsets, group_end)
                if a < z:
                    mapped, compact_reason = locate(left, right, a, z, matching, starts)
                    if mapped is not None:
                        raw_target = new_offsets[mapped[0]], new_offsets[mapped[1] - 1] + 1
                        if boundary_changed(group_start, group_end, *raw_target):
                            reason = "linked_name_boundary_changed"
                        else:
                            target, reason, method = mapped, None, "whitespace_projection"
                    elif compact_reason == "linked_text_changed_or_not_aligned":
                        reason = compact_reason
                if target is None and reason == "ambiguous_or_short_context" and a < z:
                    mapped = flank_context(left, right, a, z)
                    if mapped is not None:
                        raw_target = new_offsets[mapped[0]], new_offsets[mapped[1] - 1] + 1
                        if not boundary_changed(group_start, group_end, *raw_target):
                            target, reason, method = mapped, None, "context_projection"
            decisions[group_key] = target, reason, method
        target, reason, method = decisions[group_key]
        if target is None:
            issues.append(dict(item, reason=reason))
            continue
        if method == "exact":
            target_start = target[0] + start - group_start
            target_end = target_start + end - start
        else:
            left, right, old_offsets, new_offsets, matching, starts = compact_alignment()
            group_compact_start = bisect_left(old_offsets, group_start)
            a = bisect_left(old_offsets, start)
            z = bisect_left(old_offsets, end)
            if a == z:
                issues.append(dict(item, reason="whitespace_only_link_segment"))
                continue
            target_start = new_offsets[target[0] + a - group_compact_start]
            target_end = new_offsets[target[0] + z - group_compact_start - 1] + 1
        assignments.append((target_start, target_end, entity))
        retained.append(dict(item, new_start=target_start, new_end=target_end,
                             match_method=method))

    # A source can replace an old parenthetical alternate-name annotation with
    # its explicit [{‘alias’}] notation. Resolve that occurrence only when the
    # unchanged row subject and an independently retained relative's identity
    # both confirm the same row. This never labels additional name mentions.
    alias_pattern = re.compile(r"\[\{[‘'’]([^\n{}]+?)[’'‘]\}\]")
    relative_words = {'zoonvan', 'dochtervan', 'broervan', 'vadervan', 'moedervan'}
    retained_by_old = {(item['old_start'], item['old_end']): item for item in retained}
    new_row_offsets = {}
    for a, z, row_index, segment_index, segment in new_segments:
        new_row_offsets.setdefault(row_index, a)
    old_row_offsets = {}
    for a, z, row_index, segment_index, segment in old_segments:
        old_row_offsets.setdefault(row_index, a)
    alias_fixed = set()

    def restore_group(group, target_start, target_end, method):
        """Overlay only original segments onto an exact projected source name."""
        start, end = group[0][0], group[-1][1]
        old_offsets = [position for position in range(start, end)
                       if not old_text[position].isspace()]
        target_offsets = [position for position in range(target_start, target_end)
                          if not new_text[position].isspace()]
        if (''.join(old_text[position] for position in old_offsets)
                != ''.join(new_text[position] for position in target_offsets)
                or boundary_changed(start, end, target_start, target_end)):
            return False
        for a, z, original_row, original_segment, segment in group:
            first, last = bisect_left(old_offsets, a), bisect_left(old_offsets, z)
            if first == last:
                return False
        for a, z, original_row, original_segment, segment in group:
            first, last = bisect_left(old_offsets, a), bisect_left(old_offsets, z)
            mapped_start, mapped_end = target_offsets[first], target_offsets[last - 1] + 1
            assignments.append((mapped_start, mapped_end, segment[2]))
            retained.append(dict(row=original_row, segment=original_segment,
                                 entity_id=segment[2], text=segment[0],
                                 old_start=a, old_end=z, new_start=mapped_start,
                                 new_end=mapped_end, match_method=method))
            alias_fixed.add((a, z))
        decisions[(start, end)] = ((target_start, target_end), None, method)
        return True

    # An existing book-name link may move from an internal verse header to a
    # combined source header. The exact book/chapter/verse occurrence is the
    # anchor; the entity category is deliberately not changed here.
    for group in groups:
        start, end = group[0][0], group[-1][1]
        if decisions.get((start, end), (None, None, None))[1] is None:
            continue
        row_index = group[0][2]
        if any(segment[2] != row_index for segment in group):
            continue
        row_start = old_row_offsets[row_index]
        row_text = ''.join(segment[0] for segment in old_rows[row_index])
        local_start, local_end = start - row_start, end - row_start
        if row_text[:local_start].strip(' \t|'):
            continue
        reference = re.match(r'\s+(\d+):(\d+)([a-z]?)(?![\da-z])', row_text[local_end:])
        if reference is None:
            continue
        key = int(reference[1]), int(reference[2]), reference[3]
        name = old_text[start:end].strip()
        pattern = re.compile(re.escape(name) + r'\s+(\d+):(\d+)([a-z]?)(?![\da-z])')
        candidates = []
        for new_row_index, row in enumerate(new_rows):
            if not isinstance(row, list) or new_row_index not in new_row_offsets:
                continue
            text = ''.join(segment[0] for segment in row)
            for match in pattern.finditer(text):
                prefix = text[:match.start()].rstrip()
                if prefix and not prefix.endswith('|'):
                    continue
                if (int(match[1]), int(match[2]), match[3]) == key:
                    offset = new_row_offsets[new_row_index] + match.start()
                    candidates.append((offset, offset + len(name)))
        if len(candidates) == 1:
            restore_group(group, *candidates[0], 'exact_reference_key')

    # Reordered source notes can move a complete named relationship outside
    # the monotone text alignment. Preserve a unique explicit pair, not either
    # name alone. Both old and new occurrences must be inside a [!] note.
    for first, second in zip(groups, groups[1:]):
        a, z, b, y = first[0][0], first[-1][1], second[0][0], second[-1][1]
        first_pending = decisions.get((a, z), (None, None, None))[1] is not None
        second_pending = decisions.get((b, y), (None, None, None))[1] is not None
        if not (first_pending or second_pending):
            continue
        relation = ''.join(old_text[z:b].split()).casefold()
        if relation != 'vriendvan' or '[!]' not in old_text[max(0, a - 150):a]:
            continue
        left, right, old_offsets, new_offsets, matching, starts = compact_alignment()
        first_name, second_name = ''.join(old_text[a:z].split()), ''.join(old_text[b:y].split())
        pattern = re.compile('(' + re.escape(first_name) + r')[-–—]?(vriendvan)('
                             + re.escape(second_name) + ')')
        old_pairs, new_pairs = list(pattern.finditer(left)), list(pattern.finditer(right))
        if len(old_pairs) != 1 or len(new_pairs) != 1:
            continue
        match = new_pairs[0]
        target_first = new_offsets[match.start(1)], new_offsets[match.end(1) - 1] + 1
        target_second = new_offsets[match.start(3)], new_offsets[match.end(3) - 1] + 1
        if '[!]' not in new_text[max(0, target_first[0] - 150):target_first[0]]:
            continue
        if boundary_changed(a, z, *target_first) or boundary_changed(b, y, *target_second):
            continue
        # If one member was already mapped, its independent location must be
        # precisely this same pair; never attach the other to a homonym pair.
        consistent = True
        for group, pending, target in ((first, first_pending, target_first),
                                       (second, second_pending, target_second)):
            if not pending:
                reports = [retained_by_old.get((segment[0], segment[1])) for segment in group]
                if not all(reports) or (min(item['new_start'] for item in reports),
                                        max(item['new_end'] for item in reports)) != target:
                    consistent = False
        if not consistent:
            continue
        if first_pending:
            restore_group(first, *target_first, 'explicit_note_relationship')
        if second_pending:
            restore_group(second, *target_second, 'explicit_note_relationship')

    for group in groups:
        start, end = group[0][0], group[-1][1]
        if decisions.get((start, end), (None, None, None))[1] != 'ambiguous_or_short_context':
            continue
        row_index = group[0][2]
        if any(segment[2] != row_index for segment in group):
            continue
        row_start = old_row_offsets[row_index]
        old_row = ''.join(segment[0] for segment in old_rows[row_index])
        local_start, local_end = start - row_start, end - row_start
        opening = old_row.rfind('(', 0, local_start)
        closing = old_row.find(')', local_end)
        if opening < 0 or opening != old_row.find('(') or closing < 0:
            continue
        if ')' in old_row[opening:local_start]:
            continue
        subject = ''.join(old_row[:opening].split())
        if len(subject) < 5:
            continue
        following = [candidate for candidate in groups
                     if candidate[0][2] == row_index and candidate[0][0] >= end]
        if not following:
            continue
        relative = following[0]
        relation = ''.join(old_text[end:relative[0][0]].split()).casefold()
        if relation not in relative_words:
            continue
        relative_reports = [retained_by_old.get((segment[0], segment[1])) for segment in relative]
        if not all(relative_reports):
            continue
        relative_start = min(item['new_start'] for item in relative_reports)
        relative_end = max(item['new_end'] for item in relative_reports)
        name = ''.join(old_text[start:end].split())
        candidates = []
        for new_row_index, row in enumerate(new_rows):
            if not isinstance(row, list) or new_row_index not in new_row_offsets:
                continue
            text = ''.join(segment[0] for segment in row)
            first_parenthesis = text.find('(')
            if first_parenthesis < 0 or ''.join(text[:first_parenthesis].split()) != subject:
                continue
            aliases = [match for match in alias_pattern.finditer(text)
                       if ''.join(match.group(1).split()) == name]
            # Repeated aliases under the same subject remain ambiguous even
            # if another alignment happened to select one relative occurrence.
            if len(aliases) != 1:
                if aliases:
                    candidates.extend([None, None])
                continue
            match = aliases[0]
            first_closing = text.find(')', first_parenthesis)
            if first_closing < 0 or text[first_closing + 1:match.start()].strip():
                continue
            offset = new_row_offsets[new_row_index]
            candidates.append((offset + match.start(1), offset + match.end(1),
                               offset, offset + len(text)))
        if len(candidates) != 1 or candidates[0] is None:
            continue
        alias_start, alias_end, new_row_start, new_row_end = candidates[0]
        if not (alias_end < relative_start < relative_end <= new_row_end
                and relative_start >= new_row_start):
            continue
        if not ''.join(new_text[alias_end:relative_start].split()).casefold().endswith(relation):
            continue
        old_offsets = [position for position in range(start, end)
                       if not old_text[position].isspace()]
        alias_offsets = [position for position in range(alias_start, alias_end)
                         if not new_text[position].isspace()]
        if len(old_offsets) != len(alias_offsets):
            continue
        for a, z, original_row, original_segment, segment in group:
            first, last = bisect_left(old_offsets, a), bisect_left(old_offsets, z)
            if first == last:
                continue
            target_start, target_end = alias_offsets[first], alias_offsets[last - 1] + 1
            assignments.append((target_start, target_end, segment[2]))
            retained.append(dict(row=original_row, segment=original_segment,
                                 entity_id=segment[2], text=segment[0],
                                 old_start=a, old_end=z, new_start=target_start,
                                 new_end=target_end, match_method='explicit_source_alias'))
            alias_fixed.add((a, z))
    if alias_fixed:
        issues = [item for item in issues
                  if (item['old_start'], item['old_end']) not in alias_fixed]

    # Compact projections intentionally match letters to original source
    # offsets. Keep whitespace *inside the same original name occurrence*
    # clickable as well when formatting split that occurrence into runs.
    # An unlinked separator between two old names creates separate groups and
    # can never be bridged, even when both occurrences share an entity ID.
    retained_by_old = {(item['old_start'], item['old_end']): item for item in retained}
    linked_internal_whitespace_spans = 0
    for group in groups:
        mapped = [retained_by_old.get((segment[0], segment[1])) for segment in group]
        if not all(mapped):
            continue
        for previous, current in zip(mapped, mapped[1:]):
            a, z = previous['new_end'], current['new_start']
            if a < z and new_text[a:z].isspace():
                assignments.append((a, z, previous['entity_id']))
                linked_internal_whitespace_spans += 1

    # Every accepted source span must remain disjoint, including semantic
    # source anchors and the whitespace bridges within original occurrences.
    assignments.sort()
    for previous, current in zip(assignments, assignments[1:]):
        if previous[1] > current[0]:
            raise ValueError("Overlapping entity assignments")
    result, offset, assignment_index = [], 0, 0
    for row in new_rows:
        if not isinstance(row, list):
            if row is not None and row != 0:
                raise ValueError("A gap row must be 0 or None")
            result.append(row)
            offset += 1
            continue
        output_row = []
        for segment in row:
            text, style = segment[:2]
            end = offset + len(text)
            while (assignment_index < len(assignments)
                   and assignments[assignment_index][1] <= offset):
                assignment_index += 1
            cursor, index = offset, assignment_index
            while cursor < end:
                while index < len(assignments) and assignments[index][1] <= cursor:
                    index += 1
                assignment = assignments[index] if index < len(assignments) else None
                if assignment is not None and assignment[0] < end:
                    if assignment[0] > cursor:
                        stop, entity = min(end, assignment[0]), None
                    else:
                        stop, entity = min(end, assignment[1]), assignment[2]
                else:
                    stop, entity = end, None
                output_segment = [text[cursor - offset:stop - offset], style]
                if entity is not None:
                    output_segment.append(entity)
                output_row.append(output_segment)
                cursor = stop
            # Empty unlinked source runs have no visible content but remain
            # valid website data and should not affect offset bookkeeping.
            if not text:
                output_row.append([text, style])
            offset = end
        result.append(output_row)
        offset += 1
    report = {
        "old_link_segments": len(links),
        "retained_link_segments": len(retained),
        "unresolved_link_segments": len(issues),
        "new_link_segments": sum(len(segment) > 2 for row in result if row
                                 for segment in row),
        "text_unchanged": unchanged,
        "linked_internal_whitespace_spans": linked_internal_whitespace_spans,
        "retained": retained,
        "issues": issues,
    }
    return result, report

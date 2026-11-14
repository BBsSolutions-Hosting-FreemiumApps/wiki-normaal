#!/usr/bin/env python3
"""Independent structural/identity checks for a static Studiebijbel data tree.

Usage: python3 tools/verify_conversion.py SITE --baseline OLD_SITE --report report.json
Only reads data. Exit 0 means the data checks passed, not editorial approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any


def load_callback(path: Path, prefix: str) -> Any:
    """Accept a single expected callback containing JSON, never execute JS."""
    source = path.read_text(encoding="utf-8").strip()
    if not source.startswith(prefix) or not source.endswith(");"):
        raise ValueError(f"Unexpected JavaScript wrapper: {path}")
    return json.loads(source[len(prefix):-2])


def linked_occurrences(rows: list) -> list[tuple[int, str]]:
    """Join adjacent formatting runs of one linked name, keep occurrence order."""
    result = []
    previous_linked = False
    for row in rows:
        previous_linked = False
        for segment in row or []:
            if len(segment) == 3:
                entity = segment[2]
                if previous_linked and result[-1][0] == entity:
                    result[-1] = (entity, result[-1][1] + segment[0])
                else:
                    result.append((entity, segment[0]))
                previous_linked = True
            else:
                previous_linked = False
    return result


def block_text(block: dict) -> str:
    return "\n".join("".join(s[0] for s in row) if row else "" for row in block["x"])


def visible_rows(block: dict) -> list:
    """A source header/preface can move within its stable block identity."""
    return block.get("pre", []) + block.get("r", []) + block["x"]


def _styled_rows(block: dict, styles: list[str]) -> list:
    """Compare visible styles independently of entity-induced segment splits."""
    result = []
    for row in block["x"]:
        merged = []
        for segment in row or []:
            text, css = segment[0], styles[segment[1]]
            if merged and merged[-1][1] == css:
                merged[-1] = (merged[-1][0] + text, css)
            elif text:
                merged.append((text, css))
        result.append(merged)
    return result


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _inspect(root: Path) -> tuple[dict, dict]:
    errors, warnings = [], []

    def issue(code, path, message):
        errors.append({"code": code, "path": path, "message": message})

    try:
        meta = load_callback(root / "data/meta.js", "SBW.gotMeta(")
        for key in ("books", "blk", "sty", "ents", "notes"):
            if not isinstance(meta.get(key), list):
                raise ValueError(f"meta.{key} must be a list")
        if not _integer(meta.get("nch")) or meta["nch"] < 1:
            raise ValueError("meta.nch must be a positive integer")
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        issue("metadata", "data/meta.js", str(exc))
        return {"errors": errors, "warnings": warnings, "counts": {}}, {}

    if len(meta["books"]) != 66:
        issue("book_count", "meta.books", f"Expected 66 books, got {len(meta['books'])}")
    for i, style in enumerate(meta["sty"]):
        if not isinstance(style, str):
            issue("style_schema", f"meta.sty[{i}]", "CSS style must be a string")
    for i, entity in enumerate(meta["ents"]):
        if not isinstance(entity, list) or len(entity) < 5 or not all(isinstance(v, str) for v in entity[:3]):
            issue("entity_metadata_schema", f"meta.ents[{i}]", "Invalid wiki name metadata record")

    books, blocks, chapters = {}, {}, {}
    validated_bodies = set()
    links, style_uses, labels = Counter(), Counter(), Counter()
    counts = Counter(books=len(meta["books"]), metadata_blocks=len(meta["blk"]),
                     entity_metadata=len(meta["ents"]), study_notes=len(meta["notes"]),
                     styles=len(meta["sty"]))

    def check_rows(rows, location, kind="body"):
        """Validate the same row schema in bodies, raw references and prefaces."""
        if not isinstance(rows, list):
            issue("rows_schema", location, "Expected a list of styled rows")
            return
        names = {"rows": "text_rows", "characters": "text_characters",
                 "segments": "segments", "linked_segments": "linked_segments"} if kind == "body" else {
                     key: kind + "_" + key for key in ("rows", "characters", "segments", "linked_segments")}
        valid = True
        for row_index, row in enumerate(rows):
            row_path = f"{location}:row[{row_index}]"
            counts[names["rows"]] += 1
            counts["all_text_rows"] += 1
            if row is None or (_integer(row) and row == 0):
                continue
            if not isinstance(row, list):
                issue("row_schema", row_path, "Expected a segment list, 0 or null")
                valid = False
                continue
            for segment in row:
                if not isinstance(segment, list) or len(segment) not in (2, 3):
                    issue("segment_schema", row_path, "Expected [text, style, optional entity ID]")
                    valid = False
                    continue
                text, style = segment[:2]
                if not isinstance(text, str):
                    issue("segment_text", row_path, "Segment text must be a string")
                    valid = False
                    continue
                counts[names["characters"]] += len(text)
                counts[names["segments"]] += 1
                counts["all_text_characters"] += len(text)
                counts["all_segments"] += 1
                if not _integer(style) or not 0 <= style < len(meta["sty"]):
                    issue("style_id", row_path, f"Invalid style ID: {style!r}")
                    valid = False
                else:
                    style_uses[style] += len(text)
                if len(segment) == 3:
                    entity = segment[2]
                    counts[names["linked_segments"]] += 1
                    counts["all_linked_segments"] += 1
                    if not _integer(entity) or not 0 <= entity < len(meta["ents"]):
                        issue("entity_id", row_path, f"Invalid name ID: {entity!r}")
                        valid = False
                    else:
                        links[entity] += 1
        if valid and kind != "body":
            counts[kind + "_linked_occurrences"] += len(linked_occurrences(rows))
        return valid

    for book_id, info in enumerate(meta["books"]):
        path = f"data/b/{book_id}.js"
        try:
            if (not isinstance(info, list) or len(info) != 2 or not isinstance(info[0], str)
                    or not isinstance(info[1], list) or any(not _integer(c) or c < 1 for c in info[1])):
                raise ValueError("Invalid book metadata")
            book = load_callback(root / path, f"SBW.gotBook({book_id},")
            if not isinstance(book.get("bl"), dict) or not isinstance(book.get("ch"), dict):
                raise ValueError("Expected bl/ch dictionaries")
            books[book_id] = book
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            issue("book_schema", path, str(exc))
            continue
        if list(book["ch"]) != [str(c) for c in info[1]]:
            issue("chapter_list", path, "Chapter list/order differs from metadata")
        for chapter, ids in book["ch"].items():
            if not isinstance(ids, list):
                issue("chapter_schema", path + ":" + chapter, "Chapter IDs must be a list")
                continue
            for block_id in ids:
                if not _integer(block_id):
                    issue("chapter_block_id", path, f"Invalid chapter block ID: {block_id!r}")
                    continue
                if block_id in chapters:
                    issue("duplicate_chapter_block", path, f"Block {block_id} listed twice")
                chapters[block_id] = (book_id, chapter)
                if str(block_id) not in book["bl"]:
                    issue("missing_chapter_block", path, f"Block {block_id} has no body")
        for key, block in book["bl"].items():
            location = f"{path}:block[{key}]"
            try:
                block_id = int(key)
                if str(block_id) != key or block_id < 0:
                    raise ValueError("Noncanonical block ID")
                if block_id in blocks:
                    issue("duplicate_block_id", location, "Block ID occurs in multiple books")
                blocks[block_id] = (book_id, block)
                if not isinstance(block, dict) or not isinstance(block.get("l"), str):
                    raise ValueError("Block requires a string label")
                if not isinstance(block.get("x"), list):
                    raise ValueError("Block requires a list of rows")
                labels[block["l"]] += 1
                if not 0 <= block_id < len(meta["blk"]):
                    issue("unknown_block_id", location, "No corresponding metadata block")
                else:
                    record = meta["blk"][block_id]
                    if not isinstance(record, list) or len(record) != 3:
                        issue("block_metadata_schema", location, "Expected [book, chapter, label]")
                    elif record[0] != book_id or record[2] != block["l"]:
                        issue("block_metadata", location, "Book/label disagrees with metadata")
                    elif chapters.get(block_id) != (book_id, str(record[1])):
                        issue("chapter_boundary", location, "Block belongs to incorrect/missing chapter")
                if check_rows(block["x"], location + ":x"):
                    validated_bodies.add(block_id)
                if "r" in block:
                    check_rows(block["r"], location + ":r", "reference")
                if "pre" in block:
                    check_rows(block["pre"], location + ":pre", "prefix")
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                issue("block_schema", location, str(exc))
    counts["blocks"] = len(blocks)
    counts["chapter_memberships"] = len(chapters)
    if isinstance(meta.get("stats"), dict):
        if "blokken" in meta["stats"] and meta["stats"]["blokken"] != len(meta["blk"]):
            issue("block_statistics", "meta.stats.blokken", "Block total disagrees with metadata")
        if "entiteiten" in meta["stats"] and meta["stats"]["entiteiten"] != len(meta["ents"]):
            issue("entity_statistics", "meta.stats.entiteiten", "Wiki record total disagrees with metadata")
    for block_id in set(range(len(meta["blk"]))) - blocks.keys():
        issue("missing_block", f"meta.blk[{block_id}]", "Metadata block has no text body")
    duplicates = {label: n for label, n in labels.items() if n > 1}
    if duplicates:
        warnings.append({"code": "duplicate_labels", "count": len(duplicates),
                         "message": "Labels may repeat in this chronologically ordered source; compare with baseline.",
                         "examples": dict(list(duplicates.items())[:10])})

    extra = None
    extra_path = root / "data/rtf-extra.js"
    if extra_path.exists() or meta.get("conversion"):
        try:
            extra = load_callback(extra_path, "SBW.gotRtfExtra(")
            if not isinstance(extra, dict) or not isinstance(extra.get("title", ""), str):
                raise ValueError("Source preface must be an object with a string title")
            check_rows(extra.get("rows"), "data/rtf-extra.js:rows", "extra")
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            issue("extra_schema", "data/rtf-extra.js", str(exc))

    entities = {}
    for shard in range(meta["nch"]):
        path = f"data/e{shard}.js"
        try:
            records = load_callback(root / path, "SBW.gotEnts(")
            if not isinstance(records, dict):
                raise ValueError("Entity shard must contain a dictionary")
            for key, entity in records.items():
                entity_id = int(key)
                if not 0 <= entity_id < len(meta["ents"]) or entity_id % meta["nch"] != shard:
                    issue("entity_shard", path, f"Invalid/misplaced name ID {key}")
                if entity_id in entities:
                    issue("duplicate_entity", path, f"Duplicate name ID {key}")
                entities[entity_id] = entity
                if not isinstance(entity, dict):
                    raise ValueError(f"Entity {key} is not a dictionary")
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            issue("entity_schema", path, str(exc))
    counts["entity_records"] = len(entities)
    for entity_id in set(range(len(meta["ents"]))) - entities.keys():
        issue("missing_entity", "entities", f"No record for name ID {entity_id}")
    for entity_id, entity in entities.items():
        location = f"entity[{entity_id}]"
        if not isinstance(entity, dict):
            continue
        for field in ("o", "nt", "q", "ook"):
            if not isinstance(entity.get(field, []), list):
                issue("entity_field", location, f"{field} must be a list")
                continue
            for value in entity.get(field, []):
                target = value[0] if field == "q" and isinstance(value, list) and value else value
                valid = (0 <= target < len(meta["notes"])) if field == "nt" and _integer(target) else (
                    target in entities if field == "ook" and _integer(target) else (
                        target in blocks if field in ("o", "q") and _integer(target) else False))
                if not valid:
                    issue("entity_reference", location, f"Invalid {field} reference: {value!r}")
        for target in re.findall(r"\[\[(\d+)\|", json.dumps(entity, ensure_ascii=False)):
            if int(target) not in entities:
                issue("embedded_entity_reference", location, f"Invalid embedded name ID {target}")
    eden_ids = [i for i, e in entities.items() if isinstance(e, dict) and e.get("n") == "Eden"]
    for entity_id in eden_ids:
        entity = entities[entity_id]
        if entity.get("t") != "plaats" or entity.get("c") != "zeker":
            issue("eden_classification", f"entity[{entity_id}]", "Eden must remain plaats/zeker")
        row = meta["ents"][entity_id] if 0 <= entity_id < len(meta["ents"]) else None
        if not isinstance(row, list) or row[1:3] != ["O", "z"]:
            issue("eden_metadata", f"meta.ents[{entity_id}]", "Eden metadata must remain O/z")

    genesis_ids = books.get(0, {}).get("ch", {}).get("2", [])
    genesis_links = []
    for block_id in genesis_ids:
        if block_id not in validated_bodies:
            continue
        try:
            genesis_links.extend(linked_occurrences(blocks[block_id][1]["x"]))
        except (TypeError, KeyError, IndexError):
            pass  # The malformed block is already in errors.
    genesis_segments = sum(len(s) == 3 for block_id in genesis_ids if block_id in validated_bodies
                           for row in blocks[block_id][1].get("x", []) if isinstance(row, list)
                           for s in row if isinstance(s, list))
    counts["linked_occurrences"] = sum(len(linked_occurrences(blocks[i][1]["x"])) for i in validated_bodies)
    counts["all_linked_occurrences"] = counts["linked_occurrences"] + sum(
        counts[kind + "_linked_occurrences"] for kind in ("reference", "prefix", "extra"))
    report = {"errors": errors, "warnings": warnings, "counts": dict(counts),
              "used_styles": [{"css": meta["sty"][i], "characters": n}
                              for i, n in sorted(style_uses.items())],
              "genesis_2": {"blocks": len(genesis_ids), "linked_segments": genesis_segments,
                            "linked_occurrences": len(genesis_links),
                            "name_occurrences": [[i, text] for i, text in genesis_links],
                            "eden_ids": eden_ids},
              "duplicate_labels": duplicates}
    state = {"meta": meta, "books": books, "blocks": blocks, "entities": entities,
             "style_uses": style_uses, "links": links, "labels": labels, "extra": extra}
    return report, state


def verify_site(root: str | Path, baseline: str | Path | None = None) -> dict:
    root = Path(root)
    report, state = _inspect(root)
    report["status"] = "DATA_CHECKS_PASSED" if not report["errors"] else "FAILED"
    report["source"] = str(root)
    report["scope"] = "Data structure and baseline identity preservation; RTF fidelity requires the converter source audit."
    if baseline is not None:
        original, old = _inspect(Path(baseline))
        changes = {"text_blocks": [], "style_blocks": [], "lost_link_occurrences": [],
                   "changed_link_occurrences": [], "entity_records": [], "chapter_lists": [],
                   "added_blocks": [], "added_chapters": []}

        def fail(code, message):
            report["errors"].append({"code": code, "path": "baseline", "message": message})

        if original["errors"]:
            fail("invalid_baseline", f"Baseline has {len(original['errors'])} structural errors")
        if state and old:
            old_block_count = len(old["meta"]["blk"])
            if state["meta"]["blk"][:old_block_count] != old["meta"]["blk"]:
                fail("block_identity_changed", "Existing block IDs, references or chapter boundaries changed")
            changes["added_blocks"] = sorted(set(state["blocks"]) - set(old["blocks"]))
            if len(state["meta"]["books"]) != len(old["meta"]["books"]):
                fail("book_structure_changed", "Book list length changed")
            else:
                for book_id, previous_info in enumerate(old["meta"]["books"]):
                    current_info = state["meta"]["books"][book_id]
                    if (not isinstance(current_info, list) or len(current_info) != 2
                            or current_info[0] != previous_info[0] or not isinstance(current_info[1], list)
                            or [c for c in current_info[1] if c in previous_info[1]] != previous_info[1]):
                        fail("book_structure_changed", f"Book {book_id}: existing name/chapter order changed")
                        continue
                    changes["added_chapters"].extend({"book": book_id, "chapter": c}
                        for c in current_info[1] if c not in previous_info[1])
            if state["meta"]["ents"] != old["meta"]["ents"]:
                fail("entity_metadata_changed", "Existing wiki identity metadata changed")
            notes = old["meta"]["notes"]
            if state["meta"]["notes"][:len(notes)] != notes:
                fail("study_notes_changed", "Existing study notes changed or disappeared")
            for book_id, book in old["books"].items():
                current_chapters = state["books"].get(book_id, {}).get("ch", {})
                if any([block_id for block_id in current_chapters.get(chapter, [])
                        if _integer(block_id) and block_id < old_block_count] != ids
                       for chapter, ids in book["ch"].items()):
                    changes["chapter_lists"].append(book_id)
            if changes["chapter_lists"]:
                fail("chapter_order_changed", "Chapter block membership/order changed")
            for entity_id, entity in old["entities"].items():
                if state["entities"].get(entity_id) != entity:
                    changes["entity_records"].append(entity_id)
            if changes["entity_records"]:
                fail("wiki_records_changed", "Existing wiki records were removed or modified")
            if not original["errors"] and not report["errors"]:
                for block_id, (_, previous) in old["blocks"].items():
                    current = state["blocks"][block_id][1]
                    if block_text(previous) != block_text(current):
                        changes["text_blocks"].append(block_id)
                    old_styles = _styled_rows(previous, old["meta"]["sty"])
                    new_styles = _styled_rows(current, state["meta"]["sty"])
                    if old_styles != new_styles:
                        changes["style_blocks"].append(block_id)
                    before = linked_occurrences(visible_rows(previous))
                    after = linked_occurrences(visible_rows(current))
                    if before != after:
                        changes["changed_link_occurrences"].append(block_id)
                    missing = Counter(before) - Counter(after)
                    if missing:
                        changes["lost_link_occurrences"].append({"id": block_id, "ref": previous["l"],
                            "names": [[i, text, n] for (i, text), n in missing.items()]})
                if changes["lost_link_occurrences"]:
                    fail("lost_name_links", "One or more original linked name occurrences were lost/changed")
            introduced = {label: n for label, n in state["labels"].items() if n > old["labels"][label]
                          and n > 1}
            if introduced:
                fail("new_duplicate_labels", str(introduced))
        report["baseline"] = {"path": str(baseline), "counts": original["counts"],
                              "growth": {"original_blocks": original["counts"].get("blocks", 0),
                                         "candidate_blocks": report["counts"].get("blocks", 0),
                                         "added_blocks": len(changes["added_blocks"]),
                                         "added_chapters": len(changes["added_chapters"])},
                              "changes": changes}
    report["passed"] = not report["errors"]
    report["status"] = "DATA_CHECKS_PASSED" if report["passed"] else "FAILED"
    # Passing schema/identity checks does not attest completeness against the RTF.
    report["publication_approved"] = False
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify_site(args.site, args.baseline)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "counts": report["counts"],
                      "errors": len(report["errors"]), "report": str(args.report)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

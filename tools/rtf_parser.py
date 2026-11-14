#!/usr/bin/env python3
"""Small, dependency-free RTF reader preserving text lines and character formatting.

Unlike a plain text extractor this understands group scoping, destinations, Unicode
fallback characters, code pages and character runs. The return value is ordinary
JSON-serializable Python data. It never writes to the input or to site data.
"""
from __future__ import annotations

import codecs
from collections import Counter
from pathlib import Path
import re

_TOKEN = re.compile(r"([{}])|\\(?:([a-zA-Z]+)(-?\d+)? ?|'([0-9a-fA-F]{2})|([^a-zA-Z]))|([^{}\\]+)")
_DESTINATIONS = frozenset((
    'fonttbl', 'colortbl', 'stylesheet', 'info', 'pict', 'object',
    'header', 'headerl', 'headerr', 'headerf', 'footer', 'footerl',
    'footerr', 'footerf', 'listtable', 'listoverridetable', 'revtbl',
    'rsidtbl', 'generator', 'xmlnstbl', 'datastore', 'themedata',
    'colorschememapping', 'fldinst', 'filetbl',
))
# Layout controls do not add text. They are retained in the control inventory.
_LAYOUT = frozenset((
    'rtf', 'ansi', 'mac', 'pc', 'pca', 'ansicpg', 'deff', 'deflang',
    'cocoartf', 'cocoatextscaling', 'cocoaplatform', 'paperw', 'paperh',
    'margl', 'margr', 'margt', 'margb', 'vieww', 'viewh', 'viewkind',
    'deftab', 'pard', 'pardeftab', 'sl', 'slmult', 'partightenfactor',
    'tx', 'li', 'ri', 'fi', 'sb', 'sa', 'qc', 'ql', 'qr', 'qj',
    'pardirnatural', 'ltrpar', 'rtlpar', 'ltrch', 'rtlch', 'lang',
    'expnd', 'expndtw', 'kerning', 'field', 'fldrslt', 'nosupersub',
    'keep', 'keepn', 'widctlpar', 'nowidctlpar', 'hyphpar',
))
_DEFAULT = dict(color=None, background=None, bold=False, italic=False,
                underline=False, strike=False, superscript=0,
                underline_color=None, font=0, font_family=None, font_size_points=12.0)

_GENERIC_FONTS = dict(froman='serif', fswiss='sans-serif', fmodern='monospace',
                      fscript='cursive', fdecor='fantasy', ftech='monospace',
                      fnil='serif', fbidi='serif')


def _font_family(name: str) -> str:
    # Only strip explicit PostScript variant suffixes. The real family name
    # "Times New Roman" must not become "Times New".
    return re.sub(r'[-,](?:BoldItalic|BoldOblique|DemiBoldItalic|SemiBoldItalic|'
                  r'DemiBold|SemiBold|Bold|Italic|Oblique|Roman|Regular)(?:MT)?$',
                  '', name, flags=re.IGNORECASE) or name


def _font_table(source: str) -> dict[int, dict]:
    start = re.search(r'{\\fonttbl\b', source)
    if not start:
        return {}
    codepage = re.search(r'\\ansicpg(\d+)\b', source[:start.start()])
    encoding = 'cp' + codepage[1] if codepage else 'cp1252'
    fonts, current, chunks = {}, None, []
    depth, stack, skip, star, uc, fallback = 0, [], False, False, 1, 0

    def append(value):
        nonlocal fallback
        if fallback:
            take = min(len(value), fallback)
            value, fallback = value[take:], fallback - take
        chunks.append(value)

    def finish():
        if current is not None:
            name = ''.join(chunks).strip()
            if name:
                name = name.encode('utf-16-le', 'surrogatepass').decode('utf-16-le')
                fonts[current['id']] = {key: value for key, value in current.items() if key != 'id'}
                fonts[current['id']].update(name=name, family=_font_family(name))

    for token in _TOKEN.finditer(source, start.start()):
        brace, word, number, hexbyte, symbol, literal = token.groups()
        if brace == '{':
            depth += 1
            stack.append((skip, star, uc))
            continue
        if brace == '}':
            depth -= 1
            skip, star, uc = stack.pop()
            if not depth:
                break
            continue
        if symbol == '*':
            star = True
            continue
        if word and star:
            skip, star = True, False
        if word == 'falt':
            skip = True
        if skip:
            continue
        if word == 'f' and number is not None:
            current = dict(id=int(number), generic='serif', charset=0)
            chunks = []
        elif word in _GENERIC_FONTS and current is not None:
            current['generic'] = _GENERIC_FONTS[word]
        elif word == 'fcharset' and current is not None:
            current['charset'] = int(number or 0)
        elif word == 'uc':
            uc = max(0, int(number or 1))
        elif word == 'u':
            chunks.append(chr(int(number) & 0xffff))
            fallback = uc
        elif hexbyte is not None:
            append(bytes([int(hexbyte, 16)]).decode(encoding))
        elif symbol in ('\\', '{', '}'):
            append(symbol)
        elif literal is not None and current is not None:
            parts = literal.replace('\r', '').replace('\n', '').encode('latin1').decode(encoding).split(';')
            append(parts[0])
            if len(parts) > 1:
                finish()
                current, chunks = None, []
    return fonts


def _color_table(source: str) -> list[str | None]:
    match = re.search(r'{\\colortbl\b([^{}]*)}', source)
    if not match:
        return [None]
    result: list[str | None] = []
    for item in match.group(1).split(';')[:-1]:
        channels = dict((k, int(v)) for k, v in re.findall(r'\\(red|green|blue)(\d+)', item))
        result.append('#%02x%02x%02x' % tuple(channels.get(k, 0) for k in ('red', 'green', 'blue'))
                      if channels else None)
    return result or [None]


def parse_rtf(path: str | Path) -> dict:
    """Read an RTF file; see :func:`parse_rtf_bytes` for the returned schema."""
    return parse_rtf_bytes(Path(path).read_bytes())


def parse_rtf_bytes(raw: bytes) -> dict:
    """Return ``{lines, colors, fonts, controls, warnings, unsupported_controls}``.

    ``lines`` includes empty source lines. Each line contains runs with ``text``,
    ``style`` (CSS-ready RGB colors and booleans) and ``source_offset`` (byte
    offset in the original RTF). CR/LF used merely to wrap RTF source is ignored;
    escaped newlines, ``\\par`` and ``\\line`` delimit visible lines.
    """
    source = raw.decode('latin1')  # one source character == one byte offset
    if not source.lstrip().startswith(r'{\rtf'):
        raise ValueError('Geen RTF-document (verwacht {\\rtf...)')
    colors = _color_table(source)
    fonts = _font_table(source)
    default_font = re.search(r'\\deff(\d+)\b', source)
    default_style = dict(_DEFAULT, font=int(default_font[1]) if default_font else 0)
    default_style['font_family'] = fonts.get(default_style['font'], {}).get('family')
    state = dict(style=default_style.copy(), skip=False, star=False, uc=1, encoding='cp1252')
    stack: list[dict] = []
    lines: list[list[dict]] = [[]]
    controls: Counter = Counter()
    unsupported: Counter = Counter()
    warnings: list[str] = []
    fallback = 0

    def emit(text: str, offset: int, *, is_unicode: bool = False) -> None:
        nonlocal fallback
        if not text or state['skip']:
            return
        if not is_unicode and fallback:
            take = min(len(text), fallback)
            text, fallback = text[take:], fallback - take
        if not text:
            return
        parts = text.split('\n')
        for i, part in enumerate(parts):
            if i:
                lines.append([])
            if part:
                runs = lines[-1]
                style = state['style']
                if runs and runs[-1]['style'] == style:
                    runs[-1]['text'] += part
                else:
                    runs.append(dict(text=part, style=style.copy(), source_offset=offset))

    def color(index: int) -> str | None:
        if not 0 <= index < len(colors):
            raise ValueError(f'Ongeldige RTF-kleurindex {index}')
        return colors[index]

    position = 0
    while position < len(source):
        match = _TOKEN.match(source, position)
        if match is None:
            raise ValueError(f'Ongeldige RTF-token op byte {position}')
        position = match.end()
        brace, word, number, hexbyte, symbol, literal = match.groups()
        if brace == '{':
            stack.append(dict(state, style=state['style'].copy()))
            continue
        if brace == '}':
            if not stack:
                raise ValueError(f'Onverwachte sluitaccolade op byte {match.start()}')
            state = stack.pop()
            continue
        if literal is not None:
            # Literal CR/LF are source wrapping, never visible RTF line breaks.
            emit(literal.replace('\r', '').replace('\n', '').encode('latin1').decode(state['encoding']), match.start())
            continue
        if hexbyte is not None:
            emit(bytes([int(hexbyte, 16)]).decode(state['encoding']), match.start())
            continue
        if symbol is not None:
            if symbol == '*':
                state['star'] = True
            elif symbol in '\\{}':
                emit(symbol, match.start())
            elif symbol in '\r\n':
                # Treat escaped CRLF as one break (normal tokenizer leaves LF
                # in a literal and that physical LF is ignored above).
                emit('\n', match.start())
            elif symbol == '~':
                emit('\u00a0', match.start())
            elif symbol == '-':
                emit('\u00ad', match.start())
            elif symbol == '_':
                emit('\u2011', match.start())
            continue
        controls[word] += 1
        value = int(number) if number is not None else 1
        if state['star']:
            state['skip'], state['star'] = True, False
        if word in _DESTINATIONS:
            state['skip'] = True
        if word == 'bin':
            if value < 0 or position + value > len(source):
                raise ValueError(f'Ongeldige binaire lengte op byte {match.start()}')
            position += value
            continue
        if state['skip']:
            continue
        style = state['style']
        if word == 'ansicpg':
            encoding = 'cp' + str(value)
            codecs.lookup(encoding)
            state['encoding'] = encoding
        elif word == 'uc':
            state['uc'] = max(0, value)
        elif word == 'u':
            emit(chr(value & 0xffff), match.start(), is_unicode=True)
            fallback = state['uc']
        elif word in ('par', 'line'):
            emit('\n', match.start())
        elif word == 'tab':
            emit('\t', match.start())
        elif word in ('cf', 'cb', 'highlight', 'ulc'):
            style[{'cf':'color', 'cb':'background', 'highlight':'background', 'ulc':'underline_color'}[word]] = color(value)
        elif word in ('b', 'i', 'ul', 'strike'):
            style[{'b':'bold','i':'italic','ul':'underline','strike':'strike'}[word]] = bool(value)
        elif word.startswith('ul') and word not in ('ulc', 'ulnone'):
            style['underline'] = bool(value)
        elif word == 'ulnone':
            style['underline'] = False
        elif word == 'plain':
            state['style'] = default_style.copy()
        elif word == 'f':
            style['font'] = value
            style['font_family'] = fonts.get(value, {}).get('family')
        elif word == 'fs':
            style['font_size_points'] = value / 2
        elif word in ('super', 'sub', 'nosupersub'):
            style['superscript'] = {'super':1,'sub':-1,'nosupersub':0}[word]
        elif word in ('emdash', 'endash', 'bullet', 'lquote', 'rquote', 'ldblquote', 'rdblquote'):
            emit({'emdash':'—','endash':'–','bullet':'•','lquote':'‘','rquote':'’','ldblquote':'“','rdblquote':'”'}[word], match.start())
        elif word not in _LAYOUT:
            unsupported[word] += 1
    if stack:
        raise ValueError(f'RTF heeft {len(stack)} onafgesloten groepen')
    # RTF represents astral code points by two signed UTF-16 code units.
    for line in lines:
        for run in line:
            try:
                run['text'] = run['text'].encode('utf-16-le', 'surrogatepass').decode('utf-16-le')
            except UnicodeDecodeError as error:
                raise ValueError(f'Ongeldig Unicode-surrogaat op byte {run["source_offset"]}') from error
    if unsupported:
        warnings.append('Onbekende besturingswoorden: ' + ', '.join(sorted(unsupported)))
    return dict(lines=lines, colors=colors, fonts=fonts, controls=dict(controls), warnings=warnings,
                unsupported_controls=dict(unsupported))


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rtf', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = parse_rtf(args.rtf)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False) + '\n', encoding='utf-8')
    else:
        print('\n'.join(''.join(run['text'] for run in line) for line in result['lines']))

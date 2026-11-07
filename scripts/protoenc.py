"""Minimal protobuf encoder for Deadlock build payloads.

Reimplements the helpers from encode_payload.py (whose dependency
/home/hatch/workspace/deadlock-build-installer is gone) from the format
documented in that file's docstring, verified by byte-identical re-encoding
of the site's existing payloads.
"""
import base64
import zstandard

PHASE_TAG = {'early': '#Citadel_HeroBuilds_EarlyGame',
             'mid': '#Citadel_HeroBuilds_MidGame',
             'late': '#Citadel_HeroBuilds_LateGame'}
PHASE_FLOATS = {'early': (bytes.fromhex('1f852d44'), bytes.fromhex('e17a4543')),
                'mid': (bytes.fromhex('ec512f44'), bytes.fromhex('b89e4a43')),
                'late': (bytes.fromhex('33932f44'), bytes.fromhex('33d38943'))}
ACCOUNT_ID = 1127964747


def _varint(v):
    out = bytearray()
    while True:
        b = v & 0x7f
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _tag(field, wire):
    return _varint((field << 3) | wire)


def f_varint(field, v):
    return _tag(field, 0) + _varint(v)


def f_string(field, s):
    b = s.encode('utf-8')
    return _tag(field, 2) + _varint(len(b)) + b


def f_message(field, payload):
    return _tag(field, 2) + _varint(len(payload)) + payload


def f_fixed32_raw(field, raw4):
    return _tag(field, 5) + raw4


def encode_build(hero_id, name, phases, timestamp, account=ACCOUNT_ID):
    """phases: list of (phase_key, [item_ids]); phase_key in early/mid/late."""
    cats = b''
    for phase, ids in phases:
        items = b''.join(f_message(1, f_varint(1, iid)) for iid in ids)
        w, h = PHASE_FLOATS[phase]
        cat = (items + f_string(2, PHASE_TAG[phase]) + f_string(3, '')
               + f_fixed32_raw(4, w) + f_fixed32_raw(5, h))
        cats += f_message(1, cat)
    details = cats  # details = repeated field1 category messages
    top = (f_varint(1, hero_id) + f_varint(2, 1) + f_varint(3, account)
           + f_varint(4, timestamp) + f_string(5, name) + f_string(6, '')
           + f_varint(7, 0) + f_varint(8, 0) + f_message(10, details))
    return base64.b64encode(zstandard.ZstdCompressor().compress(top)).decode()


def decode_build(payload_b64):
    return zstandard.ZstdDecompressor().decompress(base64.b64decode(payload_b64))


def read_varint(buf, i):
    v, shift = 0, 0
    while True:
        b = buf[i]
        i += 1
        v |= (b & 0x7f) << shift
        if not b & 0x80:
            break
        shift += 7
    return v, i

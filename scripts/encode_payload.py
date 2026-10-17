"""Encode a Deadlock in-game build payload (KLUv… base64 Zstandard protobuf).

Reverse-engineered 2026-10-16 from the 69 verified working payloads on the
build-guide site: the encoder reproduces them BYTE-IDENTICAL (protobuf level).

Format (observed, all constant across every verified payload):
  top-level: field1=hero_id, field2=1, field3=author_account_id,
             field4=timestamp, field5=name, field6=description(""),
             field7=0, field8=0, field10=details
  details:   repeated field1 = category messages (NO ability_order)
  category:  repeated field1 = item messages (field1=item_id ONLY),
             field2 = "#Citadel_HeroBuilds_<Early|Mid|Late>Game",
             field3 = description (""), field4 = width (float, per-phase constant),
             field5 = height (float, per-phase constant)
  Per-phase float constants (universal):
    Early: width 694.08 (1f852d44) height 197.48 (e17a4543)
    Mid:   width 701.28 (ec512f44) height 202.62 (b89e4a43)
    Late:  width 702.30 (33932f44) height 275.65 (33d38943)

Usage:
    python3 encode_payload.py <hero_id> "<build name>" <timestamp> <early_ids> <mid_ids> <late_ids>
where each id list is comma-separated item IDs in buy order.
Prints the base64 payload. Verify with: decode -> Zstd decompress -> fields.
"""
import base64
import sys
import time

sys.path.insert(0, '/home/hatch/workspace/deadlock-build-installer')
import proto
import zstandard

PHASE_TAG = {'early': '#Citadel_HeroBuilds_EarlyGame',
             'mid': '#Citadel_HeroBuilds_MidGame',
             'late': '#Citadel_HeroBuilds_LateGame'}
PHASE_FLOATS = {'early': (bytes.fromhex('1f852d44'), bytes.fromhex('e17a4543')),
                'mid': (bytes.fromhex('ec512f44'), bytes.fromhex('b89e4a43')),
                'late': (bytes.fromhex('33932f44'), bytes.fromhex('33d38943'))}
ACCOUNT_ID = 1127964747


def encode_build(hero_id, name, phases, timestamp=None, account=ACCOUNT_ID):
    """phases: list of (phase_key, [item_ids]) with phase_key in early/mid/late."""
    ts = int(timestamp) if timestamp else int(time.time())
    cats = b''
    for phase, ids in phases:
        items = b''.join(proto.f_message(1, proto.f_varint(1, iid)) for iid in ids)
        w, h = PHASE_FLOATS[phase]
        cat = (items + proto.f_string(2, PHASE_TAG[phase]) + proto.f_string(3, '')
               + proto._tag(4, 5) + w + proto._tag(5, 5) + h)
        cats += proto.f_message(1, cat)
    out = (proto.f_varint(1, hero_id) + proto.f_varint(2, 1)
           + proto.f_varint(3, account) + proto.f_varint(4, ts)
           + proto.f_string(5, name) + proto.f_string(6, '')
           + proto.f_varint(7, 0) + proto.f_varint(8, 0)
           + proto.f_message(10, cats))
    return base64.b64encode(zstandard.ZstdCompressor().compress(out)).decode()


def verify(payload, hero_id, name, phases):
    """Round-trip check: decompress, decode, compare against expected values."""
    raw = base64.b64decode(payload)
    assert raw[:4] == b'\x28\xb5\x2f\xfd', 'not a Zstandard frame'
    dec = zstandard.ZstdDecompressor().decompress(raw, max_output_size=200000)
    top = {f: (w, v) for f, w, v in proto.decode_fields(dec)}
    assert top[1][1] == hero_id, f"hero_id {top[1][1]} != {hero_id}"
    assert top[5][1].decode() == name, f"name mismatch"
    det = top[10][1]
    cats = [v for f, w, v in proto.decode_fields(det) if f == 1]
    assert len(cats) == len(phases), 'category count mismatch'
    for cv, (phase, ids) in zip(cats, phases):
        flds = list(proto.decode_fields(cv))
        got_ids = []
        for f, w, v in flds:
            if f == 1:
                im = list(proto.decode_fields(v))
                got_ids.append([vv for ff, ww, vv in im if ff == 1][0])
        nm = [x.decode() for f, w, x in flds if f == 2][0]
        assert nm == PHASE_TAG[phase], f'category name {nm}'
        assert got_ids == ids, f'item order mismatch in {phase}'
    return True


if __name__ == '__main__':
    hero_id = int(sys.argv[1])
    name = sys.argv[2]
    ts = sys.argv[3]
    phases = [('early', [int(x) for x in sys.argv[4].split(',') if x]),
              ('mid', [int(x) for x in sys.argv[5].split(',') if x]),
              ('late', [int(x) for x in sys.argv[6].split(',') if x])]
    payload = encode_build(hero_id, name, phases, ts)
    verify(payload, hero_id, name, phases)
    print(payload)

"""Independent raw-format transport check; does not qualify consumer hardware."""
import hashlib
import importlib.util
import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / 'tools/w11_ckv_merge_feasibility.py'
SPEC = importlib.util.spec_from_file_location('candidate', MODEL)
candidate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(candidate)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify():
    rng = random.Random(20261001)
    extents = [(w, k) for w in (0, 1, 2, 3, 4, 127, 128)
               for k in (0, 1, 2, 3, 4, 511, 512)]
    groups_checked = words_checked = wire_edges = 0
    digest = hashlib.sha256()
    for window, selected in extents:
        # Independent element arrays, not a copy of the candidate packer.
        rows = []
        for row in range(window + selected):
            is_ckv = row >= window
            code_width = 4 if is_ckv else 8
            codes = [rng.getrandbits(code_width) for _ in range(512)]
            scales = [rng.getrandbits(8) for _ in range(32 if is_ckv else 16)]
            rows.append((is_ckv, codes, scales))
        packets = candidate.packets(window, selected)
        recovered = {}
        for p in packets:
            packed = shift = 0
            for row in range(p['first_row'], p['first_row'] + p['rows']):
                ck, codes, scales = rows[row]
                g = p['group']
                width = 4 if ck else 8
                code_bits = sum(codes[g * 32 + e] << (width * e) for e in range(32))
                scale_bits = (scales[2 * g] | (scales[2 * g + 1] << 8)) if ck else scales[g]
                raw = code_bits | (scale_bits << (32 * width))
                raw_width = 144 if ck else 264
                packed |= raw << shift
                shift += raw_width
            assert shift == p['raw_payload_bits']
            # Candidate header is proposed, not an existing interface. Exercise
            # all its fields without treating this encoding as frozen RTL.
            flags = sum(int(rows[p['first_row'] + i][0]) << i for i in range(p['rows']))
            mask = (1 << p['rows']) - 1
            header = 0x6A51 | (p['beat'] << 16) | (p['group'] << 24) | (mask << 28) | (flags << 32)
            packet = packed | (header << shift)
            chunks = [(packet >> (256 * i)) & ((1 << 256) - 1)
                      for i in range(p['serialization_cycles'])]
            wire_edges += len(chunks)
            rebuilt = sum(chunk << (256 * i) for i, chunk in enumerate(chunks))
            assert rebuilt == packet
            assert rebuilt >> p['packet_bits'] == 0
            assert rebuilt >> shift == header
            cursor = 0
            for i in range(p['rows']):
                row = p['first_row'] + i
                ck, codes, scales = rows[row]
                raw_width = 144 if ck else 264
                raw = (rebuilt >> cursor) & ((1 << raw_width) - 1)
                cursor += raw_width
                # Consumer-side zero insertion, without dequantising or rounding.
                actual_group = raw | (int(ck) << 264)
                g = p['group']
                if ck:
                    expected = (1 << 264) | (scales[2*g+1] << 136) | (scales[2*g] << 128)
                    expected |= sum(codes[g*32+e] << (4*e) for e in range(32))
                else:
                    expected = scales[g] << 256
                    expected |= sum(codes[g*32+e] << (8*e) for e in range(32))
                assert actual_group == expected
                key = row, g
                assert key not in recovered
                recovered[key] = actual_group
                digest.update(actual_group.to_bytes(34, 'little'))
                groups_checked += 1
            assert cursor == shift
        assert set(recovered) == {(r, g) for r in range(len(rows)) for g in range(16)}
        for first in range(0, len(rows), 4):
            beat = sum(recovered[r, g] << (((r-first)*16+g)*265)
                       for r in range(first, min(first+4, len(rows))) for g in range(16))
            assert beat.bit_length() <= 16960
            words_checked += 1
    rtl_path = 'rtl/chip/ot_chip_v41x_ckv_stream_merge.sv'
    rtl = subprocess.check_output(['git', 'show', '73d79c123:' + rtl_path], cwd=ROOT)
    for expression in (b"{1'b0, wr[4096 + 8*g +: 8], wr[256*g +: 256]}",
                       b"{1'b1, 120'b0, cr[2048 + 16*g +: 16], cr[128*g +: 128]}"):
        assert expression in rtl
    return dict(schema='opentallas.parent.ckv-raw-serial-payload-review.v1',
                candidate_commit='b6697951477dc7cd2bf4788b2524f77fabf07948',
                model_sha256=sha(MODEL.read_bytes()), existing_rtl_sha256=sha(rtl),
                extent_cases=len(extents), groups_checked=groups_checked,
                output_beats_checked=words_checked, wire_edges_checked=wire_edges,
                reconstructed_payload_sha256=digest.hexdigest(),
                verdict='PASS_RAW_PAYLOAD_RECONSTRUCTION_ONLY',
                numerical_scope='No arithmetic performed; codes/scales and existing 265-bit group layouts preserved.',
                exclusions=['actual header ABI', 'actual producer/consumer RTL', 'credit/calendar and CDC',
                            'consumer port/write enable cost', 'physical routing/SS/FF', 'full connected token'],
                engine_RTL_build_ready=False, physical_admission=False, adopt=False)

if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))

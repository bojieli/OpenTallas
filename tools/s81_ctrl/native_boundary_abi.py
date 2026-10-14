#!/usr/bin/env python3
"""Candidate H/PF wire codec, not evidence that the native controller carries PF.

H uses the actual HC element-major BF16 layout: element e, copy k occupies
16*(4*e+k). PF consists of four unmodified binary32 bit patterns. A 512-bit
transport therefore needs 641 payload rows for the canonical 40976 bytes;
the last row has 16 meaningful bytes and 48 zero padding bytes. Slot stride
must be 641 independently of the HC H load/store count of 640.
"""
import argparse
import hashlib
import json
from pathlib import Path

D = 5120
H_ROWS = 640
PAYLOAD_ROWS = 641
PAYLOAD_BYTES = 40976


def pack(h, pf):
    if len(h) != 4 or any(len(copy) != D for copy in h):
        raise ValueError('H must contain four copies of 5120 BF16 bit patterns')
    if len(pf) != 4:
        raise ValueError('PF must contain four binary32 bit patterns')
    raw = bytearray()
    for e in range(D):
        for k in range(4):
            value = h[k][e]
            if type(value) is not int or not 0 <= value < 65536:
                raise ValueError('invalid BF16 bit pattern')
            raw.extend(value.to_bytes(2, 'little'))
    for value in pf:
        if type(value) is not int or not 0 <= value < 1 << 32:
            raise ValueError('invalid PF binary32 bit pattern')
        raw.extend(value.to_bytes(4, 'little'))
    return [int.from_bytes(raw[i:i+64].ljust(64, b'\0'), 'little')
            for i in range(0, len(raw), 64)]


def unpack(rows):
    if len(rows) != PAYLOAD_ROWS:
        raise ValueError('canonical H/PF needs 641 rows; pure H640 omits PF')
    if any(type(v) is not int or not 0 <= v < 1 << 512 for v in rows):
        raise ValueError('invalid payload row')
    raw = b''.join(v.to_bytes(64, 'little') for v in rows)
    if any(raw[PAYLOAD_BYTES:]):
        raise ValueError('nonzero PF tail padding')
    h = [[int.from_bytes(raw[2*(4*e+k):2*(4*e+k)+2], 'little')
          for e in range(D)] for k in range(4)]
    pf = [int.from_bytes(raw[40960+4*k:40964+4*k], 'little') for k in range(4)]
    return h, pf


def audit(root):
    root = Path(root)
    paths = ['tools/w11_dsrom_full_tp_program.py', 'tools/hdc_program_v41.py',
             'rtl/dsrom_sys/s81_suhc/ot_s81_hc_core.sv',
             'rtl/dsrom_sys/s81_ctrl/ot_s81_hop_tx.sv',
             'rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv']
    return {'schema': 'opentallas.s81.native-boundary-abi.v1',
            'status': 'WIRE_CODEC_ONLY_NATIVE_PF_BINDING_MISSING',
            'source_sha256': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
            'h_bf16_bytes': 40960, 'pf_binary32_bytes': 16,
            'canonical_payload_bytes': PAYLOAD_BYTES, 'hc_h_rows': H_ROWS,
            'candidate_transport_rows': PAYLOAD_ROWS, 'tail_valid_bytes': 16,
            'candidate_slot_stride_rows': PAYLOAD_ROWS,
            'current_pure_h_controller_qualified_for_pf': False,
            'native_executed_transfer_count': None,
            'remaining_bindings': ['actual dynamic PF writer and macro commit',
                                   'hop PF read and full-message fence',
                                   'receiver PF epoch/slot region',
                                   'COEF_LOAD pre source from received PF',
                                   'native120 full operation and VM region table',
                                   'source-bound full arithmetic and PF mutants',
                                   'assigned pins, routes, full production throughput']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit(args.root), indent=2)+'\n')

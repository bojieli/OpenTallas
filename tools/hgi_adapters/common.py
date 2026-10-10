"""hgi-adapters (2026-10-09): shared helpers for the HGI-1 record-adapter benches.

The record an adapter receives is the sequencer's dispatch (ot_hgi_seq v1.0, main ef3135b44): header, SUT, the 7
EFFECTIVE descriptors {A,B,C,D,O,R,I} and their 21-bit effective counts.  ot_hgi_seq equals the sequencer contract
tools/hgi_seq_vectors.Ref on all 66 record-carrying conformance vectors (tb_hgi_seq +define+SEQ_CONF PASS, hbm-forks),
so the benches drive each adapter with Ref's dispatch of the hbm-sim CONFORMANCE vectors
(results/arch/hgi_sim_20261009/conformance) and of the hbm-sim Qwen3-8B token program.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hgi_seq_vectors as SV  # noqa: E402

CONF = ROOT / 'results/arch/hgi_sim_20261009/conformance'
OPND = SV.OPND                      # A B C D O R I
MD, UOP = SV.MD, SV.UOP
SPACE = {v: k for k, v in SV.SPACE.items()}


def fld(v, k, table=None):
    return SV.field(v, table or MD, k)


def image_words(v):
    img = []
    for rh in v['record_hex']:
        x = bytes.fromhex(rh)
        for q in range(0, len(x), 16):
            img.append(int.from_bytes(x[q:q + 16], 'little'))
    return img


def vm_of(die):
    vm = {}
    for base, hexs in die['vm_in']:
        b = bytes.fromhex(hexs)
        for q in range(0, len(b), 4):
            vm[base + q // 4] = int.from_bytes(b[q:q + 4], 'little')
    return vm


def vm_out_of(die):
    out = {}
    for base, hexs in json.loads(die['vm_out']) if isinstance(die['vm_out'], str) else die['vm_out']:
        b = bytes.fromhex(hexs)
        for q in range(0, len(b), 4):
            out[base + q // 4] = int.from_bytes(b[q:q + 4], 'little')
    return out


def conformance(pred=lambda v: True):
    """[(vector, dispatch trace, completion, vm_in of die 0)] for every record-carrying vector selected by pred"""
    out = []
    for f in sorted(CONF.glob('cf-*.json')):
        v = json.loads(f.read_text())
        if 'records_hex' not in v or not pred(v):
            continue
        die = v['dies'][0]
        vm = vm_of(die)
        cfg = v['cfg']
        ref = SV.Ref(image_words(v), 0, v['doorbell']['token'], v['doorbell']['pos'], int(die.get('rank', 0)),
                     cfg['cp_vocab'], cfg['cp_ctx_max'], vm)
        tr, cpl = ref.run()
        out.append((v, tr, cpl, vm))
    return out


def qwen_dispatch():
    """Ref's dispatch trace of the hbm-sim Qwen3-8B token program (TP4, P 8,192, rank 0, token 0)"""
    words, recs, g, md = SV.qwen_program()
    ref = SV.Ref(words, 0, 0, 8191, 0, 151936, 40960, {})
    tr, cpl = ref.run()
    return tr, cpl


def unit_of(d):
    return fld(d['hdr'], 'unit', UOP)


def hexw(x, bits):
    return f'{x & ((1 << bits) - 1):0{(bits + 3) // 4}X}'

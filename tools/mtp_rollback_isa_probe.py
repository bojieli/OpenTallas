#!/usr/bin/env python3
"""MR-5 exact ISA replay of squashed successors through the real stage programs.

This uses the reduced V4.1 arithmetic vehicle, not the rollback toy model.
The compressor ring opt-in is the only difference from the rejected vehicle.
The --legacy-ring negative control keeps its two-record AR allocation.
No snapshots are restored during replay: each job writes its own position.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import hdc_program_v41_array as A
import hdc_program_v41 as P
import hdc_isa_v41 as I
import hdc_golden_v41 as V
import hdc_golden as G
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def isa_replay(plan, progs, base, jobs):
    pipe = A.Pipeline(plan, progs, base)
    out = []
    for token, pos in jobs:
        for machine in pipe.pk:
            machine.tokens = machine.tokens[:pos]
        argmax, _, logits = pipe.step(token, pos)
        out.append((argmax, [int(x) for x in G.bits(logits)]))
    return out, [(mc.kv.copy(), mc.vm[plan.pb:plan.pb + A.PS].copy()) for mc in pipe.pk]


def replay(model, seq, rollback_ring=True, successors=5):
    lay = P.Layout(model, rollback_ring=rollback_ring)
    A.place_head_parts(lay)
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    plan = A.Plan(lay, [list(range(19)), [19], [20], list(range(21, model.L))], 0, False, 'relay')
    progs = [A.StageBuilder(lay, qchunk=P.QCHUNK).stage(plan, k) for k in range(plan.n)]
    clean_jobs = [(int(seq[p]), p) for p in range(len(seq))]
    bad = (int(seq[3]) + 1) % plan.vocab
    jobs = clean_jobs[:3] + [(bad, 3)] + clean_jobs[4:4 + successors] + clean_jobs[3:]
    reissue_offset = successors + 1
    clean_out, clean_state = isa_replay(plan, progs, base, clean_jobs)
    deep_out, deep_state = isa_replay(plan, progs, base, jobs)
    same = lambda a, b: bool(np.array_equal(G.bits(a), G.bits(b)))
    return dict(compressor_records=lay.ring, jobs=[(int(t), p) for t, p in jobs],
                corrected_positions=list(range(3, len(seq))),
                corrected_logits_exact=[clean_out[p][1] == deep_out[p + reissue_offset][1] for p in range(3, len(seq))],
                final_raw_kv_equal=[same(a[0], b[0]) for a, b in zip(clean_state, deep_state)],
                final_raw_persistent_vm_equal=[same(a[1], b[1]) for a, b in zip(clean_state, deep_state)],
                kv_words_differing=[int(np.count_nonzero(G.bits(a[0]) != G.bits(b[0])))
                                    for a, b in zip(clean_state, deep_state)],
                persistent_words_differing=[int(np.count_nonzero(G.bits(a[1]) != G.bits(b[1])))
                                            for a, b in zip(clean_state, deep_state)],
                program_instructions=[len(p) for p in progs],
                persistent_region_elements=sum(n for _, n in lay.vm_persist),
                compressor_ring_extra_bytes=3 * (lay.ring - 2) * 64 * 4,
                compressor_ring_added_isa_instructions=0,
                compressor_ring_added_arithmetic_cycles=0,
                physical_storage_qualification=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sequence', type=Path, required=True, help='JSON list or golden.json with seq')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--legacy-ring', action='store_true')
    parser.add_argument('--successors', type=int, choices=range(1, 6), default=5)
    args, unknown = parser.parse_known_args()
    assert all(x in ('--all-unit', '--kv-hbm') for x in unknown), unknown
    raw = json.loads(args.sequence.read_text())
    seq = raw['seq'] if isinstance(raw, dict) else raw
    assert len(seq) >= 12, 'continue through position 11 to test persistent corruption'
    start = time.time()
    rec = replay(V.Model(), seq[:12], not args.legacy_ring, args.successors)
    rec.update(schema='opentallas.mtp_rollback_mr5_isa.v1',
               scope='Reduced V4.1 exact ISA, all four packages, up to five successors squashed, corrected logits 3..11',
               rtl_qualification=False,
               elapsed_seconds=round(time.time() - start, 2),
               sequence_sha256=hashlib.sha256(args.sequence.read_bytes()).hexdigest(),
               source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [Path(__file__), Path(P.__file__), Path(A.__file__), Path(I.__file__), Path(V.__file__), Path(G.__file__)]},
               checkpoint_sha256=hashlib.sha256(V.CHECKPOINT.read_bytes()).hexdigest(),
               config_sha256=hashlib.sha256(V.CONFIG.read_bytes()).hexdigest())
    rec['exact'] = all(rec['corrected_logits_exact']) and all(rec['final_raw_kv_equal']) and all(rec['final_raw_persistent_vm_equal'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(rec), flush=True)
    return 0 if rec['exact'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

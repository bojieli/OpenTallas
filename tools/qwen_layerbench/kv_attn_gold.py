#!/usr/bin/env python3
"""QW-KVATTN (TOK.QW.KV, 10-18): the TP4 ISA golden of ONE decode position with the per-layer attention operands kept.

Runs the committed ISA golden tools/qwen_hbmacc_position_oracle_gpu.py --run (CPU) UNCHANGED in arithmetic, history-
seeded (--kv-history: every layer's K/V store = the given bins, only the recorded position is decoded), and wraps two
methods of its GpuTP machine to keep what a KV-die attention bench needs:
  run_layer  after each layer: the whole per-die VM (u32) -> L<n>_vm.npy [TP, VM_ELEMS], the K/V store -> L<n>_kv.npy
  me_kv      every KV-sourced matrix op (the score and the P.V products): its decoded ISA fields -> L<n>_me_kv.json
Nothing else is changed: the outputs the oracle writes (P<pos>/L<nn>_die<d>_x.hex, kv_at_P/, oracle.json) must equal the
fixtures of the real-prefill run (checked by kv_attn_vectors.py), which proves the history-seeded run is the same layer.

    PYTHONPATH=<torch> QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 \\
      python3 kv_attn_gold.py --src SRC --out OUT -- <oracle --run args>
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', type=Path, required=True, help='source tree holding tools/qwen_hbmacc_position_oracle_gpu.py')
    ap.add_argument('--out', type=Path, required=True)
    a, rest = ap.parse_known_args()
    if rest and rest[0] == '--':
        rest = rest[1:]
    a.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(a.src / 'tools'))
    spec = importlib.util.spec_from_file_location('oracle', a.src / 'tools/qwen_hbmacc_position_oracle_gpu.py')
    O = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(O)
    orig_run, orig_me_kv = O.GpuTP.run_layer, O.GpuTP.me_kv
    calls = {}

    def me_kv(self, vm, kv, f, dyn, pos):
        li = self._qwk_layer
        calls.setdefault(li, []).append({'fields': {k: (int(v) if isinstance(v, (int, np.integer)) else v)
                                                    for k, v in f.items() if not k.startswith('_')},
                                         'pos': int(pos)})
        return orig_me_kv(self, vm, kv, f, dyn, pos)

    def run_layer(self, li, vm, token, pos):
        self._qwk_layer = self.layer_ids[li]
        r = orig_run(self, li, vm, token, pos)
        n = self.layer_ids[li]
        np.save(a.out / f'L{n}_vm.npy', vm.cpu().numpy().view(np.uint32))
        np.save(a.out / f'L{n}_kv.npy', self.kv[li].cpu().numpy().view(np.uint32))
        (a.out / f'L{n}_me_kv.json').write_text(json.dumps({'token': int(token), 'pos': int(pos), 'calls': calls.get(n, []),
                                                            'vm_map': {k: int(v) for k, v in self.VM.items()},
                                                            'groups': int(self.GROUPS), 'W': int(self.W),
                                                            'IL': int(self.IL)}, indent=1) + '\n')
        print(f'QWK_GOLD layer {n} pos {pos} me_kv calls {len(calls.get(n, []))}', flush=True)
        return r

    O.GpuTP.run_layer, O.GpuTP.me_kv = run_layer, me_kv
    sys.argv = ['qwen_hbmacc_position_oracle_gpu.py'] + rest
    return O.main()


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""TOKSIM-S81C/MTPD: MTP draft-head golden run on the live head-return bench (codex/s81-token-integrate-1019@98a2f06da).

The draft head is the same head.weight (129280 x 5120 BF16) matvec as head.lm_head (dv_layer_fixtures.py: draft.head{i} =
V.mv(m.w["head.weight"], xn)), so it runs on the same ot_dsrom_head_bundle.  This driver re-uses the immutable built bench
and ROM images of the live-head-return run (rank-0 head.weight rows 21888..22015, weights_slice_sha256 ee9236fc...), and
feeds the GOLDEN draft normalised inputs draft.head{i}.norm.scale of the MTP layer fixture (hdc_golden_v41 chunk8, released
checkpoint).  Checker = golden draft.head{i} logits of the same 128 rows and their first-max argmax: every returned logit word
and the returned token are compared bit-exactly by the bench.  No RTL change; bench input files only.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
import numpy as np

R0 = 21888


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mtp', required=True, type=Path, help='MTP layer fixture dir')
    ap.add_argument('--base', required=True, type=Path, help='live head return run dir (exe + ROM images)')
    ap.add_argument('--work', required=True, type=Path)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    files = json.loads((a.mtp / 'files.json').read_text())
    exe = a.base / 'obj' / 'Vtb_s81_bundle_token_return'
    base_rec = json.loads((a.base / 'receipt.json').read_text())
    out = dict(schema='opentallas.toksim_s81c.mtpd_draft_head.v1', base_receipt=str(a.base / 'receipt.json'),
               base_receipt_sha256=sha(a.base / 'receipt.json'), weights_slice_sha256=base_rec['weights_slice_sha256'],
               source_hashes=base_rec['source_hashes'], exe_sha256=sha(exe), mtp_files_json_sha256=sha(a.mtp / 'files.json'),
               verilator=None, cases=[])
    for i in range(5):
        for rel in (f'ops/draft.head{i}.norm.scale.bin', f'ops/draft.head{i}.bin'):
            if rel in files and sha(a.mtp / rel) != files[rel]['sha256']:
                raise ValueError(f'fixture hash mismatch {rel}')
        x = np.fromfile(a.mtp / f'ops/draft.head{i}.norm.scale.bin', dtype='<f4').view('<u4')
        if len(x) != 5120 or np.any(x & 65535):
            raise ValueError(f'draft{i}: input must be exact BF16 [5120], got {len(x)}')
        x16 = x >> 16
        d = a.work / f'draft{i}'
        d.mkdir(exist_ok=True)
        for name, v in [('xa', x16[:4096]), ('xb', x16[4096:])]:
            (d / f'{name}.hex').write_text(''.join(''.join(f'{int(t):04x}' for t in v[j:j+16][::-1]) + '\n'
                                                   for j in range(0, len(v), 16)))
        full = np.fromfile(a.mtp / f'ops/draft.head{i}.bin', dtype='<f4')
        if len(full) != 129280:
            raise ValueError(f'draft{i}: logits length {len(full)}')
        lg = full[R0:R0 + 128]
        (d / 'logits.hex').write_text(''.join(f'{int(t):08x}\n' for t in lg.view('<u4')))
        w = int(np.argmax(lg))
        (d / 'expect.hex').write_text(f'{R0+w:08x}\n{int(lg.view("<u4")[w]):08x}\n')
        for mode, mut in [(1, 0), (1, 1)]:
            cmd = [str(exe), f'+DIR={d}', f'+OT_ROM_DIR={a.base}', f'+MODE={mode}', f'+MUT={mut}', '+DEADLINE=8416']
            r = subprocess.run(cmd, capture_output=True, text=True)
            o = r.stdout + r.stderr
            (d / f'run_mode{mode}_mut{mut}.log').write_text(o)
            m = re.search(r'Verilator (\d+\.\d+)', o)
            if m:
                out['verilator'] = m.group(1)
            want = 'FAIL' if mut else 'PASS'
            ok = r.returncode == 0 and f'LIVE_HEAD_RETURN {want}' in o
            out['cases'].append(dict(draft=i, mode=mode, mut=mut, expected=want, ok=ok,
                                     ages=[int(t) for t in re.findall(r'RETURN .* age=(\d+)', o)],
                                     summary=[l for l in o.splitlines() if l.startswith('LIVE_HEAD_RETURN')],
                                     expect_row=R0 + w, expect_bits=f'{int(lg.view("<u4")[w]):08x}',
                                     input_sha256=hashlib.sha256(x.tobytes()).hexdigest()))
            print(i, mode, mut, ok, out['cases'][-1]['summary'], flush=True)
    out['pass'] = all(c['ok'] for c in out['cases'])
    out['ages_pass_cases'] = sorted({g for c in out['cases'] if c['mut'] == 0 for g in c['ages']})
    (a.work / 'mtpd_draft_head.json').write_text(json.dumps(out, indent=1) + '\n')
    print('MTPD_DRAFT_HEAD', 'PASS' if out['pass'] else 'FAIL', out['ages_pass_cases'], flush=True)
    return 0 if out['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""hbm-system 2026-10-08: per-PC KV stream of the r25 stream service (ot_hbm_svc_core KVS = 1), one stack, against
the timed HBM3E model (rtl/test/hbm_accel/tb_hbm_svc_kvs.sv, Verilator).  Exactness: every (PC, j) sector exactly
once with the controller's data at the dskv_wb / stream-PC address; negative +mut=1 (lane 5 dropped) must FAIL.
Bandwidth: descriptor launch -> kvs_done, bytes delivered / time against the stack peak 1.0 TB/s.

    python3 tools/hbm_svc_kvs_bench.py --work DIR --out RECORD.json
"""
import argparse, hashlib, json, os, re, statistics, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
SRC = ['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv', 'rtl/hbm_accel/service/ot_hbm_kport_map.sv',
       'physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',
       'rtl/test/hbm_accel/tb_hbm_svc_kvs.sv']
CASES = {17: 'DS window rows (17 sectors a PC a layer, latency-bound)', 184: 'DS index keys at 1M (~181 sectors a PC)',
         1024: 'Qwen 8K KV sweep (4.19 MB/die/layer = 1,024 sectors a PC)', 2048: 'steady stream (2,048 sectors a PC)'}
PHASES = [0, 1300, 2700, 4100, 5500, 6900]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--work', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); a.work.mkdir(parents=True, exist_ok=True)
    obj = a.work / 'obj'
    subprocess.run([VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '8', '-O2', '--top-module',
                    'tb_hbm_svc_kvs', '--Mdir', str(obj)] + [str(ROOT / s) for s in SRC], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    exe = str(obj / 'Vtb_hbm_svc_kvs')

    def go(job):
        n, ph, mut = job
        out = subprocess.run([exe, f'+nsec={n}', '+reps=2', f'+phase_ns={ph}', f'+mut={mut}'], capture_output=True,
                             text=True, timeout=1800).stdout
        rows = [dict(t_ns=float(m[1]), frac=float(m[2])) for m in re.finditer(r't_ns=([\d.]+) bytes=\d+ tbs=[\d.]+ frac_peak=([\d.]+)', out)]
        v = re.search(r'KVS_BENCH errors=(\d+) (\w+)', out)
        return dict(nsec=n, phase_ns=ph, mut=mut, runs=rows, verdict=v[2] if v else 'FAIL')
    jobs = [(n, ph, 0) for n in CASES for ph in PHASES] + [(184, 0, 1)]
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(go, jobs))
    summ = {}
    for n, what in CASES.items():
        fr = [r['frac'] for x in res if x['nsec'] == n and not x['mut'] for r in x['runs']]
        ts = [r['t_ns'] for x in res if x['nsec'] == n and not x['mut'] for r in x['runs']]
        summ[str(n)] = dict(what=what, frac_peak=dict(min=min(fr), mean=round(statistics.mean(fr), 4), max=max(fr)),
                            t_ns=dict(min=min(ts), mean=round(statistics.mean(ts), 1), max=max(ts)), runs=len(fr))
    pos_ok = all(x['verdict'] == 'PASS' for x in res if not x['mut'])
    neg_ok = all(x['verdict'] == 'FAIL' for x in res if x['mut'])
    rec = dict(schema='opentallas.hbm_system.svc_kvs.v1',
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SRC + ['tools/hbm_svc_kvs_bench.py']},
               simulator='Verilator 5.050', model='ot_hdc_v41x_idx_hbm NPC 32 REFPB 3 (REFpb refresh-aware), 1.0 TB/s a stack',
               params=dict(KNO=15, XST=2, E_ST=11, ck_ps=1024), summary=summ, verdict='PASS' if pos_ok and neg_ok else 'FAIL',
               negative=[x for x in res if x['mut']], cases=res,
               note='end-to-end: descriptor launch on the e link to kvs_done (includes the e-link CDC + 13 wire stages and '
                    'first access); the stack peak is 32 sectors per 1.024 ns')
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(rec['verdict'], json.dumps({k: v['frac_peak'] for k, v in summ.items()}))
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())

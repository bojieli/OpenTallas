#!/usr/bin/env python3
"""Gate of the STATIC stage WFC kit dsfd_wfc_stg_s (rtl/dsrom_sys/mtp/dsfd_wfc_stg_static.sv; die name dsfd_wfc_stg under
+define+DSFD_WFC_STG_STATIC_DIE): no ready, grant or credit on any production path (owner rule 2026-10-14T18:59).

Bench rtl/dsrom_sys/mtp/tb/tb_wfc_stg_static.sv (static calendar upstream, static VM endpoint behaviour, stage core,
exact downstream checker, t_ft must stay 0).  Cases:
  equiv_<shape>   EXACT EQUIVALENCE with the grant-form kit of record: the closed cluster dsfd_wfc_stg_cl runs the
                  reference stage bench (tools/dsrom_wfc_cl_bench.py shape <shape>, its own random link / VM stalls) and
                  dumps its job stream and every outbound flit; the static kit replays the same jobs on a static calendar
                  and its outbound flit stream (513 b each: headers incl. idx / val, all words, last bits) must be
                  byte-identical.
  p<P>            production shape at calendar period P (all four 3:4 phase offsets; 175 = measured minimum)
  txd_m3_p<P>     the TX offset with 3 edges removed still passes on every phase (margin of the derived TXD)
  neg_*           must FAIL: six RTL mutants, an out-of-window position (EXPECT_FAULT), a calendar faster than the kit
                  (P 174: a row rewritten one edge before its outbound read -> fault; P 150: written while the core
                  runs -> fault)

  python3 tools/dsrom_wfc_static_bench.py --out DIR [--case NAME,..]  -> DIR/summary.json, WFC_STATIC_GATE PASS|FAIL
  python3 tools/dsrom_wfc_static_bench.py --out DIR --case neg_swap --raw-negative   -> exit 1 when the mutant FAILS
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
import dsrom_mtp_rom_bench as B
import dsrom_wfc_kit_bench as K
import dsrom_wfc_cl_bench as C

ROOT = Path(__file__).resolve().parents[1]
TB = 'rtl/dsrom_sys/mtp/tb/tb_wfc_stg_static.sv'
SRCS = ['rtl/dsrom_sys/mtp/dsfd_wfc_stg_static.sv', 'rtl/dsrom_sys/mtp/dsfd_wfc_static_cdc.sv',
        'rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv', 'rtl/dsrom_sys/mtp/dsfd_wfc_stg_cl.sv',
        'rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv',
        'rtl/lib/ot_reset_sync.sv', 'rtl/lib/ot_async_fifo.sv',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
        'physical/s81_ph_views/mtp/macros/ot_sram_1r1w_512x64_m4_r2c2/ot_sram_1r1w_512x64_m4_r2c2.v']
HOP_EP = SRCS[4:8]
CASES = {}
for sh in ('stg_vmnat', 'stg_r1', 'stg_r2_slowvm'):
    CASES[f'equiv_{sh}'] = dict(kind='equiv', shape=sh, expect='pass')
for p in (175, 176, 177, 178, 201, 202, 203, 204):
    CASES[f'p{p}'] = dict(kind='static', params=dict(P=p), expect='pass')
for p in (201, 202, 203, 204):
    CASES[f'txd_m3_p{p}'] = dict(kind='static', params=dict(P=p), defines=['OT_WFCSS_TXD_ADJ=3'], expect='pass')
for m in ('SWAP', 'TXEARLY', 'PH1', 'UPOS', 'GAP0', 'RLAT'):
    CASES[f'neg_{m.lower()}'] = dict(kind='static', params=dict(P=201), defines=[f'OT_WFCSS_MUT_{m}'], expect='fail')
CASES['neg_badpos'] = dict(kind='static', params=dict(P=201, BADPOS=5, EXPECT_FAULT=1), expect='fault')
CASES['neg_war_cal'] = dict(kind='static', params=dict(P=174, EXPECT_FAULT=1), expect='fault')      # write before its row's read
CASES['neg_run_cal'] = dict(kind='static', params=dict(P=150, EXPECT_FAULT=1), expect='fault')      # write while the core runs

CASES['user865'] = dict(kind='static', params=dict(P=201, USER_BASE=865, NUSR=1), expect='pass')
CASES['neg_user866'] = dict(kind='static', params=dict(P=201, USER_BASE=866, NUSR=1, EXPECT_FAULT=1), expect='fault')

# Test the exact parameter-free hard child ABI as well as the configurable component.
for name, case in list(CASES.items()):
    if case['kind'] == 'static':
        CASES['hard_' + name] = dict(case, defines=case.get('defines', []) + ['DSFD_WFC_SS_HARD'])

REF_DUMP = '''    integer rd_fo, rd_i;
    initial rd_fo = $fopen("ref_out.hex", "w");
    always @(posedge fclk) if (rst_n && lo_v && lo_r) $fwrite(rd_fo, "%h\\n", lo_d);
    final begin
        $fclose(rd_fo); rd_fo = $fopen("jobs.txt", "w");
        for (rd_i = 0; rd_i < jobs_in; rd_i = rd_i + 1) $fwrite(rd_fo, "%h %h %h\\n", job_u[rd_i], job_p[rd_i], job_t[rd_i]);
        $fclose(rd_fo);
    end
'''


def sh(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def run_static(d, params, defines, extra=()):
    d.mkdir(parents=True, exist_ok=True)
    cmd = ['iverilog', '-g2012', '-s', 'tb_wfc_stg_static', '-o', str(d / 'sim.vvp')] + [f'-D{x}' for x in defines] + \
          list(extra) + [f'-Ptb_wfc_stg_static.{k}={v}' for k, v in params.items()] + [str(ROOT / s) for s in SRCS + [TB]]
    b = sh(cmd); (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode or re.search(r'Port .* expects .* got', b.stderr):
        return 'build_error', b.stderr[-800:]
    r = sh(['vvp', '-n', str(d / 'sim.vvp')], cwd=d); (d / 'run.log').write_text(r.stdout + r.stderr)
    m = re.search(r'^WFC_SS (PASS|FAIL|FAULT_AS_EXPECTED).*$', r.stdout, re.M)
    if not m:
        return 'nolog', r.stdout[-400:]
    return {'PASS': 'pass', 'FAIL': 'fail', 'FAULT_AS_EXPECTED': 'fault'}[m.group(1)], m.group(0)


def run_ref(d, shape):
    """the grant-form cluster on the reference stage bench, dumping its jobs and outbound flits"""
    spec = B.cases()[shape]
    tb, body = C.cl_tb('cl')
    i = body.rindex('endmodule')
    body = body[:i] + REF_DUMP + body[i:]
    d.mkdir(parents=True, exist_ok=True); (d / 'tb.sv').write_text(body)
    srcs = [str(ROOT / s) for s in list(B.COMMON) + K.EXTRA + [C.CL, C.MAC] + HOP_EP] + [str(d / 'tb.sv')]
    cmd = ['iverilog', '-g2012', '-s', tb, '-o', str(d / 'sim.vvp')] + [f'-D{x}' for x in spec.get('defines', [])] + \
          [f'-P{tb}.{k}={v}' for k, v in spec.get('params', {}).items()] + srcs
    b = sh(cmd); (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode or re.search(r'Port .* expects .* got', b.stderr):
        return 'build_error', b.stderr[-800:]
    r = sh(['vvp', '-n', str(d / 'sim.vvp')], cwd=d); (d / 'run.log').write_text(r.stdout + r.stderr)
    m = re.search(r'^MTP_STG (PASS|FAIL).*$', r.stdout, re.M)
    return ('pass' if m and m.group(1) == 'PASS' else 'fail'), (m.group(0) if m else r.stdout[-400:])


def run(name, out):
    c = CASES[name]; d = out / name
    if c['kind'] == 'equiv':
        got, res = run_ref(d / 'ref', c['shape'])
        if got != 'pass':
            return dict(case=name, expect=c['expect'], got='ref_' + got, verdict='UNEXPECTED', result=res)
        njob = len((d / 'ref' / 'jobs.txt').read_text().split('\n')) - 1
        got, res2 = run_static(d / 'static', dict(P=201), ['DUMP', f'JOBS="{d / "ref" / "jobs.txt"}"'])
        if got == 'pass':
            a = (d / 'ref' / 'ref_out.hex').read_text(); b_ = (d / 'static' / 'out.hex').read_text()
            nfl = len(a.split())
            if a != b_:
                got = 'fail_stream_differs'
            res2 = f'{res2} | reference: {res} | outbound flits identical: {a == b_} ({nfl} flits, {njob} jobs)'
        return dict(case=name, expect=c['expect'], got=got, verdict='OK' if got == c['expect'] else 'UNEXPECTED', result=res2)
    got, res = run_static(d, c.get('params', {}), c.get('defines', []))
    return dict(case=name, expect=c['expect'], got=got, verdict='OK' if got == c['expect'] else 'UNEXPECTED', result=res,
                params=c.get('params', {}), defines=c.get('defines', []))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--out', type=Path, required=True); p.add_argument('--case'); p.add_argument('--jobs', type=int, default=8)
    p.add_argument('--raw-negative', action='store_true', help='one expected-FAIL case: exit 1 when it fails as required')
    a = p.parse_args(); a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    names = a.case.split(',') if a.case else list(CASES)
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda n: run(n, a.out), names))
    ok = all(r['verdict'] == 'OK' for r in recs)
    if a.raw_negative:
        assert len(recs) == 1 and recs[0]['expect'] != 'pass', 'raw-negative needs one negative case'
        print(f"{recs[0]['case']}: {recs[0]['result']}")
        if recs[0]['verdict'] == 'OK':
            print('WFC_STATIC_NEGATIVE FAIL_AS_REQUIRED ' + recs[0]['case']); return 1
        print('WFC_STATIC_NEGATIVE UNEXPECTED_PASS ' + recs[0]['case']); return 0
    (a.out / 'summary.json').write_text(json.dumps(dict(all_ok=ok, cases=recs), indent=1) + '\n')
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:22s} expect={r['expect']:5s} {str(r['result'])[:230]}")
    print(f"WFC_STATIC_GATE {'PASS' if ok else 'FAIL'} cases={len(recs)} "
          f"positives={sum(r['expect'] == 'pass' and r['verdict'] == 'OK' for r in recs)} "
          f"negatives={sum(r['expect'] != 'pass' and r['verdict'] == 'OK' for r in recs)}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

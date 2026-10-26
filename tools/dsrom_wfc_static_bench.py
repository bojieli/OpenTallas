#!/usr/bin/env python3
"""Gate of the STATIC die form of the WFC stage cluster (dsfd_wfc_stg_cl.sv under +define+DSFD_WFC_STG_STATIC: no
t_lir / f_lor grant pins; static RX buffer written on every calendar arrival; static TX buffer released on the compiler's
reserved edges = job's last RX arrival + TX_OFF, one flit per edge; lost arrival / underflow / overlap = sticky fault).

Production shape = the PRICED kit stage bench (tools/dsrom_wfc_cl_bench.py / dsrom_wfc_kit_bench.py, case stg_vmnat:
static VM, 40 jobs, RXWORDS 41, XWORDS 46) with the static cluster as the device under every content check of the bench
(RX words in the VM at core start, every outbound word, token / user / pos, faults), the handshake generator replaced by
a STATIC CALENDAR (job j's 42 flits on consecutive edges from CAL_T0 + j * P, no ready consulted) and the collective
taking every outbound flit (lo_r = 1).  Extra static checks: an outbound message must leave on consecutive edges, and
the RX-last -> TX-header offset is recorded (it must equal TX_OFF + 2 for every job: a compiler-known constant).
Negatives (must FAIL): DSFD_WFC_STG_STATIC_MUT (message leaves on alternate edges), TX_OFF 256 (scheduled slot
before the flit exists: underflow fault), calendar period 250 (faster than the stage: backlog -> underflow fault).

  python3 tools/dsrom_wfc_static_bench.py --out DIR [--case NAME] [--cal-p P --tx-off O]  -> WFC_STATIC_GATE PASS|FAIL
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
import dsrom_mtp_rom_bench as B
import dsrom_wfc_kit_bench as K
import dsrom_wfc_cl_bench as C

ROOT = Path(__file__).resolve().parents[1]
# the cluster's stage hand-off endpoint (dsfd_wfc_hop_ep, 10-14) instantiates the shared slab endpoint
HOP_EP = ['rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv',
          'rtl/lib/ot_reset_sync.sv', 'rtl/lib/ot_async_fifo.sv']
# name -> (base case, defines, expect, calendar period P, TX_OFF); production calendar P = 300 (the grant form's own
# steady period: 12,023 edges / 40 jobs at the same shape), TX_OFF 272 (measured minimum 264)
CASES = {'static_vmnat': ('stg_vmnat', [], 'pass', 300, 272),
         'static_vmnat_slow_cal': ('stg_vmnat', [], 'pass', 600, 272),
         'static_neg_alt_drain': ('stg_vmnat', ['DSFD_WFC_STG_STATIC_MUT'], 'fail', 300, 272),
         'static_neg_early_tx': ('stg_vmnat', [], 'fail', 300, 256),
         'static_neg_fast_cal': ('stg_vmnat', [], 'fail', 250, 272)}


GEN_OLD_HEAD = '        if (li_v && li_r) li_v <= 1\'b0;\n        if ((!li_v || li_r) && rnd[3:0] != 0) begin\n'
STATIC_GEN = '''    // STATIC CALENDAR (the compiler's collective RX slots): job j's 1 + RXW flits arrive on consecutive edges
    // starting at edge CAL_T0 + j * CAL_P; no ready is consulted (the static form has none).
    integer cal_e = 0, cal_j = 0, cal_k = -1, cal_last [0:1023];
    always @(posedge fclk) if (rst_n) begin
        cal_e = cal_e + 1; li_v <= 1'b0;
        if (cal_k < 0 && cal_j < NJOB && cal_e >= CAL_T0 + cal_j * CAL_P) begin
            gu = cal_j % NUSR; gp = nxt[gu]; gt = mix(gu, gp) % 129280; nxt[gu] = nxt[gu] + 1;
            job_u[cal_j] = gu; job_p[cal_j] = gp; job_t[cal_j] = gt; jobs_in = cal_j + 1;
            li_v <= 1'b1; li_d <= 0;
            li_d[7:0] <= 8'd1; li_d[15:8] <= 8'd0; li_d[HDR_TYPE +: 4] <= 4'd1; li_d[HDR_LEN +: 8] <= RXW;
            li_d[HDR_USER +: 8] <= gu; li_d[HDR_POS +: NW] <= gp; li_d[HDR_IDX +: NW] <= gt ^ 7;
            li_d[HDR_VAL +: 32] <= 32'h3f000000 + gp; li_d[HDR_TOK +: NW] <= gt;
            cal_k = 0;
        end else if (cal_k >= 0) begin
            li_v <= 1'b1; li_d <= {cal_k == RXW - 1, word(1, 0, job_p[cal_j], job_t[cal_j], cal_k)};
            cal_k = cal_k + 1;
            if (cal_k == RXW) begin cal_k = -1; cal_last[cal_j] = cal_e; cal_j = cal_j + 1; end
        end
    end
    // static TX checks: an outbound message leaves on consecutive edges (contiguous reserved TX slots); latency from
    // the job's last inbound arrival edge to its outbound header edge is recorded (min / max = the compiler's offset)
    integer tx_in = 0, tx_lat_min = 1000000, tx_lat_max = -1, tx_j = 0, ofe = 0;
    always @(posedge fclk) if (rst_n) begin
        ofe = ofe + 1;
        if (tx_in > 0 && !lo_v) begin $display("MTP_STG FAIL: static TX gap inside an outbound message (word %0d)", tx_in); $finish; end
        if (lo_v) begin
            if (tx_in == 0) begin
                if (cal_last[tx_j] > 0) begin
                    if (ofe - cal_last[tx_j] < tx_lat_min) tx_lat_min = ofe - cal_last[tx_j];
                    if (ofe - cal_last[tx_j] > tx_lat_max) tx_lat_max = ofe - cal_last[tx_j];
                end
                tx_j = tx_j + 1;
            end
            tx_in = (tx_in == TXW) ? 0 : tx_in + 1;
        end
    end
    integer ci; initial #1 for (ci = 0; ci < 1024; ci = ci + 1) cal_last[ci] = 0;
'''


def static_tb(cal_p, tx_off, cal_t0=40):
    tb, body = C.cl_tb('cl')
    assert body.count('dsfd_wfc_stg_cl u_kit (') == 1
    body = body.replace('dsfd_wfc_stg_cl u_kit (', f'dsfd_wfc_stg_cl #(.TX_OFF({tx_off})) u_kit (')
    for a_, b_ in (('.t_lir(li_r), ', ''), ('.f_lor(lo_r),', '')):
        assert body.count(a_) == 1, a_
        body = body.replace(a_, b_)
    body = body.replace("lo_r <= rnd[2:0] != 0;", "lo_r <= 1'b1;   // static collective: every outbound flit taken")
    # replace the handshake generator by the static calendar (keep the old block disabled)
    i0 = body.index('    always @(posedge fclk) if (rst_n) begin\n        rnd = mix(SEED * 3, cyc);')
    i1 = body.index('    // ---------------------------------------------------------------- slow side')
    body = body[:i0] + STATIC_GEN + body[i1:]
    body = body.replace('wire li_r;', "wire li_r = 1'b1;   // no inbound ready in the static form (measurement shim only)")
    body = body.replace('parameter integer SEED = 1,', f'parameter integer CAL_P = {cal_p}, CAL_T0 = {cal_t0}, SEED = 1,')
    body = body.replace('$display("MTP_STG_CYC', '$display("STATIC_TX lat_min=%0d lat_max=%0d jobs=%0d cal_p=%0d", tx_lat_min, tx_lat_max, tx_j, CAL_P);\n        $display("MTP_STG_CYC')
    return tb, body


def run(name, out, cal_p=None, tx_off=None):
    base, defs, expect, cp, co = CASES[name]
    cal_p = cal_p or cp; tx_off = tx_off or co
    spec = B.cases()[base]
    tb, body = static_tb(cal_p, tx_off)
    d = out / f'{name}_p{cal_p}_o{tx_off}'; d.mkdir(parents=True, exist_ok=True)
    (d / 'tb.sv').write_text(body)
    srcs = [str(ROOT / s) for s in list(B.COMMON) + K.EXTRA + [C.CL, C.MAC] + HOP_EP] + [str(d / 'tb.sv')]
    cmd = ['iverilog', '-g2012', '-s', tb, '-o', str(d / 'sim.vvp'), '-DDSFD_WFC_STG_STATIC'] + \
          [f'-D{x}' for x in list(spec.get('defines', [])) + defs] + \
          [f'-P{tb}.{k}={v}' for k, v in spec.get('params', {}).items()] + srcs
    b = subprocess.run(cmd, capture_output=True, text=True); (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        return dict(case=name, expect=expect, verdict='BUILD_ERROR', log=b.stderr[-1500:])
    r = subprocess.run(['vvp', '-n', str(d / 'sim.vvp')], capture_output=True, text=True, cwd=d)
    (d / 'run.log').write_text(r.stdout + r.stderr)
    m = re.search(r'^MTP_STG (PASS|FAIL).*$', r.stdout, re.M) or re.search(r'^LINK_REG (FAIL).*$', r.stdout, re.M) \
        or re.search(r'^(FAIL): VM write address.*$', r.stdout, re.M)
    tx = re.search(r'^STATIC_TX .*$', r.stdout, re.M)
    got = m.group(1).lower() if m else 'nolog'
    if got == 'pass':
        t = re.search(r'lat_min=(\d+) lat_max=(\d+)', tx.group(0)) if tx else None
        if not t or int(t.group(1)) != tx_off + 2 or int(t.group(2)) != tx_off + 2:
            got = 'fail_static_offset'      # the TX offset must be the compiler constant for every job
    return dict(case=name, base=base, defines=list(spec.get('defines', [])) + defs, expect=expect, got=got,
                verdict='OK' if got == expect else 'UNEXPECTED', result=(m.group(0) if m else r.stdout[-400:]),
                static_tx=tx.group(0) if tx else None, cal_p=cal_p, tx_off=tx_off)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--out', type=Path, required=True); p.add_argument('--case'); p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--cal-p', type=int, default=None, help='calendar period: edges between job message starts')
    p.add_argument('--tx-off', type=int, default=None, help='compiler TX offset (TX_OFF)')
    a = p.parse_args(); a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    names = a.case.split(',') if a.case else list(CASES)
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda n: run(n, a.out, a.cal_p, a.tx_off), names))
    ok = all(r['verdict'] == 'OK' for r in recs)
    (a.out / 'summary.json').write_text(json.dumps(dict(all_ok=ok, cases=recs), indent=1) + '\n')
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:22s} expect={r['expect']} {str(r.get('result', r.get('log', '')))[:170]}"
              + (f" | {r['static_tx']}" if r.get('static_tx') else ''))
    print(f"WFC_STATIC_GATE {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

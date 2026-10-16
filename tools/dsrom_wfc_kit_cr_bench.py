#!/usr/bin/env python3
"""Exact gate of the credit WFC kit dsfd_wfc_cr (rtl/dsrom_sys/mtp/dsfd_wfc_kit_cr.sv) across the die's real hub stages
(ds-1010 lat-audit, 2026-10-10).

The kit benches (tools/dsrom_wfc_kit_bench.py) wire the kit's die ports straight to the bench's VM / link / core models,
so they never see the S81 hub stations.  Here every die port crosses the stage count the generator really builds for the
layer1 x1b+rgap die (tools/s81/hub_stage_count.py): link in / out S_LI / S_LO (9 / 10 -> 10 each way), VM S_VM (13),
core start / done S_CO / S_CI (10 / 11).  Credit channels use ot_link_credit_tb_chan (far-side credit endpoint + LAT
link flops each way); the valid-only ports (VM read response, write ACK, core start / done) cross plain register relays.
The bench's VM model answers each read FROM its request (address -> vmem word, in order, 2..5 slow cycles later) and the
link / core models are the kit benches' own, so every content check is unchanged.

Cases: positives at the real stages, at the minimum (2) and at the real + 4; negatives
  neg_skid_*   the plain kit (valid / ready 2-entry skids) with valid / data relayed forward and ready relayed back over
               the same real stages: must FAIL (a ready seen late re-presents or overruns beats);
  neg_over     the far VM read landing 4 deep while the kit holds 32 credits: must FAIL (landing overflow fault).

  python3 tools/dsrom_wfc_kit_cr_bench.py --out DIR [--case NAME]   -> DIR/summary.json, prints WFC_KIT_CR_GATE PASS|FAIL
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dsrom_mtp_rom_bench as B
import dsrom_wfc_kit_bench as K

ROOT = Path(__file__).resolve().parents[1]
CR = 'rtl/dsrom_sys/mtp/dsfd_wfc_kit_cr.sv'
LINK = 'rtl/common/ot_link_credit.sv'
# fe-push-ds-1010 2026-10-10: harness 'crp' = dsfd_wfc_cr2 (the routed credit-port tile dsfd_wfc_crp + the kit): SRAM
# link-in landing, DFREE credit txs, ot_rst_relay per domain
CRP = ['rtl/dsrom_sys/mtp/dsfd_wfc_crp.sv', 'rtl/lib/ot_rst_relay.sv', 'rtl/link/ot_fifo_sram_fwft.sv',
       'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']

PARAMS = '''    parameter integer S_LI = 10, S_LO = 10, S_VM = 13, S_CO = 10, S_CI = 11;   // ds-1010: real hub stages (layer1 x1b+rgap)
    // s0 step watchdog scale.  At the real stages S0 runs 1.46x the cycles of the 2-stage run (s0_hash_u3 129,439 vs
    // 88,933) and one speculative step outgrows the unscaled 3L + T_DRAFT + 1500 NUSR bound: x2 PASSes exact,
    // x10 identical (not a hang).  Draft flits reach the WFC 745 vs 179 cycles after the last draft head (throughput
    // cost of the stationed die, reported to mtp-lead).
    parameter integer WDOG_MULT = 1;
'''
RELAY = '''
module wfc_cr_relay #(parameter integer W = 1, parameter integer N = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] p [0:N-1]; integer i;
    initial for (i = 0; i < N; i = i + 1) p[i] = '0;
    always @(posedge clk) begin p[0] <= d; for (i = 1; i < N; i = i + 1) p[i] <= p[i-1]; end
    assign q = p[N-1];
endmodule
'''
# valid-only ports: VM read response + write ACK in from the VM (S_VM), core start out (S_CO) / done in (S_CI)
VONLY = '''    wire c_swa; wire [FLIT:0] c_srq; wire [USER_W+2*NW:0] c_ks; wire [NW+32:0] c_kd;
    wfc_cr_relay #(.W(1), .N(S_VM)) r_swa (.clk(sclk), .d(swa), .q(c_swa));
    wfc_cr_relay #(.W(FLIT + 1), .N(S_VM)) r_srq (.clk(sclk), .d(srq), .q(c_srq));
    wfc_cr_relay #(.W(USER_W + 2*NW + 1), .N(S_CO)) r_ks (.clk(sclk), .d(c_ks), .q(ks));
    wfc_cr_relay #(.W(NW + 33), .N(S_CI)) r_kd (.clk(sclk), .d(kd), .q(c_kd));
'''
CR_KIT = VONLY + '''    wire [3:0] k_ft; wire c_liv, c_lic, c_lov, c_loc, c_swv, c_swc, c_srv, c_src, h_f1, h_f2, h_f3;
    wire [FLIT:0] c_lid, c_lod; wire [VWA+FLIT-1:0] c_swd; wire [VWA-1:0] c_srd;
    ot_link_credit_tb_chan #(.W(FLIT + 1), .DIR(0), .DEPTH(24), .LAT(S_LI)) h_li (.clk(fclk), .rst_n(rst_n),
        .t_valid(li_v), .t_ready(li_r), .t_data(li_d), .r_valid(), .r_ready(1'b0), .r_data(), .fault(),
        .d_valid(c_liv), .d_data(c_lid), .d_credit(c_lic), .u_valid(1'b0), .u_data({(FLIT + 1){1'b0}}), .u_credit());
    ot_link_credit_tb_chan #(.W(FLIT + 1), .DIR(1), .DEPTH(24), .LAT(S_LO)) h_lo (.clk(fclk), .rst_n(rst_n),
        .t_valid(1'b0), .t_ready(), .t_data({(FLIT + 1){1'b0}}), .r_valid(lo_v), .r_ready(lo_r), .r_data(lo_d), .fault(h_f1),
        .d_valid(), .d_data(), .d_credit(1'b0), .u_valid(c_lov), .u_data(c_lod), .u_credit(c_loc));
    ot_link_credit_tb_chan #(.W(VWA + FLIT), .DIR(1), .DEPTH(32), .LAT(S_VM)) h_sw (.clk(sclk), .rst_n(rst_n),
        .t_valid(1'b0), .t_ready(), .t_data({(VWA + FLIT){1'b0}}), .r_valid(swv), .r_ready(swr), .r_data(swd), .fault(h_f2),
        .d_valid(), .d_data(), .d_credit(1'b0), .u_valid(c_swv), .u_data(c_swd), .u_credit(c_swc));
`ifdef WFC_CR_MUT_OVER
    localparam integer SR_LAND = 4;          // negative: the VM's read landing is shallower than the kit's credits
`else
    localparam integer SR_LAND = 32;
`endif
    ot_link_credit_tb_chan #(.W(VWA), .DIR(1), .DEPTH(SR_LAND), .LAT(S_VM)) h_sr (.clk(sclk), .rst_n(rst_n),
        .t_valid(1'b0), .t_ready(), .t_data({VWA{1'b0}}), .r_valid(srv), .r_ready(srr), .r_data(srd), .fault(h_f3),
        .d_valid(), .d_data(), .d_credit(1'b0), .u_valid(c_srv), .u_data(c_srd), .u_credit(c_src));
    dsfd_wfc_cr #(.SOURCE(SRCK)KITPARAMS) u_kit (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(c_liv), .f_lid(c_lid), .t_lic(c_lic), .t_lov(c_lov), .t_lod(c_lod), .f_loc(c_loc),
        .t_swv(c_swv), .t_swd(c_swd), .f_swc(c_swc), .f_swa(c_swa), .t_srv(c_srv), .t_srd(c_srd), .f_src(c_src), .f_srq(c_srq),
        .t_ks(c_ks), .f_kd(c_kd), .f_c(CFGW), .t_tok(KTOK), .t_cfg(KCFG), .t_ft(k_ft));
    // a far landing that overflows is a fault of the die (the beat is lost): fail as a link / vmx fault
'''
SKID_KIT = VONLY + '''    wire [3:0] k_ft; wire c_liv, c_lir, c_lov, c_lor, c_swv, c_swr, c_srv, c_srr;
    wire [FLIT:0] c_lid, c_lod; wire [VWA+FLIT-1:0] c_swd; wire [VWA-1:0] c_srd;
    // negative: the plain kit's valid / ready ports with valid / data relayed forward and ready relayed back
    wfc_cr_relay #(.W(FLIT + 2), .N(S_LI)) r_li (.clk(fclk), .d({li_v, li_d}), .q({c_liv, c_lid}));
    wfc_cr_relay #(.W(1), .N(S_LI)) r_lir (.clk(fclk), .d(c_lir), .q(li_r));
    wfc_cr_relay #(.W(FLIT + 2), .N(S_LO)) r_lo (.clk(fclk), .d({c_lov, c_lod}), .q({lo_v, lo_d}));
    wfc_cr_relay #(.W(1), .N(S_LO)) r_lor (.clk(fclk), .d(lo_r), .q(c_lor));
    wfc_cr_relay #(.W(VWA + FLIT + 1), .N(S_VM)) r_sw (.clk(sclk), .d({c_swv, c_swd}), .q({swv, swd}));
    wfc_cr_relay #(.W(1), .N(S_VM)) r_swr (.clk(sclk), .d(swr), .q(c_swr));
    wfc_cr_relay #(.W(VWA + 1), .N(S_VM)) r_sr (.clk(sclk), .d({c_srv, c_srd}), .q({srv, srd}));
    wfc_cr_relay #(.W(1), .N(S_VM)) r_srr (.clk(sclk), .d(srr), .q(c_srr));
    wire h_f1 = 1'b0, h_f2 = 1'b0, h_f3 = 1'b0;
    KITMOD u_kit (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(c_liv), .f_lid(c_lid), .t_lir(c_lir), .t_lov(c_lov), .t_lod(c_lod), .f_lor(c_lor),
        .t_swv(c_swv), .t_swd(c_swd), .f_swr(c_swr), .f_swa(c_swa), .t_srv(c_srv), .t_srd(c_srd), .f_srr(c_srr), .f_srq(c_srq),
        .t_ks(c_ks), .f_kd(c_kd)SKIDSRC, .t_ft(k_ft));
'''
STG_TAIL = '''    assign proto_fault = k_ft[3]; assign lnk_ft = k_ft[2] | h_f1; assign vmx_ft = k_ft[0] | h_f2 | h_f3;
    assign tok_valid = KPATH.tok_valid; assign tok_user = KPATH.tok_user; assign tok_pos = KPATH.tok_pos;
    assign tok_id = KPATH.tok_id;
'''
SRC_TAIL = '''    assign {proto_fault, lnk_ft, tok_ft, vmx_ft} = k_ft | {1'b0, h_f1, 1'b0, h_f2 | h_f3};
'''
REAL = dict(S_LI=10, S_LO=10, S_VM=13, S_CO=10, S_CI=11)
SHORT = dict(S_LI=2, S_LO=2, S_VM=2, S_CO=2, S_CI=2)
LONG = {k: v + 4 for k, v in REAL.items()}
CASES = {   # name -> (kit bench base case, harness, stage params, extra defines, expect)
    'cr_stg_r1': ('stg_r1', 'cr', REAL, [], 'pass'), 'cr_stg_vmnat': ('stg_vmnat', 'cr', REAL, [], 'pass'),
    'cr_stg_r2_slowvm': ('stg_r2_slowvm', 'cr', REAL, [], 'pass'), 'cr_stg_lag1': ('stg_lag1', 'cr', REAL, [], 'pass'),
    'cr_stg_r1_short': ('stg_r1', 'cr', SHORT, [], 'pass'), 'cr_stg_r1_long': ('stg_r1', 'cr', LONG, [], 'pass'),
    'cr_s0_tr_forced': ('s0_tr_forced', 'cr', REAL, [], 'pass'), 'cr_s0_hash_u3': ('s0_hash_u3', 'cr', dict(REAL, WDOG_MULT=2), [], 'pass'),
    'cr_s0_hash_u3_short': ('s0_hash_u3', 'cr', SHORT, [], 'pass'),

    'neg_skid_stg_r1': ('stg_r1', 'skid', REAL, [], 'fail'), 'neg_skid_s0_tr_forced': ('s0_tr_forced', 'skid', REAL, [], 'fail'),
    'neg_over_stg_r1': ('stg_r1', 'cr', REAL, ['WFC_CR_MUT_OVER'], 'fail'),
    # fe-push-ds-1010: the credit-port tile (dsfd_wfc_crp) composition dsfd_wfc_cr2
    'crp_stg_r1': ('stg_r1', 'crp', REAL, [], 'pass'), 'crp_stg_vmnat': ('stg_vmnat', 'crp', REAL, [], 'pass'),
    'crp_stg_r2_slowvm': ('stg_r2_slowvm', 'crp', REAL, [], 'pass'), 'crp_stg_lag1': ('stg_lag1', 'crp', REAL, [], 'pass'),
    'crp_stg_r1_short': ('stg_r1', 'crp', SHORT, [], 'pass'), 'crp_stg_r1_long': ('stg_r1', 'crp', LONG, [], 'pass'),
    'crp_s0_tr_forced': ('s0_tr_forced', 'crp', REAL, [], 'pass'),
    'crp_s0_hash_u3': ('s0_hash_u3', 'crp', dict(REAL, WDOG_MULT=2), [], 'pass'),
    'neg_crp_land_stg_r1': ('stg_r1', 'crp', REAL, ['WFC_CRP_MUT_LAND'], 'fail'),
    'neg_crp_dfree_stg_r1': ('stg_r1', 'crp', REAL, ['OT_LINK_DFREE_MUT'], 'fail'),
    'neg_crp_over_stg_r1': ('stg_r1', 'crp', REAL, ['WFC_CR_MUT_OVER'], 'fail'),
}
CRP_CASES = [k for k, v in CASES.items() if v[1] == 'crp']


OSKID_K = 0   # --oskid (mtp-wfc 2026-10-10): dsfd_wfc_crp with the registered kit-side skids


def cr_tb(base, harness):
    stage = K.CASES[base][1]
    tb, body = K.kit_tb(stage)
    blk = K.STG_KIT if stage else K.SRC_KIT
    i = body.index(blk)
    j = i + len(blk)
    tail_old = body[j:]
    # drop the kit bench's hierarchical binds of kit internals (observation only) and re-point them below the wrapper
    kpath = ('u_kit.g_stg.u_kit' if stage else 'u_kit.g_src.u_kit') if harness in ('cr', 'crp') else 'u_kit'
    tail = re.sub(r'\bu_kit\.', kpath + '.', tail_old)
    if harness in ('cr', 'crp'):
        h = (CR_KIT if harness == 'cr' else CR_KIT.replace('dsfd_wfc_cr #(', 'dsfd_wfc_cr2 #(.OSKID(1), ' if OSKID_K else 'dsfd_wfc_cr2 #(')).replace('SRCK', '0' if stage else '1').replace('KITPARAMS', ', .LAG(LAG)' if stage else '')
        h = h.replace('CFGW', "{(3+10+42){1'b0}}" if stage else 'cfgw')
        h = h.replace('KTOK', '' if stage else 'k_tok').replace('KCFG', '' if stage else '{cfg_users, cfg_plen, cfg_glen}')
    else:
        h = SKID_KIT.replace('KITMOD', 'dsfd_wfc_stg #(.LAG(LAG))' if stage else 'dsfd_wfc_src')
        h = h.replace('SKIDSRC', '' if stage else ', .f_c(cfgw), .t_tok(k_tok), .t_cfg({cfg_users, cfg_plen, cfg_glen})')
    if stage:
        h += STG_TAIL.replace('KPATH', kpath)
    else:
        h = "    wire [52:0] k_tok;\n" + h + SRC_TAIL + "    assign {tok_valid, tok_user, tok_pos, tok_id} = k_tok;\n"
    body = body[:i] + h + tail
    # the kit bench's ks / srq / swa / kd are the bench-side ends now: the relays connect them to the kit
    body = re.sub(r'(module ' + tb + r';\n)', r'\1' + PARAMS, body, count=1)
    body = body.replace('cyc - last_close[u] > 3 * L + T_DRAFT + 1500 * NUSR', 'cyc - last_close[u] > WDOG_MULT * (3 * L + T_DRAFT + 1500 * NUSR)')
    return tb, body + RELAY


def run(name, out):
    base, harness, sp, defs, expect = CASES[name]
    kb, stage, kdefs, _ = K.CASES[base]
    spec = B.cases()[kb]
    tb, body = cr_tb(base, harness)
    d = out / name; d.mkdir(parents=True, exist_ok=True)
    meta = B.trace_hex(ROOT / B.TRACES / f"{spec['trace']}.cfg.json", d / 'trace.hex') if 'trace' in spec else None
    (d / 'tb.sv').write_text(body)
    # mtp-wfc 2026-10-11: K.EXTRA now carries the vmx SRAM queue (ot_fifo_sram_fwft + the SRAM model): dedupe in order,
    # else iverilog stops on a re-declared module (every crp_* case BUILD_ERROR)
    srcs = [str(ROOT / s) for s in dict.fromkeys(list(B.COMMON) + K.EXTRA + [CR, LINK] + (CRP if harness == 'crp' else []))] + [str(d / 'tb.sv')]
    cmd = ['iverilog', '-g2012', '-s', tb, '-o', str(d / 'sim.vvp')] + \
          [f'-D{x}' for x in list(spec.get('defines', [])) + kdefs + defs] + \
          [f'-P{tb}.{k}={v}' for k, v in list(spec.get('params', {}).items()) + list(sp.items())] + srcs
    b = subprocess.run(cmd, capture_output=True, text=True); (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        return dict(case=name, expect=expect, verdict='BUILD_ERROR', log=b.stderr[-1500:])
    r = subprocess.run(['vvp', '-n', str(d / 'sim.vvp')], capture_output=True, text=True, cwd=d, timeout=7200)
    (d / 'run.log').write_text(r.stdout + r.stderr)
    tag = 'MTP_STG' if stage else 'MTP_S0'
    m = re.search(rf'^{tag} (PASS|FAIL).*$', r.stdout, re.M) or re.search(r'^(?:LINK_REG )?(FAIL).*$', r.stdout, re.M)
    got = m.group(1).lower() if m else ('fail' if r.returncode else 'nolog')
    return dict(case=name, base=base, harness=harness, stages=sp, defines=defs, expect=expect, got=got,
                verdict='OK' if got == expect else 'UNEXPECTED', result=(m.group(0) if m else r.stdout[-400:]), trace=meta)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--out', type=Path, required=True); p.add_argument('--case')
    p.add_argument('--crp', action='store_true', help='only the dsfd_wfc_crp (credit-port tile) cases'); p.add_argument('--jobs', type=int, default=11)
    p.add_argument('--oskid', action='store_true', help='dsfd_wfc_crp OSKID 1 (registered kit-side skids)')
    a = p.parse_args(); a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    global OSKID_K; OSKID_K = 1 if getattr(a, 'oskid', False) else 0
    names = [a.case] if a.case else (CRP_CASES if a.crp else list(CASES))
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda n: run(n, a.out), names))
    ok = all(r['verdict'] == 'OK' for r in recs)
    (a.out / 'summary.json').write_text(json.dumps(dict(all_ok=ok, cases=recs), indent=1) + '\n')
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:22s} expect={r['expect']} {str(r.get('result', r.get('log', '')))[:160]}")
    print(f"WFC_KIT_CR_GATE {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

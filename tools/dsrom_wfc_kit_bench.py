#!/usr/bin/env python3
"""Exact gate of the WFC kit masters dsfd_wfc_src / dsfd_wfc_stg (rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv).

The closed-element system benches (tb_mtp_rom_s0_tokpipe: SOURCE + lnk + tok + vmx + sequencer; tb_mtp_rom_stg_tokpipe:
STAGE + lnk + vmx) are regenerated with the four separately instantiated elements replaced by ONE kit instance on
the die-facing ports, so the bench drives exactly the ports the S81 die wires.  Observation-only internals (latency
statistics, issue counters) are bound hierarchically (u_kit.*); the committed-token stream, the configuration and
the faults come from the kit's own ports (t_tok, t_cfg, t_ft).  Cases mirror tools/dsrom_wfc_prompt_pipe_bench.py
(--hard-token pairing: SOURCE PROMPT_EXTRA 2 + dsfd_wfc_tok_hard) plus the vmx predicted-read negative.

  python3 tools/dsrom_wfc_kit_bench.py --out DIR [--case NAME]   -> DIR/summary.json, prints WFC_KIT_GATE PASS|FAIL
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
import dsrom_mtp_rom_bench as B

ROOT = Path(__file__).resolve().parents[1]
KIT = 'rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv'
EXTRA = ['rtl/dsrom_sys/mtp/ot_dsrom_wfc_tok_r3.sv', 'rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv',
         'rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_src.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_stg.sv', KIT]
INTERNAL = ['w_in_valid', 'w_in_ready', 'w_in_last', 'w_out_valid', 'w_out_ready', 'w_out_last', 'w_in_data',
            'w_out_data', 'core_start', 'core_done_w', 'core_token', 'core_pos', 'cnt_tok', 'cnt_val', 'core_user',
            'kv_base', 'vm_we', 'vm_re', 'vm_waddr', 'vm_raddr', 'vm_wdata', 'vm_rq', 'pr_re', 'pr_user', 'pr_pos',
            'pr_blk', 'pr_q', 'pr_qk', 'core_busy', 'wf_issue', 'wf_reject', 'wf_squash', 'users_done', 'dw', 'vc_ret']
SRC_KIT = '''    wire [52:0] k_tok; wire [3:0] k_ft;
    dsfd_wfc_src u_kit (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(li_v), .f_lid(li_d), .t_lir(li_r), .t_lov(lo_v), .t_lod(lo_d), .f_lor(lo_r),
        .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(srq),
        .t_ks(ks), .f_kd(kd), .f_c(cfgw), .t_tok(k_tok), .t_cfg({cfg_users, cfg_plen, cfg_glen}), .t_ft(k_ft));
    assign {proto_fault, lnk_ft, tok_ft, vmx_ft} = k_ft;
    assign {tok_valid, tok_user, tok_pos, tok_id} = k_tok;
'''
STG_KIT = '''    wire [3:0] k_ft;
    dsfd_wfc_stg #(.LAG(LAG)) u_kit (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(li_v), .f_lid(li_d), .t_lir(li_r), .t_lov(lo_v), .t_lod(lo_d), .f_lor(lo_r),
        .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(srq),
        .t_ks(ks), .f_kd(kd), .t_ft(k_ft));
    assign proto_fault = k_ft[3]; assign lnk_ft = k_ft[2]; assign vmx_ft = k_ft[0];
    assign tok_valid = u_kit.tok_valid; assign tok_user = u_kit.tok_user; assign tok_pos = u_kit.tok_pos;
    assign tok_id = u_kit.tok_id;
'''
CASES = {  # name -> (base case in dsrom_mtp_rom_bench.cases(), stage?, extra defines, expect)
    's0_tr_dspark': ('s0_tr_dspark', 0, [], 'pass'), 's0_tr_forced': ('s0_tr_forced', 0, [], 'pass'),
    's0_tr_forced_w16': ('s0_tr_forced_w16', 0, [], 'pass'), 's0_hash_u3': ('s0_hash_u3', 0, [], 'pass'),
    's0_hash_u1_fast': ('s0_hash_u1_fast', 0, [], 'pass'), 's0_hash_u4_ar1': ('s0_hash_u4_ar1', 0, [], 'pass'),
    'stg_r1': ('stg_r1', 1, [], 'pass'), 'stg_vmnat': ('stg_vmnat', 1, [], 'pass'), 'stg_lag1': ('stg_lag1', 1, [], 'pass'),
    'stg_r2_slowvm': ('stg_r2_slowvm', 1, [], 'pass'),
    's0_neg_noepoch': ('s0_neg_noepoch', 0, [], 'fail'), 's0_neg_nohold': ('s0_neg_nohold', 0, [], 'fail'),
    's0_neg_predoff': ('s0_tr_forced', 0, ['OT_WFCVMX_MUT_PREDOFF'], 'fail'),
    'stg_neg_nocred': ('stg_neg_nocred', 1, [], 'fail'),
    'stg_neg_predoff': ('stg_r1', 1, ['OT_WFCVMX_MUT_PREDOFF'], 'fail'),
}


def kit_tb(stage):
    tb = 'tb_mtp_rom_stg_tokpipe' if stage else 'tb_mtp_rom_s0_tokpipe'
    body = (ROOT / f'rtl/dsrom_sys/mtp/tb/{tb}.sv').read_text()
    pats = [r'    ot_rom_pkg_ctrl_wfc_tokpipe #\(.*?wf_squash\)\);\n', r'    dsfd_wfc_lnk u_lnk \(.*?\);\n']
    if not stage:
        pats.append(r'    dsfd_wfc_tok_r3 u_tok \(.*?\);\n')
    for p in pats:
        body, n = re.subn(p, '', body, count=1, flags=re.S)
        assert n == 1, (tb, p)
    binds = ''.join(f'    assign {x} = u_kit.{x};\n' for x in INTERNAL if re.search(rf'\b{x}\b', body))
    body, n = re.subn(r'    dsfd_wfc_vmx #\(.*?\) u_vmx \(.*?\);\n', lambda m: (STG_KIT if stage else SRC_KIT) + binds,
                      body, count=1, flags=re.S)
    assert n == 1, tb
    return tb, body


def run(name, out):
    base, stage, defs, expect = CASES[name]
    spec = B.cases()[base]
    tb, body = kit_tb(stage)
    d = out / name; d.mkdir(parents=True, exist_ok=True)
    meta = B.trace_hex(ROOT / B.TRACES / f"{spec['trace']}.cfg.json", d / 'trace.hex') if 'trace' in spec else None
    (d / 'tb.sv').write_text(body)
    srcs = [str(ROOT / s) for s in list(B.COMMON) + EXTRA] + [str(d / 'tb.sv')]
    cmd = ['iverilog', '-g2012', '-s', tb, '-o', str(d / 'sim.vvp')] + \
          [f'-D{x}' for x in list(spec.get('defines', [])) + defs] + \
          [f'-P{tb}.{k}={v}' for k, v in spec.get('params', {}).items()] + srcs
    b = subprocess.run(cmd, capture_output=True, text=True); (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        return dict(case=name, expect=expect, verdict='BUILD_ERROR', log=b.stderr[-1500:])
    r = subprocess.run(['vvp', '-n', str(d / 'sim.vvp')], capture_output=True, text=True, cwd=d)
    (d / 'run.log').write_text(r.stdout + r.stderr)
    tag = 'MTP_STG' if stage else 'MTP_S0'
    m = re.search(rf'^{tag} (PASS|FAIL).*$', r.stdout, re.M) or re.search(r'^LINK_REG (FAIL).*$', r.stdout, re.M)
    got = m.group(1).lower() if m else 'nolog'
    return dict(case=name, base=base, defines=list(spec.get('defines', [])) + defs, expect=expect, got=got,
                verdict='OK' if got == expect else 'UNEXPECTED', result=(m.group(0) if m else r.stdout[-400:]), trace=meta)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--out', type=Path, required=True); p.add_argument('--case'); p.add_argument('--jobs', type=int, default=8)
    a = p.parse_args(); a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    names = [a.case] if a.case else list(CASES)
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda n: run(n, a.out), names))
    pins = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in list(B.COMMON) + EXTRA}
    ok = all(r['verdict'] == 'OK' for r in recs)
    (a.out / 'summary.json').write_text(json.dumps(dict(all_ok=ok, cases=recs, source_sha256=pins), indent=1) + '\n')
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:18s} expect={r['expect']} {str(r.get('result', r.get('log', '')))[:180]}")
    npos = sum(1 for r in recs if r['expect'] == 'pass' and r['verdict'] == 'OK')
    nneg = sum(1 for r in recs if r['expect'] == 'fail' and r['verdict'] == 'OK')
    print(f"WFC_KIT_GATE {'PASS' if ok else 'FAIL'} positives={npos} negatives={nneg}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

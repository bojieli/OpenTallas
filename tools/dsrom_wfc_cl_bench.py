#!/usr/bin/env python3
"""Gate of the S81 sp_wfc cluster dsfd_wfc_stg_cl (rtl/dsrom_sys/mtp/dsfd_wfc_stg_cl.sv: closed WFC + closed link bridge
+ the new VM-port tile dsfd_wfc_vmx_p = dsfd_wfc_vmx_w + dsfd_wfc_vmx_r + dsfd_wfc_hep_t) at the PRICED kit configuration.

Two kinds of case, both on the kit system bench of tools/dsrom_wfc_kit_bench.py (stage TB, VM behind 13 / 13 hub
stations + dsfd_vm_wfc_ep, posted writes, 2-port prefetch, HEP checks):
  cl_*    the cluster IS the device: every content check of the stage bench (RX words in the VM at core start, every
          outbound word, token / user / pos, faults, HEP epochs) runs on dsfd_wfc_stg_cl.
  lock_*  LOCKSTEP: the one-tile kit dsfd_wfc_stg #(VM_LINK 1, VMRQ 64, WOUTW 8, POSTED 1, RD2 1, HEP 1) drives the bench
          and the cluster receives the same pins; every cluster output is compared with the kit's on every edge of
          its clock (ck: t_lir t_lov t_lod t_ft; ckv: t_swv t_swd t_srv t_srd t_ks t_hep).  One mismatch fails.
Negatives: the mutant defines of the leaves (stale outbound word, swapped pair, predicted read off by one, DONE early);
lock_neg_noadv proves the lockstep compare itself is live (the mutant exists only in the cluster's leaf).

--snap compiles the CLOSED children at their closed-commit RTL (rtl/dsrom_sys/mtp/closed_snap/manifest.json): files
that did not drift are checked against the closed commit's sha256 (file or module text), the drifted file is taken
from the snapshot directory.  A manifest mismatch fails the case before it builds.

  python3 tools/dsrom_wfc_cl_bench.py --out DIR [--case NAME] [--snap] [--raw-negative] [--jobs N]
  -> DIR/summary.json, prints WFC_CL_GATE PASS|FAIL (or WFC_CL_NEGATIVE FAIL_AS_REQUIRED with --raw-negative)
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
import dsrom_mtp_rom_bench as B
import dsrom_wfc_kit_bench as K

ROOT = Path(__file__).resolve().parents[1]
CL = 'rtl/dsrom_sys/mtp/dsfd_wfc_stg_cl.sv'
MAC = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v'
SNAP = 'rtl/dsrom_sys/mtp/closed_snap/manifest.json'
KIT_INST = 'dsfd_wfc_stg #(.LAG(LAG), .VM_LINK(1), .VMRQ(64), .WOUTW(8), .POSTED(1), .RD2(1), .HEP(1)) u_kit ('
# the kit's observation-only internals, as hierarchical names in the cluster
ALIAS = {'core_done_w': 'u_wfc.core_done', 'cnt_tok': 'u_wfc.core_next_token', 'cnt_val': 'u_wfc.core_next_val',
         'dw': 'u_lnk.t_dw', 'vc_ret': 'vc_ret', 'w_in_valid': 'w_in_valid', 'w_in_ready': 'w_in_ready',
         'w_in_last': 'w_in_last', 'w_out_valid': 'w_out_valid', 'w_out_ready': 'w_out_ready',
         'w_out_last': 'w_out_last', 'w_in_data': 'w_in_data', 'w_out_data': 'w_out_data', 'core_start': 'core_start',
         'core_token': 'core_token', 'core_pos': 'core_pos', 'core_user': 'core_user', 'vm_we': 'vm_we',
         'vm_re': 'vm_re', 'vm_waddr': 'vm_waddr', 'vm_raddr': 'vm_raddr', 'vm_wdata': 'vm_wdata', 'vm_rq': 'vm_rq'}
LOCK = '''    // LOCKSTEP: the cluster on the kit's pins; every output compared on every edge of its clock
    wire [0:0] c_lir, c_lov, c_swv, c_srv; wire [FLIT:0] c_lod; wire [VWA+FLIT-1:0] c_swd; wire [2*VWA:0] c_srd;
    wire [USER_W+2*NW:0] c_ks; wire [USER_W+NW+4:0] c_hep; wire [3:0] c_ft;
    dsfd_wfc_stg_cl u_cl (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .f_liv(li_v), .f_lid(li_d), .t_lir(c_lir), .t_lov(c_lov), .t_lod(c_lod), .f_lor(lo_r),
        .t_swv(c_swv), .t_swd(c_swd), .f_swr(k_swg), .f_swa(k_err), .t_srv(c_srv), .t_srd(c_srd), .f_srr(k_srg),
        .f_srq(k_srq), .t_ks(c_ks), .f_kd(kd), .t_hep(c_hep), .t_ft(c_ft));
    integer lk_f = 0, lk_s = 0, lk_bad = 0, lk_act = 0;
    always @(posedge fclk) if (rst_n) begin
        lk_f = lk_f + 1;
        if ({li_r, lo_v, lo_d, k_ft} !== {c_lir, c_lov, c_lod, c_ft}) begin
            lk_bad = lk_bad + 1;
            if (lk_bad < 6) $display("LOCK MISMATCH ck t=%0t lir %b/%b lov %b/%b lod_eq %b ft %h/%h", $time, li_r, c_lir, lo_v, c_lov, lo_d === c_lod, k_ft, c_ft);
        end
        if (lo_v === 1'b1) lk_act = lk_act + 1;
    end
    always @(posedge sclk) if (rst_n) begin
        lk_s = lk_s + 1;
        if ({k_swv, k_swd, k_srv, k_srd, k_ks_unused, k_hep} !== {c_swv, c_swd, c_srv, c_srd, c_ks, c_hep}) begin
            lk_bad = lk_bad + 1;
            if (lk_bad < 6) $display("LOCK MISMATCH ckv t=%0t swv %b/%b swd_eq %b srv %b/%b srd %h/%h ks_eq %b hep %h/%h", $time, k_swv, c_swv, k_swd === c_swd, k_srv, c_srv, k_srd, c_srd, k_ks_unused === c_ks, k_hep, c_hep);
        end
        if (k_hep[USER_W+NW+4] === 1'b1) lk_act = lk_act + 1;
    end
'''
CASES = {  # name -> (base stage case, mode, extra defines, expect)
    'cl_stg_r1': ('stg_r1', 'cl', [], 'pass'), 'cl_stg_vmnat': ('stg_vmnat', 'cl', [], 'pass'),
    'cl_stg_r2_slowvm': ('stg_r2_slowvm', 'cl', [], 'pass'),
    'lock_stg_r1': ('stg_r1', 'lock', [], 'pass'), 'lock_stg_vmnat': ('stg_vmnat', 'lock', [], 'pass'),
    'lock_stg_r2_slowvm': ('stg_r2_slowvm', 'lock', [], 'pass'),
    'cl_neg_noadv': ('stg_r1', 'cl', ['OT_WFCVMXR_MUT_NOADV'], 'fail'),
    'cl_neg_swap': ('stg_r1', 'cl', ['OT_WFCVMX_MUT_RD2_SWAP'], 'fail'),
    'cl_neg_predoff': ('stg_r1', 'cl', ['OT_WFCVMX_MUT_PREDOFF'], 'fail'),
    'cl_neg_doneearly': ('stg_r1', 'cl', ['OT_WFCVMX_MUT_DONEEARLY'], 'fail'),
    'lock_neg_noadv': ('stg_r1', 'lock', ['OT_WFCVMXR_MUT_NOADV'], 'fail'),
    'cl_neg_doorbell': ('stg_r1', 'cl', ['OT_WFCVMXW_MUT_DOORBELL'], 'fail'),
    'lock_neg_doorbell': ('stg_r1', 'lock', ['OT_WFCVMXW_MUT_DOORBELL'], 'fail'),
}


def sha(t):
    return hashlib.sha256(t.encode()).hexdigest()


def module_text(text, name):
    m = re.search(rf'^module {name}\b.*?^endmodule', text, re.S | re.M)
    if not m:
        raise SystemExit(f'closed_snap: module {name} not found')
    return m.group(0)


def snap_sources(srcs):
    """the source list with the closed children at their closed-commit RTL; raises on any manifest mismatch"""
    man = json.loads((ROOT / SNAP).read_text())
    swap, pins = {}, {}
    for cname, ch in man['children'].items():
        for f, h in ch.get('files', {}).items():
            got = sha((ROOT / f).read_text())
            if got != h:
                raise SystemExit(f'closed_snap: {f} is not the closed {cname} file ({ch["commit"]}): add it to the snapshot')
            pins[f] = h
        for n, d in ch.get('modules', {}).items():
            got = sha(module_text((ROOT / d['file']).read_text(), n))
            if got != d['sha256']:
                raise SystemExit(f'closed_snap: module {n} in {d["file"]} drifted from {cname} {ch["commit"]}')
            pins[f'{d["file"]}::{n}'] = d['sha256']
        for f, d in ch.get('snapshot', {}).items():
            if sha((ROOT / d['file']).read_text()) != d['sha256']:
                raise SystemExit(f'closed_snap: {d["file"]} is not {f} at {ch["commit"]}')
            swap[str(ROOT / f)] = str(ROOT / d['file'])
            pins[d['file']] = d['sha256']
    out = [swap.get(s, s) for s in srcs]
    if len([1 for a, b in zip(srcs, out) if a != b]) != len(swap):
        raise SystemExit('closed_snap: a snapshot file is not in the bench source list')
    return out, pins


def cl_tb(mode, entries=False):
    tb, body = K.kit_tb(1, 12)
    assert body.count(KIT_INST) == 1, 'kit instance'
    if mode == 'cl':
        body = body.replace(KIT_INST, 'dsfd_wfc_stg_cl u_kit (')
        def al(m):
            n = m.group(1)
            return ('u_kit.u_cluster.' if entries else 'u_kit.') + ALIAS.get(n, 'u_wfc.' + n)
        body = re.sub(r'\bu_kit\.(\w+)', al, body)
    else:
        a = body.index(KIT_INST); e = body.index(');\n', body.index('.t_hep(k_hep)', a)) + 3
        body = body[:e] + LOCK + body[e:]
        assert body.count('        $display("MTP_STG PASS') == 1
        body = body.replace('        $display("MTP_STG PASS',
                            '        $display("WFC_CL_LOCK fast_edges=%0d slow_edges=%0d active=%0d bad=%0d", lk_f, lk_s, lk_act, lk_bad);\n'
                            '        if (lk_bad != 0 || lk_f < 10000 || lk_act < 100) begin $display("MTP_STG FAIL: lockstep, cluster != kit on '
                            '%0d edges (compared %0d + %0d, active %0d)", lk_bad, lk_f, lk_s, lk_act); $finish; end\n'
                            '        $display("MTP_STG PASS')
    if entries:
        # Exercise the actual production parent, with all child entries driven by
        # their logically related source clocks; physical insertion is die STA.
        body = body.replace('dsfd_wfc_stg_cl u_kit (', 'dsfd_wfc_stg_pc u_kit (')
        body = body.replace('dsfd_wfc_stg_cl u_cl (', 'dsfd_wfc_stg_pc u_cl (')
        body = re.sub(r'(dsfd_wfc_stg_pc u_(?:kit|cl)\s*\()\s*\.ck\(fclk\), \.ckv\(sclk\),',
                      r'\1.ck_wfc(fclk), .ck_lnk(fclk), .ck_vmx(fclk), .ckv_vmx(sclk),', body)
    return tb, body


def run(name, out, snap, entries=False):
    base, mode, defs, expect = CASES[name]
    spec = B.cases()[base]
    tb, body = cl_tb('lock' if mode.startswith('lock') else 'cl', entries)
    d = out / name; d.mkdir(parents=True, exist_ok=True)
    (d / 'tb.sv').write_text(body)
    srcs = [str(ROOT / s) for s in list(B.COMMON) + K.EXTRA + [CL, MAC]]
    pins = None
    if snap:
        srcs, pins = snap_sources(srcs)
    srcs.append(str(d / 'tb.sv'))
    cmd = ['iverilog', '-g2012', '-s', tb, '-o', str(d / 'sim.vvp')] + \
          [f'-D{x}' for x in list(spec.get('defines', [])) + defs] + \
          [f'-P{tb}.{k}={v}' for k, v in spec.get('params', {}).items()] + srcs
    b = subprocess.run(cmd, capture_output=True, text=True); (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        return dict(case=name, expect=expect, verdict='BUILD_ERROR', log=b.stderr[-1500:])
    r = subprocess.run(['vvp', '-n', str(d / 'sim.vvp')], capture_output=True, text=True, cwd=d)
    (d / 'run.log').write_text(r.stdout + r.stderr)
    m = re.search(r'^MTP_STG (PASS|FAIL).*$', r.stdout, re.M) or re.search(r'^LINK_REG (FAIL).*$', r.stdout, re.M) \
        or re.search(r'^(FAIL): VM write address.*$', r.stdout, re.M)      # the bench's VM port model (untagged line)
    got = m.group(1).lower() if m else 'nolog'
    lk = re.search(r'^WFC_CL_LOCK .*$', r.stdout, re.M)
    return dict(case=name, base=base, mode=mode, defines=list(spec.get('defines', [])) + defs, expect=expect, got=got,
                verdict='OK' if got == expect else 'UNEXPECTED', result=(m.group(0) if m else r.stdout[-400:]),
                lock=lk.group(0) if lk else None, snap=pins)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--out', type=Path, required=True); p.add_argument('--case'); p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--clock-entries', action='store_true', help='exercise wires-only parent with per-child clock inputs')
    p.add_argument('--snap', action='store_true', help='closed children at their closed-commit RTL (closed_snap manifest)')
    p.add_argument('--raw-negative', action='store_true', help='one expected-FAIL case: exit 1 when it fails as required')
    a = p.parse_args(); a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    names = a.case.split(',') if a.case else list(CASES)
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda n: run(n, a.out, a.snap, a.clock_entries), names))
    ok = all(r['verdict'] == 'OK' for r in recs)
    (a.out / 'summary.json').write_text(json.dumps(dict(all_ok=ok, snap=a.snap, cases=recs), indent=1) + '\n')
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:20s} expect={r['expect']} {str(r.get('result', r.get('log', '')))[:170]}"
              + (f" | {r['lock']}" if r.get('lock') else ''))
    npos = sum(1 for r in recs if r['expect'] == 'pass' and r['verdict'] == 'OK')
    nneg = sum(1 for r in recs if r['expect'] == 'fail' and r['verdict'] == 'OK')
    if a.raw_negative:
        assert len(recs) == 1 and recs[0]['expect'] == 'fail', 'raw-negative needs one negative case'
        if recs[0]['verdict'] == 'OK':
            print('WFC_CL_NEGATIVE FAIL_AS_REQUIRED ' + recs[0]['case']); return 1
        print('WFC_CL_NEGATIVE UNEXPECTED_PASS ' + recs[0]['case']); return 0
    print(f"WFC_CL_GATE {'PASS' if ok else 'FAIL'} positives={npos} negatives={nneg} snap={int(a.snap)}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

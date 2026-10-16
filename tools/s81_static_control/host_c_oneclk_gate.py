#!/usr/bin/env python3
"""dsfd_host_c +OT_S81_HOST_ONECLK exact gate (S-ELEM-PQ/HOST 2026-10-16, VIS-ROM S81H-01).

DUT: the tile as built (DSFD_HOST_C_STATIC, DSFD_HOST_PQ_BOOT, OT_S81_HOST_BOOT300, OT_S81_HOST_ADDR_PREFIX,
OT_S81_HOST_ONECLK): one 1.2 GHz root, no lockup latches, HOST prefix / carry-save address arithmetic with the
local*pitch and sb*0x880 terms formed one stage earlier.
Reference: the SAME source files with every module renamed ref_*, OT_S81_HOST_ONECLK / OT_S81_HOST_ADDR_PREFIX
disabled and OT_S81_HOST_PHASESAFE enabled, i.e. the legacy PHASESAFE+BOOT300 HOST with legacy '+' arithmetic,
driven with ck_ingest = {ck, ck} (the calendar of record: 59,989 compared edges / 1,093 packets / 544 sectors /
1 DONE for the IKEY case).  Every ck edge compares hw and the completion pulse; every ckv edge compares the boot
words.  External HBM storage/ACKs and expected images are test models; every on-chip result is actual RTL.
Negatives: MUT 3 (completions not emitted), address mutants (IKEY: sb*0x880 wrong shift; ROWS: local*pitch + 1),
an intercepted-CSR leak mutant.
Boot: tests/s81/tb_host_boot300.sv (8 serial phases, stopped boot clock, over-capacity, MUT 5 kind mutant).
Scope: initialization/off-chip ingress; physical timing comes from the route, not from this bench.
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import rtl_rom_host_ingest_bench as B

SRC = ['rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv', 'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv',
       'rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv', 'rtl/lib/ot_rst_relay.sv', 'rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv',
       'rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv',
       'physical/rom_host_ingest/rtl/dsfd_host.sv', 'rtl/hdc/ingest/ot_rom_host_ingest.sv', 'rtl/link/ot_link_afifo.sv',
       'rtl/hdc/ingest/ot_hdc_kv_ingest.sv', 'rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv']
DEFS = ['-DDSFD_HOST_C_STATIC', '-DDSFD_HOST_PQ_BOOT', '-DOT_S81_HOST_BOOT300', '-DOT_S81_HOST_ADDR_PREFIX',
        '-DOT_S81_HOST_ONECLK', '-DREF_HOST_PHASESAFE']
TB = 'tests/s81/tb_host_c_oneclk.sv'
BOOT_TB = 'tests/s81/tb_host_boot300.sv'


def reference(out):
    text = '\n'.join((ROOT / x).read_text() for x in SRC)
    mods = sorted(set(re.findall(r'^\s*module\s+(\w+)', text, re.M)), key=len, reverse=True)
    for m in mods:
        text = re.sub(r'\b%s\b' % re.escape(m), 'ref_' + m, text)
    for old, new in [('OT_S81_HOST_ONECLK', 'REF_HOST_ONECLK_OFF'), ('OT_S81_HOST_ADDR_PREFIX', 'REF_HOST_PREFIX_OFF'),
                     ('OT_S81_HOST_PHASESAFE', 'REF_HOST_PHASESAFE'), ('OT_S81_HOST_STRUCT', 'REF_HOST_STRUCT')]:
        text = re.sub(r'\b%s\b' % old, new, text)
    p = out / 'ref_host_c_legacy.sv'
    p.write_text(text)
    return p, mods


def sat_proof(out, kv, records):
    """All-input proof: the restructured stage A1/B address terms equal the legacy '+'/'*' expressions."""
    fns = re.findall(r'    function automatic \[31:0\] (?:host_addr_add32_prefix|host_addr_add3);.*?    endfunction', kv, re.S)
    assert len(fns) == 2
    body = '\n'.join(fns)
    tmpl = """module proof(input[31:0]base,stride,local_,gs,row,input[2:0]stk,input[4:0]pitch,input ringz,output ok);
FN
// legacy (ot_hdc_kv_ingest without OT_S81_HOST_ADDR_PREFIX): A1 rbase, then B from the A1 registers
wire[31:0]l_rbase=base+(ringz?stk*stride:32'd0);
wire[31:0]sb=gs>>6;wire[5:0]q=gs[5:0];
wire[31:0]l_blk=l_rbase+(sb<<11)+(sb<<7);
wire[31:0]l_raddr=l_rbase+local_*pitch;
wire[31:0]l_kcode=l_blk+((32'd1+{28'd0,q[5:2]})<<7)+({30'd0,q[1:0]}<<5)+((row&32'd15)<<1);
wire[31:0]l_kscal=l_blk+({26'd0,q}<<1);
// ONECLK/prefix: A1 forms rbase, lp, sbm; B is one carry-save row + one prefix add
wire[31:0]rbase=host_addr_add32_prefix(base,ringz?stk*stride:32'd0);
wire[31:0]lp=local_*pitch;wire[31:0]sbm=host_addr_add32_prefix((gs>>6)<<11,(gs>>6)<<SBM);
wire[31:0]koff=(((32'd1+{28'd0,q[5:2]})<<7)|({30'd0,q[1:0]}<<5)|((row&32'd15)<<1));
wire[31:0]raddr=host_addr_add32_prefix(rbase,lp);
wire[31:0]kcode=host_addr_add3(rbase,sbm,koff);
wire[31:0]kscal=host_addr_add3(rbase,sbm,({26'd0,q}<<1));
assign ok=(rbase==l_rbase)&&(raddr==l_raddr)&&(kcode==l_kcode)&&(kscal==l_kscal);
endmodule
"""
    # the proved expressions must be the ones in the source
    for frag in ["ap1_lp <= ap0_local*ap0_pitch;", "ap1_sbm <= host_addr_add32_prefix((ap0_gs>>6)<<11,(ap0_gs>>6)<<7);",
                 "wire [31:0] a2_raddr=host_addr_add32_prefix(ap1_rbase,ap1_lp);",
                 "wire [31:0] a2_kcode=host_addr_add3(ap1_rbase,ap1_sbm,a2_koff);",
                 "wire [31:0] a2_kscal=host_addr_add3(ap1_rbase,ap1_sbm,({26'd0,a2_q}<<1));",
                 "wire [31:0] a2_koff=(((32'd1+{28'd0,a2_q[5:2]})<<7)|({30'd0,a2_q[1:0]}<<5)|((ap1_row&32'd15)<<1));",
                 "ap1_rbase <= host_addr_add32_prefix(ap0_base,ap0_ringz?ap0_stk*ap0_stride:32'd0);"]:
        assert kv.count(frag) == 1, frag
    for name, sbm, mutant in [('sat_exact', '7', False), ('sat_sbm_shift', '6', True)]:
        f = out / (name + '.sv'); f.write_text(tmpl.replace('FN', body).replace('SBM', sbm))
        cmd = ['yosys', '-Q', '-T', '-p', f'read_verilog -sv {f}; prep -top proof; flatten; opt; sat -verify -prove ok 1 -timeout 600']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        (out / (name + '.log')).write_text(r.stdout + r.stderr)
        ok = (r.returncode == 0 and 'SUCCESS' in r.stdout) if not mutant else (r.returncode != 0 and 'proof did fail' in (r.stdout + r.stderr))
        if not ok:
            raise SystemExit('HOST_ONECLK_GATE UNEXPECTED ' + name + ' ' + (r.stdout + r.stderr)[-1500:])
        records.append(dict(case=name, marker='SAT ' + ('FAIL (expected)' if mutant else 'SUCCESS')))
        print(name, 'SAT', 'mutant FAIL as expected' if mutant else 'SUCCESS all inputs', flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out', type=Path); a = ap.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    ref, mods = reference(out)
    records = []

    def build(top, tb, mut, name, swap=None, extra=()):
        exe = out / (name + '.vvp')
        srcs = [str(swap[x]) if swap and x in swap else str(ROOT / x) for x in SRC]
        cmd = ['iverilog', '-g2012', '-s', top, f'-P{top}.MUT={mut}', *DEFS, *extra, '-o', str(exe), str(tb), str(ref), *srcs]
        cp = subprocess.run(cmd, capture_output=True, text=True)
        (out / (name + '.build.log')).write_text(cp.stdout + cp.stderr)
        if cp.returncode:
            raise SystemExit('HOST_ONECLK_GATE BUILD_FAIL ' + name + ' ' + cp.stderr[-1500:])
        return exe

    def run(exe, name, args, expect, marker, cwd):
        cp = subprocess.run(['vvp', '-n', str(exe), *args], cwd=cwd, capture_output=True, text=True, timeout=1800)
        o = cp.stdout + cp.stderr; (out / (name + '.log')).write_text(o)
        # expect: the run must finish cleanly (True) or stop on a $fatal (False); marker must be printed either way
        ok = (marker in o) and ((cp.returncode == 0 and 'FATAL' not in o) == expect)
        if not ok:
            raise SystemExit('HOST_ONECLK_GATE UNEXPECTED ' + name + ' ' + o[-1500:])
        line = next(x for x in o.splitlines() if marker in x).strip()
        records.append(dict(case=name, marker=marker, line=line))
        print(name, line, flush=True)

    kv = (ROOT / 'rtl/hdc/ingest/ot_hdc_kv_ingest.sv').read_text()
    needle = "ap1_sbm <= host_addr_add32_prefix((ap0_gs>>6)<<11,(ap0_gs>>6)<<7);"
    assert kv.count(needle) == 1
    sat_proof(out, kv, records)
    kneedle = "((ap1_row&32'd15)<<1));"
    assert kv.count(kneedle) == 1
    badkv = out / 'mut_koff_row.sv'; badkv.write_text(kv.replace(kneedle, "((ap1_row&32'd15)<<2));"))
    lpn = "ap1_lp <= ap0_local*ap0_pitch;"
    assert kv.count(lpn) == 1
    badlp = out / 'mut_lp_plus1.sv'; badlp.write_text(kv.replace(lpn, "ap1_lp <= ap0_local*ap0_pitch + 32'd1;"))
    hc = (ROOT / SRC[0]).read_text()
    leak = "wire to_ing = hv && !csr_p && !csr_l && !csr_pq;"
    assert hc.count(leak) == 1
    badhc = out / 'mut_csr_leak.sv'; badhc.write_text(hc.replace(leak, "wire to_ing = hv; // mutant: intercepted CSRs leak into the native ingest"))

    summary = {}
    for case in ['ikey', 'rows']:
        cd = out / case; cd.mkdir(exist_ok=True)
        c = B.C.case_ikey(np.random.default_rng(20261016), 1024) if case == 'ikey' else \
            B.C.case_rows(np.random.default_rng(20261016), 'ckv', 64, first=32)
        c['nb'] = B.stream_nb(c['descs']); B.write_case(cd, c, 65536)
        words = [(0, 0x10 | (0x1234567 << 32)), (0, 0x12 | (1 << 96) | (0x2345678 << 32)), (0, 0x11 | (4 << 32)), (0, 0)]
        pi = 0
        for desc, nb in zip(c['descs'], c['nb']):
            words.append((1, int(desc)))
            for _ in range(nb):
                words.append((2, int(c['beats'][pi]))); pi += 1
        (cd / 'packets.mem').write_text(''.join(f'{(cls << 513) | (w << 1) | 1:0129x}\n' for cls, w in words))
        np_arg = [f'+NP={len(words)}']
        exe = build('tb_host_c_oneclk', ROOT / TB, 0, f'{case}_m0')
        run(exe, f'{case}_m0', np_arg, True, 'HOST_ONECLK PASS', cd)
        summary[case] = records[-1]['line']
        exe = build('tb_host_c_oneclk', ROOT / TB, 3, f'{case}_m3')
        run(exe, f'{case}_m3', np_arg, False, 'HOST_ONECLK FAIL', cd)
        # IKEY uses the key-offset term, ROWS the local*pitch term: each case carries its own arithmetic mutant (the
        # sb*0x880 term is zero in these workloads; it is covered by the all-input SAT proof above).
        mname, mfile = ('koff_row', badkv) if case == 'ikey' else ('lp_plus1', badlp)
        exe = build('tb_host_c_oneclk', ROOT / TB, 0, f'{case}_{mname}', swap={'rtl/hdc/ingest/ot_hdc_kv_ingest.sv': mfile})
        run(exe, f'{case}_{mname}', np_arg, False, 'HOST_ONECLK FAIL', cd)
        exe = build('tb_host_c_oneclk', ROOT / TB, 0, f'{case}_csr_leak', swap={SRC[0]: badhc})
        run(exe, f'{case}_csr_leak', np_arg, False, 'HOST_ONECLK FAIL', cd)
    boot = (ROOT / BOOT_TB).read_text().replace('.ck_ingest({ck,ck}),', '')
    assert '.ck_ingest' not in boot
    btb = out / 'tb_host_boot300_oneclk.sv'; btb.write_text(boot)
    bd = out / 'boot'; bd.mkdir(exist_ok=True)
    exe = build('tb_host_boot300', btb, 0, 'boot0')
    for ph in range(8):
        run(exe, f'boot_phase{ph}', [f'+serial_phase={ph}'], True, 'BOOT300 PASS', bd)
    for name, arg in [('stop', '+stop_boot=1'), ('capacity', '+overload=1')]:
        run(exe, 'boot_' + name, [arg], True, 'BOOT300 FAIL_EXPECTED', bd)
    exe = build('tb_host_boot300', btb, 5, 'boot_kind_mutant')
    run(exe, 'boot_kind_mutant', [], False, 'BOOT300 FAIL payload/kind', bd)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    rec = dict(scope=__doc__, defines=DEFS, reference_modules=mods, reference_sha256=sha(ref),
               source_sha256={x: sha(ROOT / x) for x in SRC + [TB, BOOT_TB, 'tools/s81_static_control/host_c_oneclk_gate.py',
                                                             'tools/rtl_rom_host_ingest_bench.py']},
               calendars={c: {x: sha(out / c / f'{x}_calendar_m0.tsv') for x in ['emit', 'completion']} for c in ['ikey', 'rows']},
               input_slots=dict(first=128, stride=32, final_verification_edge=60000),
               added_cycles=dict(native_payload=0, completion=0, boot='0 vs legacy PHASESAFE (edge-exact compare)'),
               summary=summary, cases=records)
    (out / 'record.json').write_text(json.dumps(rec, indent=2) + '\n')
    print('HOST_ONECLK_GATE PASS ikey[' + summary['ikey'] + '] rows[' + summary['rows'] + '] + all-input address SAT + MUT3/csr-leak/koff/lp/sbm negatives + boot 8 phases/stop/capacity/kind')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Exact gate for the REGISTERED_BOUNDARY W2 station (bank veto + rb chain).

1. Bank bench tb_w2_bank_veto (registered-veto invariant: normal => q===protected
   value on every edge, plus every original corruption scenario) in both bank
   configurations used by the station (STAGE0/DIST1 payload, STAGE1/DIST0 small).
2. The released quarter publication bench (PASS19) on the rb chain. Its data,
   oracle, warm and fault stimuli are unchanged; three fixed timing waits become
   bounded waits (listed in BENCH_EDITS) because the rb chain is slower. The
   legacy chain runs the SAME edited bench for the calendar baseline.
3. Negative controls: each mutant must FAIL the bench that targets it.
   (The EVAL "settled" qualifier is not a safety mechanism: removing it only
   adds redundant recheck edges, since normal itself is sampled in EVAL and an
   EVAL excursion lasts >= 4 edges; it is therefore not a negative control.)
"""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q = 'physical/hbm_die_abstracts_20261006/links/native_quarter'
BANK = 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank_veto.sv'
STATION = Q+'/ot_hbm_native_frame_station_rb.sv'
CHAIN = Q+'/ot_hbm_native_quarter_chain_rb.sv'
BANK_TB = 'rtl/hbm_accel/integrated_20261005/tb_w2_bank_veto.sv'
VETO_TB = 'rtl/test/hbm_accel/w2_rb_veto_20261006/tb_w2_rb_cross_bank_veto.sv'
PKG = ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv']
CAL = ('module tb_native_quarter_publication;',
 'module tb_native_quarter_publication;\n integer edge_count=0; always @(posedge clk_sm) edge_count<=edge_count+1;\n'
 ' integer first_tap=-1,all_sm=-1,last_ack=-1;\n'
 ' always @(posedge clk_sm) if(tap_v[0]&&q_r&&first_tap<0) begin first_tap=edge_count; $display("CALENDAR_TAP_ACCEPT edge=%0d",edge_count); end\n'
 ' always @(posedge clk_sm) if(accepted==8\'hff&&all_sm<0) begin all_sm=edge_count; $display("CALENDAR_ALL_SM edge=%0d",edge_count); end\n'
 ' always @(posedge clk_sm) if(sm_ack==8\'h01&&!negative) begin last_ack=edge_count; $display("CALENDAR_LAST_SM_ACK edge=%0d",edge_count); end\n'
 ' always @(posedge clk_sm) if(q_ack_v && ack_gate) $display("CALENDAR_QUARTER_ACK edge=%0d",edge_count);\n'
 ' always @(posedge clk_sm) if(activation_release && activation_release_r) $display("CALENDAR_PARENT_RELEASE edge=%0d",edge_count);\n'
 ' always @(posedge clk_sm) if(warm_ack) $display("CALENDAR_WARM_ACK edge=%0d",edge_count);')
BENCH_EDITS = [
 ("  repeat(12)@(negedge clk_sm);\n  if(!q_ack_v)",
  "  for(integer k=0;k<200&&!q_ack_v;k++)@(negedge clk_sm);\n  if(!q_ack_v)",
  'fixed 12-edge wait for the empty-receipt release -> bounded 200-edge wait (same check)'),
 ("  @(negedge clk_sm);wait(q_ack_v);",
  "  for(integer k=0;k<20&&q_ack_v;k++)@(negedge clk_sm);\n  if(q_ack_v)$fatal(1,\"held receipt CE was not withdrawn\");\n  wait(q_ack_v);",
  'held-receipt CE: wait for the (registered, <=20 edge) withdrawal before the 4-edge hold check; withdrawal is now itself checked'),
 ("  do @(posedge clk_sm);while(tap_ACK_r!==4'hf);@(negedge clk_sm);other_ack=0;ack_gate=0;",
  "  do @(posedge clk_sm);while(tap_ACK_r!==4'hf);@(negedge clk_sm);other_ack=0;@(negedge clk_sm);ack_gate=0;",
  'STRONGER stimulus: the parent-side ACK gate stays open one more edge, so a held quarter ACK presented twice is counted by the existing quarter_acks==1 check'),
 ("  wait(warm_ack);if(!chain_warm||!chain_empty)",
  "  wait(warm_ack);for(integer k=0;k<8&&!(chain_warm&&chain_empty);k++)@(negedge clk_sm);\n  if(!chain_warm||!chain_empty)",
  'registered drained/warm status: <=8 edges after warm_ack (same check)'),
]
BANK_MUTANTS = {
 'B1_live_q_no_alignment': (BANK, '  assign q[g*64+:64]=q_d2[g];', '  assign q[g*64+:64]=raw64(code[g]);'),
 'B2_copy_check_removed': (BANK, '   f2<=m_ctlbad || (|m_cbad) ||', '   f2<=m_ctlbad || 1\'b0 ||'),
 'B3_controller_check_removed': (BANK, '   f2<=m_ctlbad ||', '   f2<=1\'b0 ||'),
 'B4_red_data_not_delayed': (BANK, '  always @(posedge clk)for(integer w=0;w<WORDS;w=w+1)r_q[w]<=q_d1[w];', '  always @*for(integer w=0;w<WORDS;w=w+1)r_q[w]=q_d1[w];'),
}
CHAIN_MUTANTS = {
 'S1_sm_duplicate_mask_removed': (CHAIN, '   assign sm_v[I]=ov[t]&&!fault&&!smj[I];assign ready[t]=sm_r[I]&&!fault&&!smj[I];',
                                  '   assign sm_v[I]=ov[t]&&!fault;assign ready[t]=sm_r[I]&&!fault;'),
 'S2_parent_ack_mask_removed': (CHAIN, ' assign tap_ACK_v=rv[0]&&!fault&&!tj;assign rr[0]=tap_ACK_r&&!fault&&!tj;',
                                ' assign tap_ACK_v=rv[0]&&!fault;assign rr[0]=tap_ACK_r&&!fault;'),
 'S3_frame_check_removed': (STATION, '   assign frame_bad[t]=ackv_q[t]&&fne_q[t];', '   assign frame_bad[t]=1\'b0;'),
 'S4_held_release_ignored': (STATION, '&&(held_p||!rv);', '&&(!rv);'),
 'S6_cross_bank_veto_removed': (STATION, '  assign fault_any=fault_x;', '  assign fault_any=1\'b0;'),
 'S7_ack_frame_stage_skipped': (STATION, '   ackv_q<=ackv_p;acko_q<=acko_p;', '   ackv_q<=ACK_v;acko_q<=ACK_owner;'),
 'S8_rel_q_decision_removed': (STATION, 'rel_q<=rel_ok_d&&!release_all;', "rel_q<=1'b1;"),
 'S5_learned_send_not_recorded': (STATION, '    if(learned[t]||pend[t])ns[t]=1;', '    if(1\'b0)ns[t]=1;'),
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, log):
    with open(log, 'w') as f:
        try:  # a negative control that hangs is detected by the watchdog (rc 124)
            return subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=3600 if cmd[0] == 'vvp' else None).returncode
        except subprocess.TimeoutExpired:
            return 124


RELREG = False
HALFV = False
CHAIN_DEF_OLD = 'module ot_hbm_native_quarter_chain_rb #(parameter integer ENABLE=0,STN_HALF=0)('
DEF_OLD = 'parameter integer ENABLE=0,NO=3,REL_REG=0,SAFE=0'
SAFEV = False


def relreg(out, files):
    """REL_REG=1 variant of the station (default flipped in a copy; mutants keep their edit)."""
    if not RELREG:
        return files
    res = []
    for f in files:
        if f.endswith('ot_hbm_native_frame_station_rb.sv'):
            t = Path(f).read_text(); assert t.count(DEF_OLD) == 1
            d = out/('relreg_'+hashlib.sha256(f.encode()).hexdigest()[:8]); d.mkdir(exist_ok=True)
            m = d/Path(f).name; m.write_text(t.replace(DEF_OLD, DEF_OLD.replace('REL_REG=0,SAFE=0', 'REL_REG=1,SAFE=%d' % (1 if SAFEV else 0)))); f = str(m)
        res.append(f)
    return res


def mutate(out, name, files):
    """Return file list with at most one mutated copy written under out/name."""
    if name is None:
        return relreg(out, files)
    path, old, new = {**BANK_MUTANTS, **CHAIN_MUTANTS}[name]
    text = (ROOT/path).read_text()
    assert text.count(old) == 1, (name, old)
    d = out/name; d.mkdir(exist_ok=True)
    m = d/Path(path).name; m.write_text(text.replace(old, new))
    return relreg(out, [str(m) if f == str(ROOT/path) else f for f in files])


def bank_bench(out, tag, stage, dist, mutant=None, red=1):
    files = [str(ROOT/p) for p in PKG+[BANK, BANK_TB]]
    files = mutate(out, mutant, files)
    vvp = out/f'{tag}.vvp'
    rc = run(['iverilog', '-g2012', f'-DVETO_STAGE={stage}', f'-DVETO_DIST={dist}', f'-DVETO_RED={red}', '-s', 'tb_w2_bank_veto_top', '-o', str(vvp), *files], out/f'{tag}.compile.log')
    if rc:
        return dict(compile_exit=rc, passed=False)
    rc = run(['vvp', str(vvp)], out/f'{tag}.run.log')
    text = (out/f'{tag}.run.log').read_text()
    return dict(compile_exit=0, runtime_exit=rc, passed=rc == 0 and 'PASS_W2_VETO' in text,
                summary=[l for l in text.splitlines() if l.startswith(('PASS', 'CE_REPAIR', 'FATAL', 'VETO'))][-3:])


def veto_bench(out, tag, mutant=None):
    """Station cross-bank veto bench: a station rail upset with healthy banks."""
    files = [str(ROOT/p) for p in PKG+[BANK, 'rtl/common/ot_fwd_link_stage.sv', STATION, VETO_TB]]
    files = mutate(out, mutant, files)
    vvp = out/f'{tag}.vvp'
    rc = run(['iverilog', '-g2012', '-s', 'tb_w2_rb_cross_bank_veto', '-o', str(vvp), *files], out/f'{tag}.compile.log')
    if rc:
        return dict(compile_exit=rc, passed=False)
    rc = run(['vvp', str(vvp)], out/f'{tag}.run.log')
    text = (out/f'{tag}.run.log').read_text()
    return dict(compile_exit=0, runtime_exit=rc, passed=rc == 0 and 'PASS_W2_RB_CROSS_BANK_VETO' in text,
                summary=[l for l in text.splitlines() if l.startswith(('PASS', 'FATAL'))][-2:])


VETO_MUTANTS = ('S6_cross_bank_veto_removed',)


def quarter_bench(out, tag, rb=True, mutant=None):
    srcs = (ROOT/Q/'sources.f').read_text().split()
    files = [str(ROOT/s) for s in srcs]
    if rb:
        files = [f for f in files if not f.endswith(('ot_hbm_native_frame_station.sv', 'ot_hbm_native_quarter_chain.sv'))]
        files += [str(ROOT/BANK), str(ROOT/STATION), str(ROOT/CHAIN)]
        if HALFV:
            files += [str(ROOT/Q/'ot_hbm_native_frame_station_rb_half.sv')]
    files = mutate(out, mutant, files)
    if HALFV and rb:  # the chain instantiates the half-rate shell instead of the station (text swap in a copy)
        d = out/('half_'+tag); d.mkdir(exist_ok=True); nf = []
        for f in files:
            if f.endswith('ot_hbm_native_quarter_chain_rb.sv'):
                t = Path(f).read_text(); old = 'ot_hbm_native_frame_station_rb #('; assert t.count(old) == 1
                m = d/Path(f).name; m.write_text(t.replace(old, 'ot_hbm_native_frame_station_rb_half #(')); f = str(m)
            nf.append(f)
        files = nf
    tb = (ROOT/Q/'tb_native_quarter_publication.sv').read_text()
    for old, new, _ in BENCH_EDITS + [CAL+(None,)]:
        assert tb.count(old) == 1, old
        tb = tb.replace(old, new)
    if rb:
        old = 'ot_hbm_native_quarter_chain #(.ENABLE(1)) chain('
        assert tb.count(old) == 1
        tb = tb.replace(old, 'ot_hbm_native_quarter_chain_rb #(.ENABLE(1)) chain(')
    if HALFV and rb:
        tb = tb.replace('.u_station.held.', '.u_station.hs.u_core.held.')
        # half rate: the registered drained/warm status settles in <=40 edges (2x the core step)
        assert tb.count('k<8&&!(chain_warm&&chain_empty)')==1
        tb = tb.replace('k<8&&!(chain_warm&&chain_empty)', 'k<40&&!(chain_warm&&chain_empty)')
        o2 = '  repeat(6)@(negedge clk_sm);\n  if(!chain_fault||q_ack_v'
        assert tb.count(o2)==1
        tb = tb.replace(o2, '  for(integer k=0;k<80&&!chain_fault;k++)@(negedge clk_sm);\n  repeat(6)@(negedge clk_sm);\n  if(!chain_fault||q_ack_v')
    tbp = out/f'{tag}_tb.sv'; tbp.write_text(tb)
    vvp = out/f'{tag}.vvp'
    rc = run(['iverilog', '-g2012', *os.environ.get('OT_IVL', '').split(), '-s', 'tb_native_quarter_publication', '-o', str(vvp), *files, str(tbp)], out/f'{tag}.compile.log')
    if rc:
        return dict(compile_exit=rc, passed=False)
    rc = run(['vvp', str(vvp)], out/f'{tag}.run.log')
    text = (out/f'{tag}.run.log').read_text()
    cal = {}
    for l in text.splitlines():
        if l.startswith('CALENDAR_') and ' edge=' in l:
            k, v = l.split(' edge=')
            cal.setdefault(k[9:], int(v))
    return dict(compile_exit=0, runtime_exit=rc, passed=rc == 0 and 'PASS_NATIVE_QUARTER_PUBLICATION' in text,
                calendar=cal, summary=[l for l in text.splitlines() if l.startswith(('PASS', 'FATAL'))][-2:],
                tb_sha256=sha(tbp))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True)
    ap.add_argument('--quarter-only', action='store_true')
    ap.add_argument('--neg-only', default=None, help='run one chain mutant only (exit 1 = rejected)')
    ap.add_argument('--half', action='store_true', help='half-rate station shell (quarter bench only)')
    ap.add_argument('--safe', action='store_true', help='SAFE=1 (registered permission decision), implies --rel-reg')
    ap.add_argument('--rel-reg', action='store_true', help='REL_REG=1 station (registered release)')
    ap.add_argument('--skip-legacy', action='store_true', help='calendar baseline already recorded (r1)'); a = ap.parse_args()
    global RELREG, SAFEV, HALFV; RELREG = a.rel_reg or a.safe; SAFEV = a.safe; HALFV = a.half
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    if a.quarter_only:
        r = quarter_bench(out, 'quarter_rb', True)
        print(json.dumps(r, indent=1)); raise SystemExit(0 if r['passed'] else 1)
    if a.neg_only:  # single negative control: exit 1 when the mutant is (correctly) rejected, 0 if it slips through
        r = quarter_bench(out, 'neg_only', True, a.neg_only)
        print('NEG_ONLY', a.neg_only, 'REJECTED' if not r['passed'] else 'ACCEPTED'); print('FAIL' if not r['passed'] else 'PASS')
        raise SystemExit(1 if not r['passed'] else 0)
    res = dict(bank={}, quarter={}, negative_controls={})
    res['bank']['payload_STAGE0_DIST1'] = bank_bench(out, 'bank_s0d1', 0, 1)
    res['bank']['small_STAGE1_DIST0'] = bank_bench(out, 'bank_s1d0', 1, 0)
    res['bank']['small_STAGE1_DIST0_RED0'] = bank_bench(out, 'bank_s1d0_red0', 1, 0, red=0)
    res['bank']['payload_STAGE0_DIST1_RED0'] = bank_bench(out, 'bank_s0d1_red0', 0, 1, red=0)
    res['quarter']['rb'] = quarter_bench(out, 'quarter_rb', True)
    res['veto'] = {'rb': veto_bench(out, 'veto_rb')}
    if not a.skip_legacy:
        res['quarter']['legacy_same_bench'] = quarter_bench(out, 'quarter_legacy', False)
    for name in BANK_MUTANTS:
        r = bank_bench(out, 'neg_'+name, 0, 1, name)
        res['negative_controls'][name] = dict(expected='FAIL', failed=not r['passed'], **r)
    for name in CHAIN_MUTANTS:
        if name == 'S8_rel_q_decision_removed' and not RELREG:
            continue
        r = veto_bench(out, 'neg_'+name, name) if name in VETO_MUTANTS else quarter_bench(out, 'neg_'+name, True, name)
        res['negative_controls'][name] = dict(expected='FAIL', failed=not r['passed'], **r)
    rb, leg = res['quarter']['rb'].get('calendar', {}), res['quarter'].get('legacy_same_bench', {}).get('calendar', {})
    res['calendar_delta_edges_vs_legacy'] = {k: rb[k]-leg[k] for k in rb if k in leg}
    res['bench_edits'] = [e[2] for e in BENCH_EDITS]
    pin_paths = [BANK, STATION, CHAIN, BANK_TB, VETO_TB, Q+'/tb_native_quarter_publication.sv', *PKG]
    if HALFV:
        pin_paths.append(Q+'/ot_hbm_native_frame_station_rb_half.sv')
    res['source_pins'] = {p: sha(ROOT/p) for p in pin_paths}
    res['passed'] = (all(v['passed'] for v in res['bank'].values()) and all(v['passed'] for v in res['quarter'].values())
                     and res['veto']['rb']['passed']
                     and all(v['failed'] for v in res['negative_controls'].values()))
    (out/'terminal.json').write_text(json.dumps(res, indent=2)+'\n')
    for p in out.glob('*.vvp'):
        p.unlink()
    for p in out.glob('*/*.vvp'):
        p.unlink()
    print(out, 'PASS' if res['passed'] else 'FAIL')
    raise SystemExit(0 if res['passed'] else 1)


if __name__ == '__main__':
    main()

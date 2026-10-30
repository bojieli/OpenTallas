#!/usr/bin/env python3
"""Build the HEAD hd_ctl kit on the hk5 crop (587.52 x 518.4) from a HEAD-START source plan, with the LEC kit fixes.

DIE-HEAD-30 (COORD 2026-10-29 11:09).  The plain `gen.py phys --types hd_ctl` kit of the hk5 source (Codex
hk5_cropped, unit 3691615) failed port_bind: the 32 strap_ca_* count-strap bits had no pin sites (extra) and the
5 rst_start_raw_* START exports were never added to the generated wrapper (missing).  This builder applies the same
existing HEAD steps head_tile_source7_kit.py applies to hd_tile, then the two kit-only LEC fixes:
  1. count strap pin sites (head_count_strap_sites.apply) and private raw-reset exports
     (head_start_raw_private.prepare_plan) on a copy of the source plan, written next to it;
  2. `gen.py phys --trial --clock-landing SIDECAR --types hd_ctl` on that copy (the CLI Codex ran, same defaults);
  3. wrapper: head_start_reset_aliases.patch_rtl + head_start_raw_private.patch_rtl (rst_start_raw_* registered
     outputs of the recorded ot_dp_rrelay instances, 0 cycles);
  4. LEC fix (a) FSM re-encoding: `export OT_FSM_NONE_WIRES = st ek` (ot_keep_regs.tcl hook, the existing
     FSM-mapping path of tools/ref_tile/cdc_fsm_guard.py): u_seq st/ek keep their RTL encoding and names;
  5. LEC fix (b) dead kept copies: hsf0_static g_rsel[k].u_d only for k < 5.  sd_c[k] gates d6d[32k .. 32k+31]
     (ro_q[i] <= ... | sd_c[(i-1)/32] & d6d[i-1]); d6d = {payload, 20-bit header} with payload sd_q (SW = 77 bits,
     d6d[20..96]) or hs_q << 80 (DW = 34, d6d[100..133]), so d6d[j] == 0 for j >= 134 and sd_c[5..16] only gate
     constant zeros.  Those 12 kept flops were merged by synthesis (KEEP FAIL 12 of 13,864).  sd_c[k >= 5] is
     tied 0: same function (the LEC proves it), 12 flops fewer, 0 cycles.
    python3 tools/s81_head/head_ctl_hk5_kit.py SOURCE_DIR OUT_DIR
SOURCE_DIR holds source_plan.json + source_sidecar.json (HEAD-START hk5_source/source); OUT_DIR must not exist."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/die_plan'), str(ROOT / 'tools/s81_head')]
from head_count_strap_sites import apply as count_strap_sites  # noqa: E402
from head_start_raw_private import prepare_plan, patch_rtl as private_raw_rtl  # noqa: E402
from head_start_reset_aliases import patch_rtl  # noqa: E402

TYPE = 'hd_ctl'
OUTLINE = [587.52, 518.4]
FSM_NONE = 'st ek'
RSEL_OLD = '        ot_s81hd_kf u_d (.ck(ck),.d(sd_pop||hs_pop),.q(sd_c[k]));\n'
RSEL_NEW = ('        // DIE-HEAD-30 kit fix: d6d[j] == 0 for j >= 134 (hs_q << 80 ends at bit 133), so sd_c[k >= 5] only\n'
            '        // gates constant zeros; its 12 kept copies were dead (merged by synthesis: LEC KEEP FAIL).\n'
            '        if (k < 5) begin : g_d\n'
            '            ot_s81hd_kf u_d (.ck(ck),.d(sd_pop||hs_pop),.q(sd_c[k]));\n'
            '        end else begin : g_d0\n'
            '            assign sd_c[k] = 1\'b0;\n'
            '        end\n')
D6D = ("        d6d <= {sd_pop ? {{(512-SW){1'b0}},sd_q} : ({{(512-DW){1'b0}},hs_q}<<80),4'd0,(sd_pop?T_SEED:T_DHS),"
       "4'd0,5'd1,3'd7};")
WIDTHS = 'localparam integer FW = 553, NW = 21, UW = 10, SW = UW + 3 * NW + 4, DW = UW + 3 + NW;'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rsel_fix(text):
    """g_rsel[k].u_d only for k < 5; fails closed unless the d6d layout that makes sd_c[5..16] dead is the one
    in this source (constant zero above bit 20 + max(SW, 80 + DW) - 1 = 133 < 160)."""
    if text.count(RSEL_OLD) != 1 or D6D not in text or WIDTHS not in text:
        raise ValueError('hsf0_static: g_rsel u_d / d6d layout differs from the reviewed source; re-derive the dead range')
    if 'for (k = 0; k < 17; k = k + 1) begin : g_rsel' not in text:
        raise ValueError('hsf0_static: g_rsel loop changed')
    uw, nw = 10, 21
    sw, dw = uw + 3 * nw + 4, uw + 3 + nw
    top = 20 + max(sw, 80 + dw) - 1
    if top >= 5 * 32:
        raise ValueError(f'd6d top live bit {top} reaches sd_c[5]')
    return text.replace(RSEL_OLD, RSEL_NEW), dict(removed_kept_flops=12, kept_sd_c=[0, 4], d6d_top_live_bit=top)


def build(source, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError('fresh output directory required: ' + str(out))
    path, side_path = source / 'source_plan.json', source / 'source_sidecar.json'
    plan = json.loads(path.read_text())
    t = plan['partition_types'][TYPE]
    if [float(x) for x in t['outline_um']] != OUTLINE:
        raise ValueError(f'{TYPE} outline {t["outline_um"]} is not the hk5 crop {OUTLINE}')
    plan, strap_sites = count_strap_sites(plan, path, ROOT, types={TYPE})
    plan, private_report = prepare_plan(plan, {TYPE})
    cand = path.with_name('source_plan_ctl_hk5.json')
    cand.write_text(json.dumps(plan, indent=1) + '\n')
    cmd = [sys.executable, str(ROOT / 'tools/die_plan/gen.py'), 'phys', str(cand), '--clock-landing', str(side_path),
           '--types', TYPE, '--out', str(out), '--rtl-root', str(ROOT), '--trial']
    r = subprocess.run(cmd, capture_output=True, text=True)
    (out.parent / (out.name + '.gen.log')).write_text(r.stdout + r.stderr)
    if r.returncode:
        raise ValueError(f'gen.py phys exit {r.returncode}: {(r.stdout + r.stderr)[-2000:]}')
    kit = out / TYPE
    t = plan['partition_types'][TYPE]
    wrapper = out / '_rtl' / f"{t['module']}.sv"
    rows = t.get('reset_start_raw_exports', [])
    text = patch_rtl(wrapper.read_text(), rows)
    text, private_rtl_report = private_raw_rtl(text, t)
    wrapper.write_text(text)
    (kit / 'rtl' / wrapper.name).write_text(text)
    hsf = kit / 'rtl' / 'ot_s81hd_ctl_hsf0_static.sv'
    htext, rsel_report = rsel_fix(hsf.read_text())
    hsf.write_text(htext)
    cfg = kit / 'config.mk'
    ctext = cfg.read_text()
    if 'OT_FSM_NONE_WIRES' in ctext:
        raise ValueError('config.mk already sets OT_FSM_NONE_WIRES')
    if 'export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl' not in ctext:
        raise ValueError('kit has no ot_keep_regs.tcl canonicalize hook: OT_FSM_NONE_WIRES would be ignored')
    cfg.write_text(ctext + '# DIE-HEAD-30 LEC kit fix (COORD 10-29 11:09): u_seq st/ek keep their RTL encoding '
                   '(ot_keep_regs.tcl fsm_encoding none)\n'
                   f'export OT_FSM_NONE_WIRES = {FSM_NONE}\n')
    report = dict(type=TYPE, outline_um=OUTLINE, source_plan_sha256=sha(path), source_sidecar_sha256=sha(side_path),
                  candidate_plan=str(cand), candidate_plan_sha256=sha(cand), gen_cmd=cmd,
                  count_strap_sites=strap_sites, private_raw_exports=private_report,
                  private_raw_rtl=private_rtl_report, raw_reset_exports=len(rows),
                  lec_fixes=dict(fsm_none_wires=FSM_NONE, g_rsel=rsel_report),
                  kit_rtl_sha256={p.name: sha(p) for p in sorted((kit / 'rtl').glob('*.sv'))},
                  added_cycles=0, route_qualified=False)
    (out / 'ctl_hk5_receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('type', 'raw_reset_exports', 'lec_fixes', 'count_strap_sites')}))
    return kit


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', type=Path)
    ap.add_argument('out', type=Path)
    a = ap.parse_args()
    build(a.source, a.out)


if __name__ == '__main__':
    main()

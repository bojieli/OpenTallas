#!/usr/bin/env python3
"""frame_plan_events.py -- S81-BF-GOBF 11-11: replay the in-place plan events of the col frame band plan kits.

rtl/dsrom_sys/s81_dv/frame_lp/plan/col_<M>_l4_lp_plan_kit.sv (the die-plan band sources the die binds,
physical/die_plan/s81/bind/asbuilt_s81.py) is NOT the bare tools/s81_dv/frame_band_plan.py output: two plan events
edited it in place afterwards, neither with a re-runnable generator.  This tool replays exactly those RTL edits on a
fresh frame_band_plan.py output, so the band plan kits regenerate from the frame chain (control 11-11: frame_band_plan
+ this tool on main cd5748bb22 == the committed plan_kit.sv byte for byte, col_h9 and col_h10).

  (a) DIE-S81-70 ROMQ-SPLIT-1106 (COORD-REVIEW-QUEUE 2026-11-06 16:56 PST READY [DIE-S81-70 ...] rom_q split plan
      event, claude/die-s81-70-romqsplit-1106@c34808abe5; COORD 13:0x (b) option A): RTL part of
      physical/die_plan/s81/delta_romq_split_1106.py lines 318-337 (main(), "# RTL: col frame sources"): every
      `ot_v41_rom_elem_q_qxpq_w10 u_e<k> (` becomes the dissolved split wrapper
      `ot_v41_rom_elem_q_qxpq_w10_gb_split #(.OLAT(1)) u_e<k> (` without its `.xs_sv({...}), ` connection; 16 per
      master (asserted, as there).  The plan / asbuilt JSON part of that event is already on main and is not touched.
  (b) DIE-S81-71 col station A1 (COORD-REVIEW-QUEUE 2026-11-06 17:28 PST STATE [DIE-S81-71 -> COORD] (1),
      claude/die-s81-71-colst-1106@86664ba9c3 on the romqsplit branch; spec s81_istations_native_spec_1106 "col st ->
      t0"): the r0 status hop u_r0.u_s0.st -> u_r0.u_t0.c0 gets a line-stable reset register chain cst_st_s0..s<D-1>
      in front of u_t0.c0, in col_<M>_l4_lp_r0 and col_<M>_l4_lp_r0_nx.  D = the plan's FIRM internal_stations depth
      of that hop (physical/die_plan/s81/die_plan.json partition_types col_<M>_r0_*, matched with
      tools/die_plan/kit_istations.py COL_ST, which also counts this chain back from the bound text; all entries must
      agree, fail closed): col_h9 2, col_h10 1.  Clock = u_t0's .ck, reset = u_t0's .rs (async low), width = the c0 bus.
Line counts are unchanged by both events (asserted).  frame_band_plan.py --core-reset-wavefront --from (the _cr kit)
reads the plan kit BEFORE these events on main (the committed _cr has neither event), so run it before this tool.

Chain notes (S81-BF-GOBF control 11-11; every stage byte for byte on main):
  frame_hier_kit.py --master col_h9 --tag vgch --base-kit s81frame_col_h9_vgc --cuts 1170,2250
      --edges 1183.68,2280.96 --shift 1170:17.28,2250:17.28        (without --shift the b1/b2 ref_tile specs move 17.28 um)
usage: frame_plan_events.py --master col_h9 --in PLAN_KIT.sv [--out OUT.sv] [--plan die_plan.json]"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import kit_istations as KI  # noqa: E402

ROMQ = 'ot_v41_rom_elem_q_qxpq_w10'
SPLIT = ROMQ + '_gb_split'
N_ROMQ = 16


def romq_split(src):
    """(a): delta_romq_split_1106.py lines 318-337, verbatim regexes"""
    pat = re.compile(r'^(\s*)' + ROMQ + r' (u_e\d+ \()(.*)$', re.M)
    cnt = 0

    def fix(m):
        nonlocal cnt
        cnt += 1
        body, k = re.subn(r'\.xs_sv\(\{[^}]*\}\), ', '', m.group(3))
        assert k == 1, m.group(2)
        return f'{m.group(1)}{SPLIT} #(.OLAT(1)) {m.group(2)}{body}'

    out = pat.sub(fix, src)
    assert cnt == N_ROMQ, f'rom_q split: {cnt} q elements, want {N_ROMQ}'
    return out, cnt


def col_st_depth(plan, master):
    """(b): the plan's FIRM depth of u_r0.u_s0.st -> u_r0.u_t0[.c0] over every col_<M>_r0* partition type"""
    ds = set()
    pts = plan['partition_types']
    for name, t in (pts.items() if isinstance(pts, dict) else ((x['name'], x) for x in pts)):
        if not name.startswith(f'{master}_r0'):
            continue
        for e in t.get('internal_stations', []):
            if not e.get('conn', '').startswith('bus:') and KI.COL_ST.match(KI._col_key(e)):
                ds.add(len(e['regs_um']))
    if len(ds) != 1:
        raise SystemExit(f'{master}: col st -> t0 plan depths {sorted(ds)} (need exactly one; fail closed)')
    return ds.pop()


def col_st(src, master, d):
    lines = src.split('\n')
    mod, hits = None, 0
    for i, ln in enumerate(lines):
        mm = re.match(r'^module (\w+)', ln)
        if mm:
            mod = mm.group(1)
            continue
        if mod not in (f'{master}_l4_lp_r0', f'{master}_l4_lp_r0_nx'):
            continue
        tm = re.match(r'^(\s*)(ot_s81_sstn_base566 u_t0 \(.*)$', ln)
        if not tm:
            continue
        ind, body = tm.groups()
        c0 = re.findall(r'\.c0\((\{[^}]*\})\)', body)
        ck = re.findall(r'\.ck\((\w+)\)', body)
        rs = re.findall(r'\.rs\((\w+)\)', body)
        assert len(c0) == len(ck) == len(rs) == 1, (mod, c0, ck, rs)
        src_net, ck, rs = c0[0], ck[0], rs[0]
        # the launch side: the c0 bus is u_s0's .st (fail closed)
        s0 = [l for l in lines if re.match(r'^\s*\w+ u_s0 \(', l) and f'.st({src_net})' in l]
        assert s0, f'{mod}: u_t0.c0 {src_net} is not u_s0.st'
        w = src_net.count(',') + 1
        regs, prev = [], src_net
        for j in range(d):
            q = f'cst_st_s{j}'
            regs.append(f'reg [{w - 1}:0] {q}; always @(posedge {ck} or negedge {rs}) if (!{rs}) {q} <= {w}\'b{"0" * w}; '
                        f'else {q} <= {prev};')
            prev = q
        body2 = body.replace(f'.c0({src_net})', f'.c0({prev})', 1)
        lines[i] = (f'{ind}/* DIE-S81-71 11-06 plan col station (A1, line-stable): u_s0.st -> u_t0.c0 = {d} FIRM '
                    f'stage(s) cst_st_s*, PIN CYCLES +{d}, reset of u_t0 */ ' + ' '.join(regs) + ' ' + body2)
        hits += 1
    assert hits == 2, f'{master}: u_t0 in r0 + r0_nx: {hits} (want 2)'
    return '\n'.join(lines), hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--master', required=True)
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--out')
    ap.add_argument('--plan', default=str(ROOT / 'physical/die_plan/s81/die_plan.json'))
    a = ap.parse_args()
    src = Path(a.inp).read_text()
    if SPLIT in src or 'cst_st_s0' in src:
        raise SystemExit(f'{a.inp}: events already applied (input must be the frame_band_plan.py output)')
    n = src.count('\n')
    t, nq = romq_split(src)
    d = col_st_depth(json.loads(Path(a.plan).read_text()), a.master)
    t, nt = col_st(t, a.master, d)
    assert t.count('\n') == n, 'events must be line-stable'
    Path(a.out or a.inp).write_text(t)
    print(f'{a.master}: (a) rom_q split {nq} q elements, (b) col st D={d} on {nt} u_t0 -> {a.out or a.inp}')


if __name__ == '__main__':
    main()

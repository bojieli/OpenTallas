#!/usr/bin/env python3
"""Shared die-net repeater step (DIE-FLOW 2026-10-17; owner ruling HANDOFF 0cl: repeaters inside a registered relay hop
are ordinary design, every die flow inserts native-aware repeaters on die nets).

The Tcl (die_repeaters.tcl, proc ot_die_repeaters) runs inside the caller's OpenROAD session after placement and
before global_route.  This module generates the call and judges the report, for every die flow:

    S81    physical/s81_die_views/dietop/dietop_grt_sta.sh   (OT_DIE_REPAIR=1; tools/s81/die_iter_chain.sh)
    Qwen   tools/qwen_kv_die/chain/die_chain.sh + grt.tcl    (OT_DIE_REPAIR=1; also tools/qwen_tp8/die_grt_launch.sh)
    HBM    tools/hbm_die_v15/die_case_v16.py --die-repeaters
    tops   tools/hbm_die_v15/cluster_case.py (die_cluster cluster tops)

    python3 tools/die_repeaters/step.py tcl --design s81 --report /work/die_repeaters.json --libs-file /kit/libs_tt.txt
    python3 tools/die_repeaters/step.py check RUN/die_repeaters.json      -> one STATUS line; exit 1 on FAIL
    python3 tools/die_repeaters/step.py copy DIR                          -> die_repeaters.tcl + cluster_bounds.tcl

Rule (defaults; env OT_DIE_REPAIR_MAX_WIRE / _SLEW / _SKIP / _REPEAT_NETS / _OVER_REACH override for the shell flows):
  * max wire 160 um: an unrepeated hop is slew-limited at ~175 um at the native ot_inhold first cell (H-REACH,
    tools/s81/relay_native_pair.py on closed native netlists + routed SPEF); one repeater from ~175 um then every
    ~160 um -> 600-750 um per cycle at TT 833 (repeated reach, M4/M5).  The 405-um planning hop is unchanged.
  * max transition 260 ps = the closed views' max_transition at the native receiver first cell (ETM pins hide it);
    a per-master receiver table (--receiver-slew JSON {master: ps}) may only lower it.
  * buffers BUFx4..BUFx8 only, never a register / hold cell; pre-existing instances never removed or resized (checked);
    clock / reset / special nets untouched, except forwarded-clock nets named by --repeat-nets (repeated with their
    data bits; DIE-CLOCK accepts fclk repeaters matched to the data to +-1 stage).  A master with signal pins and no
    liberty fails the step (its nets would be invisible to the resizer).
  * die nets longer than the measured die reach (results/arch/die_reach_1016.json via tools/die_reach.py) are a
    planning defect (missing relay register, standard 1): measured before repair and reported; --over-reach fail
    makes them a violation.
"""
import argparse, json, os, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

TCL = HERE / 'die_repeaters.tcl'
BOUNDS_TCL = ROOT / 'tools/die_cluster/cluster_bounds.tcl'
BUFFERS = ('BUFx4_ASAP7_75t_R', 'BUFx4f_ASAP7_75t_R', 'BUFx5_ASAP7_75t_R', 'BUFx6f_ASAP7_75t_R', 'BUFx8_ASAP7_75t_R')
DEFAULTS = dict(max_wire_um=160.0, slew_ps=260.0, over_reach='report', rc_layer='M4', legalize='snap',
                long_wire_scan=5000)
# per die flow: the die_reach design key and the clock / reset distribution net globs the step never touches
# (on top of the automatic skips: nets on register-clock / clock lib pins, CLOCK/POWER/GROUND sig type, special nets)
DESIGNS = {
    's81': dict(reach='s81', skip=('n_clk_*', 'n_rst_*', 'n_ck_col_*', 'n_rs_col_*')),
    'qwen_compute': dict(reach='qwen_compute', skip=('n_clk_*', 'n_fck_*')),   # + n_rst_* unless OT_ROUTE_RESET=1
    'qwen_kv': dict(reach='qwen_kv', skip=('n_clk_*', 'n_fck_*')),
    'hbm': dict(reach='hbm', skip=('dk?_*', 'n_dk?_*', 'ckg_*')),
    'cluster': dict(reach=None, skip=('clk_*', 'rst_*')),
}


def _reach(design):
    key = DESIGNS[design]['reach']
    if key is None:
        return 0.0
    try:
        import die_reach
        return die_reach.reach_um(key)
    except Exception:      # noqa: BLE001 -- a missing reach table only disables the over-reach report
        return 0.0


def _tcl_list(xs):
    return '{' + ' '.join('{%s}' % x for x in xs) + '}'


def config(design, report, **kw):
    """-> dict of the ot_die_repeaters cfg (env overrides applied; explicit kwargs win)."""
    if design not in DESIGNS:
        raise SystemExit(f'die_repeaters: unknown design {design!r} (known: {sorted(DESIGNS)})')
    c = dict(DEFAULTS, design=design, report=report, reach_um=_reach(design),
             skip_nets=list(DESIGNS[design]['skip']))
    env = os.environ
    if env.get('OT_DIE_REPAIR_MAX_WIRE'):
        c['max_wire_um'] = float(env['OT_DIE_REPAIR_MAX_WIRE'])
    if env.get('OT_DIE_REPAIR_SLEW'):
        c['slew_ps'] = float(env['OT_DIE_REPAIR_SLEW'])
    if env.get('OT_DIE_REPAIR_SKIP'):
        c['skip_nets'] += env['OT_DIE_REPAIR_SKIP'].split()
    if env.get('OT_DIE_REPAIR_REPEAT_NETS'):
        c['repeat_nets'] = list(c.get('repeat_nets') or []) + env['OT_DIE_REPAIR_REPEAT_NETS'].split()
    if env.get('OT_DIE_REPAIR_OVER_REACH'):
        c['over_reach'] = env['OT_DIE_REPAIR_OVER_REACH']
    for k, v in kw.items():
        if v is None:
            continue
        if k == 'skip_nets':
            c['skip_nets'] += list(v)
        else:
            c[k] = v
    if c['max_wire_um'] <= 0 or c['slew_ps'] <= 0:
        raise SystemExit('die_repeaters: max_wire_um and slew_ps must be > 0')
    if c['over_reach'] not in ('report', 'fail'):
        raise SystemExit("die_repeaters: over_reach must be 'report' or 'fail'")
    if c['legalize'] not in ('snap', 'dpl', 'none'):
        raise SystemExit("die_repeaters: legalize must be snap | dpl | none")
    return c


def tcl_call(design, report, tcl_dir='/work', fail_exit=3, **kw):
    """Tcl text: source the shared step and call it; exits the session with fail_exit on a violation."""
    c = config(design, report, **kw)
    rs = c.pop('receiver_slew', None) or {}
    parts = []
    for k, v in c.items():
        if isinstance(v, (list, tuple)):
            parts.append(f'{k} {_tcl_list(v)}')
        elif isinstance(v, float):
            parts.append(f'{k} {v:g}')
        else:
            parts.append(f'{k} {{{v}}}')
    if rs:
        parts.append('receiver_slew {%s}' % ' '.join(f'{{{m}}} {float(p):g}' for m, p in sorted(rs.items())))
    parts.append(f'bounds_tcl {{{tcl_dir}/cluster_bounds.tcl}}')
    return (f'# shared die-net repeater step (tools/die_repeaters/step.py, design {design})\n'
            f'source {tcl_dir}/die_repeaters.tcl\n'
            f'set ot_die_rep_v [ot_die_repeaters [dict create {" ".join(parts)}]]\n'
            f'if {{$ot_die_rep_v != 0}} {{ puts "OT_DIE_REP FAIL violations=$ot_die_rep_v"; flush stdout; exit {fail_exit} }}\n')


def copy(dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(TCL, dest / 'die_repeaters.tcl')
    shutil.copy(BOUNDS_TCL, dest / 'cluster_bounds.tcl')
    return [dest / 'die_repeaters.tcl', dest / 'cluster_bounds.tcl']


def check(report):
    """-> (ok, one-line summary) of a die_repeaters.v1 report"""
    p = Path(report)
    if not p.exists():
        return False, f'DIE_REPEATERS MISSING {p}'
    r = json.loads(p.read_text())
    ok = r.get('schema') == 'opentallas.die_repeaters.v1' and r.get('verdict') == 'PASS' and r.get('violations') == 0
    s = (f"DIE_REPEATERS {'PASS' if ok else 'FAIL'} repeaters={r.get('repeaters')} "
         f"max_wire={r.get('max_wire_um')} slew={r.get('max_transition_ps')} removed={r.get('removed')} "
         f"resized={r.get('resized')} non_buffer={r.get('non_buffer_inserted')} skip_nets={r.get('skip_nets')} "
         f"longest={r.get('longest_um')} over_reach({r.get('reach_um')})={r.get('over_reach_nets')} "
         f"legalize={r.get('legalize')!r}")
    return ok, s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('tcl', help='print the Tcl call')
    t.add_argument('--design', required=True, choices=sorted(DESIGNS))
    t.add_argument('--report', required=True)
    t.add_argument('--dir', default='/work', help='container dir holding die_repeaters.tcl + cluster_bounds.tcl')
    t.add_argument('--libs-file', help='text file, one liberty per line (read inside the step), e.g. /kit/libs_tt.txt')
    t.add_argument('--libs', nargs='*', default=None)
    t.add_argument('--std-corner', choices=['TT', 'FF', 'SS'])
    t.add_argument('--legalize', choices=['snap', 'dpl', 'none'])
    t.add_argument('--max-wire-um', type=float)
    t.add_argument('--slew-ps', type=float)
    t.add_argument('--receiver-slew', type=Path, help='JSON {master: max input slew ps} of the native first cells')
    t.add_argument('--skip', nargs='*', default=None, help='extra net globs left untouched')
    t.add_argument('--repeat-nets', nargs='*', default=None,
                   help='forwarded-clock net globs repeated with their data bits (override the clock skips)')
    t.add_argument('--over-reach', choices=['report', 'fail'])
    t.add_argument('--rc-layer')
    t.add_argument('--repair-args')
    t.add_argument('--exit-code', type=int, default=3)
    c = sub.add_parser('check', help='judge a report')
    c.add_argument('report')
    k = sub.add_parser('copy', help='copy the Tcl files into a run dir')
    k.add_argument('dest')
    a = ap.parse_args(argv)
    if a.cmd == 'copy':
        for p in copy(a.dest):
            print(p)
        return 0
    if a.cmd == 'check':
        ok, s = check(a.report)
        print(s)
        return 0 if ok else 1
    libs = list(a.libs or [])
    libs_tcl = ''
    if a.libs_file:   # read at run time inside the container (paths valid there)
        libs_tcl = (f'set ot_die_rep_libs {{}}\nforeach l [split [string trim [read [open {a.libs_file}]]] "\\n"] '
                    f'{{ if {{$l ne ""}} {{ lappend ot_die_rep_libs $l }} }}\n')
    rs = json.loads(a.receiver_slew.read_text()) if a.receiver_slew else None
    body = tcl_call(a.design, a.report, tcl_dir=a.dir, fail_exit=a.exit_code, libs=libs or None, std_corner=a.std_corner,
                    legalize=a.legalize, max_wire_um=a.max_wire_um, slew_ps=a.slew_ps, receiver_slew=rs,
                    skip_nets=a.skip, repeat_nets=a.repeat_nets, over_reach=a.over_reach, rc_layer=a.rc_layer, repair_args=a.repair_args)
    if a.libs_file:
        body = body.replace('[dict create ', '[dict create libs [concat $ot_die_rep_libs ' + _tcl_list(libs) + '] ', 1)
        body = body.replace(f' libs {_tcl_list(libs)}', '', 1) if libs else body
    sys.stdout.write(libs_tcl + body)
    return 0


if __name__ == '__main__':
    sys.exit(main())

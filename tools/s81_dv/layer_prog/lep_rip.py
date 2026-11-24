#!/usr/bin/env python3
"""lep ring-out (ri) date per partition type: the RIP relay stages of ot_s81sl_slice_lep.

RIP (FABLE-FIX-S81-LEPE 11-19) delays ri ONLY, by exactly RIP edges; mu_rt is not delayed.  ri is date-dependent:
it enters the end slice tier line, a static schedule (ot_s81sl_rstop: one source per line side and cycle; ot_s81sl_xr:
two CTL / RD / lo beats in a cycle are sticky faults) and the MU shift calendar has no ready / credit / stall.  So
every ri date (LATCHECK ri lane K, the lep stage hop once lowered) takes + lep_ri_rip(type).

RIP comes from the type's plan verilog_defines (bare selectors OT_S81SL_LEP_RIP<n>, parsed from the RTL so a new
selector is picked up) or an explicit OT_S81SL_LEP_RIP=<n> kit define.  A type that sets RIP only in its kit
config.mk is not seen by bind elab: pass the kit defines as well and refuse a mismatch (check_kit).

  lep_rip.py --plan PLAN.json [--rtl ot_s81sl_slice_lep.sv]               per-type table (types with a lep)
  lep_rip.py --trace-ref rit_rip0.txt --trace rit_X.txt --defines D,...   fails unless every beat is ref + RIP
"""
import argparse, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if os.path.isdir(os.environ.get('OT_REPO_ROOT') or ''):   # REPO-ROOT-1123 convention (bind_elab.REPO): the tree being bound
    ROOT = Path(os.environ['OT_REPO_ROOT']).resolve()
RTL = ROOT / 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv'


def selectors(rtl=RTL, knob='RIP'):
    """{bare selector: n} from the `ifdef OT_S81SL_LEP_<knob><n> ... `define OT_S81SL_LEP_<knob> <n> blocks
    (knob RIP = ring-out relay stages, ROS = input face stages)."""
    text = Path(rtl).read_text()
    k = 'OT_S81SL_LEP_' + knob
    out = {}
    for m in re.finditer(rf'`ifdef\s+({k}\w+)\s*\n\s*`ifndef\s+{k}\s*\n\s*`define\s+{k}\s+(\d+)', text):
        out[m.group(1)] = int(m.group(2))
    if not out:
        raise ValueError(f'no {k} selectors found in ' + str(rtl))
    # the default is the LAST guarded define (each selector block nests the same `ifndef / `define / `endif)
    m = re.findall(rf'`ifndef\s+{k}\s*\n\s*`define\s+{k}\s+(\d+)\s*\n\s*`endif', text)
    if len(m) != len(out) + 1:
        raise ValueError(f'cannot tell the {knob} default from the selector blocks in ' + str(rtl))
    return out, int(m[-1])


def lep_knob(defines, knob, rtl=RTL):
    """<knob> value for one define list (bare names or NAME=value).  The first `ifdef in the RTL wins, as in the preprocessor."""
    sel, default = selectors(rtl, knob)
    names = {}
    for d in defines:
        k, _, v = (d[2:] if d.startswith('-D') else d).partition('=')
        names[k] = v
    if 'OT_S81SL_LEP_' + knob in names:
        return int(names['OT_S81SL_LEP_' + knob])
    text = Path(rtl).read_text()
    for name in sorted(sel, key=lambda s: text.index('`ifdef ' + s)):
        if name in names:
            return sel[name]
    return default


def lep_ri_rip(defines, rtl=RTL):
    """RIP (relay stages on the ring output ri only) for one define list"""
    return lep_knob(defines, 'RIP', rtl)


# ROS (FAM-S81-LEPE 11-21, ot_s81sl_slice_lep g_inpipe): ROS extra face stages on ALL FOUR lep input ports ro / t_host / t_kd /
# mu_c and their valid copies.  In the bound LP piece (bind wrapper s81p_dsdv_slice_lep*_LP) they are fed from the type IN buses
#   ro     = {lepf_i0[0], lepk_i0[1103:1]}        mu_c = unit_i0[44:11]
#   t_host = unit_i0[116,121:117,115:45]          t_kd = unit_i0[175:122]          (lepe_mu_LP t2; nh / lepw types: mu_c only)
# so the lanes that END on lepk_i* / lepf_i* / unit_i* of a ROS type land ROS edges later at the lep.  Bits of those buses that
# do not enter u_lep (lepk_i0[0] = land reset relay, unit_i0[10:0] = rc of the landing) bypass the stages.
ROS_IN_BUSES = ('lepk_i', 'lepf_i', 'unit_i')
ROS_BYPASS = {'lepk_i': 'bit 0 (land reset relay)', 'unit_i': 'bits 10:0 (rc to the landing)'}


def lep_ro_ros(defines, rtl=RTL):
    """ROS (input face stages on ro / t_host / t_kd / mu_c) for one define list"""
    return lep_knob(defines, 'ROS', rtl)


def table(plan, rtl=RTL):
    """{type: RIP} for every plan type whose module carries a lep (name contains 'lep')."""
    types = plan['partition_types']
    return {t: lep_ri_rip(v.get('verilog_defines', []), rtl) for t, v in sorted(types.items()) if 'lep' in t}


def check_kit(plan_defines, kit_defines, rtl=RTL):
    """The kit may not set a RIP the plan (and so bind / LATCHECK) does not carry."""
    a, b = lep_ri_rip(plan_defines, rtl), lep_ri_rip(kit_defines, rtl)
    if a != b:
        raise ValueError(f'kit RIP {b} differs from plan RIP {a}: the bind and LATCHECK price ri at {a}')
    return a


def check_trace(ref, trace, defines, rtl=RTL):
    """Every ri beat of the profile must arrive exactly RIP edges after the RIP 0 reference (same beat order)."""
    rip = lep_ri_rip(defines, rtl)
    if len(ref) != len(trace) or not ref:
        raise ValueError(f'beat count {len(trace)} vs reference {len(ref)}')
    off = sorted({b - a for a, b in zip(ref, trace)})
    if off != [rip]:
        raise ValueError(f'ri dates move by {off} edges, table says {rip}')
    return rip


def kit_config_defines(config_mk):
    """the -D names of a kit config.mk 'export VERILOG_DEFINES = ...' line (the defines synthesis really sees)"""
    for line in Path(config_mk).read_text().splitlines():
        m = re.match(r'\s*(?:export\s+)?VERILOG_DEFINES\s*[:+]?=\s*(.*)', line)
        if m:
            return [t[2:] for t in m.group(1).split() if t.startswith('-D')]
    raise ValueError(f'{config_mk}: no VERILOG_DEFINES line')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--plan', type=Path); p.add_argument('--rtl', type=Path, default=RTL)
    p.add_argument('--trace-ref', type=Path); p.add_argument('--trace', type=Path); p.add_argument('--defines', default='')
    p.add_argument('--kit-config', type=Path, help='kit config.mk; with --plan and --type: refuse a kit RIP != plan RIP')
    p.add_argument('--type')
    a = p.parse_args()
    if a.kit_config:
        plan = json.loads(a.plan.read_text())
        pd = plan['partition_types'][a.type].get('verilog_defines') or []
        try:
            rip = check_kit(pd, kit_config_defines(a.kit_config), a.rtl)
        except ValueError as e:
            print(f'REFUSE {a.type}: {e}')
            return 3
        print(f'PASS {a.type}: kit RIP {rip} == plan RIP {rip}')
        return 0
    if a.plan and not a.kit_config:
        print(json.dumps(table(json.loads(a.plan.read_text()), a.rtl), indent=1))
    if a.trace:
        rd = lambda f: [int(x) for x in f.read_text().split()]
        rip = check_trace(rd(a.trace_ref), rd(a.trace), [d for d in a.defines.split(',') if d], a.rtl)
        print(f'PASS ri = reference + RIP {rip} on every beat')


if __name__ == '__main__':
    sys.exit(main())

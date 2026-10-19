#!/usr/bin/env python3
"""KV-INTEG/KITS-B 2026-10-18 (RTL-BUILD-KV item M1): physical kits of the KV die's replicated static control tiles,
generated MECHANICALLY from the tile generator so a regenerated tile (FAULT / BOOT merges) is re-kitted by re-running
this script (then `ref_tile.py gen` + the --cts gate).

Design point: kvj-g2-env.sh + OT_KV_HROOT=1 OT_KV_FANFOLD=1 + OT_KV_TILE_KITS=1 (kv_static_die: one clock port per
domain on the kit tiles, every port on a fixed canonical face KIT_FACE).  Tiles (FANFOLD: no qkd_kvs_fan):
  qkd_kvs_grp x28, qkd_kvs_grp_h x4 (slot-0 chain end), qkd_kvs_pc x124, qkd_kvs_pc_h x4 (PC 0), qkd_kvs_hroot x4.
Hierarchy (top-down contract): each tile is ONE flat leaf (kind tile).  Its children are not bindable hard macros:
  grp: landing_seg ls5 is CLOSED but 151.2 x 1512 um (the die frame is 1,188 um tall) and its native audit FAILs (spread
       106.8 ps); front_cal / landing_cal (21.6 / 30.24 um CLOSED leaves) would cost 2 clock entries each for a few
       hundred cells; boot_cdc / cfault / drain_guard4 / phase_launch have no kit.  The 4 landing SRAMs stay macros.
  pc:  pc_path_fan_nc's controller children (KV-NC-KITS sched / port / front / return_slots _nc) are NOT closed;
       return_slots_mc* is a CRITICAL prefix -> the pc kits are gated and reported, never submitted.
  hroot: es_fan_stack + stack_relays, no kits.
Outline = the die-plan frame (kv_static_die.place / FRAME) snapped DOWN to the 2.16-um lattice; pin faces = KIT_FACE,
along-face spans = the die's spread (kv_die: proportional to the bits, in face_order, 2 um end margins) for ports >= 32 b.
Port domains come from the elaborated RTL (kvs_port_domains.py on the fleet): hck-domain IO is constrained on the HBM
clock (sdc_extra), everything else on the core clock.

    python3 tools/qwen_kv_die/kvs_tile_kits.py sources KIND           # simulation / synthesis source closure
    python3 tools/qwen_kv_die/kvs_tile_kits.py ports-job OUTDIR       # tarball + script for the fleet port-domain run
    python3 tools/qwen_kv_die/kvs_tile_kits.py specs                  # write specs + sdc from results/.../<kind>_ports.json
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

ENV = dict(OT_KV_STATIC_DIE='1', OT_KV_HROOT='1', OT_KV_FANFOLD='1', OT_KV_TILE_KITS='1')
OUT = 'results/arch/qwen_kv_kits_b_1018'
SRAM = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'
TAG = 'k1'
LAT = 2.16


def S_():
    for k, v in ENV.items():
        os.environ.setdefault(k, v)
    if os.environ.get('OT_KV_TILE_KITS') != '1':
        sys.exit('kvs_tile_kits: needs OT_KV_TILE_KITS=1 (source /home/ubuntu/wt/kvj-g2-env.sh first)')
    import kv_static_die as S
    return S


def down(x):
    return round(int((x - 0.024) / LAT + 1e-9) * LAT, 4)


# die-plan frames (kv_static_die.place: pcw, pch = 270, 302.4; GH = 1188; group width = the K / V channel edge minus
# OT_KV_KV_CHAN_EXTRA: 222.0 / 222.6 um at the m1 plan (kvs14a prep log src frames 222 x 1188 / 223 x 1188); FRAME)
FRAMES = dict(grp=(222.0, 1188.0), grp_h=(222.0, 1188.0), pc=(270.0, 302.4), pc_h=(270.0, 302.4), hroot=(302.4, 302.4))
COUNT = dict(grp=28, grp_h=4, pc=124, pc_h=4, hroot=4)
CRITICAL = dict(pc='contains qkd_static_kv_return_slots_mc_nc (critical prefix qkd_static_kv_return_slots_mc*, unclosed)',
                pc_h='contains qkd_static_kv_return_slots_mc_nc (critical prefix qkd_static_kv_return_slots_mc*, unclosed)')


def rep(S, kind):
    return next(d for d, t in S.all_tiles().items() if t['kind'] == kind)


# ------------------------------------------------------------------------------------------- source closure
_IDX = {}


def index():
    if _IDX:
        return _IDX
    for base in ('rtl',):
        for f in (ROOT / base).rglob('*'):
            if f.suffix not in ('.sv', '.v') or not f.is_file() or '/test/' in str(f):
                continue
            try:
                txt = f.read_text(errors='replace')
            except OSError:
                continue
            for m in re.finditer(r'^\s*module\s+(\w+)', txt, re.M):
                _IDX.setdefault(m.group(1), []).append(str(f.relative_to(ROOT)))
    return _IDX


def strip_comments(t):
    t = re.sub(r'\(\*\s*[A-Za-z_][^()]*?\*\)', ' ', t)          # attributes (* keep *), never @(*)
    t = re.sub(r'/\*.*?\*/', ' ', t, flags=re.S)
    return re.sub(r'//[^\n]*', ' ', t)


def module_text(path, name):
    t = (ROOT / path).read_text(errors='replace')
    m = re.search(r'^\s*module\s+' + re.escape(name) + r'\b.*?^\s*endmodule\b', t, re.S | re.M)
    if not m:
        raise KeyError(f'{name} not in {path}')
    return m.group(0)


def instantiated(body):
    b = strip_comments(body)
    return set(re.findall(r'(?m)^\s*([A-Za-z_]\w*)\s*(?:#\s*\(.*?\)\s*)?[A-Za-z_][\w\[\]: ]*\(', b, re.S))


def closure(top, top_file, prefer, mode='sim'):
    """{module: file} of every module under top; prefer = files tried first for a module defined more than once"""
    idx = index()
    pref = set(prefer)
    out, todo = {top: top_file}, [top]
    while todo:
        mn = todo.pop()
        body = module_text(out[mn], mn)
        for c in sorted(instantiated(body)):
            if c in out or c in ('module', 'if', 'for', 'case', 'begin', 'assign', 'always', 'initial', 'generate'):
                continue
            if c.startswith('ot_sram_'):
                v = f'physical/asap7_memory_macros_v2/{c}/{c}' + ('_bb.v' if mode == 'synth' else '.v')
                if not (ROOT / v).exists():
                    raise FileNotFoundError(v)
                out[c] = v
                continue
            cand = idx.get(c)
            if not cand:
                continue                       # a cell / primitive / keyword-like token
            pick = [f for f in cand if f in pref] or [f for f in cand if Path(f).parent == Path(out[mn]).parent] or cand
            if len(set(pick)) > 1:
                raise ValueError(f'kvs_tile_kits: {c} defined in {sorted(set(pick))} (instantiated by {mn})')
            out[c] = pick[0]
            todo.append(c)
    return out


def tile_sources(S, kind, mode='sim', rtl=None):
    mst = S.KIND_MASTER[kind]
    cl = closure(mst, rtl or S.RTL_FILE, S.sources(), mode)
    files = [rtl or S.RTL_FILE] + sorted({f for m, f in cl.items() if f != (rtl or S.RTL_FILE)})
    return files, cl


# ------------------------------------------------------------------------------------------- port-domain fleet job
def ports_job(S, outdir):
    """writes OUTDIR/src.tgz (all sources + the analyser) and OUTDIR/run.sh (fleet: yosys per kind -> <kind>_ports.json)"""
    import tarfile
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    files = {'tools/qwen_kv_die/kvs_port_domains.py'}
    lines = ['#!/bin/bash', 'set -u', 'R=$1; shift']
    for kind in COUNT:
        srcs, _ = tile_sources(S, kind, 'synth')
        files |= set(srcs)
        lines.append(f'python3 tools/qwen_kv_die/kvs_port_domains.py --top {S.KIND_MASTER[kind]} '
                     + ' '.join(f'--src {f}' for f in srcs) + f' --out $R/{kind}_ports.json > $R/{kind}.log 2>&1; '
                     f'echo "{kind} rc=$?" >> $R/rc.txt')
    (out / 'run.sh').write_text('\n'.join(lines) + '\n')
    files.add(str((out / 'run.sh').resolve().relative_to(ROOT)) if str(out.resolve()).startswith(str(ROOT)) else None)
    files.discard(None)
    with tarfile.open(out / 'src.tgz', 'w:gz') as tf:
        for f in sorted(files):
            tf.add(ROOT / f, arcname=f)
        tf.add(out / 'run.sh', arcname='run.sh')
    print(f'{out}/src.tgz: {len(files)} files')


# ------------------------------------------------------------------------------------------- specs
def faces(S, kind, W, H):
    """{face: [ports in the die's along-face order]}, pin_ranges {port: [lo, hi]} for ports >= 32 b (die spread)"""
    t = S.all_tiles()[rep(S, kind)]
    mst = S.KIND_MASTER[kind]
    F = {f: [] for f in 'NSEW'}
    for p in sorted(t['ports']):
        F[S.pin_face(mst, p)].append(p)
    rng = {}
    for f, ps in F.items():
        ps[:] = S.face_order(mst, f, ps)
        L = H if f in 'EW' else W
        tot = sum(t['ports'][p]['width'] for p in ps)
        pos = 2.0
        for p in ps:
            span = (L - 4.0) * t['ports'][p]['width'] / tot
            if t['ports'][p]['width'] >= 32:
                rng[p] = [round(pos + 0.5, 2), round(pos + span - 0.5, 2)]
            pos += span
    return {f: v for f, v in F.items() if v}, rng, t


def hck_sdc(kit, hin, hout, fn):
    """second clock hclk (HBM trunk, 1,024 ps) on port hck; the hck-domain IO measured from the RTL (kvs_port_domains);
    no clock groups / false paths: every crossing is a datapath budget (same form as qkd_ctrl_pc_cdc_child_hclk.sdc)"""
    L = [f'# KV-INTEG/KITS-B 10-18: sdc_extra of {kit} (GENERATED by tools/qwen_kv_die/kvs_tile_kits.py specs; do not edit).',
         '# Second clock hclk on port hck (the HBM trunk clk_hbm_<region>); its IO = the ports whose registers are ALL on hck',
         '# (measured on the elaborated RTL, results/arch/qwen_kv_kits_b_1018/<kind>_ports.json); every other port stays on',
         '# core_clk.  Two asynchronous roots, NO clock groups and NO false paths: each crossing arc is a datapath budget of',
         '# core_clk period - 60 ps in both directions, hold = non-negative datapath delay; IO 0.2 T in its own domain.',
         'create_clock -name hclk -period 1024.000 [get_ports hck]',
         'set_clock_uncertainty -setup 60 [get_clocks hclk]',
         'set_clock_uncertainty -hold 25 [get_clocks hclk]',
         'set ot_cw_prop 0',
         'catch {set ot_cw_prop [get_property [get_clocks core_clk] is_propagated]}',
         'if {$ot_cw_prop} { set_propagated_clock [get_clocks hclk] }',
         'set ot_cw_x [expr {[get_property [get_clocks core_clk] period] - 60.0}]',
         'set_max_delay -ignore_clock_latency $ot_cw_x -from [get_clocks core_clk] -to [get_clocks hclk]',
         'set_max_delay -ignore_clock_latency $ot_cw_x -from [get_clocks hclk] -to [get_clocks core_clk]',
         'set_min_delay -ignore_clock_latency 0 -from [get_clocks core_clk] -to [get_clocks hclk]',
         'set_min_delay -ignore_clock_latency 0 -from [get_clocks hclk] -to [get_clocks core_clk]',
         'catch {unset_input_delay [get_ports hck]}']
    pat = lambda ps: ' '.join(f'{p}[*]' if w > 1 else p for p, w in ps)     # noqa: E731
    if not hin and not hout:
        L.append('# no hck-domain IO')
        Path(fn).write_text('\n'.join(L) + '\n')
        return
    L.append(f'set ot_cw_hi [get_ports {{{pat(hin)}}}]' if hin else 'set ot_cw_hi {}')
    L.append(f'set ot_cw_ho [get_ports {{{pat(hout)}}}]' if hout else 'set ot_cw_ho {}')
    L += ['if {[llength $ot_cw_hi]} { unset_input_delay $ot_cw_hi }',
          'if {[llength $ot_cw_ho]} { unset_output_delay $ot_cw_ho }',
          'set ot_cw_b 204.800',
          'set ot_cw_lmax 0.0; set ot_cw_lmin 0.0',
          'set ot_cw_sk 0.0; set ot_cw_hk 0.0; set ot_cw_hki 0.0',
          'if {$ot_cw_prop} {',
          '  set ot_cw_sk  [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]',
          '  set ot_cw_hk  [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]',
          '  set ot_cw_hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]',
          '  catch {sta::worst_slack_cmd max}',
          '  set ot_cw_ck {}',
          '  if {[llength $ot_cw_hi] && [llength [info procs ot_pf_clks]]} { set ot_cw_ck [ot_pf_clks $ot_cw_hi] }',
          '  if {![llength $ot_cw_ck]} { set ot_cw_ck [lrange [all_registers -clock hclk -clock_pins] 0 255] }',
          '  set ot_cw_pf {}',
          '  foreach p $ot_cw_ck {',
          '    set a [get_property $p arrival_max_rise]',
          '    if {[string is double -strict $a]} { lappend ot_cw_pf [list $a $p] }',
          '  }',
          '  if {[llength $ot_cw_pf]} {',
          '    set ot_cw_m [lindex [lsort -real -index 0 $ot_cw_pf] [expr {[llength $ot_cw_pf] / 2}]]',
          '    set ot_cw_lmax [lindex $ot_cw_m 0]',
          '    set ot_cw_lmin [get_property [lindex $ot_cw_m 1] arrival_min_rise]',
          '    if {![string is double -strict $ot_cw_lmin]} { set ot_cw_lmin $ot_cw_lmax }',
          f'    puts "{kit} hclk reference [get_full_name [lindex $ot_cw_m 1]] of [llength $ot_cw_pf] pin flops: clock arrival max $ot_cw_lmax min $ot_cw_lmin"',
          '  }',
          '}',
          'if {[llength $ot_cw_hi]} {',
          '  set_input_delay  [expr {$ot_cw_b + $ot_cw_lmax + $ot_cw_sk}] -max -clock hclk $ot_cw_hi',
          '  set_input_delay  [expr {$ot_cw_lmin - $ot_cw_hki}]          -min -clock hclk $ot_cw_hi',
          '}',
          'if {[llength $ot_cw_ho]} {',
          '  set_output_delay [expr {$ot_cw_b - $ot_cw_lmax + $ot_cw_sk}] -max -clock hclk $ot_cw_ho',
          '  set_output_delay [expr {0.0 - $ot_cw_lmin - $ot_cw_hk}]     -min -clock hclk $ot_cw_ho',
          '}']
    Path(fn).write_text('\n'.join(L) + '\n')


def sram_macros(S, kind, pins, rng, W, H):
    """grp: the landing segment's 4 row SRAMs (one per PC, u_slg.g_pc[j]...u_rows), each level with its PC's W-face
    pair (pc j: i_pc<3-j> / o_pc<3-j>, the group's PC order bottom-up), on the E side (the K / V responses leave E)"""
    if kind not in ('grp', 'grp_h'):
        return []
    lef = (ROOT / SRAM / (Path(SRAM).name + '.lef')).read_text()
    mw, mh = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef).groups())
    out = []
    for j in range(4):
        # landing_seg actual_* {.._0, .._1, .._2, .._3} <- i_pc3 .. i_pc0: PC slot j of the segment = i_pc<3 - j>
        lo, hi = rng[f'i_pc{3 - j}'][0], rng[f'o_pc{3 - j}'][1]
        yc = (lo + hi) / 2
        y = max(30.0, min(H - 30.0 - mh, yc - mh / 2))
        out.append(dict(view=SRAM, count=1, inst=f'*g_pc?{j}?*u_rows', at=[round(W - 40.0 - mw, 2), round(y, 2)], orient='R0'))
    return out


def spec(S, kind):
    mst = S.KIND_MASTER[kind]
    kit = f'{mst}_{TAG}'
    fw, fh = FRAMES[kind]
    W, H = down(fw), down(fh)
    pins, rng, t = faces(S, kind, W, H)
    pj = json.loads((ROOT / OUT / f'{kind}_ports.json').read_text())
    P = pj['ports']
    tp = t['ports']
    if set(P) != set(tp):
        raise ValueError(f'{kind}: port-domain record {OUT}/{kind}_ports.json is stale (ports differ); re-run ports-job')
    hin = [(p, tp[p]['width']) for p in tp if tp[p]['dir'] == 'input' and P[p].get('domains') == ['hck']]
    hout = [(p, tp[p]['width']) for p in tp if tp[p]['dir'] == 'output' and P[p].get('domains') == ['hck']]
    sdc = None
    if 'hck' in tp:
        sdc = f'physical/qkd_kvs_kits/{kit}_hck.sdc'
        (ROOT / sdc).parent.mkdir(parents=True, exist_ok=True)
        hck_sdc(kit, hin, hout, ROOT / sdc)
    srcs, _ = tile_sources(S, kind, 'synth')
    resets = [p for p in tp if tp[p]['cls'] == 'reset']
    comb_in = sorted(p for p in tp if tp[p]['dir'] == 'input' and P[p].get('feedthrough'))
    deep = sorted(p for p in tp if P[p].get('depth', 0) > 0 and P[p].get('role') != 'clock')
    mixed = sorted(p for p in tp if len(P[p].get('domains', [])) > 1)
    purpose = (f'KV-INTEG/KITS-B 10-18 (RTL-BUILD-KV M1): flat leaf kit of the generated KV static tile {mst} (x{COUNT[kind]} '
               f'on the KV die, design point kvj-g2 + OT_KV_HROOT/FANFOLD/TILE_KITS, RTL {S.RTL_FILE}), regenerated by '
               f'tools/qwen_kv_die/kvs_tile_kits_rep.py from the tile generator.')
    sp = dict(
        name=kit, top=mst, kind='tile', sources=srcs, params={}, clock_port='ck', reset_ports=resets,
        outline=dict(w=W, h=H, exact=True), layer_cap='M5', macros=sram_macros(S, kind, pins, rng, W, H), pins=pins,
        pin_ranges=rng,
        route=dict(pd=0.5, threads=8, peak_ram_gb=32 if kind.startswith(('grp', 'pc')) else 16, hold_margin_ns=0.03,
                   io_hold_margin_ns=0.03, macro_halo_um=5.4),     # KITS 10-18: boundary margin >= 0.025
        recipe=3, purpose=purpose,
        job=dict(owner=os.environ.get('KVS_KIT_OWNER', 'Claude:KV-INTEG2'),
                 branch=os.environ.get('KVS_KIT_BRANCH', 'claude/kv-integ2-kits-1018'), tag=TAG, purpose=purpose,
                 benches=benches(kind), extra_paths=['rtl', 'tools/qwen_kv_die', 'results/arch', OUT,
                                                     WIT, SRAM],
                 views_to=f'physical/ref_tile/{kit}/views', record_to=f'results/rtl/ref_tile/{kit}'),
        pin_regs=dict(enable=False, reason=(
            'Generated wires-only composition of the static join: every edge age (die_ages.json, kv_static_ages) is priced '
            'on the join + the die relay stages, so a flow-inserted pin stage would add a cycle the compiled calendar does '
            'not have (the lockstep bench vs the die tile would fail).  Pin facts measured on the RTL '
            f'({OUT}/{kind}_ports.json): {len(deep)} ports with logic before the first register {deep[:12]}, '
            f'{len(comb_in)} feed-through inputs {comb_in[:12]} (die-relayed chain words / pass words).')),
        children=[], inter=[], io_flop_at_pins=dict(cols=4, allow_none=True), inhold=True, outhold=True,
        keep_pin_regs=True, pin_reg_split=True, hold_pad=dict(cell='HB2xp67_ASAP7_75t_R', out_cell='HB1xp67_ASAP7_75t_R'),
        structural_change=('KV-INTEG/KITS-B 10-18: new element (no predecessor view): the generated static tile had no kit '
                           '(RTL-BUILD-KV M1).'),
        kits_b=dict(frame=[fw, fh], kit_outline=[W, H], count=COUNT[kind], rep_instance=rep(S, kind), rtl=S.RTL_FILE,
                    hck_inputs=[p for p, _ in hin], hck_outputs=[p for p, _ in hout], mixed_domain_ports=mixed,
                    critical=CRITICAL.get(kind)))
    if sdc:
        sp['sdc_extra'] = [sdc]
    return kit, sp


MUTANTS = {
    # kind: {n: (description, [(module chain from the tile's child down to the edited module)], old, new, fail regex)}
    'grp': {1: ('cfault node drops leaf 0', ['qkd_kvs_grp'], 'qkd_kv_cfault_node #(.R(4), .STAGES(1), .MUT(0))',
                'qkd_kv_cfault_node #(.R(4), .STAGES(1), .MUT(1))'),
            2: ('drain guard never faults', ['qkd_kvs_grp'], 'qkd_static_kv_drain_guard4 #(.MUT(0))',
                'qkd_static_kv_drain_guard4 #(.MUT(2))'),
            3: ('boot CDC 0 sink address +1', ['qkd_kvs_grp'], 'qkd_static_kv_boot_cdc #(.HAS_SEAL(1), .MUT(0)) u_bcdc0',
                'qkd_static_kv_boot_cdc #(.HAS_SEAL(1), .MUT(1)) u_bcdc0'),
            4: ('phase launch held word ^1', ['qkd_kvs_grp'], '.META_HOLD_CORE(8), .MUT(0))', '.META_HOLD_CORE(8), .MUT(3))'),
            5: ('landing seg response hop mutant', ['qkd_kvs_grp'], 'qkd_static_kv_landing_seg #(.MUT(0), .HOP_MUT(0))',
                'qkd_static_kv_landing_seg #(.MUT(0), .HOP_MUT(1))'),
            6: ('landing calendar phase drift', ['qkd_kvs_grp'], 'qkd_kv_landing_cal #(.MUT(0), .PH0(0))',
                'qkd_kv_landing_cal #(.MUT(2), .PH0(0))')},
    'pc': {1: ('PC chain station lane pc compared on pc[3:0]', ['qkd_static_kv_pc_path_fan_nc'],
               'qkd_kv_pc_chain_station u_chain (', 'qkd_kv_pc_chain_station #(.MUT(1)) u_chain ('),
           2: ('HBM calendar mutant', ['qkd_static_kv_pc_path_fan_nc', 'qkd_static_kv_pc_path_emb_nc', 'qkd_static_kv_pc_path_nc'],
               '.ROW0(64), .MUT(0)) u_calendar', '.ROW0(64), .MUT(1)) u_calendar'),
           3: ('elastic front mutant', ['qkd_static_kv_pc_path_fan_nc', 'qkd_static_kv_pc_path_emb_nc', 'qkd_static_kv_pc_path_nc'],
               '.STRIDE(1), .MUT(0)) u_front', '.STRIDE(1), .MUT(1)) u_front')},
    'hroot': {1: ('es fan stack compare bit 0 inverted', ['qkd_kvs_hroot'], 'qkd_kv_es_fan_stack #(.MUT(0))',
                  'qkd_kv_es_fan_stack #(.MUT(1))'),
              2: ('stack relays fan word one bit low', ['qkd_kvs_hroot'], 'qkd_kv_stack_relays #(', 'qkd_kv_stack_relays #(.MUT(1), ')},
}
MUTANTS['grp_h'] = {k: (d, ['qkd_kvs_grp_h' if c == 'qkd_kvs_grp' else c for c in ch], o, n)
                    for k, (d, ch, o, n) in MUTANTS['grp'].items()}
MUTANTS['pc_h'] = dict(MUTANTS['pc'])
MUTANTS['pc_h'][4] = ('return head never faults on an empty transfer', ['qkd_kvs_pc_h'],
                      'qkd_embedding_static_return_head #(.MUT(0)) u_embr', 'qkd_embedding_static_return_head #(.MUT(1)) u_embr')
WIT = os.environ.get('KVS_KIT_RES', 'results/rtl/qwen_kv_die/kvs_kits_1018')      # KV-INTEG2: one witness dir for every kvs kit


def benches(kind):
    """KV-INTEG2: the shared kit bench (kvs_tile_bench.sh, KITS-A): LOCKSTEP of the kit top (one clock port per domain,
    canonical faces) against the die-bound tile of the same design point without OT_KV_TILE_KITS; mutants = wiring faults
    of the KIT TOP (1 dropped child wire, 2 swapped equal-width child inputs, 3 missing child).  The children's own
    behaviour is qualified by their own benches (MUTANTS above are child-level and kept for reference only)."""
    # KV-KITS 10-18: Verilator 5.050 (the closure daemon's), KVS_SIM=verilator; iverilog only when KVS_SIM=iverilog
    sim = os.environ.get('KVS_SIM', 'verilator')
    sh = f'KVS_SIM={sim} bash tools/qwen_kv_die/kvs_tile_bench.sh {{RUN}}/bench/{kind}_m{{M}} {kind} {{M}}'
    need = ['verilator'] if sim == 'verilator' else ['iverilog']
    b = [dict(name=f'{kind}_lockstep', cmd=sh.replace('{M}', '0'), expect='pass', threads=4, peak_ram_gb=8,
              needs=need, pass_regex=rf'^KVS_TILE PASS tile={kind} .* errors=0 mut=0',
              min_count_regex=r'checks=(\d+)', pass_witness=f'{WIT}/{kind}_m0.log')]
    for n in (1, 2, 3):
        b.append(dict(name=f'{kind}_mut{n}', cmd=sh.replace('{M}', str(n)), expect='fail', threads=4, peak_ram_gb=8,
                      needs=need, pass_regex=rf'^KVS_TILE PASS tile={kind} ',
                      fail_regex=rf'^KVS_TILE FAIL tile={kind} .* mut={n} ', fail_witness=f'{WIT}/{kind}_m{n}.log'))
    return b


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s1 = sub.add_parser('sources')
    s1.add_argument('kind')
    s1.add_argument('--mode', default='sim')
    s2 = sub.add_parser('ports-job')
    s2.add_argument('outdir')
    s3 = sub.add_parser('specs')
    s3.add_argument('--kinds', default=','.join(COUNT))
    a = ap.parse_args()
    S = S_()
    if a.cmd == 'sources':
        print('\n'.join(tile_sources(S, a.kind, a.mode)[0]))
    elif a.cmd == 'ports-job':
        ports_job(S, a.outdir)
    else:
        for kind in a.kinds.split(','):
            kit, sp = spec(S, kind)
            fn = ROOT / 'tools/ref_tile/specs' / f'{kit}.json'
            fn.write_text(json.dumps(sp, indent=1) + '\n')
            dens = {f: round(sum(sp['kits_b'] and 1 for _ in ps), 1) for f, ps in sp['pins'].items()}
            print(f'{fn.relative_to(ROOT)}: {sp["outline"]["w"]} x {sp["outline"]["h"]}, faces {dens}, '
                  f'hck in/out {len(sp["kits_b"]["hck_inputs"])}/{len(sp["kits_b"]["hck_outputs"])}, '
                  f'mixed {sp["kits_b"]["mixed_domain_ports"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

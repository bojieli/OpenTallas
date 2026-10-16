#!/usr/bin/env python3
"""Die GRT + TT/FF STA case of the v15 HBM die on REAL views (H-DIE r3, 2026-10-15).

    view_case.py --region pcrow --out CASE_DIR

Region pcrow = the four PHY + PC rows of compact660_v5: every contract instance of the region is bound to a REAL view
  phy_<q>        ot_hbm3e_phy_v41x_aw30_e8p5   PHY+controller macro abstract (LEF + TT/FF Liberty; PHY = the one
                                               modelled hard core the owner rule allows)
  svc_<q>_s<k>   hfd_svc_v15_*  (34 bands)     a band is wires around its PCs only (rtl .../svc/v15/rtl/*.sv: no logic),
                                               so it is FLATTENED: each u_pc<n> = CLOSED ot_hbm_svc_static_pc view
                                               (physical/ref_tile/hv15_svc_pc/views, TT/FF ETM of the routed tile),
                                               placed at the band slot + the grant sub_layout (HBM-V15-HARDEN request
                                               (2) of 10:33: bands as soft die-level groups, PCs placed directly)
Nets = the contract's known_actual_edges between region instances (bit exact, band port bits mapped through the band
RTL to the PC port bits).  Every other pin of a region instance is OUT OF REGION (its peer is outside this case or
unbound in the contract): it stays unconnected here and is listed in manifest.json, never tied or stubbed.
Placement: grants hbm_v15.json v4 slots (bands) and compact660_v5 plan blocks (PHY).  The north PHYs face south (MX)
so their controller pins face their PC row (the plan file carries R0 for all four: planning pins were face-planned).
Clock: one die clock port per region clock (hbm), IDEAL at the die (no die CTS yet); each closed view's own insertion
is inside its ETM arcs.  Uncertainty 60 / 25 ps as every tile sign-off.  Setup TT, hold FF (owner option B).
GRT: real tracks M4..M9, coarse M2/M3 tracks (gcell 9.6 um, the dietop method of tools/hbm_die_relay_sta.py),
M4/M5 0.30 and M6..M9 0.146 adjustments as that die STA.  Writes CASE_DIR/{die.v, run.tcl, manifest.json}.
"""
import argparse, json, re, shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'results/arch/hbm_die_v15/source_contract/contract.json'
GRANTS = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
PLAN = ROOT / 'results/arch/hbm_die_v15/compact660_v5/compact.P.json'
PHY_M = 'ot_hbm3e_phy_v41x_aw30_e8p5'
PC_M = 'ot_hbm_svc_static_pc'
VIEWS = {PHY_M: dict(dir=ROOT / f'physical/asap7_memory_macros/{PHY_M}', kind='hard_macro_abstract'),
         PC_M: dict(dir=ROOT / f'physical/ref_tile/hv15_svc_pc/views/{PC_M}', kind='closed_tile_etm')}
T_PS = 833.333
TILE = 9.6


def band_map(src):
    """band RTL -> {pc inst: {pc port: [(pc_lo, band port, band_lo, width)]}} (wires only; anything else = error)."""
    t = Path(src).read_text()
    body = re.sub(r'//.*', '', t)
    assert not re.search(r'\b(always|assign|reg)\b', body), f'{src}: band has logic, cannot flatten'
    out = {}
    for m in re.finditer(r'(\w+)\s+(u_pc\d+)\s*\((.*?)\);', body, re.S):
        assert m.group(1) == PC_M, m.group(1)
        conns = {}
        for p, e in re.findall(r'\.(\w+)\s*\(([^()]*)\)', m.group(3)):
            e = e.strip()
            a = re.fullmatch(r'(\w+)\s*\[\s*(\d+)\s*\+:\s*(\d+)\s*\]', e)
            b = re.fullmatch(r'(\w+)\s*\[\s*(\d+)\s*\]', e)
            c = re.fullmatch(r'(\w+)', e)
            if a:
                conns[p] = (a.group(1), int(a.group(2)), int(a.group(3)))
            elif b:
                conns[p] = (b.group(1), int(b.group(2)), 1)
            elif c:
                conns[p] = (c.group(1), 0, None)
            else:
                raise SystemExit(f'{src}: {p}({e}) not a plain slice')
        out[m.group(2)] = conns
    return out


def lef_pins(lef):
    pins = {}
    for m in re.finditer(r'^\s*PIN (\S+)\s*\n\s*DIRECTION (\w+)', Path(lef).read_text(), re.M):
        pins[m.group(1)] = m.group(2)
    return pins


def lef_xy(lef):
    out = {}
    for m in re.finditer(r'^\s*PIN (\S+)(.*?)^\s*END \1', Path(lef).read_text(), re.M | re.S):
        r = re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', m.group(2))
        if r:
            x0, y0, x1, y1 = map(float, r.groups())
            out[m.group(1)] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return out


def place_child(bx, by, bw, bh, bo, cx, cy, cw, ch, co):
    assert co == 'R0', co
    if bo == 'R0':
        return bx + cx, by + cy, 'R0'
    if bo == 'MX':
        return bx + cx, by + (bh - cy - ch), 'MX'
    if bo == 'MY':
        return bx + (bw - cx - cw), by + cy, 'MY'
    if bo == 'R180':
        return bx + (bw - cx - cw), by + (bh - cy - ch), 'R180'
    raise SystemExit(f'orient {bo}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--region', default='pcrow', choices=['pcrow'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--paths', type=int, default=200000)
    ap.add_argument('--pc-align', action='store_true',
                    help='variant B: east PHYs mirrored (MY / R180) to the band order, every PC placed directly over '
                         'its own PHY channel pin window, 10.8 um from the PHY edge (bands = soft groups)')
    ap.add_argument('--die-clock', action='store_true',
                    help='REAL die clock delivery instead of an ideal die clock: the hbm clock enters at the PLL output '
                         '(pll_hbm) of the hfd_ckgen slot, TritonCTS builds the die tree to every view clock pin with '
                         'ASAP7 RVT buffers placed only in channels/relay rows (every non-region compact660_v5 block is '
                         'a placement blockage), the tree is global-routed with the signals and STA uses the propagated '
                         'clock (die insertion + each ETM\'s own insertion)')
    ap.add_argument('--die-clock-mode', default='explicit', choices=['explicit', 'tritoncts'],
                    help='explicit = tools/hbm_die_v15/die_clock_tree.py (repeaters in free area only, balanced binary '
                         'tree per quadrant); tritoncts = OpenROAD CTS (left 12 mm leaf nets on this die)')
    ap.add_argument('--clock-pads', type=Path, help='json {sink inst: pad repeaters} from a measured run (skew feedback)')
    ap.add_argument('--cts-opts', default='-distance_between_buffers 400 -obstruction_aware -sink_clustering_enable -macro_clustering_size 2 '
                            '-macro_clustering_max_diameter 300',
                    help='extra TritonCTS options (die repeater spacing on M8)')
    ap.add_argument('--ckgen', default='hfd_ckgen', help='slot name of the clock root block in the grants')
    a = ap.parse_args()
    C = json.loads(CONTRACT.read_text()); G = json.loads(GRANTS.read_text()); P = json.loads(PLAN.read_text())
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    slots = {s['name']: s for s in G['slots']}
    W0 = G['floorplan']['die_um'][0]
    inst = C['instances']
    region = sorted(n for n in inst if re.fullmatch(r'(phy_(SW|SE|NW|NE)|svc_(SW|SE|NW|NE)_s\d)', n))
    phys = [n for n in region if n.startswith('phy_')]
    bands = [n for n in region if n.startswith('svc_')]
    # ---- leaf instances + placement ----
    leaves = {}            # leaf name -> dict(master, x, y, orient, w, h, of)
    pcmap = {}             # band -> {u_pc: conns}
    for b in bands:
        s = slots[b]; m = inst[b]['master']
        assert s['cell'] == m, (b, s['cell'], m)
        sub = G['sub_layouts'][m]
        pcmap[b] = band_map(ROOT / inst[b]['source'])
        assert sorted(pcmap[b]) == sorted(c['name'] for c in sub), (b, sorted(pcmap[b]))
        for c in sub:
            x, y, o = place_child(s['origin']['x'], s['origin']['y'], s['outline']['w'], s['outline']['h'],
                                  s['origin']['orient'], c['origin']['x'], c['origin']['y'], c['outline']['w'],
                                  c['outline']['h'], c['origin']['orient'])
            leaves[f'{b}__{c["name"]}'] = dict(master=PC_M, x=round(x, 3), y=round(y, 3), orient=o,
                                               w=c['outline']['w'], h=c['outline']['h'], of=b)
    for p in phys:
        q = P[p]; north = q['y'] > 10000
        east = q['x'] > W0 / 2
        o = ('R180' if east else 'MX') if north else ('MY' if east else 'R0')
        if not a.pc_align:
            o = 'MX' if north else 'R0'
        leaves[p] = dict(master=PHY_M, x=q['x'], y=q['y'], orient=o, w=q['w'], h=q['h'], of=p,
                         note=f'plan orient R0 -> {o} (controller pins face the PC row' +
                              (', channel order = band order)' if a.pc_align else ')') if o != 'R0' else '')
    # ---- pin sets of the views ----
    vpins = {m: lef_pins(next(VIEWS[m]['dir'].glob('*.lef'))) for m in VIEWS}

    def leaf_bits(i, port, lo, width):
        """(region instance, port, bit range) -> list of (leaf, leafpin) per bit."""
        if i.startswith('phy_'):
            return [(i, f'{port}[{lo + k}]') for k in range(width)]
        res = [None] * width
        for u, conns in pcmap[i].items():
            for pp, (bp, blo, bw) in conns.items():
                if bp != port:
                    continue
                if bw is None:      # whole-port connection: the view's port width
                    bw = sum(1 for q in vpins[PC_M] if q.startswith(pp + '[')) or 1
                for k in range(bw):
                    j = blo + k - lo
                    if 0 <= j < width:
                        pin = f'{pp}[{k}]' if f'{pp}[{k}]' in vpins[PC_M] else pp
                        res[j] = (f'{i}__{u}', pin)
        assert all(res), (i, port, lo, width)
        return res

    nets = {}              # net -> [(leaf, pin, role)]
    used = defaultdict(set)
    edges_in = 0
    for e in C['known_actual_edges']:
        s, d = e['source'], e['sink']
        if s[0] not in region or d[0] not in region:
            continue
        edges_in += 1
        w = e['bits']
        sl = s[2] if len(s) > 2 else 0
        dl = d[2] if len(d) > 2 else 0
        sb = leaf_bits(s[0], s[1], sl, w); db = leaf_bits(d[0], d[1], dl, w)
        for k in range(w):
            n = f'n_{e["name"]}_{k}'
            nets[n] = [(sb[k][0], sb[k][1], 'drv'), (db[k][0], db[k][1], 'load')]
            used[sb[k][0]].add(sb[k][1]); used[db[k][0]].add(db[k][1])
    if a.pc_align:
        lp = lef_xy(next(VIEWS[PHY_M]['dir'].glob('*.lef')))
        chan = defaultdict(list)
        for n, ends in nets.items():
            ph = [e for e in ends if leaves[e[0]]['master'] == PHY_M]
            pc = [e for e in ends if leaves[e[0]]['master'] == PC_M]
            if ph and pc:
                chan[pc[0][0]].append((ph[0][0], lp[ph[0][1]][0]))
        for l, lst in chan.items():
            phy = leaves[lst[0][0]]
            cx = sum(x for _, x in lst) / len(lst)
            dx = phy['x'] + (phy['w'] - cx if phy['orient'] in ('MY', 'R180') else cx)
            v = leaves[l]
            v['x'] = round(round((dx - v['w'] / 2) / 0.216) * 0.216, 3)
            north = phy['y'] > 10000
            v['y'] = round(phy['y'] - 10.8 - v['h'], 3) if north else round(phy['y'] + phy['h'] + 10.8, 3)
            v['orient'] = 'MX' if north else 'R0'
            v['note'] = 'aligned over its PHY channel window (variant B)'
        # overlap check
        ls = [(l, v) for l, v in leaves.items()]
        for i, (l1, v1) in enumerate(ls):
            for l2, v2 in ls[i + 1:]:
                if v1['x'] < v2['x'] + v2['w'] and v2['x'] < v1['x'] + v1['w'] and \
                        v1['y'] < v2['y'] + v2['h'] and v2['y'] < v1['y'] + v1['h']:
                    raise SystemExit(f'overlap {l1} {l2}')
    # clocks / reset: die ports
    clk_pins = {PHY_M: ['clk'], PC_M: ['clk']}
    tree = None
    leafclk = {}
    if a.die_clock and a.die_clock_mode == 'explicit':
        import die_clock_tree as dct
        ck = slots[a.ckgen]
        root_xy = (ck['origin']['x'] + ck['outline']['w'] / 2, ck['origin']['y'] + ck['outline']['h'] / 2)
        vxy = {m: lef_xy(next(VIEWS[m]['dir'].glob('*.lef'))) for m in VIEWS}
        sinks = []
        for l, v in leaves.items():
            px, py = vxy[v['master']]['clk']
            o = v['orient']
            if o in ('MY', 'R180'):
                px = v['w'] - px
            if o in ('MX', 'R180'):
                py = v['h'] - py
            sinks.append((l, 'clk', v['x'] + px, v['y'] + py))
        obs = [(v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h']) for v in leaves.values()]
        for n, b in P.items():
            if isinstance(b, dict) and 'x' in b and n.split('_')[0] not in ('phy', 'pc'):
                obs.append((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
        Wd, Hd = G['floorplan']['die_um']
        tree = dct.build(Wd, Hd, obs, root_xy, sinks,
                         lambda inst: re.search(r'(SW|SE|NW|NE)', inst).group(1),
                         leaf_pads=(json.loads(a.clock_pads.read_text()).get('leaf') if a.clock_pads else None),
                         quad_pads=(json.loads(a.clock_pads.read_text()).get('quadrant') if a.clock_pads else None))
        for n, d, loads in tree['nets']:
            for ld in loads:
                if ld[0] == 'pin':
                    leafclk[ld[1]] = n
    for l, v in leaves.items():
        used[l].update(clk_pins[v['master']]); used[l].add('rst_n')
    # ---- die.v ----
    L = ['// H-DIE r3 v15 PC-row die case on REAL views (tools/hbm_die_v15/view_case.py); out-of-region pins open',
         'module hbm_v15_pcrow (input wire clk_hbm, input wire rst_n);']
    for n in sorted(nets):
        L.append(f'  wire {n};')
    nc = []
    conn = defaultdict(list)
    for n, ends in nets.items():
        for l, p, _ in ends:
            conn[l].append((p, n))
    for l in sorted(leaves):
        v = leaves[l]
        cs = [f'.clk({leafclk.get(l, "clk_hbm")})', '.rst_n(rst_n)']
        bus = defaultdict(dict); scal = []
        for p, n in conn[l]:
            m = re.fullmatch(r'(\w+)\[(\d+)\]', p)
            if m:
                bus[m.group(1)][int(m.group(2))] = n
            else:
                scal.append((p, n))
        for p, n in sorted(scal):
            cs.append(f'.{p}({n})')
        for p, bits in sorted(bus.items()):
            # width of the view bus
            wv = 1 + max(int(re.fullmatch(r'\w+\[(\d+)\]', q).group(1)) for q in vpins[v['master']]
                         if q.startswith(p + '['))
            parts = [bits.get(k, '') for k in range(wv - 1, -1, -1)]
            for k in range(wv):
                if not bits.get(k):
                    nc.append(f'nc_{l}_{p}_{k}')
            parts = [x if x else f'nc_{l}_{p}_{k}' for k, x in zip(range(wv - 1, -1, -1), parts)]
            cs.append(f'.{p}({{{", ".join(parts)}}})')
        L.append(f'  {v["master"]} {l} (\n    ' + ',\n    '.join(cs) + '\n  );')
    if tree:
        for n, d, loads in tree['nets']:
            L.append(f'  wire {n};')
        drv = {}
        for n, d, loads in tree['nets']:
            if d[0] == 'buf':
                drv[d[1]] = n
        inp = {}
        for n, d, loads in tree['nets']:
            for ld in loads:
                if ld[0] == 'buf':
                    inp[ld[1]] = n
        first = [n for n, d, _ in tree['nets'] if d == ('port', 'clk_hbm')]
        assert len(first) == 1, first
        ren = {first[0]: 'clk_hbm'}
        L[:] = [x for x in L if x != f'  wire {first[0]};']
        for b, cell, x, y in tree['buffers']:
            L.append(f'  {cell} {b} (.A({ren.get(inp[b], inp[b])}), .Y({drv.get(b, b + "_nc")}));')
    L.append('endmodule')
    L[2:2] = [f'  wire {n};' for n in nc]
    (out / 'die.v').write_text('\n'.join(L) + '\n')
    # nc_* = an out-of-region bit: a dangling single-pin net, never a constant; STA sees it unconstrained
    # ---- run.tcl ----
    W, H = G['floorplan']['die_um']
    plat = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    p_ = TILE / 15.0
    libs = []
    for m, v in VIEWS.items():
        d = v['dir']
        libs.append((m, d))
    tree_pl = [] if not tree else [f'place_inst -name {b} -location {{{x:.3f} {y:.3f}}} -orientation R0 -status FIRM'
                                   for b, cell, x, y in tree['buffers']]
    pl = [f'place_inst -name {l} -location {{{v["x"]:.3f} {v["y"]:.3f}}} -orientation {v["orient"]} -status FIRM'
          for l, v in sorted(leaves.items())]
    tcl = f'''# H-DIE r3: v15 PC-row die GRT + TT/FF STA on real views (generated by tools/hbm_die_v15/view_case.py)
read_lef {plat}/lef/asap7_tech_1x_201209.lef
read_lef {plat}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/views/{PHY_M}.lef
read_lef /work/views/{PC_M}.lef
define_corners tt ff
read_liberty -corner tt /work/views/{PC_M}_tt.lib
read_liberty -corner ff /work/views/{PC_M}_ff.lib
read_liberty -corner tt /work/views/{PHY_M}_tt.lib
read_liberty -corner ff /work/views/{PHY_M}_ff.lib
{{STDLIB}}
read_verilog /work/die.v
link_design hbm_v15_pcrow
initialize_floorplan -die_area {{0 0 {W} {H}}} -core_area {{0 0 {W} {H}}} -site asap7sc7p5t
make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064
make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048
make_tracks M3 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.009 -y_pitch {p_:.3f}
make_tracks M2 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.045 -y_pitch {p_:.3f}
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
{chr(10).join(pl)}
{chr(10).join(tree_pl)}
{{PINS}}
source {plat}/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
{{CTS}}
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
set t0 [clock seconds]
global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
report_wire_length -net * -global_route -file /work/out/wirelength_grt.csv
estimate_parasitics -global_routing
create_clock -name hbm -period {T_PS} [get_ports clk_hbm]
{{PROP}}
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_n]
proc dump {{corner kind fn}} {{
  set f [open $fn w]
  set n 0
  foreach pe [find_timing_paths -corner $corner -path_delay $kind -group_path_count {a.paths} -endpoint_path_count 1 -slack_max 1e9 -sort_by_slack] {{
    set sp [get_full_name [get_property $pe startpoint]]
    set ep [get_full_name [get_property $pe endpoint]]
    puts $f "$sp $ep [get_property $pe slack]"
    incr n
  }}
  close $f
  puts "OT_PATHS $corner $kind $n"
}}
foreach {{c k}} {{tt max ff min}} {{
  report_checks -corner $c -path_delay $k -group_path_count 5 -format full_clock_expanded -fields {{slew cap input_pins nets fanout}} > /work/out/worst_${{c}}_${{k}}.rpt
  dump $c $k /work/out/paths_${{c}}_${{k}}.txt
}}
report_tns
{{SKEW}}
puts OT_DONE
'''
    if a.die_clock:
        ck = slots[a.ckgen]
        cx = ck['origin']['x'] + ck['outline']['w'] / 2; cy = ck['origin']['y'] + ck['outline']['h'] / 2
        region_kinds = ('phy', 'pc')
        blk = []
        for n, b in sorted(P.items()):
            if not isinstance(b, dict) or 'x' not in b or n.split('_')[0] in region_kinds:
                continue
            blk.append((n, b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
        bl = '\n'.join(f'odb::dbBlockage_create $blk [expr int({x0}*$dbu)] [expr int({y0}*$dbu)] '
                        f'[expr int({x1}*$dbu)] [expr int({y1}*$dbu)]  ;# {n}' for n, x0, y0, x1, y1 in blk)
        pins = (f'place_pin -pin_name clk_hbm -layer M9 -location {{{cx:.3f} {cy:.3f}}} -pin_size {{0.4 0.4}}\n'
                'place_pins -hor_layers M4 -ver_layers M5 -min_distance 2')
        cts = f'''set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
# every compact660_v5 block outside this region is a hard placement blockage: die clock buffers live in the
# 0.6 mm channels, relay rows and the soft service bands only (the closed views block themselves)
{bl}
create_clock -name hbm -period {T_PS} [get_ports clk_hbm]
set_wire_rc -clock -layer M8
set_wire_rc -signal -layer M6
# die clock on M7-M9 (tiles cap M5, clusters M6): the die tree crosses blocks above their layer cap
set_routing_layers -signal M4-M9 -clock M7-M9
set t1 [clock seconds]
clock_tree_synthesis -root_buf BUFx24_ASAP7_75t_R -buf_list {{BUFx16f_ASAP7_75t_R BUFx24_ASAP7_75t_R}} {a.cts_opts}
puts "OT_CTS_S [expr {{[clock seconds]-$t1}}]"
# legality without a die-wide site grid (detailed_placement over 660 mm2 of sites exceeds 32 GB): every clock buffer
# must lie outside every blockage and every placed view
set nb 0; set bad 0
set obs {{}}
foreach b [$blk getBlockages] {{ set r [$b getBBox]; lappend obs [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] }}
foreach i [$blk getInsts] {{
  if {{[[$i getMaster] isBlock]}} {{ set r [$i getBBox]; lappend obs [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] }}
}}
foreach i [$blk getInsts] {{
  if {{[[$i getMaster] isBlock]}} continue
  incr nb
  set r [$i getBBox]
  foreach o $obs {{
    if {{[$r xMin] < [lindex $o 2] && [lindex $o 0] < [$r xMax] && [$r yMin] < [lindex $o 3] && [lindex $o 1] < [$r yMax]}} {{ incr bad; break }}
  }}
}}
puts "OT_CTS_BUFS $nb OT_CTS_ILLEGAL_BEFORE $bad"
# legalise: move each clock buffer that sits on a blockage / view to the nearest free point (8 directions, growing
# radius 5 um .. 3 mm); the moved wire is real and global-routed below
proc ot_free {{x0 y0 x1 y1 obs W H}} {{
  if {{$x0 < 0 || $y0 < 0 || $x1 > $W || $y1 > $H}} {{ return 0 }}
  foreach o $obs {{ if {{$x0 < [lindex $o 2] && [lindex $o 0] < $x1 && $y0 < [lindex $o 3] && [lindex $o 1] < $y1}} {{ return 0 }} }}
  return 1
}}
set W [[$blk getDieArea] xMax]; set H [[$blk getDieArea] yMax]
set moved 0; set unfixed 0; set maxd 0
foreach i [$blk getInsts] {{
  if {{[[$i getMaster] isBlock]}} continue
  set r [$i getBBox]; set x0 [$r xMin]; set y0 [$r yMin]; set w [expr [$r xMax]-$x0]; set h [expr [$r yMax]-$y0]
  if {{[ot_free $x0 $y0 [expr $x0+$w] [expr $y0+$h] $obs $W $H]}} continue
  set done 0
  foreach d {{5 10 20 40 80 120 160 240 320 480 640 960 1280 1920 2560 3000}} {{
    set dd [expr int($d*$dbu)]
    foreach {{dx dy}} {{1 0 -1 0 0 1 0 -1 1 1 1 -1 -1 1 -1 -1}} {{
      set nx [expr $x0+$dx*$dd]; set ny [expr $y0+$dy*$dd]
      if {{[ot_free $nx $ny [expr $nx+$w] [expr $ny+$h] $obs $W $H]}} {{ $i setLocation $nx $ny; set done 1; break }}
    }}
    if {{$done}} {{ if {{$d > $maxd}} {{ set maxd $d }}; break }}
  }}
  if {{$done}} {{ incr moved }} else {{ incr unfixed }}
}}
puts "OT_CTS_LEGALISE moved $moved unfixed $unfixed max_move_um $maxd"
# clock-net geometry audit: driver and every sink location of each clock net (um)
set f [open /work/out/clock_nets.txt w]
foreach n [$blk getNets] {{
  if {{[$n getSigType] ne "CLOCK" && ![string match clknet* [$n getName]] && [$n getName] ne "clk_hbm"}} continue
  set s "[$n getName]"
  foreach it [$n getITerms] {{
    set i [$it getInst]; set ok [$it getAvgXY]
    append s " [$i getName]/[[$it getMTerm] getName]@[expr [lindex $ok 1]/$dbu],[expr [lindex $ok 2]/$dbu]"
  }}
  puts $f $s
}}
close $f
'''
        if a.die_clock_mode == 'explicit':
            cts = f'''set blk [ord::get_db_block]
# explicit die clock tree (tools/hbm_die_v15/die_clock_tree.py): {tree['model']['buffers']} repeaters, model insertion
# {tree['model']['model_insertion_ps']} ps; clock nets routed on M7-M9 (tiles cap M5, clusters M6)
foreach n [$blk getNets] {{ if {{[string match dck_* [$n getName]] || [string match n_dck_* [$n getName]] || [$n getName] eq "clk_hbm"}} {{ $n setSigType CLOCK }} }}
set_wire_rc -clock -layer M8
set_wire_rc -signal -layer M6
set_routing_layers -signal M4-M9 -clock M7-M9
puts "OT_DIE_CLOCK explicit buffers {tree['model']['buffers']}"
'''
        prop = 'set_propagated_clock [all_clocks]'
        skew = '''report_clock_skew -setup > /work/out/clock_skew.rpt
report_clock_skew -hold >> /work/out/clock_skew.rpt
catch {report_clock_latency -include_internal_latency > /work/out/clock_latency.rpt}
# per-sink die clock latency, both corners: the clock-pin arrival in each view's worst launched path (parsed by
# tools/hbm_die_v15/sink_latency.py from the full_clock_expanded reports)
foreach c {tt ff} {
  foreach n {SINKS} {
    report_checks -from [get_cells $n] -corner $c -path_delay [expr {$c eq "tt" ? "max" : "min"}] -format full_clock_expanded >> /work/out/sink_paths_$c.rpt
  }
}
catch {report_clock_latency > /work/out/clock_latency_plain.rpt}'''
    else:
        pins = 'place_pins -hor_layers M4 -ver_layers M5 -min_distance 2'
        cts = prop = skew = ''
    stdlib = '' if not a.die_clock else '\n'.join(
        f'read_liberty -corner {c} {plat}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{c.upper()}_nldm_220122.lib.gz' for c in ('tt', 'ff'))
    skew = skew.replace('{SINKS}', '{' + ' '.join(sorted(leaves)) + '}')
    tcl = tcl.replace('{STDLIB}', stdlib)
    tcl = tcl.replace('{PINS}', pins).replace('{CTS}', cts).replace('{PROP}', prop).replace('{SKEW}', skew)
    # worst_slack per corner: use report_worst_slack with -corner where available
    (out / 'run.tcl').write_text(tcl)
    vd = out / 'views'; vd.mkdir(exist_ok=True)
    for m, d in libs:
        shutil.copy(next(d.glob('*.lef')), vd / f'{m}.lef')
        for c in ('tt', 'ff'):
            shutil.copy(d / f'{m}_{c}.lib', vd / f'{m}_{c}.lib')
    (out / 'out').mkdir(exist_ok=True)
    # ---- manifest ----
    open_pins = {}
    for l, v in leaves.items():
        allp = [p for p, dr in vpins[v['master']].items() if p not in ('VDD', 'VSS')]
        un = [p for p in allp if p not in used[l]]
        open_pins[l] = len(un)
    man = dict(schema='opentallas.hbm_v15.view_case.v1', region=a.region, variant='B_pc_align' if a.pc_align else 'A_grants_v4', die_um=[W, H],
               contract_sha_file=str(CONTRACT.relative_to(ROOT)), grants=str(GRANTS.relative_to(ROOT)),
               grants_version=G['version'], plan=str(PLAN.relative_to(ROOT)),
               views={m: dict(dir=str(v['dir'].relative_to(ROOT)), kind=v['kind']) for m, v in VIEWS.items()},
               region_instances=region, leaves=len(leaves), pcs=sum(1 for v in leaves.values() if v['master'] == PC_M),
               edges_in_region=edges_in, signal_nets=len(nets),
               out_of_region_open_pins=sum(open_pins.values()), open_pins_by_leaf=open_pins,
               placement={l: v for l, v in leaves.items()},
               clock=('REAL die clock delivery: PLL pll_hbm output at the hfd_ckgen slot, TritonCTS die tree (ASAP7 RVT '
                      'buffers, channels/relay rows only), global-routed, propagated; tile insertion inside each ETM'
                      if a.die_clock else 'ideal die clock hbm 833.333 ps (no die CTS); tile insertion inside each ETM'),
               corners='setup TT, hold FF (owner option B); SS not run (sensitivity only)')
    if tree:
        man['die_clock_tree'] = tree['model']
        man['die_clock_buffers'] = [dict(name=b, cell=c, x=x, y=y) for b, c, x, y in tree['buffers']]
    (out / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps({k: man[k] for k in ('leaves', 'pcs', 'edges_in_region', 'signal_nets', 'out_of_region_open_pins')}))


if __name__ == '__main__':
    main()

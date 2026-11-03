#!/usr/bin/env python3
"""DIE-HBM-59/CORES 11-02 plan event ONEFACE-1 (class MACRO-ARRAY ONE-FACE PINS, COORD GEOM 11-02).

    python3 mk_event.py BASE_DIE_PLAN.json[.gz] SIDECAR_DIR OUT_DIR TOOLS_DIE_PLAN_DIR

BASE = d44q die_plan (metadata-only descendant of d44o; same 84 designs + pins sha).  SIDECAR_DIR = the d44o_cm plan
dir (cores/, core_macros.json, core_conns.json, ...).  Writes OUT_DIR/die_plan.json, OUT_DIR/core_macros.json, the new
pins files in OUT_DIR/cores/ and OUT_DIR/oneface_event.json; every other sidecar is symlinked.
  (1) ot_hbm_su_static_sfustore_hw: lane-grouped S/M5 pins under each bank column (lane_pin_align.py lane mode;
      clk + fault kept: fault's partner u_hleaf_Q is on the E side).
  (2) ot_hnx_idxn_keybuf_slice: its 2231 W/M4 pins spread over the whole W face (10.4 -> 7.7 pins/um; order kept) and
      the 5-SRAM stack stays (a shift to the E bound put the clock entry island over gm[2]: G0C clock_entry_macro).
  (3) PLAN_CORE_MACROS 'no KNOWN macro rects' (gen_core_kit_hbm core_macros_placement needs status KNOWN): static
      KNOWN sites through core_macros_fix.fix (outline inset, no overlap, LEF size, 10.8-um channel arithmetic):
      selector_static_sel = the 12 sites of the placed kits-26 kit at the same outline (selector_k26a_macro_placement.tcl);
      dma_back_static_vp4_banks_cp = its 10 PLAN-TRIAL R-SRAM-ENTRY rows (names checked against the flattened RTL);
      svc_wb_kport_q = 4 columns (g_root) x 8 (g_lane) u_payload, equal channels, the centre channel holds the clock
      entry island [233.28,241.92]^2.  tkm_m_tp192__root is NOT a macro case: its gen stops at MAP_AMBIGUOUS (cut map).
"""
import gzip, json, os, subprocess, sys
from pathlib import Path

base, side, out, tools = map(Path, sys.argv[1:5])
op = gzip.open if str(base).endswith('.gz') else open
P = json.load(op(base, 'rt'))
out.mkdir(parents=True, exist_ok=True); (out / 'cores').mkdir(exist_ok=True)
for f in side.iterdir():
    if f.name in ('die_plan.json', 'core_macros.json', 'cores') or (out / f.name).exists():
        continue
    os.symlink(f.resolve(), out / f.name)
for f in (side / 'cores').iterdir():
    if not (out / 'cores' / f.name).exists():
        os.symlink(f.resolve(), out / 'cores' / f.name)
CM = json.load(open(side / 'core_macros.json'))
LPA = str(tools / 'lane_pin_align.py')
ev = dict(schema='opentallas.hbm_plan_event.v1', event='oneface1', base=str(base), changes=[])


def hc_of(module):
    return [(tn, hc) for tn, t in P['partition_types'].items() for hc in t.get('hard_cores') or [] if hc['module'] == module]


def repoint(module, new, note):
    n = 0
    for tn, hc in hc_of(module):
        hc['pins_file'] = 'cores/' + new
        hc['note'] = (hc.get('note') or '') + ' | ' + note
        n += 1
    return n


# (1) sfustore_hw
m = 'ot_hbm_su_static_sfustore_hw'
(tn, hc), = hc_of(m)[:1]
W, H = hc['outline_um']
new = '%s__%gx%g__lanealign.json' % (m, W, H)
subprocess.run([sys.executable, LPA, str(side / hc['pins_file']), str(side / 'core_macros.json'), m, str(W), str(H),
                str(out / 'cores' / new), '--face', 'S', '--layer', 'M5', '--keep', 'clk,fault'], check=True)
# fault stays on E (partner u_hleaf_Q is E) but moves to the low end of E, next to the S lane band: probe AUTO-GEOM
# r2r worst u_fcore.fault -> u_bout_fault 419.47 um at y 257.544 (limit 405).
pf = out / 'cores' / new
pp = json.load(open(pf))
for q in pp:
    if q['name'] == 'fault':
        q['y'] = 10.008                     # M4 track 0.024 + 208 * 0.048
json.dump(pp, open(pf, 'w'), indent=1)
ev['changes'].append(dict(module=m, pins_from=hc['pins_file'], pins_to='cores/' + new, fault_y=[257.544, 10.008],
                          instances=repoint(m, new, 'DIE-HBM-59 ONEFACE-1: lane-grouped S pins under bank columns')))
# (2) keybuf_slice
m = 'ot_hnx_idxn_keybuf_slice'
(tn, hc), = hc_of(m)[:1]
W, H = hc['outline_um']
new = '%s__%gx%g__spread.json' % (m, W, H)
subprocess.run([sys.executable, LPA, str(side / hc['pins_file']), str(side / 'core_macros.json'), m, str(W), str(H),
                str(out / 'cores' / new), '--mode', 'spread', '--face', 'W', '--layer', 'M4'], check=True)
ev['changes'].append(dict(module=m, pins_from=hc['pins_file'], pins_to='cores/' + new,
                          instances=repoint(m, new, 'DIE-HBM-59 ONEFACE-1: W pins spread over the face')))
# (3) PLAN_CORE_MACROS static sites
import re
sys.path.insert(0, str(tools.parent.parent / 'physical' / 'die_plan' / 'hbm'))
import core_macros_fix as CMF  # noqa: E402
here = Path(__file__).resolve().parent
sizes = CMF.lef_sizes(str(tools.parent.parent / 'physical' / 'asap7_memory_macros_v2'))
static = {}
sel = [dict(name=n.replace('\\', ''), master=mm, origin_um=[float(x), float(y)], orient=o) for n, mm, x, y, o in
       re.findall(r'\{(\S+)\}\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)', (here / 'selector_k26a_macro_placement.tcl').read_text())]
static['ot_hbm_idx_selector_static_sel'] = dict(basis='kits-26 placed kit ot_hbm_idx_selector_static_sel_a8b6d07217f0-_k26a '
                                                'macro_placement.tcl (same view, same outline 600.048x450.36)', macros=sel)
d = CM['cores']['ot_hgi_dma_back_static_vp4_banks_cp']
static['ot_hgi_dma_back_static_vp4_banks_cp'] = dict(
    basis='PLAN-TRIAL R-SRAM-ENTRY rows promoted (names = flattened RTL instances, DIE-HBM-59 11-02)',
    macros=[dict(name=r['name'], master=r['master'], origin_um=r['rect_um'][:2], orient=r.get('orient', 'R0')) for r in d['macros']])
CM['cores']['ot_hgi_dma_back_static_vp4_banks_cp']['status'] = 'UNKNOWN'   # fix() refuses to overwrite KNOWN only
mw, mh = sizes['ot_sram_1r1w_128x256_m1_r2c2']
W, H = CM['cores']['ot_hbm_svc_wb_kport_q']['outline_um']
gx, gy = (W - 8.64 - 4 * mw) / 5, (H - 8.64 - 8 * mh) / 9
snapx = lambda v: round(round(v / 0.054) * 0.054, 4)
snapy = lambda v: round(round((v - 0.012) / 0.048) * 0.048 + 0.012, 4)
static['ot_hbm_svc_wb_kport_q'] = dict(
    basis='DIE-HBM-59 ONEFACE-1 column rule: column r = u_fcore.u_wb.g_root[r], lane l stacked bottom-up, equal channels',
    macros=[dict(name='u_fcore.u_wb.g_root[%d].g_lane[%d].u_payload' % (r, l), master='ot_sram_1r1w_128x256_m1_r2c2',
                 origin_um=[snapx(4.32 + gx + r * (mw + gx)), snapy(4.32 + gy + l * (mh + gy))], orient='R0')
            for r in range(4) for l in range(8)])
rep = CMF.fix({'cores': {k: CM['cores'][k] for k in static}}, sizes, {}, static, {'hnx_lane_x'})  # static pass only; entries edited in place
ev['changes'].append(dict(class_='PLAN_CORE_MACROS', static=rep['static']))
# the stack is NOT moved: the clock entry island [203.04,142.56,211.68,151.2] sits 5.4 um right of the stack (G0C
# clock_entry_macro on a probe shift to x0 53.976); the clock entry is a die clock contract, so only the pins move.
json.dump(CM, open(out / 'core_macros.json', 'w'), indent=1)
json.dump(P, open(out / 'die_plan.json', 'w'))
json.dump(ev, open(out / 'oneface_event.json', 'w'), indent=1)
print(json.dumps(ev, indent=1))

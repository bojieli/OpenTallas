"""Default-off geometry/model delta. No RTL installation or physical launcher."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import qwen_rom_fulldie_b3r2 as B

ROOT = Path(__file__).resolve().parents[1]
LIMIT_NM = 5_250_000
PINS = ['tools/qwen_rom_fulldie_b3r2.py', 'tools/qwen_rom_fulldie.py',
        'tools/qwen_rom_fulldie_pg_r3.py', 'tools/hdc_isa.py', 'tools/uarch_model.py',
        'results/uarch/qwen_clock_boundary_reconcile_20261004/inputs/clocking_decision.json']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def nm(value):
    return round(value * 1000)


def split_regions(regions, cuts, enabled=False):
    if not enabled:
        raise ValueError('clock boundary reconciliation is default off')
    result, changed = [], []
    for original in regions:
        r = copy.deepcopy(original)
        x0, y0, x1, y1 = r['rect']
        if max(nm(x1)-nm(x0), nm(y1)-nm(y0)) > LIMIT_NM:
            candidates = [c for c in cuts if y0 < c < y1]
            if r['kind'] not in ('tile_block', 'spine_band') or len(candidates) != 1:
                raise ValueError('overlength region lacks unique existing channel cut')
            cut = candidates[0]
            changed.append({'original': r['name'], 'original_rect_um': r['rect'], 'cut_um': cut})
            for suffix, lo, hi in [('south', y0, cut), ('north', cut, y1)]:
                q = copy.deepcopy(r)
                q.update(name=r['name']+'_'+suffix, rect=[x0, lo, x1, hi], parent_region=r['name'])
                result.append(q)
        else:
            r['parent_region'] = r['name']
            result.append(r)
    for r in result:
        x0,y0,x1,y1 = map(nm, r['rect'])
        r['extent_nm'] = max(x1-x0,y1-y0)
        r['extent_mm'] = r['extent_nm']/1e6
        r['within_5p25'] = r['extent_nm'] <= LIMIT_NM
        if not r['within_5p25']:
            raise ValueError('corrected region still exceeds exact 5.25mm bound')
    return result, changed


def owner(inst, regions):
    found = [r for r in regions if r['rect'][0] <= inst.cx < r['rect'][2]
             and r['rect'][1] <= inst.cy < r['rect'][3]]
    if len(found) > 1:
        raise ValueError('ambiguous region ownership: '+inst.name)
    return found[0]['name'] if found else None


def project(v, m, enabled=False):
    original = copy.deepcopy(m['clock_regions'])
    cuts = [round(c+v.HCH/2,3) for c in m['geo']['ch_y']]
    regions, changed = split_regions(original, cuts, enabled)
    by = {i.name:i for i in m['insts']}
    before = {n:owner(i, original) for n,i in by.items()}
    after = {n:owner(i, regions) for n,i in by.items()}
    separated, unassigned, spanning = [], [], []
    for bid,cl,width,eps in m['buses']:
        if len(eps) != 2:
            raise ValueError('unpriced bus arity: '+bid)
        a,b = [e[0] for e in eps]
        if before[a] and before[a] == before[b] and after[a] != after[b]:
            separated.append(dict(bus=bid, kind=cl, bits=width, endpoints=eps,
                                  old_region=before[a], new_regions=[after[a],after[b]]))
        if after[a] is None or after[b] is None:
            unassigned.append(bid)
    for i in m['insts']:
        for change in changed:
            x0,y0,x1,y1 = change['original_rect_um']
            c = change['cut_um']
            if i.x < x1 and i.x+i.w > x0 and i.y < c < i.y+i.h:
                spanning.append(dict(instance=i.name, master=i.master, kind=i.kind,
                                     rect_um=[i.x,i.y,i.x+i.w,i.y+i.h], cut_um=c,
                                     region=change['original']))
    # Exact tree dependency graph: each hosted node has n_a/n_b inputs and one n_y.
    tree = [b for b in m['buses'] if b[1]=='tree_block']
    incoming = {}
    for bid,_,_,eps in tree:
        incoming.setdefault(eps[1][0],[]).append((bid,eps[0]))
    extra = {e['bus'] for e in separated}
    visiting, memo = set(), {}
    def depth(host):
        if host in visiting:
            raise ValueError('tree dependency cycle')
        if host in memo:
            return memo[host]
        visiting.add(host)
        d = max((int(bid in extra)+(depth(src) if port=='n_y' else 0)
                 for bid,(src,port) in incoming[host]), default=0)
        visiting.remove(host)
        memo[host]=d
        return d
    longest = max(map(depth,incoming),default=0)
    priced = {}
    for e in separated:
        p=priced.setdefault(e['kind'],dict(count=0,payload_bits_per_cycle=0,storage_bits=0))
        p['count']+=1
        p['payload_bits_per_cycle']+=e['bits']
        # Capacity envelope, not a codec: depth4 + binary pointers (3 bits),
        # 3FF synchronization in each direction + local pointers/flags/reset synchronizers.
        p['storage_bits'] += 4*e['bits']+32
    count=len(separated)
    total_bits=sum(p['storage_bits'] for p in priced.values())
    logic=total_bits*B.FIFO_MM2_PER_BIT
    for p in priced.values():
        p['port_bytes_per_cycle']=p['payload_bits_per_cycle']/8
        p['boundary_bits_per_cycle_with_valid_ready']=p['payload_bits_per_cycle']+2*p['count']
        p['mux_input_bits']=4*p['payload_bits_per_cycle']
        p['fifo_read_write_ports_each']=p['count']
    # Head drives two outward chains, never two serial channel crossings.
    corridor_in = {eps[1][0]:(bid,eps[0][0]) for bid,cl,_,eps in m['buses'] if cl=='corridor'}
    def corridor_depth(host, seen=frozenset()):
        if host in seen:
            raise ValueError('corridor dependency cycle')
        if host not in corridor_in:
            return 0
        bid,src=corridor_in[host]
        return int(bid in extra)+corridor_depth(src,seen|{host})
    corridor_hops=max(map(corridor_depth,corridor_in),default=0)
    import uarch_model as U
    probes = {}
    for delta in (0, 4, 8, 16):
        p = U.qwen_tp_point(4, 6144, 'board', clock_hz=U.PRODUCT_CLOCK_HZ,
                            me_lat_extra=167+delta, su_width=64)
        probes[str(delta)] = dict(cycles=p['cycles'], tokens_s_b1=p['tokens_s_b1'])
    dependency_paths = set()
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and Path(filename).suffix == '.py':
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT) and path != Path(__file__).resolve():
                dependency_paths.add(path)
                for value in vars(module).values():
                    if isinstance(value, Path) and value.is_absolute() and value.is_relative_to(ROOT):
                        if value.is_file() and value.suffix == '.json':
                            dependency_paths.add(value)
    # Eager model globals read these two analytical ledgers through expressions.
    dependency_paths.update(ROOT/p for p in ('results/arch/arch_budget_v41.json',
                                             'results/arch/qwen3_budget.json',
                                             'configs/hardware/technology.json'))
    dependencies = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(dependency_paths)}
    return dict(schema='opentallas.qwen-clock-boundary-reconcile.r1',
        frozen_source='084c732e6a3f938445853606db9fbc149d13ff20',
        archived_clock_model_origin='d99237f66:results/uarch/rom_die_clocking_decision_20261003.json',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PINS},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        selection='default off; region projection only, no installed clock/RTL change',
        unified_model_dependency_sha256=dependencies,
        unified_model_probe=dict(entry='qwen_tp_point(4,6144,board,PRODUCT_CLOCK_HZ,me_lat_extra=167+delta,su_width=64)',
             points=probes, scope='prospective ME-path sensitivity only; sideband/scale/link clocks and prefetch remain unresolved'),
        die=m['die'], cuts_um=cuts, original_count=len(original), corrected_count=len(regions),
        max_extent_mm=max(r['extent_mm'] for r in regions), changes=changed, regions=regions,
        preserved_geometry_sha256=digest([(i.name,i.master,i.x,i.y,i.w,i.h,i.orient) for i in m['insts']]),
        preserved_bus_graph_sha256=digest(m['buses']),
        source_ownership={n:after[n] for n in sorted(after)},
        newly_separated_buses=separated, new_crossing_capacity=priced,
        fifo_envelope=dict(depth=4, per_fifo_control_state_bits=32,
             control='two 3-bit binary pointers, two 3FF pointer synchronizers, 2 flags, two 3FF reset synchronizers',
             total_state_bits=total_bits, gross_area_mm2=logic,
             cost_basis='same gross per-bit proxy as frozen decision-C; new added capacity, existing 2.53mm2 not charged again',
             prospective_home_50pct_mm2=2*logic,
             placement='unallocated die area envelope only; actual aligned FIFO slots/PG/routing must be signed by Claude',
             mux='4-entry read mux per payload bit; included only in inherited gross per-bit area proxy, no physical census'),
        latency=dict(tree_serial_new_crossings=longest,corridor_serial_new_crossings=corridor_hops,
             nominal_extra_cycles_per_ME_op=2*(longest+corridor_hops),
             sensitivity_cycles_per_ME_op={str(d):d*(longest+corridor_hops) for d in (1,2,4)},
             assumption='unprefetched instruction path plus golden-order return; all endpoints/fifos ready; no bound on backpressure',
             clock_ns=1/1.2, measured_primitive_extra_cycles=2,
             primitive='Claude meso measured functional delta2/crossing; SS unclosed, not installed',
             reset='3FF reset release per selected region; accepted debt must drain before coordinated reset, no forced clearing'),
        admission=dict(physical_launch_allowed=False, claude_agreement='requested; not received',
             source_MACs_per_cycle_delta=0, compute_intensity_delta=0,
             channel_capacity='unchanged geometry; new valid/ready/sync routes not assigned: no positive track admission',
             unassigned_source_bus_count=len(unassigned), unassigned_source_buses=unassigned,
             macros_spanning_new_cut=spanning,
             blockers=['Claude ownership agreement', 'actual clock/reset and corridor codec implementation (reset is not ordinary FIFO data)',
                       'link/corner macro clock ownership spanning new boundary', 'matched SS/FF FIFO/forwarded-clock qualification',
                       'aligned home/track and source-matched PG/IR admission']),
        scope='geometry/model proposal only; actual265746overflow remains failure, no adoption')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--enable-boundary-reconcile',action='store_true')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--regions-def',type=Path)
    a=p.parse_args()
    if not a.enable_boundary_reconcile:
        p.error('selection is default off')
    v,m=B.selected(True,True,True)
    r=project(v,m,True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    if a.regions_def:
        m['clock_regions']=r['regions']
        B.write_def_regions(v,m,a.regions_def)


if __name__=='__main__':
    main()

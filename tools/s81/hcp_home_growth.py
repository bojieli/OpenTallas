#!/usr/bin/env python3
"""Actual native HCP hard-child geometry and die home growth, no timing claim."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys

R = Path(__file__).resolve().parents[2]
AREA_COMMIT = '164085869'
AREA_PATH = 'results/rtl/s81_hcx_partition_1015/mapped_area_summary.json'
OUT = R / 'results/physical/die_iter_1012/s81/hcp_home_growth_1015'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default=str(OUT / 'plan_r8c.json.gz'))
    a = ap.parse_args()
    raw = subprocess.check_output(['git', '-C', str(R), 'show', AREA_COMMIT + ':' + AREA_PATH])
    area = json.loads(raw)
    sys.path.insert(0,str(R / 'tools/ref_tile'))
    spec = importlib.util.spec_from_file_location('native_ref_tile', R / 'tools/ref_tile/ref_tile.py')
    rt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rt)
    homes = json.loads((R / 'physical/s81_die_pins/v20_functional/homes.json').read_text())
    plan_path = Path(a.plan)
    plan = json.load(gzip.open(plan_path))
    W, H = 1728.0, 1296.0
    nodes = []
    def add(name, master, x, y, w, h, std_area=None):
        nodes.append(dict(name=name, master=master, idx=len(nodes), kind='child',
                          x=x, y=y, w=w, h=h, offtrack=None,
                          standardcell_area_um2=std_area,
                          native_pin_views='NOT_YET_PUBLISHED: offtrack is unknown; geometry only'))
    for b in range(8):
        add(f'bank{b}', 'ot_s81_hcx_hcp_bank', 43.2 + 345.6 * (b % 4),
            43.2 + 388.8 * (b // 4), 324, 367.2,
            area['hard_owner_standardcell_area_um2'][f'top/g_bank[{b}].child'])
    lane_area = max(v for k,v in area['hard_owner_standardcell_area_um2'].items() if '.g_hard_lane[' in k)
    for i in range(6):
        add(f'lane{i}', 'ot_s81_hcx_hcp_lane8', 1425.6, 43.2 + 86.4 * i, 211.68, 62.64, lane_area)
    for i in range(26):
        add(f'lane{i+6}', 'ot_s81_hcx_hcp_lane8', 43.2 + 259.2 * (i % 6),
            820.8 + 86.4 * (i // 6), 211.68, 62.64, lane_area)
    tree_area = area['per_kind_summary']['tree_stdcell_area_um2'][0] if 'per_kind_summary' in area else None
    if tree_area is None:
        tree_area = next(v for k,v in area['hard_owner_standardcell_area_um2'].items() if 'tree' in k)
    add('tree', 'ot_hdc_v41x_addtree', 1425.6, 561.6, 211.68, 62.64, tree_area)
    add('shell', 'ot_s81_hcx_projection_partition::shell_clock_owner', 1425.6, 648, 211.68, 125.28,
        area['hard_owner_standardcell_area_um2']['shell'])
    assert len(nodes) == 42
    gate_spec = dict(kind='cluster', pins={f: ['real_pending_pins'] for f in 'NSEW'})
    checks = rt.floorplan_checks(gate_spec, W, H, nodes, None)
    assert not checks, checks
    util = []
    for n in nodes:
        if n['name'].startswith('bank'):
            continue  # bank10 macro native probe at source commit owns macro packing proof
        core = (n['w'] - 2 * rt.CORE_MARGIN) * (n['h'] - 2 * rt.CORE_MARGIN)
        u = n['standardcell_area_um2'] / core
        assert u <= 0.60, (n['name'], u)
        util.append(dict(name=n['name'], core_area_um2=core, standardcell_util=u))
    grown = copy.deepcopy(homes)
    audits = []
    reserved = []
    for home in grown['hc_projection']:
        home['outline'] = dict(w=W, h=H)
        home['master_candidate'] = 'ot_s81_hcx_projection_partition'
        home['source_structural_defect'] = 'bank rotation traverses shell combinationally: registered rotation boundary redesign required before native adoption'
        home['qualification'] = 'GEOMETRIC_GRANT_ONLY: actual42root native pins/cuts/phi-R/latency/CTS/TT/FF/DRC still required'
        x,y = home['at_um']
        bad = [t[0] for t in plan['insts'] if x < t[2]+t[4]-1e-6 and x+W > t[2]+1e-6
               and y < t[3]+t[5]-1e-6 and y+H > t[3]+1e-6]
        assert not bad, (home['name'],bad)
        assert x >= 0 and y >= 0 and x+W <= plan['die'][0] and y+H <= plan['die'][1]
        audits.append(dict(name=home['name'], origin_um=[x,y], outline_um=[W,H],
                           existing_instance_collisions=bad, outside=False))
        reserved.append((home['name'],x,y,W,H))
    for home in [homes['engram_mix'],json.loads((R/'physical/s81_die_pins/v20_embedding/home.json').read_text())]:
        if 'at_um' in home and 'outline' in home:
            reserved.append((home.get('name','embedding'),*home['at_um'],home['outline']['w'],home['outline']['h']))
    for a,b in itertools.combinations(reserved,2):
        assert not(a[1]<b[1]+b[3]-1e-6 and a[1]+a[3]>b[1]+1e-6 and a[2]<b[2]+b[4]-1e-6 and a[2]+a[4]>b[2]+1e-6),(a,b)
    OUT.mkdir(parents=True, exist_ok=True)
    report=dict(scope='Constructive42child geometric sizing candidate + six expanded home collision audits; NOT pin/timing qualification',
        mapped_area_source=dict(commit=AREA_COMMIT,path=AREA_PATH,sha256=hashlib.sha256(raw).hexdigest()),
        plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),placed_instances=len(plan['insts']),
        parent_outline_um=[W,H],child_count=len(nodes),checks=checks,nodes=nodes,
        native_geometry_tool_sha256=hashlib.sha256((R/'tools/ref_tile/ref_tile.py').read_bytes()).hexdigest(),
        hard_child_geometry_status='PRE_ROTATOR_REDESIGN: sizing evidence for current mapped owners, not an adopted partition',
        child_core_utilization=util,home_audits=audits,
        rules=dict(channel_um=rt.CHANNEL_UM,core_edge_margin_um=rt.CORE_MARGIN,
                   child_origin_lattice_um=rt.CHILD_LATTICE_UM,diagnostic_exceptions=False),
        open=['bank->lane combinational shell rotation violates strict registered boundary: implement real registered rotation and re-measure area/latency/clock ABI',
              'actual lane pin files and all per-bit bank/rotator/lane/shell cuts',
              'actual offtrack pin check from published child LEFs',
              'registered die hops and physical compiled calendar;264cycles is component-only',
              'per-root measured phi-R/CTS and TTsetup/FFhold/DRC0',
              'actual wrapper shell hard boundary/module and full real view binding'])
    (OUT/'geometry.json').write_text(json.dumps(report,indent=1)+'\n')
    target=R/'physical/s81_die_pins/v20_hcx_partition';target.mkdir(parents=True,exist_ok=True)
    (target/'homes.json').write_text(json.dumps(grown,indent=1)+'\n')
    print(json.dumps(dict(child_count=len(nodes),floorplan_checks=checks,homes=len(audits),
                         audited_instances=len(plan['insts']),outline=[W,H],max_leaf_util=max(v['standardcell_util'] for v in util))))

if __name__ == '__main__':
    main()

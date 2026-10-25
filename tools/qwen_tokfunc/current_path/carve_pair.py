#!/usr/bin/env python3
"""Compose the literal QC T1 path and a complete native KV bound top at their declared PHY bumps.

No native/service substitutes or idle-zero lane drivers are generated. Every unprovided data/control boundary
remains an explicit testbench port. Omitted QC reset/START carriers use published prefix ages; retained RTL is exact.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

# Resolve relative to the repository (this file is tools/qwen_tokfunc/current_path/carve_pair.py).
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'tools/die_plan'))
import bind_smoke as SM
spec = importlib.util.spec_from_file_location('literal_carve', REPO / 'tools/qwen_tokfunc/xdie_bound/bound_carve.py')
BC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BC)

T1 = {f'sl_W5_{x}' for x in ['ctl','fe','fw','hc0','hc1','hc2','hc3','sc','st_a','st_b','stm','su_c','su_l0','su_l1']}
T1 |= {f'c_W5_{s}_{r}{c}' for s in ['bf','bn','tn','tf'] for r in range(2) for c in range(2)}
T1 |= {'coll_f4','native59','glue','ucie_kv','tt_ctlm'}


def path_seeds(plan):
    """Include actual projection plus every transit of a lane between the retained functional endpoints."""
    wanted = set(T1)
    ports = {x['id']: x for x in plan['ports']}
    # Only endpoints of the specified path determine closure: transit-only additions do not pull in unrelated work.
    for lane in plan['lanes']:
        chain = [ports[n] for n in lane['ports']]
        if chain[0]['src']['part'] in T1 and chain[-1]['dst']['part'] in T1:
            wanted.update(x[k]['part'] for x in chain for k in ['src','dst'])
    return sorted(wanted)


def top_ports(path):
    result = {}
    for line in path.read_text().splitlines():
        m = re.match(r'^\s*(input|output)\s+wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*[,;]?', line)
        if m:
            result[m[4]] = dict(direction=m[1], width=int(m[2])-int(m[3])+1 if m[2] else 1)
        if re.match(r'^\s*wire\b', line):
            break
    return result


def compose(qc_top, qc_plan, kv_top, out, whole_qc=False):
    out.mkdir(parents=True, exist_ok=False)
    plan = json.loads(qc_plan.read_text())
    _, _, insts = BC.parse_top(qc_top)
    seeds = sorted(i['name'] for i in insts) if whole_qc else path_seeds(plan)
    if whole_qc:
        pp = top_ports(qc_top)
        manifest = {k:{n:v for n,v in pp.items() if v['direction']==d} for k,d in [('inputs','input'),('outputs','output')]}
        qc_module = re.search(r'^module\s+(\w+)', qc_top.read_text(), re.M)[1]
    else:
        manifest = BC.carve(qc_top, seeds, 'qc_t1_carve', out)
        qc_module = 'qc_t1_carve'
    keep = [i for i in insts if i['name'] in seeds]
    # Recover image IDs from source names, rather than physical nicknames.
    names = json.loads((qc_top.parent.parent/'bind_names.json').read_text())
    rom = []
    rom_ids = set()
    for i in keep:
        if not re.fullmatch(r'c_[EW][0-5]_[bt][fn]_[01][01]', i['name']):
            continue
        for r, c in SM.tiles_of(qc_top.parent, i['module']):
            local = f"{i['name']}.u_u_t_{r}_{c}"
            source = names.get(local, '')
            m = re.fullmatch(r'c16_[EW][0-5]_([0-3])\.u_t_(\d)_(\d)', source)
            if not m or (int(m[2]), int(m[3])) != (r, c):
                raise ValueError(f'no exact source ROM identity for {local}: {source}')
            strap = re.search(r'\.S_u_t_'+str(r)+'_'+str(c)+r"_tile_id\(16'b([01]{16})\)", '\n'.join(i['text']))
            if not strap:
                raise ValueError(f'no exact source tile strap for {local}')
            high = int(strap[1],2) & ~15
            rid = high+SM.SLOT[(r,c)]
            if rid in rom_ids:
                raise ValueError(f'duplicate ROM image {rid}')
            rom_ids.add(rid)
            rom.append(f'defparam `OT_ROM_BIND_TOP.u_qc.{local}.ROM_TILE = {rid};')
    expected_roms = 768 if whole_qc else 64
    if rom_ids != set(range(expected_roms)):
        raise ValueError(f'expected {expected_roms} distinct source ROM images, got {sorted(rom_ids)}')
    (out/'rom_bind_pair.vh').write_text('// Define OT_ROM_BIND_TOP as the pair instance. Source-derived image IDs.\n'+'\n'.join(rom)+'\n')
    # Hard PHY receives its reset from the real D2D master; it is not a wavefront carrier.
    by_part = {p['name']:p for p in plan['partitions']}
    hard = [i for i in keep if plan['partition_types'][by_part[i['name']]['type']].get('hard')]
    soft = [i for i in keep if i not in hard]
    reset = SM.qc_reset_contract(qc_top, soft)
    meta = json.loads((qc_top.parent.parent/'bind_reset.json').read_text())
    for i in hard:
        cs = dict(i['conns'])
        if 'start_i' in cs:
            raise ValueError(f"hard PHY unexpectedly has a START input: {i['name']}")
        if 'arst_n' not in cs:
            continue
        row = meta['parts'][i['name']]
        age = int(row['release'])-int(row['entry_stages'])-int(row['depth_K'])
        if age < 0:
            raise ValueError('invalid hard-IP reset prefix age')
        net=cs['arst_n']
        if net!='rst_n' and row.get('parent') not in set(seeds):
            old=reset['boundary_prefixes'].setdefault(net,age)
            if old!=age:
                raise ValueError('conflicting hard-IP reset prefix age')
    if reset.get('release') != 'wavefront' or not reset.get('start'):
        raise ValueError('T1 requires declared reset and START wavefronts')
    qp = {n: dict(v, direction=d) for d, k in [('input','inputs'),('output','outputs')] for n,v in manifest[k].items()}
    kp = top_ports(kv_top)
    for p, prefix in [(qp,'ucie_kv'), (kp,'sys_c')]:
        for pin, direction, width in [('link_v','output',1),('link_flit','output',583),('far_v','input',1),('far_flit','input',583)]:
            row = p.get(f'{prefix}_{pin}')
            if not row or row['direction'] != direction or row['width'] != width:
                raise ValueError(f'missing/invalid real PHY bump {prefix}_{pin}: {row}')
    module = re.search(r'^module\s+(\w+)', kv_top.read_text(), re.M)[1]
    hdr = ['input wire ck', 'input wire rst_n', 'input wire start']
    body, wires, connections = [], [], {'qc':{}, 'kv':{}}
    prefixes = dict(reset['boundary_prefixes'])
    start_prefixes = reset['start']['boundary_prefixes']
    bump_links = {
        ('qc','ucie_kv_far_v'): 'kv__sys_c_link_v',
        ('qc','ucie_kv_far_flit'): 'kv__sys_c_link_flit',
        ('kv','sys_c_far_v'): 'qc__ucie_kv_link_v',
        ('kv','sys_c_far_flit'): 'qc__ucie_kv_link_flit',
    }
    external = []
    for die, pp in [('qc',qp),('kv',kp)]:
        for name, row in pp.items():
            width, direction = row['width'], row['direction']
            rng = f'[{width-1}:0] ' if width>1 else ''
            sig = f'{die}__{name}'
            if direction=='input' and name in ['rst_n','start']:
                connections[die][name] = name
            elif direction=='input' and name.startswith('clk_'):
                connections[die][name] = 'ck'
            elif (die,name) in bump_links:
                connections[die][name] = bump_links[(die,name)]
            elif die=='qc' and direction=='input' and name in (set(prefixes)|set(start_prefixes)):
                source = 'rst_n' if name in prefixes else 'start'
                age = prefixes[name] if name in prefixes else start_prefixes[name]
                wires.append(f'wire {sig};')
                if age:
                    body += [f"reg [{age-1}:0] p_{name} = {age}'d0;", f'always @(posedge ck) p_{name} <= {{p_{name}, {source}}};',f'assign {sig} = p_{name}[{age-1}];']
                else:
                    body.append(f'assign {sig} = {source};')
                connections[die][name] = sig
            else:
                hdr.append(f'{direction} wire {rng}{sig}')
                connections[die][name] = sig
                external.append(dict(die=die, name=name, direction=direction, width=width, lane=row.get('lane')))
    for die, mod in [('qc',qc_module),('kv',module)]:
        body.append(f'{mod} u_{die} (\n'+',\n'.join(f'    .{p}({n})' for p,n in connections[die].items())+'\n);')
    text = '// Literal QC projection/transport + native KV; all environmental inputs are explicit.\n`timescale 1ns/1ps\n`default_nettype none\n'
    text += 'module qwen_native_pair (\n    '+',\n    '.join(hdr)+'\n);\n'+'\n'.join(wires+body)+'\nendmodule\n`default_nettype wire\n'
    (out/'qwen_native_pair.sv').write_text(text)
    report = dict(schema='opentallas.qwen.literal_pair.v1',qc_top=str(qc_top),kv_top=str(kv_top),qc_plan=str(qc_plan),
                  qc_top_sha256=BC.sha256(qc_top),kv_top_sha256=BC.sha256(kv_top),plan_sha256=BC.sha256(qc_plan),
                  qc_seeds=seeds, whole_qc=whole_qc, rom_tiles=len(rom_ids), reset=reset, boundary_ports=external,
                  link='QC.ucie_kv_link_* -> KV.sys_c_far_* and KV.sys_c_link_* -> QC.ucie_kv_far_*',
                  scope='Structural adapter only. Scheduler must drive every environmental input; no boot/token verdict implied.')
    (out/'pair.json').write_text(json.dumps(report,indent=1)+'\n')
    return report


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--qc-top',type=Path,required=True);ap.add_argument('--qc-plan',type=Path,required=True)
    ap.add_argument('--kv-top',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--whole-qc',action='store_true',help='Retain the entire native QC top for complete projection coverage')
    a=ap.parse_args();r=compose(a.qc_top,a.qc_plan,a.kv_top,a.out,a.whole_qc)
    print('LITERAL_PAIR_STAGED',len(r['qc_seeds']),'QC partitions,',len(r['boundary_ports']),'explicit boundary ports')

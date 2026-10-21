"""Explicit frame LP clock sources and master-local placement transforms.

Absent instance_clock_ports/instance_orientations retain the legacy binder and
RVcase behavior. This module builds source input, never a qualification receipt.
"""
from __future__ import annotations
import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT_WIDTHS = dict(rst_n=1, x=1104, xk=4, lk=12, xo=1104, xok=4, ret=70,
                   ck_r0=1, ck_r1=1, ck_r2=1)
VECTOR_PORTS = {'x', 'xk', 'lk', 'xo', 'xok', 'ret'}
ORIENT_BITS = {'R0': (False, False), 'MX': (False, True),
               'MY': (True, False), 'R180': (True, True)}


def compose_orientation(a, b):
    try:
        aa, bb = ORIENT_BITS[a], ORIENT_BITS[b]
    except KeyError as e:
        raise ValueError(f'unsupported frame orientation {e.args[0]}') from e
    bits = tuple(x != y for x, y in zip(aa, bb))
    return next(k for k, v in ORIENT_BITS.items() if v == bits)


def orient_point(x, y, w, h, orient='R0'):
    try:
        mx, my = ORIENT_BITS[orient]
    except KeyError as e:
        raise ValueError(f'unsupported frame orientation {orient}') from e
    return (w - x if mx else x), (h - y if my else y)


def orient_face(face, t, w, h, orient='R0'):
    """Physical/local face conversion; these four reflections are self-inverse."""
    mx, my = ORIENT_BITS[orient]
    if face in 'WE':
        return ({'W':'E', 'E':'W'}[face] if mx else face), (h-t if my else t)
    return ({'S':'N', 'N':'S'}[face] if my else face), (w-t if mx else t)


def instance_clocks(table, block, region):
    """Ordered clock-port/net pairs; explicit maps are real declared top inputs."""
    m = table['masters'][block['master']]
    ports = m.get('clock_ports') or [m['clk']] + list(m.get('clk_extra', []))
    row = table.get('instance_clock_ports', {}).get(block['name'])
    if row is None:
        root = m.get('clock_port', f'ck_{region}')
        return [(p, root) for p in [m['clk']] + list(m.get('clk_extra', []))]
    if set(row) != set(ports) or m['clk'] not in row or len(set(row.values())) != len(row):
        raise ValueError(f"{block['name']}: exact distinct clock-port bindings required: {ports}")
    domains = table.get('clock_domains', {})
    for p, net in row.items():
        if not isinstance(net, str) or not re.fullmatch(r'[A-Za-z_]\w*', net) or net not in domains:
            raise ValueError(f"{block['name']}.{p}: clock must name a declared real top input, got {net!r}")
    return [(p, row[p]) for p in ports]


def orientation(table, name):
    value = table.get('instance_orientations', {}).get(name, 'R0')
    if value not in ORIENT_BITS:
        raise ValueError(f'{name}: unsupported instance orientation {value}')
    return value


def ranged_pin_plan(spec):
    """Unoriented planned pin positions inside the actual kit's per-port ranges.

    These are planned positions, not a claim about the routed PPL coordinates.
    They replace the old whole-face centroid approximation only for this opt-in
    frame table. A real closed LEF remains authoritative when available.
    """
    pins = {}
    ranges = spec.get('pin_ranges') or {}
    for face, ports in spec['pins'].items():
        for port in ports:
            if port not in ranges or port not in PORT_WIDTHS:
                raise ValueError(f"{spec['name']}: missing explicit frame pin range {port}")
            lo, hi = ranges[port]
            width = PORT_WIDTHS[port]
            for bit in range(width):
                name = f'{port}[{bit}]' if port in VECTOR_PORTS else port
                pins[name] = [face, lo + (hi-lo)*(bit+.5)/width, 'M4' if face in 'WE' else 'M5']
    return dict(source=f"{spec['name']}:spec.pin_ranges", outline=[spec['outline']['w'],spec['outline']['h']], pins=pins)


def source_text(ref, path):
    return subprocess.run(['git','-C',str(ROOT),'show',f'{ref}:{path}'],check=True,
                          capture_output=True,text=True).stdout


def apply(plan, table, read, source_ref='21b97190e'):
    """Build the explicit frame-only overlay; non-frame bindings stay unchanged."""
    out = copy.deepcopy(table)
    frames = [b for b in plan['blocks'] if b['master'] in ('col_h9','col_h9_MX','col_h10')]
    maps = out.setdefault('instance_clock_ports', {})
    orients = out.setdefault('instance_orientations', {})
    domains = out.setdefault('clock_domains', {})
    kits = out.setdefault('kits', {})
    pin_plans = out.setdefault('standin_pin_plans', {})
    refs = out.setdefault('rtl_refs', {}).setdefault(source_ref, [])
    prefer = out.setdefault('prefer', [])
    meta = dict(source_ref=source_ref, instances={}, view_status='GATE_PENDING',
                clock_sources='Distinct die top inputs, three per instance; related same-frequency PLL sources.',
                pin_coordinates='Planned within exact kit pin_ranges, transformed once; routed LEF supersedes.',
                legacy_chain_end_modules_removed=[], steady_state_cycles_added_by_ownership=0)
    for h in (9,10):
        module = f'col_h{h}_l4_lp';kit=f'physical/ref_tile/s81frame_col_h{h}_rf3rlfs1'
        spec = json.loads(read(f'{kit}/spec.json'))
        pp = ranged_pin_plan(spec);pin_plans[module]=pp
        kits[module] = dict(ref=source_ref,kit=kit)
        # Functional twin retains INSTANCE and exact child parameters for source
        # GEN. Kit source is separately pinned by the physical gate/view.
        twin=f'rtl/dsrom_sys/s81_dv/frame_lp/col_h{h}_l4_lp_rf3r.sv'
        deps=[twin,'rtl/lib/ot_reset_sync.sv','rtl/common/landed_parent/ot_pl_land.sv',
              'rtl/common/landed_parent/ot_pl_land_field_copies.sv',
              'rtl/common/landed_parent/ot_pl_land_reset_forest.sv']
        for path in deps:
            if path not in refs:refs.append(path)
            pathref=f'{source_ref}/{path}'
            if pathref not in prefer:prefer.append(pathref)
        out.setdefault('rtl_widths', {})[module]=dict(PORT_WIDTHS)
        for key in (('col_h9','col_h9_MX') if h==9 else ('col_h10',)):
            m=out['masters'][key]
            if m.get('chain_end'):meta['legacy_chain_end_modules_removed'].append(dict(master=key,contract=m.pop('chain_end')))
            m.pop('inst_module',None)
            m.update(module=module,clk='ck_r0',clock_ports=['ck_r0','ck_r1','ck_r2'],clk_extra=[],
                     view=None,view_note=f'Actual reset-landed LP source; {kit} gate pending at {source_ref}; no closed view claimed.')
            m['instance_param']='INSTANCE'
    for b in frames:
        name=b['name'];module=out['masters'][b['master']]['module'];pp=pin_plans[module]
        class_o='MX' if b['master']=='col_h9_MX' else 'R0'
        # The selected plan's orient is a die transform; the logical MX class
        # still needs its master-local mirror unless explicitly recorded there.
        die_o=b.get('orient','R0')
        final=die_o if b.get('orientation_includes_master',False) else compose_orientation(die_o,class_o)
        orients[name]=final;maps[name]={}
        entry=dict(logical_master=b['master'],module=module,programme_instance=f'u_{name}',
                   die_orientation=die_o,class_orientation=class_o,orientation=final,
                   receiver_reset_edges=4,forwarded_reset_edges=2,clock_ports={})
        for i in range(3):
            cp=f'ck_r{i}';net=f'ck_frame_{name}_r{i}'
            f,t,layer=pp['pins'][cp]
            x,y=(0 if f=='W' else b['w'],t) if f in 'WE' else (t,0 if f=='S' else b['h'])
            x,y=orient_point(x,y,b['w'],b['h'],final);xy=[round(b['x']+x,3),round(b['y']+y,3)]
            maps[name][cp]=net
            domains[net]=dict(period_ps=833.333,asynchronous_to_core=False,relationship='same_pll_fixed_phase',
                              source_kind='die_top_input',receiver_instance=f'u_{name}',receiver_clock_port=cp,
                              receiver_region=f'r{i}',receiver_pin_xy_um=xy,receiver_pin_source=pp['source'],
                              source_ref=source_ref)
            entry['clock_ports'][cp]=dict(net=net,xy_um=xy,source='distinct_die_top_input')
        meta['instances'][name]=entry
    fw=out.setdefault('frame_wrapper',{})
    fw.update(masters=['col_h9','col_h9_MX','col_h10'],receiver_reset_edges=4,
              note='Plan-master keys. Actual LP rst_n -> two FRL stages -> crs4 two-stage rsync; xk relay reset adds two receiver edges separately.')
    names={b['name']:b for b in frames}
    lane_rows={n:{} for n in names}
    for link in plan['links']:
        dst=plan['blocks'][link['e'][1][0]]
        if dst['name'] in names and link['e'][1][1]=='x':
            match=re.search(r'_l([0-3])$',link['i'])
            if not match:raise ValueError(f"frame x lane lacks exact lane index: {link['i']}")
            lane_rows[dst['name']][match.group(1)]=link['i'].replace('-','_')
    out.setdefault('frame_lk',{})['rows']=[dict(inst=n,master=names[n]['master'],lanes=lanes,
        source='actual selected plan x-lane endpoints; K supplied by selected land plan')
        for n,lanes in sorted(lane_rows.items())]
    meta['integration_holds']=['Use the selected72 land plan; inherited legacy table land_plan is not qualified.',
        'Full LP chain-end outputs remain real ports. Legacy non-LP _nx substitution removed; unconsumed outputs must remain visible to strict bind.',
        'Per-frame programme/calendar must use LP compiler records; no current72 functional qualification claimed.']
    out['frame_lp_binding']=meta
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True)
    ap.add_argument('--table',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--source-ref',default='21b97190e');a=ap.parse_args()
    result=apply(json.loads(a.plan.read_text()),json.loads(a.table.read_text()),
                 lambda path:source_text(a.source_ref,path),a.source_ref)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=1)+'\n')
    print(f"FRAME_BIND source overlay: {len(result['frame_lp_binding']['instances'])} instances -> {a.out}")

if __name__=='__main__':main()

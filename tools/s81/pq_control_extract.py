#!/usr/bin/env python3
"""Extract the actual PQ control group without changing its clocks or cycles.

Yosys elaborates the immutable source packet, keeps existing datapath hard-leaf
boundaries, and groups all control cells plus the two real calendar ROMs.
The generated netlist remains a candidate until exact simulation, body/pins,
clock delivery, static calendars and physical qualification pass.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess

KEEP = {
    'ot_s81_pq_aq_common_native', 'ot_s81_pq_aq_math_native', 'ot_s81_pq_aq_mem_native',
    'ot_s81_pq_ix_ba_native', 'ot_s81_pq_ix_rb_native', 'ot_s81_pq_qb_headpc_native',
    'ot_s81_pq_qb_bankp_native', 'ot_s81_pq_qb_align_native', 'ot_s81_pq_fault_pin',
    *{f'ot_s81_pq_bc_slice{k}' for k in range(4)},
}
ROOT = Path(__file__).resolve().parents[2]


def run(yosys, script, path):
    path.with_suffix('.ys').write_text(script)
    with path.with_suffix('.log').open('w') as log:
        subprocess.run([yosys, '-s', str(path.with_suffix('.ys'))], stdout=log, stderr=subprocess.STDOUT, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hierarchy', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--yosys', default='yosys')
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    h = json.loads(a.hierarchy.read_text())
    if not {'OT_PQ_QB_PINREAD', 'OT_PQ_CTL_CALCAP', 'DSFD_PQ_ROM4', 'DSFD_PQ_STATIC_X2'} <= set(h['defines']):
        raise ValueError('Extraction requires the explicit physical candidate PINREAD+CALCAP+ROM4+STATIC_X2')
    sources = [ROOT / f for f in h['source_sha256']]
    for source, expected in h['source_sha256'].items():
        if hashlib.sha256((ROOT/source).read_bytes()).hexdigest() != expected:
            raise ValueError('Stale hierarchy source: ' + source)
    physical_sources=[];transforms=[]
    normalized=a.out/'physical_sources';normalized.mkdir(exist_ok=True)
    for source in sources:
        text=source.read_text();original=text
        memory=source.name in ('ot_sram_1r1w_128x256_m1_r2c2.v','ot_rom_4096x72_m8.v')
        if memory:
            # A physical blackbox retains the functional header's exact image
            # parameters, names and ports. Candidate simulation binds the real
            # mapped macro model, never this empty physical elaboration header.
            begin=text.index('module '+source.stem)
            end=text.index(');',begin)+2
            text='(* blackbox *)\n'+text[begin:end]+'\nendmodule\n'
        text,n=re.subn(r'\bparameter\s+string\s+', 'parameter ',text)
        if text!=original:
            dest=normalized/(str(len(physical_sources))+'_'+source.name)
            dest.write_text(text);physical_sources.append(dest.resolve())
            transforms.append(dict(source=str(source.relative_to(ROOT)),physical=str(dest),memory_header_only=memory,string_parameter_types_removed=n,original_sha256=hashlib.sha256(original.encode()).hexdigest(),physical_sha256=hashlib.sha256(text.encode()).hexdigest()))
        else:physical_sources.append(source)

    defs = ' '.join('-D' + d for d in h['defines'])
    read = 'read_verilog -sv -defer -DSYNTHESIS ' + defs + ' ' + ' '.join(map(str,physical_sources)) + ';\n'
    seed = read + 'hierarchy -check -top dsfd_sp_pq_produced; proc;\nwrite_json ' + str((a.out/'hierarchy.json').resolve()) + ';\n'
    run(a.yosys, seed, a.out/'elaborate')
    design = json.loads((a.out/'hierarchy.json').read_text())
    blackboxes=[]
    for name, mod in design['modules'].items():
        original = mod.get('attributes', {}).get('hdlname', name).split()[0]
        if original in KEEP or name in KEEP:
            blackboxes.append(name)
    if not blackboxes:
        raise ValueError('No actual datapath hard leaves found')
    # The macro models are black boxes; controller descriptor arrays remain
    # actual storage and are mapped to flops before the source partition.
    script = read + 'hierarchy -check -top dsfd_sp_pq_produced;\n'
    script += ''.join('blackbox ' + name + ';\n' for name in blackboxes)
    script += 'setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; proc; memory_map; flatten; opt_clean -purge;\n'
    script += 'write_json ' + str((a.out/'flat.json').resolve()) + ';\n'
    run(a.yosys, script, a.out/'flatten')
    flat = json.loads((a.out/'flat.json').read_text())
    cells = flat['modules']['dsfd_sp_pq_produced']['cells']
    controls=[]; lanes=[]; retained=[]
    for name, cell in cells.items():
        if cell['type'] in blackboxes:
            retained.append(name)
        elif 'u_datapath.u_lane.' in name.replace(chr(92),''):
            lanes.append(name)
        else:
            controls.append(name)
    if not controls or not lanes or not retained:
        raise ValueError('Incomplete semantic groups')
    def selection(names):
        return ' '.join('dsfd_sp_pq_produced/c:' + name for name in names)
    for name in controls:cells[name].setdefault('attributes',{})['submod']='ot_s81_pq_control_joint'
    for name in lanes:cells[name].setdefault('attributes',{})['submod']='ot_s81_pq_lane_joint'
    (a.out/'marked.json').write_text(json.dumps(flat))
    final = 'read_json ' + str((a.out/'marked.json').resolve()) + '; submod;\n'
    final += 'rename dsfd_sp_pq_produced dsfd_sp_pq_joint_candidate;\n'
    final += 'write_json ' + str((a.out/'partition.json').resolve()) + ';\n'
    run(a.yosys, final, a.out/'partition')
    partition=json.loads((a.out/'partition.json').read_text())
    top=partition['modules']['dsfd_sp_pq_joint_candidate']
    group_names=('ot_s81_pq_control_joint','ot_s81_pq_lane_joint')
    groups={logical:cell['type'] for name,cell in top['cells'].items() for logical in group_names if name.endswith(logical)}
    group_cells={name for name in top['cells'] if any(name.endswith(g) for g in group_names)}
    if len(groups)!=2:raise ValueError('Both extracted groups must remain actual children')
    if set(top['cells'])!=set(retained)|group_cells:raise ValueError('Unowned parent cells remain after partition')
    actual_control=partition['modules'][groups['ot_s81_pq_control_joint']]['cells']
    actual_lane=partition['modules'][groups['ot_s81_pq_lane_joint']]['cells']
    if set(actual_control)-set(controls) or set(actual_lane)-set(lanes):raise ValueError('Unexpected extracted cells')
    dead=(set(controls)-set(actual_control))|(set(lanes)-set(actual_lane))
    # submod drops kept public prefix carry gates with no observable fanout.
    # Prove the ENTIRE removed cone is combinational and isolated from every
    # surviving cell input and every original external output; never permit
    # a register, macro, consumed bit or producer result to disappear.
    observable={b for port in flat['modules']['dsfd_sp_pq_produced']['ports'].values() if port['direction']=='output' for b in port['bits'] if isinstance(b,int)}
    for name,cell in cells.items():
        if name in dead:continue
        for port,bits in cell['connections'].items():
            if cell['port_directions'][port]=='input':observable.update(b for b in bits if isinstance(b,int))
    for name in dead:
        cell=cells[name]
        if cell['type'] not in ('$and','$or'):raise ValueError('Non-carry cell removed: '+name)
        output={b for port,bits in cell['connections'].items() if cell['port_directions'][port]=='output' for b in bits if isinstance(b,int)}
        if output & observable:raise ValueError('Observable logic removed: '+name)

    selected=['dsfd_sp_pq_joint_candidate',*groups]
    export='read_json '+str((a.out/'partition.json').resolve())+'; '
    export+=''.join('rename '+actual+' '+logical+'; ' for logical,actual in groups.items())
    export+='write_json '+str((a.out/'named_partition.json').resolve())+'; select '+' '.join(selected)+'; write_verilog -selected -noattr '+str((a.out/'candidate.v').resolve())+';\n'
    run(a.yosys,export,a.out/'export')
    receipt=dict(scope='Source partition only. Existing clocks/cycles unchanged; physical candidate unqualified.',
                 extraction_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 yosys_version=subprocess.check_output([a.yosys,'-V'],text=True).strip(),
                 hierarchy_sha256=hashlib.sha256(a.hierarchy.read_bytes()).hexdigest(),
                 physical_elaboration_transforms=transforms,source_sha256=h['source_sha256'],defines=h['defines'],blackbox_datapath_modules=blackboxes,
                 moved_control_cells=len(actual_control),moved_lane_cells=len(actual_lane),retained_hard_leaf_instances=len(retained),
                 unobservable_cleanup=dict(cells=sorted(dead),count=len(dead),types=sorted({cells[n]['type'] for n in dead}),proof='Every removed cell is AND/OR carry logic; its outputs feed only other removed cells and no surviving input or external output. No sequential state or memory removed.'),
                 candidate_sha256=hashlib.sha256((a.out/'candidate.v').read_bytes()).hexdigest(),
                 native_qualified=False,physical_adopted=False)
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ['moved_control_cells','moved_lane_cells','retained_hard_leaf_instances']}))


if __name__ == '__main__':
    main()

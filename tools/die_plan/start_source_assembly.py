#!/usr/bin/env python3
"""Build a complete source-only virtual START/RAW module from the selected CA bind.

Native partitions remain explicit interfaces. No clock tree or physical home is
invented here; the generated clock ports must later bind to the actual clock
source graph. This is the concrete input for locked synthesis/map extraction.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sid(region):
    return 's'+hashlib.sha256(region.encode()).hexdigest()[:20]


def emit(bind, root_settle=None):
    assert bind['period_ps']==833
    root_settle = int(bind.get('root_settle_cycles',64) if root_settle is None else root_settle)
    if root_settle<1: raise ValueError('invalid root SETTLE')
    reg=bind['regions']; virtual={r:d for r,d in reg.items() if d.get('virtual') is True}
    roots=[r for r,d in virtual.items() if d['parent'] is None]
    if len(roots)!=1:
        raise ValueError('one actual virtual root required')
    if set(virtual)!=set(r for r in reg if r.startswith('st:')):
        raise ValueError('ambiguous virtual/native region ownership')
    for r,d in reg.items():
        if d['parent'] is not None and d['parent'] not in reg:
            raise ValueError('missing actual parent '+r)
    source=lambda r: 'st_'+sid(r)+'_start' if r in virtual else 'rs_'+sid(r)
    raw=lambda r: 'st_'+sid(r)+'_rraw' if r in virtual else 'rraw_'+sid(r)
    ins={d['parent'] for d in virtual.values() if d['parent'] and d['parent'] not in virtual}
    outs={r:d for r,d in reg.items() if r not in virtual and d['parent'] in virtual}
    direct={r:d for r,d in reg.items() if r not in virtual and d['parent'] not in virtual}
    ports=['input wire rst_raw_n']
    ports += ['input wire clk_'+sid(r) for r in sorted(virtual)]
    ports += ['input wire '+n(r) for r in sorted(ins) for n in (source,raw)]
    ports += ['output wire pst_'+sid(r) for r in sorted(outs)]
    sv=['// Complete selected virtual CA graph; source-only, clocks/homes unqualified.',
        'module ot_die_start_stages (',',\n'.join('    '+p for p in ports),');']
    stages=[]
    for r in sorted(virtual):
        d=virtual[r]; i=sid(r); root=d['parent'] is None
        sv += ['    wire '+source(r)+';','    wire '+raw(r)+';']
        if root:
            sv += ['    wire st_'+i+'_start_d;',f'    assign {raw(r)} = rst_raw_n;',
                   f'    ot_dp_landing_root #(.SETTLE({root_settle})) u_st_{i} (.clk(clk_{i}), .rst_raw_n(rst_raw_n), .start({source(r)}), .start_d(st_{i}_start_d));']
        else:
            ef=int(bool(d['edge_fall'])); pad=int(d['pad'])
            if pad<0: raise ValueError('negative PAD')
            sv += [f'    ot_die_start_reset_relay #(.EDGE_FALL({ef})) u_rst_{i} (.clk(clk_{i}), .d({raw(d["parent"])}), .q({raw(r)}));',
                   f'    ot_dp_landing_origin #(.PAD({pad}), .EDGE_FALL({ef})) u_st_{i} (.clk(clk_{i}), .rst_raw_n({raw(r)}), .p_start({source(d["parent"])}), .start({source(r)}));']
        stages.append(dict(region=r,id=i,parent=d['parent'],root=root,pad=int(d['pad']),edge_fall=bool(d['edge_fall']),clock_port='clk_'+i,
                           source_home_status='UNASSIGNED; actual mapping/site allocation required'))
    outputs=[]
    for r,d in sorted(outs.items()):
        net='pst_'+sid(r); sv += [f'    assign {net} = {source(d["parent"])};']
        outputs.append(dict(dst_region=r,stage=sid(d['parent']),net=net))
    sv += ['endmodule',
        '(* keep_hierarchy *) module ot_die_start_reset_relay #(parameter bit EDGE_FALL=0) (input wire clk,input wire d,output wire q);',
        '    (* keep="true" *) reg r0,r1; wire x;',
        '    if(EDGE_FALL) begin:g_fall (* keep="true" *) reg rf; always @(negedge clk) rf<=d; assign x=rf; end',
        '    else begin:g_rise assign x=d; end',
        '    always @(posedge clk) begin r0<=x; r1<=r0; end',
        '    assign q=r1;', 'endmodule']
    doc=dict(schema='ot_start_source_assembly/1',period_ps=833,source_only=True,physical_qualified=False,root_settle=root_settle,stages=stages,
             reset_wave='bounded_synchronous_parent_relays',die_outputs=outputs,direct_ports=[],
             native_direct_edges=[dict(dst=r,parent=d['parent'])for r,d in sorted(direct.items())],
             native_interfaces=dict(inputs=sorted(ins),outputs=sorted(outs)),
             holds=['actual global clock source binding and native origin+reader tree','actual mapped QN/source gate/complete native loads',
                    'legal fullcell homes and DATA routing/retention','unchanged native direct edges owned by actual native/top assembly'])
    return doc,'\n'.join(sv)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bind');p.add_argument('--rtl',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();b=Path(a.bind).read_bytes();d,sv=emit(json.loads(b));o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
    d['bind_sha256']=hashlib.sha256(b).hexdigest()
    (o/'start_source.sv').write_text(sv)
    # Exact repository primitive bodies, without unrelated ring modules/macros.
    text=Path(a.rtl).read_text(); prim=[]
    for name in ('ot_dp_landing_root','ot_dp_landing_origin'):
        m=re.search(r'\bmodule\s+'+name+r'\s*#\(',text)
        if not m: raise ValueError('actual primitive missing '+name)
        end=text.index('endmodule',m.start())+len('endmodule');prim.append(text[m.start():end])
    (o/'start_primitives.sv').write_text('\n\n'.join(prim)+'\n')
    d['primitive_source_sha256']=hashlib.sha256(Path(a.rtl).read_bytes()).hexdigest()
    (o/'source_assembly.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(virtual_stages=len(d['stages']),native_outputs=len(d['die_outputs']),native_direct=len(d['native_direct_edges']),physical_qualified=False)))

if __name__=='__main__':main()

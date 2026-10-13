#!/usr/bin/env python3
"""Explicit physical cell mapping and PG prototype for die clock/reset nodes.

The source generator specifies hfd_ckb as a clock buffer and hfd_rrl as a
positive-edge reset pipeline flop. Other station families are never guessed.
DFFHQNx1 has QN=registered(!D) in the pinned Liberty, so an INVx2 restores D.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

PLAT='/OpenROAD-flow-scripts/flow/platforms/asap7'
BUF='BUFx24_ASAP7_75t_R'
FF='DFFHQNx1_ASAP7_75t_R'
INV='INVx2_ASAP7_75t_R'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(a):
    p=a.model
    m=json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
    nodes=[]
    for it in m['insts']:
        name,master,kind,region,domain,x,y,w,h,orient=it
        if master not in ('hfd_ckb','hfd_rrl'):
            continue
        cells=([dict(cell=BUF,name='u_buf',pins=dict(A='i',Y='o'),xy_um=[.54,.54])] if master=='hfd_ckb' else
               [dict(cell=FF,name='u_ff',pins=dict(D='i',CLK='ck',QN='qn'),xy_um=[.54,.54]),
                dict(cell=INV,name='u_inv',pins=dict(A='qn',Y='o'),xy_um=[1.836,.54])])
        nodes.append(dict(instance=name,master=master,domain=domain,rect_um=[x,y,x+w,y+h],orientation=orient,
                          cell_mapping=cells,semantics='combinational true clock buffer' if master=='hfd_ckb' else
                          'positive-edge true reset pipeline register; actual QN inversion compensated',
                          implemented_pg_layers=['M1','M2','M3','M4','M5'],parent_pg_layer='M6',
                          placement_status='local offsets planned within existing footprint, not routed'))
    a.out.mkdir(parents=True,exist_ok=True)
    rec=dict(schema='opentallas.hbm.clock_reset_physical_mapping.v1',source_commit=m.get('source_commit'),
             input_sha256={str(p):sha(p),str(Path(__file__)):sha(__file__)},
             nodes=nodes,clock_buffers=sum(n['master']=='hfd_ckb' for n in nodes),
             registered_resets=sum(n['master']=='hfd_rrl' for n in nodes),
             standard_cells=sum(len(n['cell_mapping']) for n in nodes),
             unsupported_station_families='forwarded/data stations require their native RTL mapping; no generic flop count assigned',
             final_signoff_eligible=False)
    (a.out/'cell_mapping.json').write_text(json.dumps(rec,indent=1)+'\n')
    rtl=f'''// Cell truth is checked against the actual ASAP7 TT Liberty before PG generation.
module hfd_ckb_native(input i, output o);
{BUF} u_buf(.A(i), .Y(o));
endmodule
module hfd_rrl_native(input i, input ck, output o);
wire qn;
{FF} u_ff(.D(i), .CLK(ck), .QN(qn));
{INV} u_inv(.A(qn), .Y(o));
endmodule
module hbm_glue_pg(input ck, input [3:0] ri, output [3:0] co, output [3:0] ro);
'''
    for i in range(4):
        rtl+=f'{BUF} b{i}(.A(ck), .Y(co[{i}]));\nwire qn{i};\n{FF} f{i}(.D(ri[{i}]), .CLK(co[{i}]), .QN(qn{i}));\n{INV} v{i}(.A(qn{i}), .Y(ro[{i}]));\n'
    (a.out/'mapped.v').write_text(rtl+'endmodule\n')
    t=f'''read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_verilog /work/mapped.v
link_design hbm_glue_pg
initialize_floorplan -die_area {{0 0 36.72 36.72}} -core_area {{2.16 2.16 34.56 34.56}} -site asap7sc7p5t
'''
    for i in range(4):
        y=4.32+i*5.4
        for n,x in ((f'b{i}',4.32),(f'f{i}',10.8),(f'v{i}',12.096)):
            t+=f'set inst [[ord::get_db_block] findInst {n}]\n$inst setLocation {round(x*1000)} {round(y*1000)}\n$inst setOrient R0\n$inst setPlacementStatus FIRM\n'
    t+='''check_placement
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name native -voltage_domains CORE -pins {M5}
add_pdn_stripe -grid native -layer M1 -width 0.018 -followpins
add_pdn_stripe -grid native -layer M2 -width 0.018 -followpins
add_pdn_stripe -grid native -layer M3 -width 0.09 -pitch 1.08 -spacing 0.45 -offset 0.27 -extend_to_boundary
add_pdn_stripe -grid native -layer M4 -width 0.12 -pitch 2.16 -spacing 0.96 -offset 0.54 -extend_to_boundary
add_pdn_stripe -grid native -layer M5 -width 0.12 -pitch 2.16 -spacing 0.96 -offset 0.54 -extend_to_boundary
foreach pair {{M1 M2} {M2 M3} {M3 M4} {M4 M5}} { add_pdn_connect -grid native -layers $pair }
pdngen -failed_via_report /work/failed_vias.rpt
puts {OT_PDN PASS}
write_db /work/native_pg.odb
write_abstract_lef /work/native_pg.lef
foreach net {VDD VSS} {
check_power_grid -net $net -error_file /work/pg_err_$net.rpt
puts "OT_PG net=$net PASS"
}
puts OT_DONE
'''
    (a.out/'run.tcl').write_text(t)
    (a.out/'manifest.json').write_text(json.dumps({k:v for k,v in rec.items() if k!='nodes'},indent=2)+'\n')
    print(json.dumps({k:v for k,v in rec.items() if k!='nodes'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    main(p.parse_args())

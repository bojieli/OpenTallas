from pathlib import Path
import json
r=Path(__file__).resolve().parents[2];out=r/'rtl/dsrom_sys/s81_ph/dsfd_gth_strip.sv'
s=['`timescale 1ns/1ps','// Gather control strip (v4): 133 one-cycle relay instances, each exactly as wide as its signal (no tied input);', '// parent contains wires only.  cs = {busy, fault} of every leaf (32 x 2) with the column ready, 9 b a column.', 'module dsfd_gth_strip(input wire [132:0] ck_r, input wire rst, input wire rsv,', 'input wire [23:0] tst_i, input wire [63:0] cs_i, input wire [7:0] ready_i, input wire [7:0] rc_i,', 'input wire [162:0] tc_i, input wire [11:0] fcd_i,', 'output wire [23:0] tst_o, output wire [63:0] cs_o, output wire [7:0] ready_o, output wire [7:0] rc_o,', 'output wire [162:0] tc_o, output wire [11:0] fcd_o);']
manifest=[]
def inst(name,master,d,q,width,role,stage):
 idx=len(manifest);reset='rsv' if role=='f_cd' else 'rst';s.append(f'    {master} {name} (.ck(ck_r[{idx}]), .rs({reset}), .i({d}), .o({q}));')
 manifest.append(dict(instance='u_strip.'+name,master=master,width=width,clock_index=idx,role=role,stage=stage,view='physical/ref_tile/s81_rly_'+master[9:].lower()+'/views/'+master))
for bus,n in [('tst',12),('cs',8)]:
 for g in range(n):
  if bus=='cs':
   s.append(f'    wire [44:0] cs_{g}; assign cs_{g}[8:0] = {{ready_i[{g}], cs_i[{8*g} +: 8]}};')
   for j in range(4):
    inst(f'cs_{g}_{j}','dsfd_rly_9_WE',f'cs_{g}[{9*j} +: 9]',f'cs_{g}[{9*j+9} +: 9]',9,f'cs{g}',j)
   s.append(f'    assign cs_o[{8*g} +: 8] = cs_{g}[43:36]; assign ready_o[{g}] = cs_{g}[44];')
  else:
   s.append(f'    wire [9:0] tst_{g}; assign tst_{g}[1:0] = tst_i[{2*g} +: 2];')
   for j in range(4):
    inst(f'tst_{g}_{j}','dsfd_rly_2_EW' if g>=6 else 'dsfd_rly_2_WE',f'tst_{g}[{2*j} +: 2]',f'tst_{g}[{2*j+2} +: 2]',2,f'tst{g}',j)
   s.append(f'    assign tst_o[{2*g} +: 2] = tst_{g}[9:8];')
for g in range(8):
 s.append(f'    wire [6:0] rc_{g}; assign rc_{g}[0] = rc_i[{g}];')
 for j in range(6):inst(f'rc_{g}_{j}','dsfd_rly_1_EW' if j<4 else 'dsfd_rly_1_WE',f'rc_{g}[{j}]',f'rc_{g}[{j+1}]',1,f'rc{g}',j)
 s.append(f'    assign rc_o[{g}] = rc_{g}[6];')
for g in range(3):inst(f'tc_{g}','dsfd_rly_54_EW',f'tc_i[{54*g} +: 54]',f'tc_o[{54*g} +: 54]',54,'tc',0)
inst('tc_3','dsfd_rly_1_EW','tc_i[162]','tc_o[162]',1,'tc',0)
inst('fcd','dsfd_rly_12_EN','fcd_i','fcd_o',12,'f_cd',0)
s.append('endmodule')
assert len(manifest)==133
out.write_text('\n'.join(s)+'\n')
(r/'tools/s81_ph/gather_strip_instances.json').write_text(json.dumps({'schema':'opentallas.s81.gather.strip_instances.v2','relay_cycles':{'tst':4,'cs':4,'root_ready':4,'rc':6,'tc':1,'f_cd_serial':1,'f_vm':0,'c_cmd':0},'instances':manifest,'pending':['placed geometry and pair reach','exact full-shape benchmark','reset pin assignment','routed ctl view and insertion']},indent=2)+'\n')

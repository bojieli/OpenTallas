import json,sys,pathlib,subprocess
import numpy as np
root=pathlib.Path.cwd();sys.path[:0]=[str(root/'tools'),str(root/'tools/hbm_static'),str(root/'tools/hgi_adapters')]
from hbm_layer_vehicle import layer_images as L
from hbm_layer_vehicle.idx_layer_lower_1021 import lower_broadcast,runtime_gather
from hbm_layer_vehicle.native_profile import NativeTiming
import su_bench as SB
records=L.ds_dispatches_image(root/'fixture/images/ds_v41_1M_L00_per_die.json')
fixtures=L.load_fixture(root/'fixture');timing=NativeTiming(18,15)
row=next(x for x in records if x[2]['tag']=='q_norm.y');raw=SB.pack_rec(row[1])
x=lower_broadcast(raw,q=0,timing=timing,rf_address=8,scalar_ready=24,rf_local=1,data=fixtures[10]['vm_in'].copy(),tag='q_norm.y')
assert x['status']=='candidate_requires_binding',x
assert not x['inputs_placeholder']
assert len(x['issue_edges'])==3
for v in x['ql'].f['rf'].values(): assert v==((256|8)<<9)
gather=next(x for x in records if x[2]['tag']=='route.gather0');g=runtime_gather(SB.pack_rec(gather[1]),timing=timing)
assert g['status']=='candidate_requires_binding',g
# Real scalar input only. O is never read by this RTL stimulus.
z=np.load(root/'fixture/operands.npz');scalar=int(z['r0.k11.B'][0]);assert all(int(v)==scalar for v in z['r0.k11.B'])
tb="""module tb;
reg clk=0;always #5 clk=~clk;reg rst=0,cmd=0;
wire[135:0]rq;reg[2055:0]rr=0;wire[2247:0]wq;
wire rv,busy,done,fault;wire[2:0]tag;wire[255:0]data;
ot_hbm_vm_scalar_coll_1021 #(.READ_RETURN(4))d(.clk(clk),.rst_n(rst),.cmd_v(cmd),
.cmd_indexed(1'b0),.cmd_to_rf(1'b1),.cmd_base_word(24'd49984),.cmd_index_word(24'd0),
.cmd_destination_word(24'd0),.cmd_return_tag(3'd3),.vm_rq(rq),.vm_rr(rr),.vm_kq(wq),
.rr_v(rv),.rr_tag(tag),.rr_d(data),.busy(busy),.done(done),.fault(fault));
integer e=0,due=-1,checks=0;
always @(posedge clk)begin
 e=e+1;
 if(rq[16])begin if(rq[15:0]!==16'd6248)$fatal(1,"BAD_REQUEST");due=e+4;end
end
always @(negedge clk)begin
 rr=0;
 if(e+1==due)rr[0+:257]={1'b1,224'd0,32'hSCALAR};
 if(rv)begin
  if(data!=={8{32'hSCALAR}}||tag!==3||fault)$fatal(1,"SCALAR_DATA");
  checks=checks+1;$display("SELECTED_Q_NORM_B_SCALAR_PASS checks=%0d",checks);$finish;
 end
 if(e>40)$fatal(1,"TIMEOUT");
end
initial begin repeat(3)@(negedge clk);rst=1;@(negedge clk);cmd=1;@(negedge clk);cmd=0;end
endmodule
""".replace('SCALAR',f'{scalar:08x}').replace('SELECTED_Q_NORM_B_'+f'{scalar:08x}'+'_PASS','SELECTED_Q_NORM_B_SCALAR_PASS')
(root/'selected_scalar_tb.sv').write_text(tb)
rtl='rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_vm_scalar_runtime_1021.sv'
vl=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
version=subprocess.check_output([str(vl),'--version'],text=True).strip()
assert '5.050' in version,version
subprocess.run([str(vl),'--binary','--timing','-O1','-j','1','-Wno-fatal','--top-module','tb','--Mdir','obj_selected',rtl,'selected_scalar_tb.sv'],check=True)
subprocess.run(['./obj_selected/Vtb'],check=True)
report=dict(scope='selected_i10_scalar_bridge_component_only',qualifies_native_layer=False,qualifies_native_chain=False,
 i10=dict(status=x['status'],issues=x['issue_edges'],commands=x['commands'],reservations=x['reservations']),
 i42=g,fixture_O_used_as_stimulus=False,verilator=version,remaining=['selected_contract_binding','actual_VM_return_age','IDX_produced_index','native_SU_numerical_connected_run'])
(root/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print('IDX_LOWER_COMPONENT_PASS')

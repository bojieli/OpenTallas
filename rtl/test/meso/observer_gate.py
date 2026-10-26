import sys,re,json,hashlib
from pathlib import Path
wt=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
sys.path.insert(0,str(wt/'tools/die_plan'))
from clock_landings import gate_observer
wrap=wt/'rtl/qwen_split/qfd_sys_face_lctx3_wrapped.sv';core=wt/'rtl/qwen_split/qfd_sys_face_lctx3_core.sv'
w=wrap.read_text();c=core.read_text()
captures=[]
for n in ['obs_fault','seq_cfg_image_ready']:
 m=re.search(r'  wire \[0:0\] '+n+r'__ot_pr;.*?  assign '+n+r'__ot_pr = '+n+r'__ot_q;',w,re.S);assert m;captures.append(m.group())
m=re.search(r'    reg obs_fault_q;.*?    assign fault = face_fault;',c,re.S);assert m
sticky=m.group();admit=re.search(r'admit_ready <= boot_done.*?;',c).group();assert 'rp_program_ready' in admit
# Exact source cut: wrapper registered boundary followed by sticky fault and
# admission expression. Other real face-fault and admission inputs are frontier.
cut='module observer_cut(input ck,rst_obs,obs_fault,seq_cfg_image_ready,input boot_done,rp_program_ready,t_running_q,input boot_fault,prog_fault,cal_fault,emb_fault,prov_fault_q,rp_fault,head_tx_fault,head_mux_fault,armed_fault,go_fault,mu_hc_fault,output fault,output wire ready_capture,output reg admit_ready);\nwire face_fault;\n'+'\n'.join(captures)+'\n'+sticky.replace('else if (obs_fault)','else if (obs_fault__ot_pr)')+'\nassign ready_capture=seq_cfg_image_ready__ot_pr;\nalways @(posedge ck) begin '+admit+' end\nendmodule\n'
# Core receives __ot_pr through the actual wrapper instance connections.
assert '.obs_fault(obs_fault__ot_pr)' in w and '.seq_cfg_image_ready(seq_cfg_image_ready__ot_pr)' in w
spec=dict(module='qfd_sys_face_lctx3_wrapped',instance_suffix='u_sys_face',fault_port='obs_fault',ready_port='seq_cfg_image_ready')
text='    qfd_sys_face_lctx3_wrapped u_sys_face (\n        .obs_fault(old_fault),\n        .seq_cfg_image_ready(old_ready)\n    );\n'
gated=gate_observer(text,spec)
args={}
for n in ['obs_fault','seq_cfg_image_ready']:
 start=gated.index('.'+n+'(')+len(n)+2;end=gated.index('\n',start);args[n]=gated[start:end].rstrip(',')[:-1]
connections=''' .ck(ck),.rst_obs(rst),.boot_done(boot),.rp_program_ready(prog_ready),.t_running_q(running),.boot_fault(other),.prog_fault(1'b0),.cal_fault(1'b0),.emb_fault(1'b0),.prov_fault_q(1'b0),.rp_fault(1'b0),.head_tx_fault(1'b0),.head_mux_fault(1'b0),.armed_fault(1'b0),.go_fault(1'b0),.mu_hc_fault(1'b0)'''
tb='''module tb_observer; reg ck=0; always #5 ck=~ck;
reg rst=0,old_fault=0,old_ready=0,cland_up_fault=0,cland_up_ready=0,boot=0,prog_ready=0,running=0,other=0;
wire cf,cr,ca,rf,rr,ra;
observer_cut candidate('''+connections+f',.obs_fault({args["obs_fault"]}),.seq_cfg_image_ready({args["seq_cfg_image_ready"]}),.fault(cf),.ready_capture(cr),.admit_ready(ca));\n'+'''observer_cut reference('''+connections+''',.obs_fault(old_fault|cland_up_fault),.seq_cfg_image_ready(old_ready&cland_up_ready),.fault(rf),.ready_capture(rr),.admit_ready(ra));
integer i;initial begin
for(i=0;i<1024;i=i+1)begin
 @(negedge ck); rst=(i%41)>1; {old_fault,old_ready,cland_up_fault,cland_up_ready,boot,prog_ready,running,other}=i[7:0];
 @(posedge ck);#1;
 if({cf,cr,ca}!=={rf,rr,ra}) $fatal(1,"observer mismatch cycle %0d",i);
end
$display("OBSERVER_SOURCE_CUT_PASS 1024 cycles all fault/ready/admission frontier outputs");$finish;end
endmodule
'''
(out/'observer_cut.sv').write_text(cut+tb)
(out/'observer_ready_mutant.sv').write_text((cut+tb).replace(args['seq_cfg_image_ready'],args['seq_cfg_image_ready'].replace('&','|'),1))
(out/'observer_fault_mutant.sv').write_text((cut+tb).replace(args['obs_fault'],args['obs_fault'].replace('|','&'),1))
(out/'observer_source.json').write_text(json.dumps(dict(scope='Exact source input-capture/sticky-fault/admission cut; record-port programming is a frontier, not full-controller proof.',sources={str(p.relative_to(wt)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [wrap,core]},gated_instance=gated),indent=2)+'\n')

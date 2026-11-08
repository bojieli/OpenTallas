from pathlib import Path
import subprocess,re,json,hashlib
r=Path(__file__).resolve().parents[2]; out=Path(__file__).resolve().parent/'runtime';out.mkdir(exist_ok=True)
def read(path):return subprocess.check_output(['git','-C',str(r),'show','HEAD:'+path],text=True)
files=['rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv','rtl/hbm_accel/loader/service_native/ot_hbm_svc_ring_h9b.sv','rtl/hbm_accel/loader/service_native/ot_hbm_svc_pin_skid2_h9.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv']
names=['ot_hbm_svc_pc_ctrl_leaf_cfg_h9b','ot_hbm_svc_ring_h9b','ot_hbm_svc_pin_skid2_h9','ot_hbm_r14_stream_pc_strap_h9']
receipt={}
for side in ['off','on']:
 chunks=[]
 for f in files:
  s=read(f);receipt[f]=hashlib.sha256(s.encode()).hexdigest()
  for n in names:s=re.sub(r'\b'+n+r'\b',n+'_'+side,s)
  if side=='on' and 'stream_pc_strap' in f:s='`define OT_H9B_WQDIAG\n'+s+'\n`undef OT_H9B_WQDIAG\n'
  chunks.append(s)
 (out/(side+'.sv')).write_text('\n'.join(chunks))
common=['rtl/lib/ot_rst_relay.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
mut=(out/'on.sv').read_text(); assert mut.count("~(WQ'(1) << ai)")==1
(out/'on_mut.sv').write_text(mut.replace("~(WQ'(1) << ai)","~(WQ'(1) << ((ai+1)%WQ))"))
(out/'common.sv').write_text('\n'.join(read(f) for f in common))
s=read('rtl/hbm_accel/loader/service_native/tb_hbm_pc_h9b_txn.sv')
s=s.replace('RMUT=0, NREQ=6000','RMUT=0, NREQ=2000, RELOAD=150').replace('always #512','always #416.5')
s=s.replace('ot_hbm_svc_pc_ctrl_leaf_cfg_h9 a(', 'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b_off #(.TIMING_833(1)) a(')
s=s.replace('ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.RMUT(RMUT)) b(', 'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b_on #(.RMUT(RMUT),.TIMING_833(1)) b(')
s=s.replace("refresh_reload=8'd151","refresh_reload=8'(RELOAD)")
s=s.replace('if(pc_fault[d]||(|of[d])) begin errors=errors+1; if(errors<5) $display("H9B_TXN_FAULT dut%0d of=%b edge%0d",d,of[d],now); end','if(pc_fault[d]||(|of[d])) $fatal(1,"WQDIAG_BASELINE_FAULT dut%0d of=%b edge%0d",d,of[d],now);')
s=s.replace('(d==0 ? r_now : r_prev)','r_prev').replace('done_at[1]>done_at[0]+done_at[0]/20+64','done_at[1]!=done_at[0]')
outputs=['k_rdy','kr_v','kr_tag','kr_beat','kr_data','k_wr_done','row_v','row_op','row_bank','row_row','col_v','col_we','col_bank','col_col','col_data','col_strb','pc_fault','of']
check='\n  always @(posedge clk) begin #1; if(rst_n && now>24) begin\n'
for n in outputs:check+='    if('+n+'[0] !== '+n+'[1]) $fatal(1,"WQDIAG_EDGE '+n+' mismatch edge%0d",now);\n'
check+='    if(idx[0] != idx[1]) $fatal(1,"WQDIAG_ACCEPT mismatch");\n  end end\n'
phase='''\n  integer refresh_checks=0;\n  always @(negedge clk) begin #1; if(rst_n && now>24 && a.controller.on.ref_due) begin\n    refresh_checks=refresh_checks+1;\n    if(refresh_checks<5) $display("WQDIAG_REFRESH edge%0d reload%0d phase%0d slot%0d fire%b op%0d",now,RELOAD,a.controller.on.phase,a.controller.slot_parity,a.controller.on.row_fire,a.controller.on.c_op);\n    if(a.controller.on.phase != 2*a.controller.slot_parity || !a.controller.on.row_fire || a.controller.on.c_op!=a.controller.REFPB)\n      $fatal(1,"WQDIAG_REFRESH_PHASE illegal actual row calendar");\n  end end\n'''
s=s.replace('  integer nrd=0;',check+phase+'  integer nrd=0;')
s=s.replace('    for(d=0;d<2;d=d+1) begin idx[d]=0;', '    if(!$value$plusargs("SEED=%d",rng)) rng=32\'h1d872b41;\n    for(d=0;d<2;d=d+1) begin idx[d]=0;')
assert 'cfg_h9 a(' not in s
(out/'tb.sv').write_text(s)
(out/'source_receipt.json').write_text(json.dumps(receipt,indent=1))

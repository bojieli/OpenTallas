#!/usr/bin/env python3
"""Dedicated caller projection; preserves pinned originals and provider ownership."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'rtl/rom/wavefront/context/protected_20261006';out.mkdir(exist_ok=True)
 ctrl_path=ROOT/'rtl/rom/wavefront/context/enclosing_20261005/ot_rom_pkg_ctrl_wfc_enclosed.sv'
 src=ctrl_path.read_text();s=src
 names=['ot_rom_pkg_ctrl_wfc_enclosed','ot_rom_pkg_ctrl_wfc_upos','ot_rom_pkg_ctrl_wfc_src','ot_rom_pkg_ctrl_wfc_grp','ot_dsrom_wfc_position_inc']
 for name in sorted(names,key=len,reverse=True):s=s.replace(name,name+'_vm')
 s=re.sub(r'(input\s+wire\s+)clk\s*,',r'\1clk, advance,',s)
 s=s.replace('input  wire               clk, advance,','input  wire               clk, advance,\n    input wire memory_step,')
 # Every retained clocked state update obeys CE; asynchronous reset still works.
 def ce(m):
  reset=m.group(2);return m.group(0)+' if (advance'+(' || !'+reset if reset else '')+')'
 s=re.sub(r'always\s*@\(posedge clk(\s+or negedge (\w+))?\)',ce,s)
 s=s.replace('.clk(clk),','.clk(clk), .advance(advance),')
 anchor='    output wire core_done_accepted,'
 s=s.replace(anchor,'    output wire [USER_W-1:0] vm_owner_user,\n    output wire [NW-1:0] vm_owner_pos,\n    output wire vm_read_capture,\n'+anchor)
 idx=s.index('    wire side_ok =')
 s=s[:idx]+'''    // Actual RX header or retained TX owner, independent of whole ACK.
    assign vm_owner_user = vm_we ? ((rx_st==R_SIDE)?side_user:hdr_user) : (job_done?cur_user:tx_user);
    assign vm_owner_pos = vm_we ? hdr_pos : (job_done?cur_pos:tx_pos);
    assign vm_read_capture = advance && rd_inflight && !job_done && !q_hdr_r && !q_hdr_s;
'''+s[idx:]
 # In the read-capture bubble no new memory event or RX flit is accepted.
 # Read and write of distinct native RX/TX owners are serialized by RX ready.
 # XB same-bundle collision remains a provider old-data read-before-write event.
 needle='        rx_last_word = (rx_st == R_DATA) && vm_we && (rx_j == RXW - 1);'
 s=s.replace(needle,needle+'\n        if (vm_we && ((job_done && SEND_HIDDEN) || ((tx_st==T_DATA || tx_st==T_SDATA) && tx_space))) begin in_ready=0;vm_we=0;rx_last_word=0;end')
 needle='        // core start: at most one source per cycle; the core samples it on this edge'
 s=s.replace(needle,'''        if (!memory_step) begin
            in_ready=0;rx_hdr=0;rx_res=0;rx_side=0;vm_we=0;vm_re=0;rx_last_word=0;rx_side_last=0;
        end
'''+needle)
 cp=out/'ot_rom_pkg_ctrl_wfc_enclosed_vm.sv';cp.write_text(s)
 pp=ROOT/'rtl/rom/wavefront/context/enclosing_20261005/ot_dsrom_wfc_parent_enclosed.sv';s=pp.read_text()
 s=s.replace('ot_dsrom_wfc_parent_enclosed','ot_dsrom_wfc_parent_enclosed_vm').replace('ot_rom_pkg_ctrl_wfc_enclosed','ot_rom_pkg_ctrl_wfc_enclosed_vm')
 s=s.replace('    input  wire               clk,','    input  wire               clk,\n    input wire advance,memory_step,')
 s=s.replace(anchor,'    output wire [USER_W-1:0] vm_owner_user,\n    output wire [NW-1:0] vm_owner_pos,\n    output wire vm_read_capture,\n'+anchor)
 s=s.replace('pc_out_valid};','pc_out_valid && advance};').replace('assign pc_out_ready = r_in_ready[0];','assign pc_out_ready = r_in_ready[0] && advance;').replace('out_ready, pc_in_ready};','out_ready, pc_in_ready && advance};')
 # Router/reset keep root clocks; only controller and its internal helpers pause.
 s=s.replace('.wf_reject(wf_reject));', '.wf_reject(wf_reject),.wf_squash(wf_squash));')
 s=s.replace(') u_ctrl (\n        .clk(clk),',') u_ctrl (\n        .clk(clk),.advance(advance),.memory_step(memory_step),\n        .vm_owner_user(vm_owner_user),.vm_owner_pos(vm_owner_pos),.vm_read_capture(vm_read_capture),')
 newpp=out/'ot_dsrom_wfc_parent_enclosed_vm.sv';newpp.write_text(s)
 ep=ROOT/'rtl/rom/wavefront/context/ot_dsrom_wfc_enclosing_stage.sv';s=ep.read_text().replace('ot_dsrom_wfc_enclosing_stage','ot_dsrom_wfc_enclosing_vm_stage').replace('ot_dsrom_wfc_parent_enclosed #','ot_dsrom_wfc_parent_enclosed_vm #')
 s=s.replace(' input wire clk,rst_n,',' input wire clk,rst_n,advance,memory_step,\n output wire vm_we,vm_re,\n output wire [14:0]vm_waddr,vm_raddr,\n output wire [511:0]vm_wdata,\n input wire [511:0]vm_rq,\n output wire [9:0]vm_owner_user,\n output wire [20:0]vm_owner_pos,\n output wire vm_read_capture,')
 s=re.sub(r' input wire \[3:0\]xb_we4,.*?output wire \[511:0\]xb_rq,\n','',s,flags=re.S)
 s=s.replace('   wire vm_we,vm_re;wire [14:0]vm_waddr,vm_raddr;\n   wire [511:0]vm_wdata,vm_rq;\n','')
 s=re.sub(r'   ot_dsrom_wfc_vm_port u_vm\(.*?\);\n','',s,flags=re.S)
 s=s.replace('assign stage_request_v=offer&&c8_ready;','assign stage_request_v=offer&&c8_ready&&advance;')
 s=s.replace('.offer_v(offer&&stage_request_ready)', '.offer_v(offer&&stage_request_ready&&advance)')
 s=s.replace('assign whole_stage_accepted=accepted&&result_v&&health;','assign whole_stage_accepted=accepted&&result_v&&health&&advance;')
 s=s.replace('if(core_start)begin','if(core_start&&advance)begin')
 s=s.replace('     .clk(clk),.rst_n(rst_n),.cfg_users(cfg_users)', '     .clk(clk),.rst_n(rst_n),.advance(advance),.memory_step(memory_step),\n     .vm_owner_user(vm_owner_user),.vm_owner_pos(vm_owner_pos),.vm_read_capture(vm_read_capture),.cfg_users(cfg_users)')
 s=s.replace('whole_stage_accepted,xb_rq,context_v','whole_stage_accepted,context_v')
 s=s.replace(' end else begin:g_disabled',' end else begin:g_disabled\n   assign {vm_we,vm_re,vm_waddr,vm_raddr,vm_wdata,vm_owner_user,vm_owner_pos,vm_read_capture}=0;')
 ne=out/'ot_dsrom_wfc_enclosing_vm_stage.sv';ne.write_text(s)
 record={'schema':'opentallas.wfc.protected_caller.projection.v1','source':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ctrl_path,pp,ep]},'outputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [cp,newpp,ne]},'controller_posedge_CE_sites':len(re.findall(r'always\s*@\(posedge clk',src)),'changes':['clock-enable all controller/helper state with async reset preserved','router keeps fast root clock, actual controller/router handshake qualified by CE','read capture bubble prevents another memory/RX acceptance','serialize simultaneous native XA TXread/RXwrite using RX backpressure','export actual RX/TX memory owner and actual read capture','hold actual core start and whole ACK until caller advances'],'qualified':False}
 (out/'source_binding.json').write_text(json.dumps(record,indent=2)+'\n')
 print('Generated dedicated CE/controller projection; originals unchanged')
if __name__=='__main__':main()

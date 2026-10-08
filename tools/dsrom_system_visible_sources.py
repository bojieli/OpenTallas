#!/usr/bin/env python3
"""Add source-owned native completion to retained reduced system interfaces.

This does NOT replace its behavioral weight provider with a ROM field. The
system copy is an integration reference, not a selected-ROM token admission.
Originals are git-pinned and untouched; publication defaults off.
"""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='1bfb4b6e855b723c06f8885ee1de4de950158c5a'

def original(path):
 return subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT,text=True)

def prefetch(source):
 s=source.replace('module ot_chip_v41x_kv_prefetch #(', 'module ot_chip_v41x_kv_prefetch_visible #(\n    parameter integer PUBLICATION=0,\n    parameter integer MAX_PENDING=2048,')
 anchor='    input  wire [3:0]          m_rdy,'
 assert s.count(anchor)==1
 s=s.replace(anchor,anchor+'\n    input wire [3:0] m_wr_done,\n    input wire [4*6-1:0] m_wr_done_count,\n    output wire write_quiet,\n    output reg write_fault=0,write_quarantine=0,')
 # ACKs may occur on multiple PCs together. An OR-reduced wr_done cannot
 # decrement a transaction count. Actual backend completion count is supplied.
 anchor='    wire f_any = (f_h || f_t) && wq_empty;'
 assert s.count(anchor)==1
 s=s.replace(anchor,'    wire f_any = (f_h || f_t) && wq_empty && (!PUBLICATION || pending_empty);')
 s=s.replace('&& wq_empty && !c_v[0]', '&& wq_empty && (!PUBLICATION || pending_empty) && !c_v[0]')
 anchor='    // -- read service '
 idx=s.index(anchor)
 extra='''    localparam integer PCW=$clog2(MAX_PENDING+1);
    reg [PCW-1:0] pending[0:3];
    wire pending_empty=pending[0]==0 && pending[1]==0 && pending[2]==0 && pending[3]==0;
    assign write_quiet=wq_empty && !c_v[0] && (!PUBLICATION || (pending_empty && !write_fault && !write_quarantine));
    initial for(integer p=0;p<4;p=p+1)pending[p]=0;
    // Preserve pending ACK debt at warm reset; native journals retain identities.
    always @(posedge clk)begin
     if(!rst_n)begin
      if(PUBLICATION && (!pending_empty || !wq_empty || c_v[0]))write_quarantine<=1;
     end else if(PUBLICATION && !write_fault && !write_quarantine)begin
      for(integer p=0;p<4;p=p+1)begin:pub
       integer accepted,completed,next_count;
       accepted=m_v[p] && m_rdy[p] && m_we[p];
       completed=32'(m_wr_done_count[p*6+:6]);
       next_count=32'(pending[p])+accepted-completed;
       if(m_wr_done[p]!=(completed!=0) || completed>32'(pending[p]) || next_count>MAX_PENDING)begin
        write_fault<=1;write_quarantine<=1;
       end else pending[p]<=PCW'(next_count);
      end
     end
    end

'''
 s=s[:idx]+extra+s[idx:]
 return s

def system(source):
 s=source.replace('    parameter integer USERS = 2,','    parameter integer PUBLICATION=0,\n    parameter integer USERS = 2,',1)
 s=s.replace("assign c_done = PRIME ? (done && sh_st == 3'd0) : done;", "wire visible_done,root_active,root_retire,root_fault,root_quarantine;\n            wire [46:0] root_identity;\n            wire publication_quiet,publication_fault,publication_quarantine;\n            assign c_done = PRIME ? ((PUBLICATION ? visible_done : done) && sh_st == 3'd0) : (PUBLICATION ? visible_done : done);\n            if(PUBLICATION)begin:g_root_visible\n             ot_dsrom_root_visible #(.NW(NW),.UW(8)) root(\n              .clk(clk),.rst_n(rst_n),.start(core_start),.pos(core_pos),.user(cur_u),.engine_done(done),\n              .owners_quiet(publication_quiet),.owner_fault(publication_fault),.owner_quarantine(publication_quarantine),\n              .root_identity(root_identity),.active(root_active),.done(visible_done),.retire_v(root_retire),.fault(root_fault),.quarantine(root_quarantine));\n             always @(posedge clk)begin\n              if(root_fault||root_quarantine)$fatal(1,\"SYS_ROOT_OWNER_FAULT node=%0d identity=%h\",n,root_identity);\n              if(root_retire)$display(\"SYS_ROOT_VISIBLE node=%0d cycle=%0d identity=%h\",n,cyc,root_identity);\n             end\n            end else begin:g_root_legacy\n             assign root_identity=0;assign root_active=0;assign visible_done=done;assign root_retire=0;assign root_fault=0;assign root_quarantine=0;\n            end")
 s=s.replace('wire bridge_busy;', 'wire bridge_busy;\n                wire [3:0] journal_quiet,journal_fault,journal_quarantine,kv_wr_done;\n                wire [23:0] kv_wr_done_count;\n                wire kv_write_quiet,kv_write_fault,kv_write_quarantine;\n                assign publication_quiet=(&journal_quiet) && kv_write_quiet && !bridge_busy && !pikw_v;\n                assign publication_fault=(|journal_fault)||kv_write_fault;\n                assign publication_quarantine=(|journal_quarantine)||kv_write_quarantine;')
 s=s.replace('ot_chip_v41x_kv_prefetch #(', 'ot_chip_v41x_kv_prefetch_visible #(.PUBLICATION(PUBLICATION),')
 s=s.replace('.m_v(km_v), .m_rdy(km_rdy), .m_addr(km_addr),', '.m_v(km_v), .m_rdy(km_rdy), .m_wr_done(kv_wr_done),.m_wr_done_count(kv_wr_done_count),\n                        .write_quiet(kv_write_quiet),.write_fault(kv_write_fault),.write_quarantine(kv_write_quarantine),.m_addr(km_addr),')
 s=s.replace('assign kv_ok = 1\'b1;', "assign kv_write_quiet=1;assign kv_write_fault=0;assign kv_write_quarantine=0;\n                    assign kv_ok = 1'b1;",1)
 s=s.replace('.k_wstrb(km_wstrb[s*32 +: 32]), .k_wr_done(),', '.k_wstrb(km_wstrb[s*32 +: 32]), .k_wr_done(kv_wr_done[s]),')
 s=s.replace('ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(28), .DW(256),\n                            .MEM_WORDS(KV_SBASE + KV_SECTORS)', 'ot_hdc_v41x_idx_hbm_c8 #(.NPC(32), .AW(28), .DW(256),\n                            .MEM_WORDS(KV_SBASE + KV_SECTORS)')
 s=s.replace('.wr_done(sh_wr_done), .rsp_v(sr_v)', '.wr_done(sh_wr_done), .wr_done_addr(native_done_addr),.wr_done_tag(native_done_tag),.rsp_v(sr_v)')
 anchor='                        reg [63:0] refresh_count;'
 idx=s.index(anchor)
 extra='''                        wire [32*28-1:0] native_done_addr;
                        wire [32*17-1:0] native_done_tag;
                        wire [31:0] kv_native_done;
                        wire [63:0] native_kind;
                        for(genvar p=0;p<32;p=p+1)begin:g_native_kind
                         assign kv_native_done[p]=sh_wr_done[p] && native_done_tag[p*17+16];
                         assign native_kind[p*2+:2]=sh_tag[p*17+16]?2'b10:2'b00;
                        end
                        assign kv_wr_done_count[s*6+:6]=6'($countones(kv_native_done));
                        if(PUBLICATION)begin:g_native_journal
                         wire [31:0] v;wire [32*47-1:0] id;wire [32*28-1:0] addr;wire [63:0] kind;
                         ot_dsrom_c8_write_journal #(.NPC(32),.DEPTH(64),.AW(28),.IDW(47),.TAGW(17)) journal(
                          .clk(clk),.rst_n(rst_n),.accepted_write(sh_v & sh_rdy & sh_we),.backend_wr_done(sh_wr_done),
                          .accepted_addr(sh_addr),.accepted_tag(sh_tag),.backend_done_addr(native_done_addr),.backend_done_tag(native_done_tag),
                          .accepted_writer(native_kind),.accepted_identity(root_identity),.visible_v(v),.visible_identity(id),.visible_addr(addr),.visible_writer(kind),
                          .quiet(journal_quiet[s]),.debt(),.fault(journal_fault[s]),.quarantine(journal_quarantine[s]));
                         always @(posedge clk)if(rst_n)begin
                          if((|(sh_v & sh_rdy & sh_we)) && !root_active)$fatal(1,"SYS_WRITE_WITHOUT_ROOT node=%0d",n);
                          for(integer p=0;p<32;p=p+1)if(v[p])begin
                           if(id[p*47+:47]!==root_identity)$fatal(1,"SYS_STALE_WRITE_IDENTITY node=%0d",n);
                           $display("SYS_WRITE_VISIBLE node=%0d cycle=%0d stack=%0d pc=%0d identity=%h addr=%h writer=%0d",n,cyc,s,p,id[p*47+:47],addr[p*28+:28],kind[p*2+:2]);
                          end
                         end
                        end else begin:g_native_journal_off
                         assign journal_quiet[s]=1;assign journal_fault[s]=0;assign journal_quarantine[s]=0;
                        end
'''
 s=s[:idx]+extra+s[idx:]
 return s

def generate():
 m=json.loads((ROOT/'results/uarch/dsrom_system_visible_integration_20261003/model.json').read_text())
 assert m['admission']['implementation_component']
 dest=ROOT/'rtl/dsrom_sys/visible/ot_chip_v41x_kv_prefetch_visible.sv';dest.write_text(prefetch(original('rtl/chip/ot_chip_v41x_kv_prefetch.sv')))
 dest=ROOT/'rtl/test/dsrom_sys/visible/tb_dsrom_system.sv';dest.write_text(system(original('rtl/test/dsrom_sys/tb_dsrom_system.sv')))

if __name__=='__main__':generate()

`timescale 1ns/1ps
// Explicit optional per-slice AR phase. No payload reset and no transaction queue.
module qfd_dv_ar_go_phase805 #(
 parameter integer ENABLE=0, MUT=0,
 parameter [191:0] HGD_TABLE={16'd57,16'd52,16'd47,16'd42,16'd37,16'd32,16'd27,16'd22,16'd17,16'd12,16'd7,16'd2}
)(input wire ck,rst_n,input wire[3:0]sid,input wire[452:0]hr_i,
 output wire[452:0]hr_o,output wire fault);
 generate if(!ENABLE)begin:g_off
  assign hr_o=hr_i;assign fault=1'b0;
 end else begin:g_on
  wire[378:0]ib=hr_i[451:73];
  wire raw_go=hr_i[0]&&hr_i[452];
  wire ar_role=ib[378:361]==4096 && ib[360:343]==3 &&
   (ib[342:325]==2 || ib[342:325]==6) && !ib[324] &&
   ib[128:125]==8 && !ib[27] && ib[26] && !ib[25];
  wire[11:0]sid_onehot;
  wire[15:0]phase;
  for(genvar s=0;s<12;s++)begin:g_sid
   assign sid_onehot[s]=(sid==s);
  end
  for(genvar b=0;b<16;b++)begin:g_phasebit
   wire[11:0]terms;
   for(genvar s=0;s<12;s++)begin:g_term
    assign terms[s]=sid_onehot[s]&&HGD_TABLE[16*s+b];
   end
   assign phase[b]=|terms;
  end
  reg[378:0]ib_pipe,ib_hold;
  (* keep="true" *)reg[11:0]cap;
  (* keep="true" *)reg[11:0]sel;
  reg[15:0]left;
  reg pending,emit,sticky;
  reg[3:0]txn_sid;
  wire busy=pending||emit;
  wire sid_bad=busy&&(sid!=txn_sid || sid>=12);
  wire accept=raw_go&&ar_role&&!busy&&sid<12&&phase>=2;
  wire emit_next=pending&&!sid_bad&&(left==((MUT==2)?16'd2:16'd1));
  wire emit_safe=emit&&!sid_bad;
  always @(posedge ck)ib_pipe<=ib;
  for(genvar g=0;g<12;g++)begin:g_chunk
   localparam integer L=32*g,W=(379-L<32)?379-L:32;
   always @(posedge ck)if(cap[g])ib_hold[L+:W]<=ib_pipe[L+:W];
   assign hr_o[73+L+:W]=sel[g]&&emit_safe ? ((MUT==1)?ib_pipe[L+:W]:ib_hold[L+:W]):ib[L+:W];
  end
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin cap<=0;sel<=0;left<=0;pending<=0;emit<=0;sticky<=0;txn_sid<=0;end
   else begin
    cap<={12{accept}};sel<={12{emit_next}};emit<=emit_next;
    if(raw_go&&(busy||sid>=12||(ar_role&&phase<2)))sticky<=1;
    if(sid_bad)begin sticky<=1;pending<=0;left<=0;emit<=0;sel<=0;end
    else if(accept)begin txn_sid<=sid;pending<=1;left<=phase-1'b1;end
    else if(pending)begin
     if(emit_next)begin pending<=0;left<=0;end
     else left<=left-1'b1;
    end
   end
  end
  // Outer valid is needed by the real tap GO decoder. Qualify descriptor valid
  // by its ORIGINAL outer valid, so an idle stale XPF is not replayed on emit.
  assign hr_o[0]=hr_i[0]||emit_safe;
  assign hr_o[1]=(MUT==3)?hr_i[1]:(hr_i[0]&&hr_i[1]);
  assign hr_o[72:2]=hr_i[72:2];
  assign hr_o[452]=emit_safe||(raw_go&&!ar_role&&!busy&&sid<12);
  assign fault=sticky;
 end endgenerate
endmodule

// Same ports as the selected tap. Existing master remains byte-identical.
module qfd_dv_s8_tap_phase805 #(
 parameter integer ENABLE=0,MUT=0,
 parameter [191:0] HGD_TABLE={16'd57,16'd52,16'd47,16'd42,16'd37,16'd32,16'd27,16'd22,16'd17,16'd12,16'd7,16'd2}
)(input wire ck,rst_n,input wire[3:0]sid,input wire[452:0]hr_q,
 input wire[5:0]xt_vcopies,input wire[23:0]xt_a,input wire[1023:0]xt_d,
 input wire xt_bad,input wire[31:0]lq_bad,output wire[1566:0]hw,
 output wire[23:0]cid,output wire tap_fault);
 wire[452:0]ph;wire pf,tf;
 qfd_dv_ar_go_phase805 #(.ENABLE(ENABLE),.MUT(MUT),.HGD_TABLE(HGD_TABLE)) u_phase(ck,rst_n,sid,hr_q,ph,pf);
 qfd_dv_s8_tap_bounded u_tap(.ck(ck),.rst_n(rst_n),.sid(sid),.hr_q(ph),.xt_vcopies(xt_vcopies),.xt_a(xt_a),.xt_d(xt_d),.xt_bad(xt_bad),.lq_bad(lq_bad),.hw(hw),.cid(cid),.tap_fault(tf));
 assign tap_fault=pf|tf;
endmodule

`timescale 1ns/1ps
// default-off (enabled=0) new modules vs stock modules with enabled=0 and random host traffic: outputs must be identical.
module tb_off;
    logic ck=0; always #5 ck=~ck; logic rst_n=0;
    logic open,pc,slot,cap,hv,ev,aw,mc; logic [60:0] pid,aid; logic [28:0] ad; logic [3:0] sk; logic [4:0] sb; logic [1:0] su; logic [547:0] hr,rr;
    wire nv,sv,nc,sc,nf,sf,nh,sh; wire [547:0] nr,sr;
    qkd_pc11_b1_kind11_tx n(.ck,.rst_n,.enabled(1'b0),.authorized(1'b1),.mctx(mc),.parent_open(open),.parent_identity(pid),.parent_address(ad),.parent_user(su),
      .pcc_commit(pc),.pcc_identity(pid),.pcc_address(ad),.port1_slot(slot),.slot_kind(sk),.slot_beat(sb),.slot_user(su),.port1_capture(cap),.host_valid(hv),.host_record(hr),
      .tx_valid(nv),.tx_record(nr),.commit_capture(nc),.fault(nf));
    qkd_pc11_commit_record_tx s(.ck,.rst_n,.enabled(1'b0),.authorized(1'b1),.parent_open(open),.parent_identity(pid),.parent_user(su),
      .pcc_commit(pc),.pcc_identity(pid),.port1_slot(slot),.slot_kind(sk),.slot_beat(sb),.slot_user(su),.port1_capture(cap),.host_valid(hv),.host_record(hr),
      .tx_valid(sv),.tx_record(sr),.commit_capture(sc),.fault(sf));
    wire nrdy,nf2; wire [60:0] nid; wire [28:0] nadr; wire rc; wire [60:0] ri; wire rfault;
    qfd_pc11_b1_kind11_rx nrx(.ck,.rst_n,.enabled(1'b0),.authorized(1'b1),.mctx(mc),.awaited_parent_v(aw),.awaited_identity(aid),.awaited_address(ad),.awaited_user(su),
      .port1_slot(slot),.port1_event(ev),.any_event(ev),.any_event_kind(sk),.slot_kind(sk),.slot_beat(sb),.slot_user(su),.rx_record(rr),
      .host_event(nh),.b1_ready(nrdy),.b1_identity(nid),.b1_address(nadr),.fault(nf2));
    qfd_pc11_commit_record_rx srx(.ck,.rst_n,.enabled(1'b0),.authorized(1'b1),.awaited_parent_v(aw),.awaited_identity(aid),.awaited_user(su),
      .port1_slot(slot),.port1_event(ev),.slot_kind(sk),.slot_beat(sb),.slot_user(su),.rx_record(rr),.host_event(sh),.remote_commit(rc),.remote_identity(ri),.fault(rfault));
    int bad=0, n_=0;
    initial begin
        repeat(3) @(negedge ck); rst_n=1;
        repeat(20000) begin
            @(negedge ck);
            {open,pc,slot,cap,hv,ev,aw,mc}=$urandom; sk=($urandom%2)?4'd11:$urandom; sb=$urandom; su=$urandom;
            pid=$urandom; pid[44:39]=1+$urandom%36; aid=pid; ad=$urandom; hr={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}; rr=hr;
            #1;
            if (nv!==sv || nr!==sr || nc!==sc || nf!==sf || nh!==sh || nrdy!==rc || nf2!==rfault) bad++;
            n_++;
        end
        $display("K11_OFF cycles=%0d mismatches=%0d",n_,bad);
        if (bad) $fatal(1,"default-off differs from stock"); 
        $finish;
    end
endmodule

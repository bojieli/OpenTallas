`timescale 1ns/1ps
// HBM-CORES-B 11-12: lock-step bench for ot_hbm_sm_pv_merge RDREG (macro-output register).
// Reference RDREG 0 and DUT RDREG 1 get the same random legal request stream (PV runs of 1..8 chunks on every
// slot at its barrel turn, publications incl. word14 prefetch, folds).  Contract (EQ_CYCLE_SHIFTED):
//   pv_v / pv_y / pv_tag and fault          cycle-identical;
//   pub_v / pub_data / pub_word / slot / tag DUT = reference delayed by exactly one edge.
// The stream keeps each folded entry pending until the DUT write (one edge after the reference write).
// MODE 1 drives full-range finite sum bits (denormals, overflow to Inf in the adders): outputs are compared while the
// reference has no fault, and the DUT fault must equal the reference fault or the reference fault one edge earlier (a fold add
// that faults issues one edge later).  RDMUT 1/2/3 are negative controls and must fail.
module tb_hbm_sm_pv_rdreg;
    parameter integer RDMUT=0, MODE=0, DREG=1, TREG=0, TRMUT=0;   // DUT RDREG / TREG / TRMUT (TREG form, 11-12)
    integer CYCLES=200000, seed=1;
    reg clk=0,rst_n=0,ev=0,pub_start=0,fold_start=0;
    reg [511:0] sum=0;
    reg [15:0] tag_d=0;
    reg [2:0] pub_slot=0,fold_a=0,fold_b=0;
    wire r_pv_v,r_pub_v,r_fault,d_pv_v,d_pub_v,d_fault;
    wire [511:0] r_pv_y,d_pv_y;
    wire [15:0] r_pv_tag,d_pv_tag,r_pub_tag,d_pub_tag;
    wire [31:0] r_pub_data,d_pub_data;
    wire [3:0] r_pub_word,d_pub_word;
    wire [2:0] r_pub_out_slot,d_pub_out_slot;
    always #0.5 clk=~clk;
    ot_hbm_sm_pv_merge #(.PUBLISH(1),.RDREG(0)) u_ref(.clk,.rst_n,.ev,.sum,.tag_d,.pv_v(r_pv_v),.pv_y(r_pv_y),
        .pv_tag(r_pv_tag),.fault(r_fault),.pub_start,.pub_slot,.pub_v(r_pub_v),.pub_data(r_pub_data),.pub_word(r_pub_word),
        .pub_out_slot(r_pub_out_slot),.pub_tag(r_pub_tag),.fold_start,.fold_a,.fold_b);
    ot_hbm_sm_pv_merge #(.PUBLISH(1),.RDREG(DREG),.RDMUT(RDMUT),.TREG(TREG),.TRMUT(TRMUT)) u_dut(.clk,.rst_n,.ev,.sum,.tag_d,.pv_v(d_pv_v),.pv_y(d_pv_y),
        .pv_tag(d_pv_tag),.fault(d_fault),.pub_start,.pub_slot,.pub_v(d_pub_v),.pub_data(d_pub_data),.pub_word(d_pub_word),
        .pub_out_slot(d_pub_out_slot),.pub_tag(d_pub_tag),.fold_start,.fold_a,.fold_b);
    // reference publication stream delayed one edge
    reg q_v=0,q_fault=0; reg [31:0] q_data; reg [3:0] q_word; reg [2:0] q_slot; reg [15:0] q_tag;
    always @(posedge clk)begin q_v<=r_pub_v;q_data<=r_pub_data;q_word<=r_pub_word;q_slot<=r_pub_out_slot;q_tag<=r_pub_tag;q_fault<=r_fault;end
    // expected DUT publication stream: reference delayed one edge when the DUT has RDREG 1, undelayed for DREG 0
    wire e_v=DREG ? q_v : r_pub_v, e_fault=DREG ? q_fault : r_fault; wire [31:0] e_data=DREG ? q_data : r_pub_data;
    wire [3:0] e_word=DREG ? q_word : r_pub_word; wire [2:0] e_slot=DREG ? q_slot : r_pub_out_slot; wire [15:0] e_tag=DREG ? q_tag : r_pub_tag;
    integer cyc=0,nodes=0,words=0,folds=0,pubs=0,evs=0,mism=0,first_mism=-1,reqc=-1,lat_bad=0;
    task automatic bad(input [255:0] what);
        begin mism=mism+1; if(first_mism<0)begin first_mism=cyc;$display("MISMATCH %0s cycle=%0d",what,cyc);end end
    endtask
    always @(posedge clk)begin
        cyc=cyc+1;
        if(pub_start && reqc<0)reqc=cyc;
        #0.01;
        if(rst_n)begin
            if(MODE==0 && r_fault)begin $display("BENCH_ILLEGAL reference fault cycle=%0d",cyc);$fatal(1,"illegal stream");end
            if(!r_fault)begin
                if(d_pv_v!==r_pv_v)bad("pv_v");
                else if(r_pv_v && (d_pv_y!==r_pv_y || d_pv_tag!==r_pv_tag))bad("pv_y/tag");
                if(r_pv_v)nodes=nodes+1;
            end
            if(!e_fault)begin
                if(d_pub_v!==e_v)bad("pub_v");
                else if(e_v && (d_pub_data!==e_data || d_pub_word!==e_word || d_pub_out_slot!==e_slot || d_pub_tag!==e_tag))bad("pub data");
                if(d_pub_v)words=words+1;
                if(d_pub_v && words==1 && cyc-reqc!=2+DREG)lat_bad=lat_bad+1;
            end
            if(MODE==0 ? (d_fault!==r_fault) : !(d_fault===r_fault || d_fault===q_fault))bad("fault");
        end
    end
    // ---------------- legal random stream ----------------
    integer len[0:7], n[0:7];
    integer s,i,gap=0,phase=0,plen=0,busy_runs;
    function automatic [31:0] fpw(input integer m);
        reg [31:0] x;
        begin x=$urandom;
            if(m==1) fpw=(x[30:23]==8'hff) ? {x[31],8'hfe,x[22:0]} : x;   // full finite range: denormals, huge exponents
            else if(x[3:0]==0) fpw=32'd0;
            else fpw={x[31],8'd110+{3'd0,x[8:4]},$urandom()%(1<<23)};
        end
    endfunction
    reg pub_ok,fold_ok,ev_ok;
    reg [2:0] a,b;
    initial begin
        if($value$plusargs("seed=%d",seed))begin end
        if($value$plusargs("cycles=%d",CYCLES))begin end
        i=$urandom(seed);
        for(s=0;s<8;s=s+1)begin n[s]=0;len[s]=1+$urandom%8;end
        repeat(3)@(negedge clk);rst_n=1;
        while(cyc<CYCLES)begin
            @(negedge clk);
            ev=0;pub_start=0;fold_start=0;
            if(gap>0)gap=gap-1;
            s=u_ref.bp;
            // phases: 0 = PV runs; 1 = drain (finish open runs only); 2 = publications and folds
            busy_runs=0; for(i=0;i<8;i=i+1)if(n[i]!=0)busy_runs=busy_runs+1;
            if(plen>0)plen=plen-1;
            if(phase==0 && plen==0)phase=1;
            else if(phase==1 && busy_runs==0 && u_ref.e_busy==0)begin phase=2;plen=50+$urandom%400;end
            else if(phase==2 && plen==0)begin phase=0;plen=20+$urandom%600;end
            ev_ok=(phase==0 || (phase==1 && n[s]!=0)) &&!u_ref.e_busy[s] && !u_ref.pub_d0 && !u_ref.pub_d1 && !u_ref.pub_active &&
                  (u_ref.node_pending==0) && (u_dut.node_pending==0) && !u_ref.fd0 && !u_ref.fd1 && !u_dut.fd2 && gap==0;
            if(ev_ok && ($urandom%100)<55)begin
                ev=1;tag_d={1'b1,(n[s]==0),(n[s]+1==len[s]),10'($urandom),3'(s)};
                for(i=0;i<16;i=i+1)sum[32*i+:32]=fpw(MODE);
                evs=evs+1;
                if(n[s]+1==len[s])begin n[s]=0;len[s]=1+$urandom%8;end else n[s]=n[s]+1;
            end else if(phase==2)begin
                pub_slot=$urandom;
                pub_ok=(u_ref.e_busy==0) && u_ref.node_valid[pub_slot] && !u_ref.pub_d0 && !u_ref.pub_d1 &&
                       (!u_ref.pub_active || u_ref.word_next==14) && !u_dut.node_pending[pub_slot] && !u_ref.node_pending[pub_slot] &&
                       !u_ref.fd0 && !u_ref.fd1 && !u_dut.fd2 && !(u_ref.e_busy[s]) && gap==0;
                // no run may be mid-way: a pending chunk run on any slot keeps publications off
                for(i=0;i<8;i=i+1)if(n[i]!=0)pub_ok=0;
                a=$urandom;b=$urandom;
                fold_ok=(u_ref.e_busy==0) && u_ref.node_valid[a] && u_ref.node_valid[b] && a!=b &&
                        !u_ref.node_pending[a] && !u_ref.node_pending[b] && !u_dut.node_pending[a] && !u_dut.node_pending[b] &&
                        !u_ref.pub_d0 && !u_ref.pub_d1 && !u_ref.pub_active && !u_ref.fd0 && gap==0;
                for(i=0;i<8;i=i+1)if(n[i]!=0)fold_ok=0;
                if(pub_ok && ($urandom%100)<30)begin pub_start=1;pubs=pubs+1;end
                else if(fold_ok && ($urandom%100)<30)begin fold_start=1;fold_a=a;fold_b=b;folds=folds+1;end
            end
        end
        @(negedge clk);ev=0;pub_start=0;fold_start=0;
        repeat(40)@(negedge clk);
        $display("RDREG_LOCKSTEP DREG=%0d TREG=%0d TRMUT=%0d RDMUT=%0d MODE=%0d seed=%0d cycles=%0d evs=%0d nodes=%0d pubs=%0d words=%0d folds=%0d first_lat_bad=%0d mismatches=%0d first=%0d ref_fault=%0d dut_fault=%0d",
                 DREG,TREG,TRMUT,RDMUT,MODE,seed,cyc,evs,nodes,pubs,words,folds,lat_bad,mism,first_mism,r_fault,d_fault);
        if(mism==0 && lat_bad==0 && (MODE==1 || (nodes>0 && words>0 && folds>0)))$display("RDREG_LOCKSTEP PASS");
        else $display("RDREG_LOCKSTEP FAIL");
        $finish;
    end
endmodule

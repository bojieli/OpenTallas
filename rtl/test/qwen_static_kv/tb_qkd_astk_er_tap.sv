`timescale 1ns/1ps
// KVJ-D 2026-10-17 / ECTLA-2 2026-10-17: the pin-registered inline e-read leaf qkd_astk_er_tap against
// qkd_astk_native_er_service_w on the FULL SO/SI bus, lockstep every edge with the tap's pin flops accounted for:
// the service is fed read_v/read_addr delayed 2 edges (tap read pin flop + aso pin flop), so the strip's so must be
// identical every cycle ({engine so[424:13], tap aso} == service so); the service's response is delayed 2 more edges
// (tap esi pin flop + response pin flop) and must equal the tap's response every cycle, i.e. TAP_RL = 3 + 4 = 7.
// Fault law: an owner collision must raise the tap's fault exactly 2 edges after the colliding pin value, then (after
// a reset) a legacy ECTL read likewise.  MUT 1: the tap reads e_rdq one bit low.  MUT 2: response compared 1 edge early.
module tb_qkd_astk_er_tap;
    parameter integer MUT=0, N=4;
    reg ck=0,rst_n=0; always #0.5 ck=~ck;
    reg [N-1:0] rv; reg [11*N-1:0] ra; reg [425*8-1:0] eso; reg [634*8-1:0] asi;
    reg [N-1:0] rv1,rv2; reg [11*N-1:0] ra1,ra2;                 // request delay (2 tap pin edges)
    wire [425*8-1:0] so_ref; wire [634*8-1:0] esi_ref; wire [N-1:0] v_ref,v_tap; wire [11*N-1:0] a_ref,a_tap;
    wire [64*N-1:0] d_ref,d_tap; wire f_ref,f_tap; wire [13*8-1:0] aso;
    reg [N-1:0] v1,v2; reg [11*N-1:0] a1,a2; reg [64*N-1:0] d1,d2; // response delay (2 tap pin edges)
    wire [64*8-1:0] tsi; wire [7:0] tv;
    genvar g;
    generate for(g=0;g<8;g=g+1)begin:gb
        assign tsi[64*g+:64]=asi[634*g+569-(MUT==1?1:0)+:64]; assign tv[g]=eso[425*g];
    end endgenerate
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin rv1<=0;rv2<=0;ra1<=0;ra2<=0;v1<=0;v2<=0;a1<=0;a2<=0;d1<=0;d2<=0; end
        else begin rv1<=rv;rv2<=rv1;ra1<=ra;ra2<=ra1;v1<=v_ref;v2<=v1;a1<=a_ref;a2<=a1;d1<=d_ref;d2<=d1; end
    wire [N-1:0] vx=(MUT==2)?v1:v2; wire [11*N-1:0] ax=(MUT==2)?a1:a2; wire [64*N-1:0] dx=(MUT==2)?d1:d2;
    qkd_astk_native_er_service_w #(.N(N)) ref_(.ck(ck),.rst_n(rst_n),.read_v(rv2),.read_addr(ra2),.engine_so(eso),.astk_so(so_ref),
        .astk_si(asi),.engine_si(esi_ref),.response_v(v_ref),.response_addr(a_ref),.response_data(d_ref),.fault(f_ref));
    qkd_astk_er_tap #(.N(N)) dut(.ck(ck),.rst_n(rst_n),.read_v(rv),.read_addr(ra),.eso_v_lo(tv[3:0]),.eso_v_hi(tv[7:4]),.aso_lo(aso[0+:52]),.aso_hi(aso[52+:52]),.esi_lo(tsi[0+:256]),.esi_hi(tsi[256+:256]),
        .response_v(v_tap),.response_addr(a_tap),.response_data(d_tap),.fault(f_tap));
    reg [425*8-1:0] so_tap; integer e,j,cyc,reads=0,used,resp=0;
    always @* begin so_tap=eso; for(e=0;e<8;e=e+1) so_tap[425*e+:13]=aso[13*e+:13]; end
    function automatic [425*8-1:0] rnd_so(); integer k; begin for(k=0;k<107;k=k+1) rnd_so[32*k+:32]=$urandom; for(k=0;k<8;k=k+1) rnd_so[425*k]=1'b0; end endfunction
    function automatic [634*8-1:0] rnd_si(); integer k; begin for(k=0;k<159;k=k+1) rnd_si[32*k+:32]=$urandom; end endfunction
    initial begin
        rv=0;ra=0;eso=0;asi=0;
        repeat(3)@(negedge ck);rst_n=1;
        for(cyc=0;cyc<20000;cyc=cyc+1)begin
            @(negedge ck);
            if(cyc==19100)rst_n=0; else rst_n=1;
            eso=rnd_so();asi=rnd_si();rv=0;ra=0;used=0;
            if(cyc==19000)begin rv[0]=1;rv[1]=1;ra[0+:11]=11'h018;ra[11+:11]=11'h01f; end      // owner collision
            else if(cyc==19500)eso[425*3]=1'b1;                                                 // legacy ECTL read
            else if(cyc<19000 || (cyc>19110 && cyc<19490)) for(j=0;j<N;j=j+1)begin
                e=$urandom%8;
                if(($urandom%4)!=0 && !used[e])begin used=used|(1<<e);rv[j]=1;ra[11*j+:11]={5'($urandom),3'(e),3'($urandom)};reads=reads+1;end
            end
            #0.1;
            if(rst_n)begin
                if(so_tap!==so_ref)$fatal(1,"so differs cyc%0d",cyc);
                if(esi_ref!==asi)$fatal(1,"si pass-through differs");
                if(v_tap!==vx)$fatal(1,"response_v differs cyc%0d",cyc);
                // full-word compare until the mid-run reset; after it the un-reset data pipes differ only on idle ports
                for(j=0;j<N;j=j+1) if((cyc<19100 || v_tap[j]) && (a_tap[11*j+:11]!==ax[11*j+:11] || d_tap[64*j+:64]!==dx[64*j+:64]))
                    $fatal(1,"response differs cyc%0d port%0d",cyc,j);
                resp=resp+$countones(v_tap);
                if(cyc<19002 && f_tap)$fatal(1,"legal stimulus faulted cyc%0d",cyc);
                if(cyc==19002 && !f_tap)$fatal(1,"collision fault not raised at +2");
                if(cyc>19100 && cyc<19502 && f_tap)$fatal(1,"fault after reset cyc%0d",cyc);
                if(cyc==19502 && !f_tap)$fatal(1,"legacy-read fault not raised at +2");
                if(cyc==19503 && !f_ref)$fatal(1,"service fault law not exercised");
            end
        end
        $display("ER_TAP PASS lockstep cycles=%0d reads=%0d responses=%0d TAP_RL=7 N=%0d MUT=%0d",cyc,reads,resp,N,MUT);$finish;
    end
endmodule

// DIE-HBM-62 lockstep bench: ot_hbm_argmax_static_sw_vm_r2 against its pre-fix copy (git show <base>:... with _old module
// suffixes on r2, ot_hgi_argmax18_m, ot_hgi_argmax18_value_m). Compares busy, done, fault, nan, seq, cq valid, cq when valid
// and vm_rq when valid. iverilog -g2012 -DRDLAT=11 -DWRLAT=11 -DSEED=n -DRUNS=n
`timescale 1ns/1ps
module tb;
  reg clk=0, rst_n=0; always #1 clk=~clk;
  reg [7:0] die_id=8'd3; reg go=0, mode=0, a_mirror=0; reg [17:0] imm_a=0,a_base=0,n=0,o_base=0; reg [15:0] o_is=0;
  reg [263:0] vm_rr=0; reg [273:0] cr=0;
  wire [135:0] rq_o,rq_n; wire [337:0] cq_o,cq_n; wire [1:0] seq_o,seq_n; wire busy_o,busy_n,done_o,done_n,f_o,f_n,nan_o,nan_n;
  ot_hbm_argmax_static_sw_vm_r2_old u_o(.clk(clk),.rst_n(rst_n),.die_id(die_id),.go(go),.mode(mode),.imm_a(imm_a),.a_mirror(a_mirror),.a_base(a_base),.n(n),.o_base(o_base),.o_is(o_is),.vm_rq(rq_o),.vm_rr(vm_rr),.cq(cq_o),.cq_seq(seq_o),.cr(cr),.busy(busy_o),.done(done_o),.fault(f_o),.nan_flag(nan_o));
  ot_hbm_argmax_static_sw_vm_r2 u_n(.clk(clk),.rst_n(rst_n),.die_id(die_id),.go(go),.mode(mode),.imm_a(imm_a),.a_mirror(a_mirror),.a_base(a_base),.n(n),.o_base(o_base),.o_is(o_is),.vm_rq(rq_n),.vm_rr(vm_rr),.cq(cq_n),.cq_seq(seq_n),.cr(cr),.busy(busy_n),.done(done_n),.fault(f_n),.nan_flag(nan_n));
  // reactive memory model: a read answers VMX+N cycles later with random data, a write acks ACK cycles later
  localparam RDL=`RDLAT, WRL=`WRLAT;
  reg [7:0] rdp [0:64]; reg [17:0] wtag [0:64]; integer i;
  integer ndone=0,nfault=0,nnan=0,ncq=0,nerr=0,seed=`SEED,run=0,cyc=0;
  reg [7:0] rqv; reg [255:0] dat; reg started=0;
  function automatic [31:0] fp(input integer s);
    integer r; begin
      r=$random(s);
      case (r&7) 0: fp=32'h7FC00000; 1: fp=32'h00000000; 2: fp=32'h80000000; 3: fp=32'h3F800000;
        default: fp={r[31],8'd120+8'(r[10:8]),r[22:0]}; endcase
    end
  endfunction
  initial begin
    for(i=0;i<=64;i=i+1) begin rdp[i]=0; wtag[i]=0; end
    repeat(8) @(negedge clk); rst_n=1; repeat(6) @(negedge clk);
    while (run<`RUNS) begin
      @(negedge clk);
      cyc=cyc+1;
      go=0;
      if(!busy_n && ($random(seed)&15)==0 && (cyc>40)) begin
        go=1; mode=(($random(seed)&31)==0); a_mirror=$random(seed); started=1;
        a_base=$random(seed)&18'h0FFFF; n=1+($random(seed)&63); imm_a=(($random(seed)&7)==0)?18'h3FFFF:$random(seed)&18'h0FFFF;
        o_base=$random(seed)&18'h0FF00; o_is=$random(seed)&255; die_id=$random(seed);
        if(($random(seed)&15)==0) n=0;
        run=run+1;
      end
      for(i=64;i>0;i=i-1) begin rdp[i]=rdp[i-1]; wtag[i]=wtag[i-1]; end
      for(i=0;i<8;i=i+1) rqv[i]=rq_n[17*i+16];
      rdp[0]=rqv;
      wtag[0]={cq_n[337],1'b1,cq_n[15:0]};
      for(i=0;i<8;i=i+1) begin dat[32*i+:32]=fp(seed+i*7+cyc); end
      seed=seed+1;
      vm_rr={rdp[RDL],(|rdp[RDL])?dat:256'd0};
      cr[273]=wtag[WRL][17]; cr[272:257]=wtag[WRL][15:0]; cr[256]=wtag[WRL][16]; cr[255:0]=0;
      // compare at this negedge
      if(cq_n[337]) ncq=ncq+1;
      if(done_n) ndone=ndone+1; if(f_n) nfault=nfault+1; if(nan_n) nnan=nnan+1;
      if(busy_o!==busy_n||done_o!==done_n||f_o!==f_n||nan_o!==nan_n||seq_o!==seq_n||cq_o[337]!==cq_n[337]) begin nerr=nerr+1; if(nerr<5)$display("CTRL DIFF t=%0t %b%b %b%b %b%b %b%b",$time,busy_o,busy_n,done_o,done_n,f_o,f_n,nan_o,nan_n); end
      if(cq_n[337] && cq_o!==cq_n) begin nerr=nerr+1; if(nerr<5)$display("CQ DIFF t=%0t\n %h\n %h",$time,cq_o,cq_n); end
      for(i=0;i<8;i=i+1) if(rq_o[17*i+16]!==rq_n[17*i+16] || (rq_n[17*i+16] && rq_o[17*i+:16]!==rq_n[17*i+:16])) begin nerr=nerr+1; if(nerr<5)$display("RQ DIFF t=%0t",$time); end
      if(nerr>=5) begin $display("LOCKSTEP EARLY err=%0d run=%0d",nerr,run); $finish; end
    end
    repeat(400) @(negedge clk);
    $display("LOCKSTEP runs=%0d cyc=%0d done=%0d fault=%0d nan=%0d cq=%0d err=%0d",run,cyc,ndone,nfault,nnan,ncq,nerr);
    $finish;
  end
endmodule

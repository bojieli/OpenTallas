`timescale 1ns/1ps
module tb_qfd_vm_band_controls;
 parameter integer SMAX=9, MUT=0;
 localparam integer PHW=SMAX-7;
 localparam integer PHASES=(1<<SMAX)/128;
 reg clk=0; always #5 clk=~clk;
 reg me_early=0;
 reg [19:0] pc=0;
 reg [27:0] lc=0,tags=0;
 reg [27:0] coverage=0,tag_one=0,tag_zero=0,lc_one=0,lc_zero=0;
 reg [19:0] pc_one=0,pc_zero=0;
 wire [639:0] pc_columns;
 wire [895:0] lc_columns,tags_columns;
 wire [31:0] me_columns;
 ot_qfd_vm_band_controls #(.MUT(MUT),.PHW(PHW)) dut
 (.clk_child({116{clk}}),.me_early(me_early),.pc(pc),.lc(lc),.tags(tags),
 .pc_columns(pc_columns),.lc_columns(lc_columns),.tags_columns(tags_columns),.me_columns(me_columns));
 reg [19:0] refpc[0:2];
 reg [27:0] reflc[0:2],reftags[0:2];
 reg [2:0] meref=0;
 integer t,c,enabled=0,stalls=0;
 reg [31:0] rng=32'h1298acde;
 initial begin
   if(SMAX!=9 && SMAX!=11)$fatal(1,"bad SMAX");
   for(t=0;t<640;t=t+1)begin
     @(negedge clk);
     rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
     me_early=(t<16 || t>612) ? 1'b1 : ((t%31<9)?1'b0:rng[0]);
     // Independent input tags: valid, phase, epoch, payload. Change even while
     // stalled, so an accidental free-running stage cannot hide behind holds.
     pc=rng[19:0];
     lc=rng[27:0] ^ (28'(t*172939));
     tags=28'(t%5!=0) | (28'(t%PHASES)<<1) | (28'(t*1999 & 65535)<<(PHW+1));
     coverage=coverage | tags;
     @(posedge clk);
     if(meref[2])begin
       refpc[2]=refpc[1];refpc[1]=refpc[0];refpc[0]=pc;
       reflc[2]=reflc[1];reflc[1]=reflc[0];reflc[0]=lc;
       reftags[2]=reftags[1];reftags[1]=reftags[0];reftags[0]=tags;
       enabled=enabled+1;
     end else stalls=stalls+1;
     meref={meref[1:0],me_early};
     #1;
     if(t>10)begin
       tag_one=tag_one | tags_columns[27:0];tag_zero=tag_zero | ~tags_columns[27:0];
       pc_one=pc_one | pc_columns[19:0];pc_zero=pc_zero | ~pc_columns[19:0];
       lc_one=lc_one | lc_columns[27:0];lc_zero=lc_zero | ~lc_columns[27:0];
     end
     if(t>10)for(c=0;c<32;c=c+1)begin
       if(pc_columns[20*c+:20]!==refpc[2] || lc_columns[28*c+:28]!==reflc[2] || tags_columns[28*c+:28]!==reftags[2] || me_columns[c]!==meref[1])begin
         $display("FAIL controls SMAX=%0d cycle=%0d col=%0d phase=%0d epoch=%0d pc=%h expected=%h lc=%h expected=%h tags=%h expected=%h",SMAX,t,c,t%PHASES,t/PHASES,pc_columns[20*c+:20],refpc[2],lc_columns[28*c+:28],reflc[2],tags_columns[28*c+:28],reftags[2]);
         $fatal(1,"full32 tag/delay/me mismatch");
       end
     end
   end
   if(coverage !== ((28'h1<<(PHW+17))-1))$fatal(1,"tag bits coverage incomplete");
   if((tag_one & tag_zero) !== ((28'h1<<(PHW+17))-1) || (pc_one & pc_zero)!==20'hfffff || (lc_one & lc_zero)!==28'hfffffff)$fatal(1,"observed payloadbit coverage incomplete");
   $display("PASS controls NRB=64 SMAX=%0d phases=%0d columns=32 cycles=640 enabled=%0d stalls=%0d controls_enabled_edges=3 me_free_edges=2 tagged_payload_bits=%0d",SMAX,PHASES,enabled,stalls,48+PHW+17);
   $finish;
 end
endmodule

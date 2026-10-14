`timescale 1ns/1ps
module tb_qfd_vm_band_gather;
 parameter integer SMAX=9,LAT=3,MUT=0;
 localparam integer PHW=SMAX-7,PHASES=1<<PHW,TOTAL=3+LAT;
 reg clk=0;always #5 clk=~clk;
 reg me_early=0;
 reg [27:0] source_tags=0;
 reg [4095:0] source_data=0,next_data=0;
 wire [31:0] me_columns;
 wire [895:0] column_tags,fan_tags,unused_lc;
 wire [639:0] unused_pc;
 ot_qfd_vm_band_controls #(.PHW(PHW)) u_fan
  (.clk_child({116{clk}}),.me_early(me_early),.pc(20'b0),.lc(28'b0),.tags(source_tags),
   .pc_columns(unused_pc),.lc_columns(unused_lc),.tags_columns(fan_tags),.me_columns(me_columns));
 wire [4095:0] aligned[0:3];
 assign aligned[0]=source_data;
 genvar s,b,tc;
 generate for(tc=0;tc<32;tc=tc+1)begin: tag_source_identity
   // Adversarial per-source epoch salt tests designated-column selection.
   // This is a logical proxy and does not model production epoch creation.
   assign column_tags[28*tc+:28]=fan_tags[28*tc+:28] ^ (28'(tc)<<(PHW+1));
 end endgenerate
 generate for(s=0;s<3;s=s+1)begin: source_align
   for(b=0;b<8;b=b+1)begin: banks
     ot_qfd_vm_xrelay_t #(.W(512),.MEREG(1)) u_relay
      (.clk(clk),.me_e(me_columns[0]),.d(aligned[s][512*b+:512]),.q(aligned[s+1][512*b+:512]));
   end
 end endgenerate
 wire [4095:0] root_words;
 wire [895:0] root_tags;
 ot_qfd_vm_band_gather #(.LAT(LAT),.PHW(PHW),.MUT(MUT)) dut
  (.clk_child({10*LAT{clk}}),.me_e(me_columns[0]),.plane_data(aligned[3]),.column_tags(column_tags),.root_words(root_words),.root_tags(root_tags));
 reg [4095:0] expected_data[0:TOTAL-1];
 reg [27:0] expected_tag[0:TOTAL-1];
 reg [4095:0] data_one=0,data_zero=0;
 reg [895:0] tag_one=0,tag_zero=0;
 reg [2:0] me_ref=0;
 reg [31:0] rng=32'hdf193aca;
 reg [15:0] phases_seen=0;
 integer t,i,r,c,k,enabled=0,stalls=0;
 initial begin
   for(t=0;t<800;t=t+1)begin
     @(negedge clk);
     me_early=(t<40 || t>760)?1'b1:((t%37<12)?1'b0:rng[4]);
     source_tags=28'(t%7!=0)|(28'(t%PHASES)<<1)|(28'(t*1999 & 65535)<<(PHW+1));
     for(i=0;i<4096;i=i+1)begin
       rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
       next_data[i]=rng[0];
     end
     source_data=next_data;
     @(posedge clk);
     // Independent reference follows the actual two free ME stages and the
     // local MEREG stage; it never uses ideal undelayed input me_early.
     if(me_ref[2])begin
       for(i=TOTAL-1;i>0;i=i-1)begin expected_data[i]=expected_data[i-1];expected_tag[i]=expected_tag[i-1];end
       expected_data[0]=source_data;expected_tag[0]=source_tags;
       enabled=enabled+1;
     end else stalls=stalls+1;
     me_ref={me_ref[1:0],me_early};
     #1;
     if(t>40)begin
       for(r=0;r<32;r=r+1)begin
         if(root_tags[28*r+:28] !== (expected_tag[TOTAL-1] ^ (28'(r)<<(PHW+1))))begin
           $display("FAIL gather tag cycle=%0d root=%0d got=%h expected=%h",t,r,root_tags[28*r+:28],(expected_tag[TOTAL-1] ^ (28'(r)<<(PHW+1))));$fatal(1,"tag mismatch");
         end
         for(k=0;k<4;k=k+1)for(c=0;c<32;c=c+1)begin
           if(root_words[128*r+32*k+c] !== expected_data[TOTAL-1][128*c+4*r+k])begin
             $display("FAIL gather data cycle=%0d root=%0d element=%0d column=%0d",t,r,k,c);$fatal(1,"data mismatch");
           end
         end
       end
       data_one=data_one|root_words;data_zero=data_zero|~root_words;
       tag_one=tag_one|root_tags;tag_zero=tag_zero|~root_tags;
       phases_seen[expected_tag[TOTAL-1][1+:PHW]]=1'b1;
     end
   end
   if((data_one & data_zero)!=={4096{1'b1}})$fatal(1,"4096bit coverage incomplete");
   for(r=0;r<32;r=r+1)if((tag_one[28*r+:28]&tag_zero[28*r+:28])!==((28'h1<<(PHW+17))-1))$fatal(1,"all32tagbit coverage incomplete");
   if(phases_seen !== ((16'h1<<PHASES)-1))$fatal(1,"phase coverage incomplete");
   $display("PASS gather NRB=64 SMAX=%0d phases=%0d LAT=%0d roots=32 data_bits=4096 tagged_bits=%0d cycles=800 enabled=%0d stalls=%0d allbitcoverage=PASS allphasecoverage=PASS",SMAX,PHASES,LAT,32*(PHW+17),enabled,stalls);$finish;
 end
endmodule

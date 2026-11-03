`timescale 1ns/1fs
// Finite genuine tile0 PART1 component. No global dates, scales, or AMAX claim.
module tb_native_head_leaf;
 reg clk=0,rst_n=0;always #0.416500 clk=~clk;
 reg [507:0]tap=0;wire[513:0]result;
 native_tile0_cut cut(.clk(clk),.rst_n(rst_n),.tap(tap),.t_out(result));
 reg[378:0]ib[0:3];reg[31:0]h[0:31],gold[0:3199];reg[23:0]rows[0:3199];
 integer outputs=0,reads=0,chunk=0,phase,k,g,l,r,goal,edges=0;reg[127:0]xl;
 // Four native chunks issue1600 slots total.8000edges covers those slots,
 // reset/face/IREG and four finite MUL8/ACC7/tree7/TX/result drains generously.
 // This is a semantic component watchdog, not an external job wall-time cap.
 localparam integer MAX_COMPONENT_EDGES=8000;
 always @(posedge clk)if(edges>=MAX_COMPONENT_EDGES)
  $fatal(1,"COMPONENT_WATCHDOG chunk=%0d outputs=%0d reads=%0d edges=%0d",chunk,outputs,reads,edges);
 `define LOGIC cut.native_tile0.u_g.u_tile.u_tile.u_logic
 `define ME `LOGIC.u_me
 `define ROM0 `LOGIC.g_rom_pipe.g_rph.g_rb[4].g_single.g_col[0].u_leaf
 wire actual_idle=cut.native_tile0.u_g.me_idle;
 // Real macro request, observed before its read edge. Exactly1600 words/column.
 always @(posedge clk)begin
  if(rst_n&&`ROM0.req_m[12])begin
   if(`ROM0.req_m[11:0]!==12'(2048+reads))$fatal(1,"CODE_ORDER count=%0d row=%0d",reads,`ROM0.req_m[11:0]);
   reads++;
  end
  #0.2;
  if(rst_n&&result[512])begin
   if(result[513])$fatal(1,"NATIVE_TILE_FAULT");
   // Native t_vout publishes every K prefix. KC8 selects K7's last8slots.
   // Reuse outputs as the raw ordinal; no new public state or golden arrays.
   if(outputs==0)begin
    $display("FIRST_K0_RAW actual=%h independent_expected=c3174c00",result[31:0]);
   end
   if(outputs>=1600)$fatal(1,"EXTRA_RAW_OUTPUT");
   if(outputs%64>=56)for(integer lane=0;lane<16;lane++)begin
    if(result[32*lane+:32]!==gold[16*((outputs/64)*8+outputs%8)+lane])begin
     $display("RAW_PARTIAL_MISMATCH raw=%0d vector=%0d lane=%0d row=%0d actual=%h expected=%h",outputs,(outputs/64)*8+outputs%8,lane,rows[16*((outputs/64)*8+outputs%8)+lane],result[32*lane+:32],gold[16*((outputs/64)*8+outputs%8)+lane]);
     $fatal(1,"RAW_PARTIAL_MISMATCH");
    end
   end
   outputs++;
  end
  edges++;
 end
 initial begin
  $readmemh("data/resident_ib379.hex",ib);$readmemh("data/H32_me_fp32.hex",h);
  $readmemh("data/raw_partial_expected.hex",gold);$readmemh("data/row_indices.hex",rows);
  // These are BF16-RNE STREAM values expanded to FP32, not raw upstream H.
  for(g=0;g<32;g++)if(h[g][15:0]!=0)$fatal(1,"X_IS_NOT_STREAM_PROJECTION");
  repeat(4)@(negedge clk);rst_n=1;
  // Let the actual reset relay settle; wait on the real face reset and idle.
  wait(cut.native_tile0.u_g.reset_q);repeat(16)@(negedge clk);
  for(chunk=0;chunk<4;chunk++)begin
   wait(actual_idle);@(negedge clk);tap={128'd0,ib[chunk],1'b1};
   @(posedge clk);#0.3;
   r=(chunk==3)?1:8;goal=outputs+64*r;
   // Source-derived XOFF3: tap face + IREG precede the actual issue loop;
   // e_v=active, MEM_EXTRA delays data/tags equally, s1/s1b/s2/s3 consume X.
   // Thus xl for issue(r,k,j) arrives at tap GO+3+64*r+8*k+j.
   // No observed output or fitted latency selects X values.
   for(phase=1;phase<=64*r+2;phase++)begin
    @(negedge clk);xl=0;
    if(phase>=3)begin
     k=((phase-3)/8)%8;
     for(g=0;g<4;g++)xl[32*g+:32]=h[8*g+k];
    end
    tap={xl,ib[chunk],1'b0};@(posedge clk);#0.3;
   end
   @(negedge clk);tap={128'd0,ib[chunk],1'b0};
   wait(actual_idle);
   // Native t_out has one face edge beyond the engine; allow that edge to land.
   repeat(2)@(negedge clk);
   if(outputs!=goal)$fatal(1,"CHUNK_OUTPUT_COUNT chunk=%0d actual=%0d goal=%0d",chunk,outputs,goal);
   if(reads!=((chunk==3)?1600:512*(chunk+1)))$fatal(1,"CHUNK_CODE_COUNT");
   $display("CHUNK_PASS chunk=%0d raw_vectors=%0d reads=%0d edges=%0d",chunk,outputs,reads,edges);
  end
  if(outputs!=1600||reads!=1600)$fatal(1,"FINAL_COUNTS");
  $display("NATIVE_HEAD_LEAF_PASS raw_vectors=1600 selected_vectors=200 values=3200 code_words=1600");$finish;
 end
endmodule

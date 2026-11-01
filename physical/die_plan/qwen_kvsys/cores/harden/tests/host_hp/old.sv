`default_nettype none
module hp_old #(parameter RP_REPL=4)(input wire ck,rst_n,take,input wire[2047:0] words,input wire[59:0] flags,output wire[511:0] h,output wire[14:0] hf);
localparam HDR_PREDECODE=1;
wire[511:0] q[0:3];wire[14:0] qf[0:3];
for(genvar k=0;k<4;k=k+1)begin assign q[k]=words[k*512+:512];assign qf[k]=flags[k*15+:15];end
 if(HDR_PREDECODE)begin:g_hp
  localparam integer SW=512/RP_REPL;
  genvar gi;
  wire[511:0] hm;
  for(gi=0;gi<=RP_REPL;gi=gi+1)begin:g_rp
   (* keep *) reg[3:0] oh;
   always @(posedge ck or negedge rst_n)if(!rst_n)oh<=4'b0001;else if(take)oh<={oh[2:0],oh[3]};
  end
  for(gi=0;gi<RP_REPL;gi=gi+1)begin:g_sl
   assign hm[gi*SW+:SW]=({SW{g_rp[gi].oh[0]}}&q[0][gi*SW+:SW])|({SW{g_rp[gi].oh[1]}}&q[1][gi*SW+:SW])|
                        ({SW{g_rp[gi].oh[2]}}&q[2][gi*SW+:SW])|({SW{g_rp[gi].oh[3]}}&q[3][gi*SW+:SW]);
  end
  // header fields [47:0] and the flags from the dedicated copy
  wire[47:0] hh=({48{g_rp[RP_REPL].oh[0]}}&q[0][47:0])|({48{g_rp[RP_REPL].oh[1]}}&q[1][47:0])|
                ({48{g_rp[RP_REPL].oh[2]}}&q[2][47:0])|({48{g_rp[RP_REPL].oh[3]}}&q[3][47:0]);
  assign h={hm[511:48],hh};
  assign hf=({15{g_rp[RP_REPL].oh[0]}}&qf[0])|({15{g_rp[RP_REPL].oh[1]}}&qf[1])|({15{g_rp[RP_REPL].oh[2]}}&qf[2])|({15{g_rp[RP_REPL].oh[3]}}&qf[3]);
 end
endmodule

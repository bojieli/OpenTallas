`timescale 1ns/1ps
// Fixed calendar successor. No ready, reservation, queue occupancy or survivor
// predicate changes a production edge. Historical dynamic engines stay separate.
module ot_hgi_coll_tkm_static #(parameter integer KMAX=2048, MUT=0)(
 input wire clk,rst_n,start,
 input wire[31:0]tile_clk,input wire buffer_clk,
 input wire[11:0]cfg_n,input wire[12:0]cfg_k,cfg_nout,
 input wire[7:0]cfg_g,cfg_gbase,input wire[15:0]cfg_pf,
 input wire[39:0]cfg_obase,cfg_rbase,input wire cfg_has_r,
 input wire[3:0]del_slot,del_valid,input wire[2179:0]del_flit,
 output reg w_v,output reg[39:0]w_addr,output reg[15:0]w_mask,output reg[511:0]w_data,
 output reg busy,done,fault,output reg[31:0]stat_cycles
);
 localparam integer EW=85,KW=83,VB=83,NT=(KMAX+63)/64,SETTLE=3*NT+8;
    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic [31:0] unkey(input [31:0] k, input nz);
        unkey = nz ? 32'h8000_0000 : (k[31] ? (k & 32'h7FFF_FFFF) : ~k);
    endfunction
    function automatic [KW-1:0] vkey(input [EW-1:0] e);
        vkey = e[VB:1];
    endfunction
    function automatic [KW-1:0] ikey(input [EW-1:0] e);
        ikey = {e[83], e[50:19], e[82:51], e[18:1]};
    endfunction
    // insertion key (84 bits): {valid, ~region, body}: region 0 = the value order (selection phase), region 1 = the id
    // order (re-insertion phase, always below region 0); an invalid element is 0 (the lowest)
    function automatic [KW:0] key2(input [EW-1:0] e);
        reg [KW-1:0] b_;
        begin
            b_ = e[84] ? ikey(e) : vkey(e);
            key2 = e[83] ? {1'b1, ~e[84], b_[KW-2:0]} : {(KW+1){1'b0}};
        end
    endfunction
    // KEY FORM (r3, the chain's storage format): T = {key2(e), nz} -- T[EW-1:1] is the 84-bit insertion key, so the
    // tiles compare stored bits with no key mux; tinv restores the element (an invalid element is 0 in both forms)
    function automatic [EW-1:0] tform(input [EW-1:0] e);
        tform = e[83] ? {key2(e), e[0]} : {EW{1'b0}};
    endfunction
    function automatic [EW-1:0] tinv(input [EW-1:0] t);
        reg [81:0] b_;
        begin
            b_ = t[82:1];
            tinv = !t[84] ? {EW{1'b0}} : (!t[83] ? {1'b1, 1'b1, b_[49:18], b_[81:50], b_[17:0], t[0]} : {1'b0, 1'b1, b_, t[0]});
        end
    endfunction

 reg[31:0]tick,ingress_end,first,clear2,read2,second,finish;
 reg[31:0]valid_pairs;reg[12:0]k;
 reg[23:0]flits;reg[12:0]nout,cells;reg[7:0]gb,g;
 reg[15:0]pf;reg[39:0]ob,rb;reg hr;
 reg[2179:0]beat;
 wire[31:0]rel=tick-8;
 wire ingest=busy&&tick>=8&&tick<ingress_end;
 wire capture=ingest&&(rel[2:0]==0);
 wire issue1=busy&&tick>=9&&tick<=ingress_end;
 wire[31:0]irel=tick-9;
 wire[1:0]lane=irel[2:1];
 wire[544:0]flit=beat[545*lane+:545];
 wire[31:0]group_index=rel>>3;
 reg[3:0]expected;
 always @*begin
  expected=0;
  for(integer l=0;l<4;l=l+1)expected[l]=capture&&((group_index*4+32'(l))<flits);
 end
 wire conv1=busy&&tick>=first&&tick<first+32'(cells);
 wire conv2=busy&&tick>=second&&tick<second+32'(cells);
 wire clr=busy&&(tick==1||tick==clear2);
 wire read_v=busy&&tick>=read2&&tick<read2+32'(cells);
 wire[9:0]read_addr=10'(tick-read2);
 wire[339:0]buf_data;wire buf_valid;
 reg[2:0]conv_pipe;
 reg[31:0]cap1,cap2;
 reg[339:0]buf_wdata;reg buf_wv;reg[9:0]buf_wa;
 ot_hgi_coll_tkm_buffer u_buffer(.clk(buffer_clk),.rst_n(rst_n),
  .w_v(buf_wv),.w_addr(buf_wa),.w_data(buf_wdata),
  .r_v(read_v),.r_addr(read_addr),.rd_v(buf_valid),.rd_data(buf_data));
 reg[339:0]entry;reg entry_v;
 reg[84:0]raw[0:3],sorted[0:3];
 always @*begin:decode
  reg[7:0]rank_;reg[23:0]f,j;reg[31:0]vv,id;
  rank_=flit[535:528]-gb;
  f=24'(flit[527:512])-24'(rank_)*24'(pf);
  for(integer s=0;s<4;s=s+1)begin
   vv=flit[32*(4*irel[0]+s)+:32];id=flit[256+32*(4*irel[0]+s)+:32];j=f*8+24'(4*irel[0])+24'(s);
   raw[s]={1'b0,1'b1,okey(vv),~id,~rank_[6:0],~j[10:0],(vv==32'h80000000)};
   if(vv==32'hffffffff||32'(irel>>3)*4+32'(lane)>=32'(flits))raw[s]=0;
   sorted[s]=0;
  end
  if(buf_valid)for(integer s=0;s<4;s=s+1)raw[s]=tinv(buf_data[85*s+:85]);
  for(integer s=0;s<4;s=s+1)begin:rank_sort
   integer rank_s;rank_s=0;
   for(integer j_=0;j_<4;j_=j_+1)if(key2(raw[j_])>key2(raw[s])||(key2(raw[j_])==key2(raw[s])&&j_<s))rank_s=rank_s+1;
   sorted[rank_s]=raw[s];
  end
 end
 wire[339:0]down[0:NT],up[0:NT];wire[NT:0]dv;
 assign down[0]=entry;assign dv[0]=entry_v;assign up[NT]=0;
 for(genvar t=0;t<NT;t=t+1)begin:g_tiles
  ot_hgi_coll_tkm_tile #(.PT((KMAX<64)?KMAX:64))u_tile(.clk(tile_clk[t]),.tid(6'(t)),.clr(clr),.conv(conv1||conv2),
   .tau_t(6'd0),.tau_l(7'd0),.ins_v(dv[t]),.ins_b(down[t]),.ovf_v(dv[t+1]),.ovf_b(down[t+1]),
   .up_in(up[t+1]),.up_out(up[t]),.tau_o(),.busy());
 end
 reg[31:0]ids[0:15],values[0:15];
 reg pending_r;reg[511:0]rline;reg[39:0]raddr;reg[15:0]rmask;
 always @(posedge clk)begin
  if(capture)beat<=del_flit;
  entry_v<=busy&&(issue1||buf_valid);
  for(integer s=0;s<4;s=s+1)entry[85*s+:85]<=tform((MUT==1&&s==3)?85'd0:sorted[s]);
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;done<=0;fault<=0;stat_cycles<=0;tick<=0;conv_pipe<=0;
   cap1<=0;cap2<=0;buf_wv<=0;w_v<=0;pending_r<=0;end
  else begin
   done<=0;w_v<=0;buf_wv<=0;
   conv_pipe<={conv_pipe[1:0],conv1||conv2};
   if(busy)begin
    tick<=tick+1;stat_cycles<=tick+1;
    if(del_valid!=expected||del_slot!=expected)fault<=1;
    if(issue1)begin:count_pairs
     integer added;added=0;for(integer s=0;s<4;s=s+1)added=added+int'(raw[s][83]);
     valid_pairs<=valid_pairs+32'(added);
    end
    if(capture)for(integer l=0;l<4;l=l+1)if(expected[l])begin
     for(integer s=0;s<8;s=s+1)begin
      if(del_flit[545*l+32*s+23+:8]==8'hff&&del_flit[545*l+32*s+:23]!=0&&del_flit[545*l+32*s+:32]!=32'hffffffff)fault<=1;
     end
     if(!del_flit[545*l+544]||del_flit[545*l+528+:8]<gb||del_flit[545*l+528+:8]>=gb+g)fault<=1;
    end
    if(conv_pipe[1]&&tick<clear2)begin
     buf_wv<=1;buf_wa<=10'(cap1);cap1<=cap1+1;
     for(integer s=0;s<4;s=s+1)begin:tag
      reg[84:0]e;e=tinv(up[0][85*s+:85]);
      buf_wdata[85*s+:85]<=((cap1*4+32'(s))<32'(nout))?(e|{e[83],84'd0}):85'd0;
     end
    end
    if(pending_r)begin w_v<=1;w_data<=rline;w_addr<=raddr;w_mask<=rmask;pending_r<=0;end
    if(conv_pipe[1]&&tick>=second)begin:output_cell
     reg[84:0]e;reg[511:0]oline,rl;reg[15:0]mask_;integer ix;integer count_;
     cap2<=cap2+1;oline=0;rl=0;
     for(integer i=0;i<16;i=i+1)begin oline[32*i+:32]=ids[i];rl[32*i+:32]=values[i];end
     for(integer s=0;s<4;s=s+1)begin
      e=tinv(up[0][85*s+:85]);ix=4*int'(cap2[1:0])+s;
      ids[ix]<=~e[50:19];values[ix]<=unkey(e[82:51],e[0]);
      oline[32*ix+:32]=~e[50:19];rl[32*ix+:32]=unkey(e[82:51],e[0]);
     end
     if(cap2[1:0]==3||cap2+1==32'(cells))begin
      count_=int'(nout)-16*int'(cap2>>2);if(count_>16)count_=16;
      mask_=16'((17'd1<<count_)-1);
      for(integer i=0;i<16;i=i+1)if(i>=count_)begin oline[32*i+:32]=0;rl[32*i+:32]=0;end
      w_v<=1;w_data<=oline;w_mask<=mask_;w_addr<=ob+40'(16*(cap2>>2));
      if(hr)begin pending_r<=1;rline<=rl;raddr<=rb+40'(16*(cap2>>2));rmask<=mask_;end
     end
    end
    if(tick==finish)begin
     if(cap1!=32'(cells)||cap2!=32'(cells)||pending_r||32'(nout)!=((32'(k)<valid_pairs)?32'(k):valid_pairs))fault<=1;
     busy<=0;done<=1;
    end
   end
   if(start)begin:configure
    reg[31:0]i_,c_,a_,b_,r_,s_,f_;reg[31:0]fl_;
    fl_=32'(cfg_g)*32'(cfg_pf);i_=8+((fl_+3)/4)*8;c_=(32'(cfg_nout)+3)/4;
    a_=i_+SETTLE;b_=a_+c_+5;r_=b_+5;s_=r_+c_+6+SETTLE;f_=s_+c_+8;
    if(busy)fault<=1;
    else begin
     fault<=cfg_g==0||cfg_g>96||cfg_pf!=(16'(cfg_n)+7)/8||cfg_nout==0||cfg_nout>KMAX||cfg_k>KMAX||
        cfg_nout>cfg_k||cfg_obase[3:0]!=0||cfg_rbase[3:0]!=0;
     busy<=1;tick<=0;stat_cycles<=0;ingress_end<=i_;first<=a_;clear2<=b_;read2<=r_;second<=s_;finish<=f_;
     valid_pairs<=0;k<=cfg_k;flits<=24'(fl_);cells<=13'(c_);nout<=cfg_nout;gb<=cfg_gbase;g<=cfg_g;pf<=cfg_pf;ob<=cfg_obase;rb<=cfg_rbase;hr<=cfg_has_r;
     cap1<=0;cap2<=0;conv_pipe<=0;pending_r<=0;
    end
   end
  end
 end
endmodule

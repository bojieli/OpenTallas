module leafw_n10_reference #(parameter integer NV=80,K=5,P=3,TREES=1,PB=0,R=0)(
 input wire[TREES*P*NV-1:0] da,db,input wire[P*K*32-1:0] id,output wire[38:0] wp);
 localparam integer NJ=(NV+K-1)/K, NW=TREES*NJ;
 wire[NW-1:0] wa,wb;
 wire[P*K-1:0] sa,sb;
 for(genvar t=0;t<TREES;t=t+1)begin:g_t
  for(genvar j=0;j<NJ;j=j+1)begin:g_j
   localparam integer IX=K*j+R;
   if(IX>=NV)begin:g_none
    assign wa[t*NJ+j]=1'b0;assign wb[t*NJ+j]=1'b0;
   end else if(TREES==1)begin:g_norm
    wire[K-1:0] ca,cb;
    for(genvar k=0;k<K;k=k+1)begin:g_k
     if(IX-k>=0)begin:g_v assign ca[k]=da[PB*NV+IX-k];assign cb[k]=db[PB*NV+IX-k];end
     else begin:g_z assign ca[k]=1'b0;assign cb[k]=1'b0;end
    end
    assign wa[t*NJ+j]=|ca;assign wb[t*NJ+j]=|cb;
   end else begin:g_eng
    assign wa[t*NJ+j]=da[(t*P+PB)*NV+K*j];assign wb[t*NJ+j]=db[(t*P+PB)*NV+K*j];
   end
  end
 end
 for(genvar q=0;q<P;q=q+1)begin:g_q
  for(genvar k2=0;k2<K;k2=k2+1)begin:g_k2
   wire[NW-1:0] ta,tb;
   for(genvar t=0;t<TREES;t=t+1)begin:g_t
    for(genvar j=0;j<NJ;j=j+1)begin:g_j
     localparam integer IX=K*j+R;
     if(TREES==1 && IX<NV && IX-k2>=0)begin:g_n
      assign ta[t*NJ+j]=wa[t*NJ+j]&&da[q*NV+IX-k2];assign tb[t*NJ+j]=wb[t*NJ+j]&&db[q*NV+IX-k2];
     end else if(TREES!=1 && k2==R && IX<NV)begin:g_e
      assign ta[t*NJ+j]=wa[t*NJ+j]&&da[(t*P+q)*NV+K*j];assign tb[t*NJ+j]=wb[t*NJ+j]&&db[(t*P+q)*NV+K*j];
     end else begin:g_z
      assign ta[t*NJ+j]=1'b0;assign tb[t*NJ+j]=1'b0;
     end
    end
   end
   assign sa[q*K+k2]=|ta;assign sb[q*K+k2]=|tb;
  end
 end
 reg[15:0] dlo,dhi;reg[5:0] slot;
 integer i,n;
 always @*begin
  dlo=0;dhi=0;slot=0;
  for(i=0;i<P*K;i=i+1)begin
   dlo=dlo|({16{sa[i]}}&id[i*32+:16]);
   dhi=dhi|({16{sb[i]}}&id[i*32+16+:16]);
  end
  for(n=0;n<NW;n=n+1)if(wa[n])slot=slot|6'(TREES==1?n:(n/NJ)*16+(n%NJ));
 end
 wire en=|wa;
 assign wp={en,slot[5:1],slot[0],dhi,dlo};
endmodule

`timescale 1ns/1ps
// Source selector test only. No event table or programme is manufactured here.
// Missing child blocks are intentionally outside this combinational selector vehicle.
module tb_sys_face_lctx_select;
  reg te; reg[2:0] tp; reg[8:0] ta; wire[3:0] tk=ta[8:5]; wire[4:0] tb=ta[4:0];
  integer a,p,v,n; reg lay,stage,bad,seg;
  qfd_sys_face_ovl_lctx1 #(.L_CONTEXTS(1)) d();
  qfd_sys_face_ovl_lctx1 #(.L_CONTEXTS(0)) legacy();
  initial begin
    force d.t_ev=te; force d.t_p=tp; force d.t_k=tk; force d.t_b=tb;
    force legacy.t_ev=te; force legacy.t_p=tp; force legacy.t_k=tk; force legacy.t_b=tb;
    n=0;
    for(v=0;v<2;v=v+1)for(p=0;p<8;p=p+1)for(a=0;a<512;a=a+1)begin
      te=v;tp=p;ta=a;#1;
      stage=v && p==0; lay=v && (p==0 || p==5) && ((a & 64)!=0);
      bad=lay && (!stage || (a & 63)<1 || (a & 63)>36);
      seg=stage && (a & 63)>=2 && (a & 63)<=36;
      if(d.l_context_bad!==bad || d.l_go!==(lay && !bad) || d.l_context_seg!==seg)
        $fatal(1,"context selector v=%0d class=%0d arg=%0d",v,p,a);
      if(legacy.l_context_bad!==0 || legacy.l_go!==lay || legacy.l_context_seg!==0)
        $fatal(1,"default selector changed");
      n=n+1;
    end
    $display("PASS selector %0d cases; default behavior preserved; no programme playback claim",n);$finish;
  end
endmodule

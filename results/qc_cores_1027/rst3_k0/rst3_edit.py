import sys
p=sys.argv[1]; s=open(p).read()
old="""    for (gc = 0; gc < 8; gc = gc + 1) begin : g_xsl"""
new="""    // QC-CORES-1 10-27 (rst3 KEEP-FAIL fix): lane 0 has multiplier K=0, so qfd_dv_su8_stride #(0) is y=0 and
    // xs_l[0] can only ever load 0 -> its 16 select replicas g_xsl[0].g_sel[*] and the K=0 xlane register were dead
    // logic (yosys const-folded g_xsl[0].u.q, ORFS 1_synth eliminate_dead_logic then removed the 16 kept-but-unloaded
    // kff instances -> routed LEC KEEP FAIL 16/3254).  Lane 0 is now the constant it already was (power-up X of the
    // never-loaded-nonzero register refined to 0, as synthesis and the LEC gold already did); lanes 1..7 keep their
    // names g_xsl[1..7].* unchanged.  0 edges, same values.
    assign xs_l[0] = {4*AW{1'b0}};
    for (gc = 1; gc < 8; gc = gc + 1) begin : g_xsl"""
assert s.count(old)==1; s=s.replace(old,new); open(p,"w").write(s); print("edited")

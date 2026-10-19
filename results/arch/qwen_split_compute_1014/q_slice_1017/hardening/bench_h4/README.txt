Q-H16C 10-18 bench_h4: tb_qfd_dv_heads after the held-ib compare fix (ea921af17), Verilator 5.050, ot-epyc4.
heads_pos   HD_W130=1          PASS 397,440 tile-edges, 256 gos, offset 4 edges; 192 held-ib non-go diffs (info)
heads_pos0  HD_W130=0          PASS 397,696 tile-edges, offset 0; 0 held-ib diffs
heads_m8    HD_W130=1 MUT=8    FAIL (^FAIL heads errors=397248)   column head TDM wrong line
heads_m9    HD_W130=1 MUT=9    FAIL (^FAIL heads errors=397248)   x word bit flip
heads_ibmut HD_W130=1 IBMUT=1  FAIL (^FAIL heads errors=256)      ib bit 1 flipped on the slice's go edges: go-edge ib check is live
Root cause of bench_h3's 192/397,440: testbench compared the HELD ib field on non-go edges; w130 heads (FILL_LEAD 5, DX 14)
update the held ib 9 edges before the go vs the fabric's 8 -> 3 op changes x 64 tiles. Tiles sample ib only with go. No RTL change.

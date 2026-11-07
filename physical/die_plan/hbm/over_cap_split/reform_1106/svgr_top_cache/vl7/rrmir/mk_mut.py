#!/usr/bin/env python3
"""DIE-HBM-88 RRMIR mutants: python3 -I mk_mut.py SRC_cachecut.sv OUTDIR (one file per mutant, run by run_rr.sh MUTS=1)."""
import sys
from pathlib import Path
src = Path(sys.argv[1]).read_text(); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
M = {
 'M01_noclr': ("assign rrm_alloc_keep[g]=allocated[g]&&!rrm_clr[g];", "assign rrm_alloc_keep[g]=allocated[g];"),
 'M02_noset': ("assign av_d[b]=!(rrm_alloc_keep[b]||(!rrm_clr[b]&&set_b))", "assign av_d[b]=!(rrm_alloc_keep[b])"),
 'M03_nodescf': ("wire rrm_set_fault=reserve_fire&&!rrm_desc_ok;", "wire rrm_set_fault=1'b0;"),
 'M04_nostartf': ("assign rrm_nsf_p=stream_fault||start_fault;", "assign rrm_nsf_p=stream_fault;"),
 'M05_nohf_rr': ("wire rr_x=!seam_h_fault&&", "wire rr_x="),
 'M06_sfp0_stuck': ("sf_p<={LBANKS{next_sf}}", "sf_p<={{(LBANKS-1){next_sf}},1'b0}"),
 'M07_sfd_lag': ("sf_d<=next_sf;", "sf_d<=stream_fault;"),
 'M08_avi_rst0': ("av_i<={LBANKS{1'b1}};", "av_i<={LBANKS{1'b0}};"),
 'M09_avi_idx0': ("assign reserve_ready=rrm_srst&&av_i[reserve_bank]&&rr_x;", "assign reserve_ready=rrm_srst&&av_i[0]&&rr_x;"),
 'M10_nobf_go': ("!(sf_p[g]||seam_h_fault||(|seam_bfault))", "!(sf_p[g]||seam_h_fault)"),
 'M11_avf_lag': ("else begin av_i<=av_d;av_f<=av_d;end", "else begin av_i<=av_d;av_f<=av_i;end"),
 'M12_nosrst_rr': ("assign reserve_ready=rrm_srst&&av_i[reserve_bank]&&rr_x;", "assign reserve_ready=av_i[reserve_bank]&&rr_x;"),
 'M13_sfd_drain_raw0': ("   if(draining&&!fault_d)begin", "   if(draining&&!g_sfm.sf_d)begin"),
}
for k, (a, b) in M.items():
    assert src.count(a) == 1, (k, src.count(a))
    (out / f"{k}.sv").write_text(src.replace(a, b))
print(len(M), "mutants")

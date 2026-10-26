#!/usr/bin/env python3
"""Selected regional station tail ABI repair: actual per-K width=min(nwords,JB).
Preserves fixed JB8 storage/pipeline and cfg publication edge. New source/view;
old CLOSED qfd_dv_redstn2_region must not alias this module.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def main():
 s=(R/'rtl/qwen_dv/qfd_dv_redstn2_regional.sv').read_text()
 a=s.index('module qfd_dv_redstn2_region #');b=s.index('endmodule',a)+len('endmodule')
 s=s[a:b].replace('module qfd_dv_redstn2_region #','module qfd_dv_s8_station_tail1 #',1)
 old='wire          eblo = plo && wlo == JB - 1, ebhi = phi && whi == JB - 1;'
 new='''// LASTK counts actual words in each K block. A production tail may carry
    // fewer than JB words (e.g. LM48rows=3words); nwords>=JB keeps JB width.
    // Zero encodes the legacy full-width counter wrap and is not newly adopted.
    reg [JBW-1:0] word_last;
    always @(posedge ck or negedge sr_reset[2])
        if (!sr_reset[2]) word_last <= JBW'(JB - 1);
        else if (cfg_final[6]) word_last <= JBW'((safe_cfg_nwords != 0 && safe_cfg_nwords < JB) ? safe_cfg_nwords - 1 : JB - 1);
    wire          eblo = plo && wlo == word_last, ebhi = phi && whi == word_last;'''
 assert s.count(old)==1;s=s.replace(old,new)
 (R/'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_tail1.sv').write_text('`timescale 1ns/1ps\n// Opt-in selected S8 LASTK tail repair; same ports/stages, new unclosed view required.\n'+s+'\n')
if __name__=='__main__':main()

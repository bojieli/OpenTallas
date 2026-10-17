#!/usr/bin/env python3
"""Native projection leaf pins from its reserved HC band placement.
All six leaves use one top-facing staging bus; each band routes a split staged
broadcast around the leaves. Die-wide static delivery/cut proof remains OPEN.
"""
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_functional';out.mkdir(exist_ok=True)
 pp={};x=200.064
 for p,n in [('stage_d',4096),('stage_word',7),('stage_v',1),('stage_begin',1),('cmd_v',1),('cmd_ffn',1),('cmd_layer',6),('norm_eps',32)]:
  pp[p]=[['N','M5',round(x+.096*i,3),.192] for i in range(n)];x+=.096*n+.96
 pp['o_d']=[['S','M5',400.032+.096*i,.192] for i in range(32)]
 pp['o_v']=[['S','M5',403.2,.192]];pp['fault']=[['S','M5',404.16,.192]]
 pp['clk']=[['W','M4',4.032,.192]];pp['rst_n']=[['W','M4',4.992,.192]]
 V.write(out,'ot_s81_hcx_projection_leaf',[1728.,864.],pp,'clk','N fixed80-beat X staging multicast corridor; S gathered FP32 projection result; W clock/reset', 'v20_native_hcp',{'clock_entries':{'serial':['clk']},'adoption':'OPEN: clock/native/reset, exact static flight and each band cut proof, 43-set resident2-page capacity; all physical multicast/return paths remain OPEN','source':'tools/s81/hcx_leaf_pins.py'})
 print('HCX_NATIVE_PIN_ASSIGN4096stage+controls,32result,serialroot')
if __name__=='__main__':main()

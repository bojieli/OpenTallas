from pathlib import Path
import re
r=Path('/srv/opentallas-scratch2/claude/codex-head-token-1106')
for old,new in [('phase_control3','phase_control_age_tt'),('phase_control_ff1','phase_control_age_ff')]:
 src=r/old;o=r/new;o.mkdir(exist_ok=False);s=(src/'tb.sv').read_text()
 # Independent unwrapped source-word history. Current literal strap60 is signed−4
 # (baseK−6 + two writer START stages); reader word m must equal source m+4.
 marker='always@(negedge refclk)if(cycles==800)'
 i=s.index(marker)
 age='''reg[47:0] history[0:1023];integer wn=0,rn=0,age_checks=0,idx;
 always@(posedge clock_landing_fwd_ctl_nstrip__unit_ft_o)begin
  if(!clock_landing_start_ctl_nstrip__unit_ft_o)wn=0;
  else begin history[wn]=data;wn=wn+1;end
 end
 always@(posedge pc_lep0N)begin
  if(!lep0N.cland_start)rn=0;
  else begin idx=rn+4;rn=rn+1;#0.001;
   if(ready)begin age_checks++;if(idx>=wn||q!==history[idx])$fatal(1,"DATA_AGE rn%0d idx%0d wn%0d got%0d expected%0d",rn,idx,wn,q,history[idx]);end
  end
 end
'''
 s=s[:i]+age+s[i:];s=s.replace('if(!ready||fault)$fatal','if(!ready||fault||age_checks<400)$fatal').replace('ready,fault);if','ready,fault);$display("AGE_CHECKS %0d",age_checks);if');(o/'tb.sv').write_text(s);(o/'source.f').write_text((src/'source.f').read_text().replace(str(src/'tb.sv'),str(o/'tb.sv')));(o/'run.sh').write_text('#!/bin/bash\nset -u\niverilog -g2012 -s phase_control_tb -o sim -c source.f >build.log 2>&1\nrc=$?;echo $rc >build.rc;if [ $rc -ne 0 ];then exit $rc;fi\nvvp sim >run.log 2>&1\nrc=$?;echo $rc >run.rc;exit $rc\n')
print('TT_FF_AGE_READY')

import sys
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kv-pv-resume-1029')
sys.path.insert(0,str(p/'named_source/tools/die_plan'))
import core_family_slice as C
C.ENV += ['BUFx6f_ASAP7_75t_R','BUFx4f_ASAP7_75t_R','BUFx3_ASAP7_75t_R','BUFx2_ASAP7_75t_R']
sys.argv=['core_family_slice.py','run','--family',str(p/'pv_family_named.json'),'--core','kv3_pv_pair','--kit',str(p/'R0cluster16'),'--work',str(p/'named_lowload'),'--libtt',str(p/'invbuf_tt.lib'),'--libff',str(p/'invbuf_ff.lib')]
C.main()

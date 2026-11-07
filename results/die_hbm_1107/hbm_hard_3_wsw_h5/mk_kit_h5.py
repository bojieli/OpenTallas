import json,hashlib,os,shutil,subprocess,sys
S='/srv/opentallas-scratch3/claude/hbm-hard-2-wsw/kits/ot_wbq_sw_vH4/ot_wbq_sw_0fbb129992ad'
W='/srv/opentallas-scratch3/claude/hbm-hard-3'
K=W+'/kits/wsw_vH5/ot_wbq_sw_0fbb129992ad'
assert not os.path.exists(K)
assert not os.path.exists(S+'/run')
shutil.copytree(S,K,ignore=shutil.ignore_patterns('__pycache__','rtl_lint.json','rtl_lint.log'))
open(W+'/kits/.keep','w').close();open(K+'/.keep','w').close()
p=K+'/rtl/ot_wbq_split.sv'
subprocess.check_call(['python3','-I',W+'/hh3_h5.py',p,p])
p=K+'/rtl/ot_wbq_sw__fshell.sv';s=open(p).read()
assert s.count('#(.HREG(4)) u_fcore')==1
s=s.replace('#(.HREG(4)) u_fcore','#(.HREG(4),.SEL16(1)) u_fcore');open(p,'w').write(s)
p=K+'/config.mk';s=open(p).read()
s+='''
# HBM-HARD-3 11-07 vH5 = vH4 + SEL16=1 (RTL, same cycle). vH4 routed: 54 slew nets / 634 pins, every one a K-switch sel_q bit
#  through one BUFx6f to ~48 AND legs over ~61 um. SEL16: one sel_q set per 16-bit slice (18 slices), so <=16 legs per select flop.
#  No new pin cycles, no schedule change (lock-step bench vs flat ref + vH4, mutants k1-k9/r2/l1-l7 FAIL).
'''
open(p,'w').write(s)
p=K+'/added_rx_clk_PIN_cycles.json';c=json.load(open(p))
c['vH5']={"by":"HBM-HARD-3","SEL16":1,"new_PIN_CYCLES":0,"note":"select flops replicated per 16-bit slice, same edge; schedule unchanged"}
json.dump(c,open(p,'w'),indent=1)
p=K+'/PROVENANCE.json';c=json.load(open(p))
for f in list(c['files']):
  if os.path.exists(K+'/'+f): c['files'][f]=hashlib.sha256(open(K+'/'+f,'rb').read()).hexdigest()
c['form']={"by":"HBM-HARD-3","base":"hbm-hard-2-wsw ot_wbq_sw vH4 kit inputs","rtl_patch":"hh3_h5.py (SEL16) on claude/hbm-hard-3-wsw-h5-1107","note":"kit-local RTL + config; kit_hash not recomputed; re-sign on main tag after merge"}
json.dump(c,open(p,'w'),indent=1)
print('OK',K)

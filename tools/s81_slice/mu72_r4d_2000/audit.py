#!/usr/bin/env python3
"""Real r4d top elaboration plus pair-clock/reset/data contract, no array simulation."""
import json,subprocess,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('tools/s81_slice').resolve()))
from mu72_lnland_audit import LIB
root=Path.cwd();out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
top='ot_s81sl_slice_lepw_mab_r4d_mu_72'
src=root/'rtl/dsrom_sys/s81_dv/slice/mu72'/f'{top}.sv'
base=src.read_text()
rows=[]
for name,source in [('base',base),('wrong_pair_clock',base.replace('u_ln0 (.ck(ck_KA)','u_ln0 (.ck(ck_KB)')),('wrong_credit',base.replace('#(.CORE_CRED(12)) u_ln1','#(.CORE_CRED(8)) u_ln1'))]:
 d=out/name;d.mkdir(exist_ok=True);s=d/'top.sv';s.write_text(source)
 ys=[f'read_verilog -sv -lib {root/p}' for p in LIB]
 ys += [f'read_verilog -sv {s}',f'hierarchy -check -top {top}','proc','opt_clean',f'write_json {d/"net.json"}']
 (d/'a.ys').write_text('\n'.join(ys)+'\n')
 with (d/'yosys.log').open('w')as f:r=subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-q','-s',str(d/'a.ys')],stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(name,r.returncode)
 m=json.loads((d/'net.json').read_text())['modules'][top];c=m['cells'];ports=m['ports'];e=[]
 n=lambda cell,port:c[cell]['connections'][port]
 val=lambda cell,param:int(c[cell]['parameters'][param],2)
 check=lambda ok,msg:e.append(msg)if not ok else None
 check(not any(p.startswith('ck_N')for p in ports),'unused lane clock ports')
 check(not any(x.startswith('u_lnl')for x in c),'redundant lane landing')
 for k,v in {'CRED':12,'DR':12,'RX_SRAM':1,'IN_PIPE':1,'NATIVE32':1}.items():check(val('u_lep',k)==v,'lep '+k)
 for i in range(4):
  ln='u_ln'+str(i);reg='A'if i<2 else'B';check(n(ln,'ck')==n('u_lep','clk_'+reg.lower()),ln+' pair clock')
  check(n(ln,'rs')==n('u_lep','rst_n_'+reg.lower()),ln+' pair reset')
  check(val(ln,'CORE_CRED')==12,ln+' credit')
  for lp,ep in [('lo_v',f'lo{i}_v'),('lo_r',f'lo{i}_r'),('lo_d',f'lo{i}_d'),('li_v',f'li{i}_v'),('li_r',f'li{i}_r'),('li_d',f'li{i}_d'),('flt',f'l{i}_f')]:check(n(ln,lp)==n('u_lep',ep),ln+' '+lp)
  rp='rxv'if i<2 else'rxvb';check(n(ln,'rx')[0]==n('u_lep',rp)[i%2],ln+' receive valid')
 check(len([x for x in c if x.startswith('u_lpl_')])==6,'S/K landings changed')
 check(all(k in c for k in ['u_ml_wr','u_ml_cmd','u_ml_ret']),'K/ML landings changed')
 expected=(not e)if name=='base'else bool(e);assert expected,(name,e)
 rows.append({'case':name,'errors':e,'expected':True});print('R4D_AUDIT',name,'PASS'if name=='base'else'CAUGHT',e)
(out/'receipt.json').write_text(json.dumps({'top':top,'source_sha256':hashlib.sha256(base.encode()).hexdigest(),'library_sha256':{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in LIB},'cases':rows,'scope':'Real full top elaboration and source contract only; physical closure and composed token integration remain owed'},indent=1)+'\n')
print('R4D_FULL_TOP_AUDIT_PASS')

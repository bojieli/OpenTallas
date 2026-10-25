import sys,subprocess,types,re
from pathlib import Path
w=Path(__file__).resolve().parents[4];sys.path[:0]=[str(w/'tools/mem_compiler'),str(w/'tools/qwen_missing')]
import link_phy_gen as G
old=types.ModuleType('baseline');old.__file__=str(w/'tools/qwen_missing/link_phy_gen.py');sys.modules['baseline']=old
exec(subprocess.check_output(['git','show','eccf35226c:tools/qwen_missing/link_phy_gen.py'],cwd=w,text=True),old.__dict__)
a,ai=old.write_lef('ot_qkvd_ucie_x64_phy',777.6,777.6,G.pins(583),.192)
b,bi=G.write_lef('ot_qkvd_ucie_x64_phy',777.6,777.6,G.pins(583),.192)
assert a==b and ai==bi,'default drift'
c,ci=G.write_lef('ot_qkvd_ucie_x64_phy',777.6,777.6,G.pins(583),.192,pg_access_layer='M6')
def strip_pg(s):
 return re.sub(r'  PIN (VDD|VSS)\n.*?  END \1\n','',s,flags=re.S)
assert strip_pg(b)==strip_pg(c),'signal/OBS drift'
for pin in ('VDD','VSS'):
 block=re.search(r'  PIN '+pin+r'\n.*?  END '+pin+r'\n',c,re.S).group()
 assert 'LAYER M6' in block and 'LAYER M4' not in block
try:G.write_lef('x',777.6,777.6,G.pins(583),.192,pg_access_layer='M2')
except ValueError:pass
else:raise AssertionError('invalid PG profile accepted')
print('PASS default byte-identical, signal/OBS unchanged, M6 PG terminals only, invalid profile rejected')

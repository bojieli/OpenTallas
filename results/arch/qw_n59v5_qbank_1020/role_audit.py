import sys,re,json,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import textbook_lint as T
net=Path(sys.argv[2]);lib=Path(sys.argv[3]);out=Path(sys.argv[4])
g,top=T.flatten(T.parse_verilog(net.read_text()),'qfd_native59_qbank');a=T.build(g,None)
s=lib.read_text();m=re.search(r'cell\s*\(\s*"?([^"\)\s]+)',s);master=m.group(1)
roles={name:direction for name,_,direction in re.findall(r'(?:pin|bus)\s*\(\s*"?([^"\)\s]+)"?\s*\)\s*\{([^{}]*?)direction\s*:\s*(input|output|inout)',s,re.S)}
checked=[];bad=[]
for ci,(typ,name,pins) in enumerate(g.cells):
 if a['kind'][ci]!='macro':continue
 if typ!=master:bad.append(dict(cell=name,reason='unbound macro master',master=typ));continue
 for pn,bs in pins.items():
  want=roles.get(T._base(pn));actual=a['pin_dir'][ci].get(pn)
  expect={'input':'in','output':'out','inout':'inout'}.get(want)
  checked.append(dict(cell=name,pin=pn,bits=len(bs),liberty_direction=want,census_direction=actual))
  if expect!=actual:bad.append(checked[-1])
res=dict(schema='codex.native_macro_roles.v1',top=top,mapped_sha256=hashlib.sha256(net.read_bytes()).hexdigest(),liberty=str(lib),liberty_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),authority='actual SRAM SS Liberty pin and bus directions; no coordinates or cell behavior fabricated',master=master,liberty_roles=roles,checked=checked,mismatches=bad,verdict='PASS' if not bad and len(checked)==64 else 'FAIL')
out.write_text(json.dumps(res,indent=2)+'\n');print('MACRO_ROLE_AUDIT',res['verdict'],'pin families',len(checked),'mismatches',len(bad));raise SystemExit(0 if res['verdict']=='PASS' else 1)

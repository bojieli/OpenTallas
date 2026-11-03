from pathlib import Path
import re,json,hashlib,shutil
R=Path('/srv/opentallas-scratch2/claude/codex-ds-bf-native-pair-0605');F=Path('/srv/opentallas-scratch2/claude/codex-ds-service-hier-0340/fs');M=json.loads(Path('/srv/opentallas-scratch2/claude/codex-ds-legacy-xs-gate-0538/module_definitions.json').read_text());M={n:[d for d in ds if '/rtl/test/' not in d['file'] and '/frame_lp/kit/' not in d['file'] and not d['file'].endswith('/cells_used.v')] for n,ds in M.items()};M={n:ds for n,ds in M.items() if ds};known=set(M)
roots=['ot_s81sl_xrt1','ot_s81sl_rstopt_xo','ot_s81sl_xs4','dsfd_cfifo_crs4','ot_s81_sstn_base566','ot_s81_sstn_payload536','dsfd_rly_2_NW','dsfd_rly_15_SN','dsfd_rly_283_EW','dsfd_rly_266_EW','dsfd_rly_536_SW','dsfd_rly_536_EN','dsfd_rly_54_WN','dsfd_rly_38_WN','ot_dp_dly','ot_s81_cfg7_seq_bfp','ot_rom_4096x72_m8','dsfd_bf_front_roots','dsfd_bf_col']
seen=set();todo=roots[:];files={}
while todo:
 n=todo.pop()
 if n in seen:continue
 seen.add(n)
 for d in M[n]:
  p=F/d['file'];raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==d['file_sha256']
  if p.name=='ot_s81sl_xs4.sv':raw=(R/'xs4.sv').read_bytes()
  files[str(p)]=raw;text=re.sub(r'/\*.*?\*/|//[^\n]*','',raw.decode(),flags=re.S);text=re.sub(r'"(?:\\.|[^"\\])*"','',text);todo.extend((set(re.findall(r'\b[A-Za-z_][\w$]*\b',text))&known)-seen)
D=R/'src3';D.mkdir(exist_ok=False);paths=[];records=[]
for i,(p,raw) in enumerate(sorted(files.items())):
 name=f'{i:03}_'+Path(p).name;(D/name).write_bytes(raw);paths.append('src3/'+name);records.append(dict(original=p,staged='src3/'+name,sha256=hashlib.sha256(raw).hexdigest()))
(R/'sources.f').write_text(''.join(p+'\n'for p in paths)+'tb.sv\n');(R/'sources.json').write_text(json.dumps(dict(roots=roots,modules=sorted(seen),files=records),indent=2)+'\n');print('NATIVE_BF_PAIR',len(seen),len(paths))

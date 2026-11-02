from pathlib import Path
import re,json,hashlib
base=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/source1131/out_c11e4/rtl');rows=json.load(open('rows.json'));out=[]
for r in rows:
 tn=r['type'];options=[base/f'hbm_arch_{tn}.sv',base/f'hbm_arch_q_b101__{tn}.sv'];files=[p for p in options if p.exists()];assert len(files)==1,(tn,files)
 f=files[0];s=f.read_text();inst='u_'+re.sub('_+','_',r['inst']);m=re.search(r'ot_hbm_idx_tail_native\s*#\(([^;]*?)\)\s+'+re.escape(inst)+r'\s*\((.*?)\);',s,re.S);assert m,(r,inst)
 assert m[1]=='.DELIVERED_RESET(1)',m[1]
 pins=dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|\s*$)',m[2],re.S));assert set(pins)=={'clk','rst_n','i_v','i_kv','i_keep','i_sum','i_fault','o_v','o_kv','o_score','o_fault'},pins.keys()
 out.append(dict(part=r['part'],type=tn,planned_inst=r['inst'],actual_source_inst=inst,module=r['module'],source_file=str(f),source_file_sha256=hashlib.sha256(s.encode()).hexdigest(),parameters=m[1],clock=pins['clk'],delivered_reset=pins['rst_n'],connections=pins,instance_text_sha256=hashlib.sha256(m[0].encode()).hexdigest()))
Path('actual_source_rows.json').write_text(json.dumps(out,indent=2)+'\n');print([(r['part'],r['actual_source_inst'],r['parameters'],r['delivered_reset'])for r in out])

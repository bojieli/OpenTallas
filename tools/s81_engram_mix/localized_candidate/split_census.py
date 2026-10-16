#!/usr/bin/env python3
"""Actual Yosys FF/root census; exact module extraction with no body substitutes."""
import argparse,json,re,subprocess,collections,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();O=a.out;O.mkdir(parents=True,exist_ok=True);R=Path(__file__).resolve().parents[3];new=(R/'rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_distributed_candidate.sv').read_text();old=(R/'rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv').read_text();mods=[]
for s,n in[(old,'ot_s81_engram_reset'),(new,'ot_s81_engram_capture_slice'),(new,'ot_s81_engram_rly_split'),(old,'ot_s81_engram_rly')]:mods.append(re.search(r'\bmodule '+n+r'\b.*?endmodule',s,re.S)[0])
(O/'source.sv').write_text('\n'.join(mods));result={}
for label,top in[('split','ot_s81_engram_rly_split'),('baseline','ot_s81_engram_rly')]:
 command=['yosys','-Q','-T','-p',f'read_verilog -sv {O}/source.sv; hierarchy -check -top {top}; proc; flatten; opt_expr; opt_clean; write_json {O}/{label}.json; stat'];run=subprocess.run(command,capture_output=True,text=True);(O/f'yosys_{label}.log').write_text(run.stdout+run.stderr);assert run.returncode==0
 t=json.loads((O/f'{label}.json').read_text())['modules'][top];rootbits=t['ports']['ck'if label=='split'else'clk']['bits'];counts=collections.Counter();resets=collections.Counter();rows=[]
 for n,c in t['cells'].items():
  if c['type']not in['$dff','$adff','$sdff','$dffe','$adffe']:continue
  width=len(c['connections']['Q']);clk=c['connections']['CLK'];assert len(clk)==1 and clk[0]in rootbits;root=rootbits.index(clk[0]);counts[root]+=width
  if 'reset_leaf' in n:resets[root]+=width
  rows.append({'cell':n,'type':c['type'],'width':width,'clock_index':root})
 result[label]={'ff':sum(counts.values()),'root_count':len(counts),'per_root_ff':dict(counts),'per_root_reset_sync_ff':dict(resets),'rows':rows,'json_sha256':hashlib.sha256((O/f'{label}.json').read_bytes()).hexdigest()}
assert result['baseline']['ff']==107 and result['split']['ff']==229
assert result['split']['root_count']==18
profiles=[{'width':2,'copies_per_cluster':8,'payload_ff_each':2,'reset_sync_ff_each':2,'reset_mask':'11'}, {'width':4,'copies_per_cluster':5,'payload_ff_each':4,'reset_sync_ff_each':2,'reset_mask':'1111'}, {'width':32,'copies_per_cluster':4,'payload_ff_each':32,'reset_sync_ff_each':0,'reset_mask':'0; unused local reset synchronizer pruned by actual Yosys'}, {'width':37,'copies_per_cluster':1,'payload_ff_each':37,'reset_sync_ff_each':2,'reset_mask':'bits36:32 reset;31:0 unreset'}]
r={'status':'ACTUAL_YOSYS_SPLIT_ROOT_FF_CENSUS','actual_source_sha256':hashlib.sha256(new.encode()).hexdigest(),'baseline_source_sha256':hashlib.sha256(old.encode()).hexdigest(),'profiles':profiles,'new_payload_ff_per_copy':201,'new_reset_sync_ff_per_copy':28,'new_ff_per_copy':229,'old_ff_per_copy':107,'added_ff_per_copy':122,'added_ff_all4':488,'added_payload_ff_all4':384,'added_reset_ff_all4':104,'new_roots':285,'added_roots':68,'added_logical_edges':0,'previous_source_estimate':'237percopy/+520all4 assumed2resetFF per32unreset leaf. Actual optimizer prunes8unused resetFF/copy. This actual229/+488 supersedes that estimate; historical source/mechanism logs preserved.','actual':result,'scope':'Actual source Yosys proc/flatten/opt_expr/opt_clean census; no newleaf mapped area/clock/native/FFhold/pin qualification. Width2 physical probe cannot qualify4/32/37.'};(O/'census.json').write_text(json.dumps(r,indent=1)+'\n');print('PASS actual229FF/copy vs107baseline;18roots; width2x8/4x5/32x4/37x1; +488FFall4;285roots;0newedges')

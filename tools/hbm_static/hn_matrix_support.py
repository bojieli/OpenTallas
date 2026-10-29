#!/usr/bin/env python3
"""Fail-closed HGI census gate for the explicit P3 HN matrix-only candidate.

This profile describes backend pins, not a command frontend or a production
programme. A supported arithmetic format remains unresolved until the actual
frontend, P3 reduction mapping and source event dates are composed.
"""
import argparse,json
from pathlib import Path
PROFILE = dict(identity='hn_p3_pair16_matrix_candidate_v1',status='candidate_only',
 backend=dict(pinned_source='4d6',pairs=16,columns=8,tiles_per_column=2,
 row_left_bits=3272,row_right_bits=3272,beat_left_bits=4138,beat_right_bits=4138,
 xs_bits=832,gout_bits=1600),
 formats=['BF16','FP8E4M3','FP4E2M1'],
 absent_frontends=['command192','kv_desc64','packet1099','ATT.QK','ATT.PV','INT8'],
 required_gates=['actual HGI command/operand frontend','normative P3 reduction and operand mapping',
 'exact source publication/gather/reset dates','actual VM IO and row publication'],
 whole_programme_supported=False)
FMT_CODE={'BF16':0,'FP8E4M3':1,'FP4E2M1':2}
def classify(r):
 op=r['op'];d=r['operands'];reasons=[]
 if op.startswith('ATT.'):
  return 'unsupported',['attention QK/PV frontend/backend absent']
 if op!='SM.MATVEC':return 'unsupported',['SM opcode not implemented by matrix-only candidate']
 b=d.get('B',{});fmt=b.get('fmt');a=d.get('A',{});o=d.get('O',{})
 if fmt not in PROFILE['formats']:reasons.append('unsupported matrix weight format '+str(fmt))
 elif (r['param']&3)!=FMT_CODE[fmt]:reasons.append('matrix format parameter disagrees with B descriptor')
 if a.get('space')!='VM' or a.get('fmt')!='FP32':reasons.append('activation publication/format not mapped')
 if b.get('space')!='HBM':reasons.append('weight source not mapped')
 if o.get('space')!='VM' or o.get('fmt') not in ('BF16','FP32'):reasons.append('output destination/format not mapped')
 if any(k not in ('A','B','O') for k in d):reasons.append('mixed/index operand semantics not mapped')
 if any(v.get('indexed') or v.get('ibcast') for v in d.values()):reasons.append('indexed/broadcast operand semantics not mapped')
 rx=r.get('rowx') or {}
 if rx.get('rsel') or rx.get('emask'):reasons.append('indirect row/expert selection semantics not mapped')
 if reasons:return 'unsupported',reasons
 return 'unresolved',list(PROFILE['required_gates'])
def gate(census):
 counts={};issues=[]
 for r in census['sm_att_records']:
  status,reasons=classify(r);key=r['op']+':'+status;counts[key]=counts.get(key,0)+1
  issues.append(dict(offset=r['offset'],op=r['op'],param=r['param'],rows=r['rows'],status=status,reasons=reasons))
 return dict(profile=PROFILE,input_sha256=census['sha256'],input_records=census['records'],target_counts=counts,
 target_records=len(issues),issues=issues,programme_emission_allowed=False,
 verdict='REFUSED: matrix-only candidate lacks required production frontend/attention/format composition')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('census',type=Path);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();r=gate(json.loads(a.census.read_text()));a.out.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:r[k] for k in ('target_counts','target_records','programme_emission_allowed','verdict')}))
 raise SystemExit(2)
if __name__=='__main__':main()

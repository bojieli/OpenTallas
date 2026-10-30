"""Stage real current XQ body and its dependencies for the missing middle V leg.

This is a component coupon, without bound wire ages or physical START claims.
"""
import hashlib
import json
import subprocess
from pathlib import Path
import sys

repo=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
def blob(path):
    return subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+path])
inventory='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json'
manifest=json.loads(blob(inventory))
seed='rtl/dsrom_sys/s81_dv/eng/test/miter_ohsel/sources.txt'
paths=[l[4:] for l in blob(seed).decode().splitlines() if l.startswith('SRC ')]
paths=[x.replace('rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv',
                 'rtl/hdc/ot_hdc_prefix.sv') for x in paths]
paths += ['rtl/dsrom_sys/s81_dv/eng/ot_s81eng_rr_n32.sv',
          'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r0c0_pc/ot_sram_1r1w_64x512_m1_r0c0_pc.v']
records=[]
for p in dict.fromkeys(paths):
    b=blob(p); dst=out/'src'/p; dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b)
    records.append({'path':p,'sha256':hashlib.sha256(b).hexdigest()})
defs=['SYNTHESIS',*manifest['defines']]
(out/'source.f').write_text('\n'.join('+define+'+x for x in defs)+'\n'+
    '\n'.join('src/'+r['path'] for r in records)+'\n')
rec={'scope':'REAL_NATIVE_XQ_BODY_TRANSPORT_COMPONENT_ONLY',
     'repo_commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip(),
     'selected_manifest':inventory,'selected_manifest_sha256':hashlib.sha256(blob(inventory)).hexdigest(),
     'actual_parent':'physical/die_plan/s81/bind/generated/dsdv_eng_rr.sv:u_xq',
     'params':{'TXD':8,'MUT':0},'input_mapping':'vi_s->vi_a;vi_n->vi_b',
     'output_mapping':'vo_b->vo_n;vo_a->vo_s','defines':defs,'files':records,
     'source_note':'Real XQ/AQ body files explicitly supplied beyond hard-core bind abstract closure.',
     'expected_component_latency_edges':2,'bound_wire_ages_qualified':False,
     'physical_START_qualified':False,'full_token':False}
(out/'source.json').write_text(json.dumps(rec,indent=2)+'\n')
print('STAGED',len(records),'files',rec['repo_commit'])

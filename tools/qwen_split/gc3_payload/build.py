#!/usr/bin/env python3
"""Bind a real ctlm1032 payload to the actual sys_face cfgROM instance.
Emits an explicit partial mask authority; never invents an OPSEG filler image.
"""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/qwen_split'),str(ROOT/'tools/qwen_layerbench')]
import sys_face_image as S
import lane_ages_export as LA
p=argparse.ArgumentParser();p.add_argument('--ctlm',required=True);p.add_argument('--die-params',required=True);p.add_argument('--out',required=True);p.add_argument('--events',required=True);p.add_argument('--fwd',required=True);a=p.parse_args()
b=Path(a.ctlm);o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
d=json.loads(Path(a.die_params).read_text());ms=d['masters'];cp=ms['qfd_tt_ctlm_dv'];sf=ms['qfd_sys_face']
for k,v in dict(CTX_SRC=1,FCTX=1,NU=4,OPSEG=1,STAGE_ME=1,XPF_TRANSPORT_EDGES=21).items():assert cp[k]==v,(k,cp.get(k))
r=json.loads((b/'ctlm_image.json').read_text());w=[int(x,16) for x in (b/'program.memh').read_text().split()]
assert len(w)==1032 and r['xpf_transport_edges']==21
lane=LA.export(Path(a.fwd),'dv2f20g5r2b')
for k in LA.NEED:
 if r['relay'][k]!=lane[k]:raise SystemExit(f'SOURCE_LANE_AGE_MISMATCH {k}: programme{r["relay"][k]} actualGEN{lane[k]}')
assert cp['XPF_TRANSPORT_EDGES']==lane['XPF_TRANSPORT_EDGES']==r['xpf_transport_edges']
assert w[1029]==w[1030]==0
# mu_opcal.ctx_words({},mask=set()) = (0,4D43<<48), the source ABI's
# tagged empty boot record. RuntimeCTX_SRC supplies real filler identities later.
w[1029],w[1030]=0,0x4D43000000000000
rows,rec=S.build(json.loads(Path(a.events).read_text()),w)
(o/'sys_face_cfg.viamap.hex').write_text(S.viamap(rows));(o/'program.memh').write_text(''.join(f'{x:016x}\n' for x in w))
(o/'program_metadata.svh').write_text(f"localparam [63:0] DIGEST=64'h{S.image_digest(w):016x};\n")
(o/'cfg_writes.memh').write_text(''.join(f"{x['target']:x}{x['addr']:02x}{x['data']:08x}\n" for x in rec['cfg_writes']))
(o/'sys_face_image.json').write_text(json.dumps(rec,indent=2)+'\n')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=dict(schema='opentallas.qwen.cfg-rom-payload-authority.v1',status='CFG_CANDIDATE_OPSEG_UNBOUND',adopted=False,
 die='dv2f20g5r2b',actual_fwd_lanes_sha256=sha(a.fwd),actual_lane_ages=lane,die_params_sha256=sha(a.die_params),actual_ctlm_params=cp,actual_sysface_params=sf,
 source_program_sha256=sha(b/'program.memh'),program_sha256=sha(o/'program.memh'),program_words=1032,
 context='DW5/DW6 magic4D43 mask0 is valid runtimeCTX_SRC bootstrap; filler contexts must arrive through actualctx_x beforeuse.',
 bindings=[dict(die_instance='sys_face',macro_instance='u_rom',macro='ot_rom_4096x72_m8',instance_key='sys_face_cfg',viamap='sys_face_cfg.viamap.hex',sha256=sha(o/'sys_face_cfg.viamap.hex'),simulation='+OT_ROM_DIR=<this directory>; uses unchanged actualdefaultINSTANCE, noexplicitVIAMAPrequired')],
 missing_bindings=[dict(die_instance='tt_ctlm',macro_instance='g_opseg.u_leaf.g_opseg.u_rom',instance_key='qfd_tt_ctlm_opseg',reason='Matchedreal4useropgroupcalendar/ROM notyetbound; noempty/fabricatedfillerROMprovided')],
 physical='rom_gen characterizesallvias, LEF/Lib contentindependent; thismanifest personalizesactualcfgvia-mask only, doesnotclaimmaskfabrication/oldclosedviewcontainsit.',
 holds=['MatchedOPSEGprogrammeandruntimefillercontextproof','BothD2Dcalendarsmatchedr17codec2/TXshift1/status213','K22seamgeometry13>9','Actualnativecompletionbarrierproof'])
(o/'authority.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(words=len(w),digest=rec['program_digest'],status=manifest['status'])))

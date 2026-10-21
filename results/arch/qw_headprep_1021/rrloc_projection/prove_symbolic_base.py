"""Prove the actual RR source inputs differ only by the true HP export delta."""
from pathlib import Path
import argparse,subprocess,hashlib,json,difflib
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('qko_source',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
repo=Path(__file__).resolve().parents[4];a.out.mkdir(parents=True,exist_ok=True)
records=[]
for base,hp in [('qfd_tt_ctlm_dv_lpf.sv','qfd_tt_ctlm_dv_lpf_hp.sv'),('qfd_tt_ctlm_dv_lpf_parts.sv','qfd_tt_ctlm_dv_lpf_hp_parts.sv')]:
 original=(a.qko_source/'rtl/qwen_dv'/base).read_bytes()
 source=subprocess.check_output(['git','-C',str(repo),'show','9add100c4:rtl/qwen_dv/headprep/'+hp])
 restored=source.decode().replace('_hp','').split('\n',1)[1]
 if 'parts' not in base:
  restored=restored.replace('    output wire [17:0]   emb_position,\n    output wire [1:0]    emb_user,\n','')
  restored=restored.replace('    wire [17:0]  g_emb_token, g_emb_position;\n    wire [1:0]   g_emb_user;','    wire [17:0]  g_emb_token;')
  for extra in [', .emb_position(g_emb_position), .emb_user(g_emb_user)',', .emb_position_i(g_emb_position), .emb_user_i(g_emb_user)',', .emb_position(emb_position), .emb_user(emb_user)']:
   restored=restored.replace(extra,'')
 else:
  restored=restored.replace('    output reg  [17:0]   emb_position,\n    output reg  [1:0]    emb_user,\n','')
  start=restored.index('    // Same pre-edge bank/user read');end=restored.index('    assign st =',start);restored=restored[:start]+restored[end:]
  restored=restored.replace('    input  wire [17:0]   emb_position_i,\n    input  wire [1:0]    emb_user_i,\n','')
  restored=restored.replace('    output wire [17:0]   emb_token,\n    output wire [17:0]   emb_position,\n    output wire [1:0]    emb_user','    output wire [17:0]   emb_token')
  restored=restored.replace('    assign emb_position = emb_position_i;\n    assign emb_user = emb_user_i;\n','')
 if restored.encode()!=original:raise ValueError('actual RR symbolic body differs beyond the explicit HP exports: '+base)
 (a.out/base).write_bytes(original)
 (a.out/hp).write_bytes(source)
 (a.out/(base+'.patch')).write_text(''.join(difflib.unified_diff(original.decode().splitlines(True),source.decode().replace('_hp','').splitlines(True),fromfile=base,tofile=hp)))
 records.append(dict(baseline=base,baseline_sha256=hashlib.sha256(original).hexdigest(),hp=hp,hp_sha256=hashlib.sha256(source).hexdigest(),exact_reverse_export_identity=True))
(a.out/'symbolic_identity.json').write_text(json.dumps(dict(status='EXACT_SYMBOLIC_BODY_IDENTITY_ONLY_NOT_NATIVE_OR_SELECTED_AGE',hp_commit='9add100c4',files=records),indent=2)+'\n')
print('EXACT_RR_SYMBOLIC_HP_EXPORT_DELTA_PASS',len(records))

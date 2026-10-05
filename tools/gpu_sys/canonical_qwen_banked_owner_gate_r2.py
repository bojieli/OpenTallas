"""One physical bank gate, unchanged239 root with a DIFFERENT execution actor.

Synthetic control events; no payload/engine/fullbank-join clock qualification.
Original manifest failure/source remain untouched. Every edge expectation is
from complete immutable consumers; all local child page ACKs remain required.
"""
from pathlib import Path
import re,json,hashlib
from tools.gpu_sys.canonical_qwen_manifest_owner_gate_r2 import prepare as prepare_base
from tools.gpu_sys.canonical_qwen_banked_manifest_owner import generate,model,required_banks
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement


def prepare(out):
 out=Path(out);prepare_base(out);p=SourcePlacement.released()
 # Preserve old generated source in temporary preparation only; installed
 # candidate source list selects the new banked leaf, never overlays originals.
 rtl=generate(out,p)
 tb=(out/'tb.sv').read_text().replace('ot_gpu_qwen_manifest_range_owner #','ot_gpu_qwen_banked_manifest_range_owner #')
 tb=tb.replace('wire [6:0] captured_output_rows;','wire [63:0] required_bank_mask64,required_input_bank_mask64,required_output_bank_mask64;\nwire [6:0] captured_output_rows;')
 # Execution actor1, physical bank0: do not alter source bank/protected row seal.
 tb=re.sub(r"([TZ]\d+=239'h)([0-9a-f]+)",lambda m:m[1]+f'{int(m[2],16)|(1<<30):060x}',tb)
 # PC11 has no RF inputs/outputs anywhere: only actor1 participates, bank0
 # must reject it. PC10 already exercises true empty-output input-bank lifecycle.
 start=tb.index('issuer_held_owner55=OZ11;launch')
 end=tb.index('must(published_rows==live_rows&&live_rows==',start)
 tb=tb[:start]+'''bind_tuple=Z11;bind_mask=0;bind_valid=1;#1;
 must(required_bank_mask64==64'h2&&!bind_ready,"nonparticipating bank cannot bind PC11 actor1");bind_valid=0;
 '''+tb[end:]
 expected=[]
 normal={pc:required_banks(p,pc,1) for pc in range(11)}
 for pc,mask in normal.items():expected.append(f"11'd{pc}:must(required_bank_mask64==64'h{mask:016x},\"whole-operation bank mask PC{pc}\");")
 seeds={p.version_ids[h.version] for h in p.rf.values() if h.rank==0 and h.sm==0 and h.birth<0}
 initial=[]
 for v in sorted(seeds):initial.append(f"11'd{v}:must(required_bank_mask64==64'h{required_banks(p,2047,1,v):016x},\"INITIAL exact version-bank mask\");")
 # Tasks inspect required-bank ROM after the actual bind root has settled.
 tb=tb.replace('bind_tuple=id;bind_mask=mask;bind_valid=1;#1;', 'bind_tuple=id;bind_mask=mask;bind_valid=1;#1;\n case(id[174:164])\n'+ '\n'.join(expected)+"\n11'd2047:case(id[29:19])\n"+'\n'.join(initial)+'\ndefault:must(0,"unknown initial");endcase\ndefault:must(0,"unknown gate PC");endcase\n')
 tb=tb.replace('PASS_MANIFEST_OWNER','PASS_BANKED_MANIFEST_OWNER').replace('sourcecompletePC0to11','sourcecompletePC0to10 foreignActor1bank0 exactMask64')
 # Deassert observed input then settle CURRENT combinational outputs. No
 # accepted edge, source event or consumer lifetime is moved.
 tb=tb.replace('step;producer_visible_valid=0;must(rf_range_ack_valid', 'step;producer_visible_valid=0;#1;must(rf_range_ack_valid')
 (out/'tb.sv').write_text(tb)
 (out/'model.json').write_text(json.dumps(model(p),indent=2,sort_keys=True)+'\n')
 manifest={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir()) if f.is_file() and f.name!='manifest.json'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 return manifest

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);print(prepare(a.parse_args().out))

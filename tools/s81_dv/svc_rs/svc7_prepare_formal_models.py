"""Lower the couponed ASR model's mutually exclusive event predicates for Yosys.

No new truth-table assumption: replay the full pinned PDK UDP coupon against
the exact rewritten file, and use its imported-model identity for SAT.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('models',type=Path);ap.add_argument('out',type=Path)
a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
identity=json.loads((a.models.parent/'canonical_model_identity.json').read_text())
assert hashlib.sha256(a.models.read_bytes()).hexdigest()==identity['normalized_library_sha256']
text=a.models.read_text()
def replace(m):
    s=m.group();assert 'wire asr_clear = ~SETN;' in s and 'wire asr_set = ~RESETN & SETN;' in s
    s,n=re.subn(r'if\(!SETN\)', 'if(asr_clear)',s);assert n==1
    s,n=re.subn(r'if\(!RESETN\)', 'if(asr_set)',s);assert n==1
    return s
text,n=re.subn(r'module DFFASRHQNx1_ASAP7_75t_R\b.*?endmodule',replace,text,flags=re.S);assert n==1
model=a.out/'library_model_formal.v';model.write_text(text)
tool=Path(__file__).resolve().parents[2]/'qwen_kv_die/canonical_seq_coupon.py'
subprocess.run(['python3',str(tool),'--pdk-seq',str(a.models.parent/'canonical_SEQ.v'),
                '--pdk-sha256',identity['canonical_SEQ_sha256'],'--imported-model',str(model),
                '--out',str(a.out)],check=True)
j=json.loads((a.out/'canonical_model_identity.json').read_text())
assert all(v.get('pass_canonical_coupon') for v in j['imported_results'].values())
print('SVC7_FORMAL_MODEL coupon=ASR544+HQN128 PASS sha256='+j['imported_model_sha256'])

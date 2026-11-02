from pathlib import Path
import hashlib,json
r=Path(__file__).parent;k=r/'kit'
for name,digest in json.loads((r/'source_closure_check.json').read_text())['sha256'].items():
 assert hashlib.sha256((k/name).read_bytes()).hexdigest()==digest,name
snap=k/'run/results/asap7/kq_qfd_tile_nl_a0c_a0nl14icg1r1/base/source_snapshot'
for name,digest in json.loads((r/'scope.json').read_text())['input_artifacts'].items():
 assert hashlib.sha256((snap/name).read_bytes()).hexdigest()==digest,name
print('NL_EXACT_POSTMM_INPUT_AND_SOURCE_GUARD PASS35+2; no4CTSidentitycredit')

assert (snap/'final_grt.sdc').read_bytes()==(snap/'4_cts.sdc').read_bytes()
print('SAMEBYTE_NORMAL_GRT_SDC_ALIAS_GUARD PASS; no4CTSidentitycredit')

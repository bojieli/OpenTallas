"""Reprove saved LP AIG correspondence with four exact physical-flop renames.

Diagnostic only: original gold/gate AIGs and failures are preserved. No RTL change.
"""
import collections
import importlib.util
import json
import os
from pathlib import Path

os.environ['OT_LEC_RESET_CYCLES'] = '64'
spec = importlib.util.spec_from_file_location('lec', Path(__file__).with_name('lec_current.py'))
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)
root = Path('/work')
inp, out = root / 'input', root / 'proof_v2'
out.mkdir(exist_ok=True)
log = []
L = lec.Lec(lec.read_aig(inp/'gold.aig'), lec.read_map(inp/'gold.map'),
            lec.read_aig(inp/'gate.aig'), lec.read_map(inp/'gate.map'))
L.kit_reset_ports = ['rs']
# A saved profile uses correspond()'s normalized array/alias namespace. Apply
# the exact production preparatory transforms before restoring those keys.
import shutil
shutil.copyfile(inp/'gold.aliases.json',out/'gold.aliases.json')
lec.normalize_gold_elements(L,lec.slang_elements(inp/'gold.aliases.json'),log)
lec.json_alias_keys(L,log,work=out)
lec.slang_element_keys(L,log,work=out)
lec.alias_arrays(L,log,work=out)
lec.relayout(L,log,packed=lec.slang_packed_vectors(inp/'gold.aliases.json'))
lec.renamed(L,log)
lec.noreset_classify(L)
profile = json.loads((inp/'hyp.json').read_text())
report = {'scope':'saved actual LP hunt-none64 AIG diagnostic; not fresh official kit LEC',
          'profile':lec.transfer_profile(L, profile, log)}
pairs = [
 ('u.u_ep.in_ready', 'u.u_ep.rdy_k[3]'),
 ('u.u_gb.g_pc[0].g_b[0].a0', 'u.u_gb.g_pc[0].ps[5]'),
 ('u.u_gb.g_pc[11].g_b[280].a2', 'u.u_gb.g_pc[11].ps[3]'),
 ('u.u_gb.g_pc[5].g_b[140].a1', 'u.u_gb.g_pc[5].ps[4]')]
hints = [['gate', 'ff:u_dut.'+g, ['eq','gold','ff:u_dut.'+r,0]] for g,r in pairs]
(root/'hints.json').write_text(json.dumps(hints,indent=2)+'\n')
report['hints'] = lec.apply_hints(L,hints,out,1000,log,propose_only=True)
report['joint'] = lec.prove_profile(L,out,1000,log)
m, kind = L.build(with_compare=True,with_hyp=True)
status = lec.prove(m,out,1000,log,tag='compare')
report['counts'] = dict(collections.Counter(status.values()))
report['failed'] = {k:v for k,v in status.items() if v != 'proved'}
decl,missing,const = lec.kept_registers(L,inp/'gold.keep')
report['keep'] = {'declared':len(decl),'missing':missing,'constant':const}
report['verdict'] = 'PASS' if not missing and not report['failed'] else 'FAIL'
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'proof.log').write_text('\n'.join(log))
print(json.dumps({'counts':report['counts'],'failed_count':len(report['failed']),
                  'keep':report['keep'],'verdict':report['verdict']},indent=2))

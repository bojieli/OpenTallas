import hashlib,json,shutil,sys,re
from pathlib import Path
R=Path(sys.argv[1]);P=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-producer-1030')
stage=json.loads((P/'stage.json').read_text());source=Path('/srv/opentallas-scratch2/claude/codex-s81-h2-bind-2249/frozen_source')
for name,digest in stage['source_sha256'].items():
 path=source/name
 if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('current selected source changed '+name)
 target=R/'src'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
(R/'source.f').write_text('\n'.join('src/'+n for n in stage['source_sha256'])+'\n');shutil.copyfile(P/'defines.f',R/'defines.f')
capture=Path('/srv/opentallas-scratch2/claude/codex-ds-valid-partial-1030')
observed=re.findall(r'ACTUAL_VALID_PARTIAL leaf(\d+) cycle\d+ data([0-9a-f]{8})',(capture/'base.log').read_text())
partials={int(i):word for i,word in observed}
assert len(observed)==80 and sorted(partials)==list(range(80)) and 'NORM_PRODUCER_PASS checks80 errors0'in(capture/'base.log').read_text()
assert 'GATE_PASS'in(capture/'status.txt').read_text()
# The input is captured actual producer words. The independently generated
# partial.memh remains a scoreboard file,never the source of this handoff.
(R/'actual_partials80.hex').write_text(''.join(partials[i]+'\n'for i in range(80)))
native=json.load(open('/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030/L14/norm_control.json'))
eps=native['eps_fp32_bits'];assert eps=='1e3ce508' and native['epsilon_source']['key']=='norm_eps' and native['epsilon_source']['value']==1e-20
for c in native['commands']:
 if c['kind']=='XFIN_GO':
  payload=int(native['templates'][c['template']]['payload186'],16)
  assert (payload>>26)==int(eps,16) and ((payload>>16)&31)==1
(R/'eps_actual_config.hex').write_text(eps+'\n')
selected=json.load(open('/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030/xf_selected.json'))
assert len(selected['slices'])==16 and all(s['params']==dict(LA=6,LM=5,NS=16,NVL=5,SIW=7)for s in selected['slices'])
(R/'stage.json').write_text(json.dumps(dict(source_sha256=stage['source_sha256'],defines=stage['defines'],selected_XF=selected,
 partial_file_sha256=hashlib.sha256((R/'actual_partials80.hex').read_bytes()).hexdigest(),
 epsilon_source=native['epsilon_source'],epsilon_native_GO_payloads_checked=16,clock_ps=833,
 ring_scope='one registered edge per neighbour is explicit component transport only; no current die NX physical age inferred',
 source_input_epoch=dict(reset_release=32,public_GO=64,partial_leaf_cycles=[96,97,98,99,100]),
 partial_cadence='one public partial per edge,matching actual current XRcollector output',
 global_GO_qualified=False,physical_START_qualified=False),indent=1)+'\n')

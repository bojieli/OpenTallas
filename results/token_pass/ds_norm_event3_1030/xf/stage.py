import hashlib,json,shutil,sys
from pathlib import Path
R=Path(sys.argv[1]);P=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-producer-1030')
stage=json.loads((P/'stage.json').read_text());source=Path('/srv/opentallas-scratch2/claude/codex-s81-h2-bind-2249/frozen_source')
for name,digest in stage['source_sha256'].items():
 path=source/name
 if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('current selected source changed '+name)
 target=R/'src'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
(R/'source.f').write_text('\n'.join('src/'+n for n in stage['source_sha256'])+'\n');shutil.copyfile(P/'defines.f',R/'defines.f')
shutil.copyfile(P/'partial.memh',R/'actual_partials80.hex');(R/'eps_actual_config.hex').write_text('1e3ce508\n')
selected=json.load(open('/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030/xf_selected.json'))
assert len(selected['slices'])==16 and all(s['params']==dict(LA=6,LM=5,NS=16,NVL=5,SIW=7)for s in selected['slices'])
(R/'stage.json').write_text(json.dumps(dict(source_sha256=stage['source_sha256'],defines=stage['defines'],selected_XF=selected,
 partial_file_sha256=hashlib.sha256((R/'actual_partials80.hex').read_bytes()).hexdigest(),
 epsilon_source='fixture-pinned norm_eps1e-20 FP32bits1e3ce508',clock_ps=833,
 ring_scope='one registered edge per neighbour is explicit component transport only; no current die NX physical age inferred',
 source_input_epoch=dict(reset_release=32,public_GO=64,partial_leaf_cycles=[96,97,98,99,100]),
 partial_cadence='one public partial per edge,matching actual current XRcollector output',
 global_GO_qualified=False,physical_START_qualified=False),indent=1)+'\n')

from pathlib import Path
import json,hashlib
base=Path('/srv/opentallas-scratch/claude/codex-qdie-2000')
for t in ('dv2f21g5r51cxc','dv2f21g5r51cxd'):
 s=base/t; src=s/'src'; overlay=s/'prep_source'; h=overlay/'tools/qwen_kv_die/chain'; h.mkdir(parents=True,exist_ok=True)
 orig=src/'tools/qwen_kv_die/chain/die_chain.sh'; text=orig.read_text()
 checkpoint='''# QCHAIN 10-22 opt-in measured prep checkpoint, no full-route credit.
if [ "${OT_STOP:-}" = prep ]; then
  say "PREPARED_WAIT_GRT: validated case/PDN/clock prepared; full GRT/STA still required"
  printf '%s\\n' PREPARED_WAIT_GRT > "$R/PREPARED_WAIT_GRT"
  exit 0
fi
'''
 marker='# ROOT14 10-20 (owner: reduce die closure risk): GEN hard checks before any GRT'
 assert marker in text
 text=text.replace(marker,checkpoint+marker)
 (h/'die_chain.sh').write_text(text)
 for f in orig.parent.iterdir():
  if f.name!='die_chain.sh' and not (h/f.name).exists(): (h/f.name).symlink_to(f)
 aft=(src/'tools/qwen_split/chain_after_build.sh').read_text()
 aft=aft.replace('bash $S/src/tools/qwen_kv_die/chain/die_chain.sh',f'bash {h}/die_chain.sh')
 # Resume rechecks strict bind and the existing die-chain validates preserved case/PDN.
 start=aft.index('# several closed revisions')
 end=aft.index('# owner no-stub gate')
 aft=aft[:start]+'if [ "${OT_FROM:-case}" != grt ]; then\n'+aft[start:end]+'fi\n'+aft[end:]
 ap=overlay/'chain_after_build.sh';ap.write_text(aft)
 chain=(s/'chain.sh').read_text().replace('bash tools/qwen_split/chain_after_build.sh',f'bash {ap}')
 (overlay/'chain.sh').write_text(chain)
 phase=(s/'phase3.sh').read_text().replace('bash $S/chain.sh',f'bash {overlay}/chain.sh')
 (overlay/'phase3.sh').write_text(phase)
 runner='''#!/bin/bash
set -u
S=TAGPATH
. "$S/hp_env.sh"
[ -f "$S/DIAGNOSTIC_BIND_OPEN" ] && export OT_CHAIN_DIAGNOSTIC=1
export OT_STOP=prep
bash "$S/prep_source/phase3.sh" TAG
rc=$?
[ "$rc" = 0 ] || exit "$rc"
[ -s "$S/chain/PREPARED_WAIT_GRT" ] || exit 31
echo 'PREPARED_WAIT_GRT: no GRT/STA qualification'
'''.replace('TAGPATH',str(s)).replace('TAG',t)
 (s/'guarded_prep32.sh').write_text(runner)
 resume=runner[0:runner.index('export OT_STOP=prep')]+'''unset OT_STOP
export OT_FROM=grt
bash "$S/prep_source/phase3.sh" TAG
'''.replace('TAG',t)
 (s/'guarded_resume200.sh').write_text(resume)
 files=[orig,src/'tools/qwen_split/chain_after_build.sh',s/'chain.sh',s/'phase3.sh',h/'die_chain.sh',ap]
 rec=dict(scope='prep phase split only; original pinned source untouched',original_source=(src/'SOURCE_COMMIT').read_text().strip(),prep_mem_GB=32,resume_mem_GB=200,evidence='prior comparable r48 PDN peak ~7.4 GB; ~31k block inventory',checkpoint='after validated case, PDN and physical clock; PREPARED_WAIT_GRT only, no DONE/closure credit',files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
 (overlay/'PREP_PROVENANCE.json').write_text(json.dumps(rec,indent=2)+'\n')
 print(t,'READY',rec['original_source'])

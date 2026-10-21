#!/usr/bin/env bash
set -euo pipefail
ENG_REF=54aa19348e6d1efb0897fd7ada0aee5e95329eed
ENG_MIRROR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
ENG_WORK=/srv/opentallas-scratch/claude/codex-s81-eng-native-1021/rr
mkdir -p "$ENG_WORK"
export BR=codex/s81-eng-native-1021 J=8
git --git-dir="$ENG_MIRROR" cat-file -e "$ENG_REF^{commit}" 2>/dev/null || git --git-dir="$ENG_MIRROR" fetch -q origin "$BR"
git --git-dir="$ENG_MIRROR" show "$ENG_REF:tools/s81_dv/eng_rr/run_eng_rr.sh" > "$ENG_WORK/existing_runner.sh"
bash "$ENG_WORK/existing_runner.sh" "$ENG_REF" "$ENG_WORK/out"
python3 - "$ENG_WORK/out" <<'PY'
import pathlib,json,sys
p=pathlib.Path(sys.argv[1]);d=json.loads((p/'check.json').read_text());assert d['pass'] and all(m['failed'] for m in d['mutants']),d
for n in ['base','xq1','xq2','tap1','tap2','rpar','onesc']:
 assert (p/f'obj_{n}/sim').is_file(),f'no built simulator {n}'
 if n!='base':
  t=(p/f'{n}.log').read_text();assert 'TB_ENG_RR FAIL' in t or 'ENG_RR_PY FAIL' in t,f'no actual causal failure {n}'
for q in p.glob('var_*.log'):
 t=q.read_text();assert 'TB_ENG_RR PASS' in t and 'ENG_RR_PY PASS' in t,q
print('ENG_CURRENT_SOURCE_REQUIRED_COHORT PASS')
PY

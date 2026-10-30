from pathlib import Path
import sys,re
D=Path('/srv/opentallas-scratch2/claude/codex-kvtok-2249')
sys.path.insert(0,str(D/'compiler_root2/tools/qwen_layerbench/kv_dieslice'))
from kv_verdict import classify
p=D/'kvl/probe_Wc_o2';s=(p/'sim.log').read_text(errors='replace')
v,why=classify(p,1)
clean=bool(re.search(r'^GATE_END .*verdict PASS$',s,re.M)) and not re.search(r'^FAR_FAULT\b|^POSTOBS .*epoch_abort 1\b',s,re.M)
result='PASS' if v=='PASS' and clean else 'FAIL'
line=f'PROBE_L0_{result} {v} {why}; transport_clean={clean}'
# Keep the run's 36-layer FAIL verdict intact; this is an additional scoped result.
(p/'probe_gate.txt').write_text(line+'\n');print(line)
raise SystemExit(0 if result=='PASS' else 1)

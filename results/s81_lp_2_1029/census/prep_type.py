#!/usr/bin/env python3
"""S81-LP-2: build a census closure for another LP type from the exact S81-LP-1/Codex census_complete closure:
same 92 non-top snapshots (same picks, physical SRAM interfaces, restored deps), only the top file swapped for the
type's bound top (from the same bind out), with the same approved clock-tap comment syntax fix (62c2ae900 regex)."""
import hashlib,json,re,shutil,sys
from pathlib import Path
src=Path('/srv/opentallas-scratch2/claude/codex-s81-lp-parent-1029/census_complete')
bound=Path('/srv/opentallas-scratch2/claude/codex-tok-s81-1028/bind_s13rfunc_reset/out/rtl')
top=sys.argv[1];dst=Path(sys.argv[2])/'phys';assert not dst.exists(),dst
d=json.load(open(src/'sources.json'));old=d['top']
shutil.copytree(src/'rtl',dst/'rtl');(dst/'rtl'/('000_'+old+'.sv')).unlink()
t=bound/(top+'.sv');txt=t.read_text()
pat=re.compile(r'(?m)^(\s*input wire clk_t[0-9]+\s*)// planned physical tap: forwarded-clock export only(,?)$')
new,n=pat.subn(r'\1/* planned physical tap: forwarded-clock export only */\2',txt)
q=dst/'rtl'/('000_'+top+'.sv');q.write_text(new)
fs=['/out/rtl/000_'+top+'.sv' if l.endswith('000_'+old+'.sv') else l for l in (src/'sources.f').read_text().splitlines()]
(dst/'sources.f').write_text('\n'.join(fs)+'\n')
for r in d['files']:
  if r['snapshot']=='rtl/000_'+old+'.sv':
    r.update(path=str(t),snapshot='rtl/000_'+top+'.sv',sha256=hashlib.sha256(new.encode()).hexdigest(),bytes=len(new.encode()),orig_sha256=hashlib.sha256(txt.encode()).hexdigest())
d['top']=top;d['params']={};d['s81_lp_2_top_swap']=dict(from_closure=str(src),old_top=old,new_top=top,tap_comment_fixes=n)
(dst/'sources.json').write_text(json.dumps(d,indent=1)+'\n');print(json.dumps(d['s81_lp_2_top_swap']))

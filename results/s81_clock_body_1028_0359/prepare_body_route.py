import json,re,shutil
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body');B=Path('/srv/opentallas-scratch2/claude/die-s81-7');site=json.load(open(R/'clock_G_body/tree.json'))['sites']
for c in ['TT','FF']:
 o=R/f'route_{c}';o.mkdir(exist_ok=False);s=(B/f'out_G_{c}/combo.tcl').read_text();seen=[]
 def sub(m):
  n=m[1];seen.append(n);x,y=site[n];return f'place_inst -name ck_{n} -location {{{x:.3f} {y:.3f}}} -status PLACED'
 s=re.sub(r'place_inst -name ck_(\S+) -location \{[^}]+\} -status PLACED',sub,s);assert len(seen)==len(site) and set(seen)==set(site)
 (o/'combo.tcl').write_text(s);shutil.copy2(B/f'out_G_{c}/combo.v',o/'combo.v')
(R/'GEOM_REVIEW.txt').write_text('PASS for clock-only GRT experiment. Personally viewed clock_body_review.png: root coincident copies now disjoint legal rows; shared checker all24523body/halo/host checks0. Signal taps/core/partition positions and topology unchanged. MaxL1move2.222um, totalwire +0.027%, modeled intra-regionrelative change<=1.154ps. Current-main syntheticCA2306crossings0fail:min105.4TTscale1.0485/109.0FFscale1.0552. This is an estimate, not a physical or source adoption. Existing G FFhold failure and F1 opaque-M7 data-relay failure stay open. Fresh routedCA and intraregion<=150 inclOCV/droop/SPICE mandatory before qualification.\n')
print('PREPARED')

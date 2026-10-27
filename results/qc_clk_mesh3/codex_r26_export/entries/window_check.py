import sys,json
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-qc-export-1027/tools/die_plan')
import schema as S,die_clock as D
p=Path('/srv/opentallas-scratch2/claude/codex-qc-export-1027/native100_io/qwen_compute/candidate_guard51_native100_io.json');P=S.Plan(S.load(p),p)
win=[817.83,9629.685,826.47,9638.325];halo=[win[0]-5.4,win[1]-5.4,win[2]+5.4,win[3]+5.4];host=P.rect('coll_core')
overlap=lambda a,b:a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
inside=lambda a:host[0]<=a[0] and host[1]<=a[1] and a[2]<=host[2] and a[3]<=host[3]
r=dict(verdict='PLAN_CANDIDATE; NOT DECLARED OR PHY-CONNECTED',host='coll_core',host_rect=host,window_um=win,halo_um=halo,window_inside_host=inside(win),halo_inside_host=inside(halo),window_opaque_hits=[k[4] for k in D.keepouts(P) if overlap(win,k)],halo_opaque_hits=[k[4] for k in D.keepouts(P) if overlap(halo,k)],stack_clearance=dict(max_riser_um=2.5,stack_xy_span_um=.54,via89_halfpad_um=.64,nominal_origin_um=[821.34,9633.6],three_rows_top_um=9634.41,stack_top_um=9637.415,within_window=True),limitations='This spare geometric window is not a finished branch: actual UCIe clk M5 boundary pin and missing macro origin must replace invalid centre target; die-metal shields and PG clearance need actual full importer census.')
Path('/srv/opentallas-scratch2/claude/codex-qc-export-1027/entry_inventory6/ucie_window.json').write_text(json.dumps(r,indent=1))
print(json.dumps(r))

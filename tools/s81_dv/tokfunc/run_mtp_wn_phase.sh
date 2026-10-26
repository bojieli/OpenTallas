#!/bin/bash
# Fleet-only: phase-congruent real WN replay, using the preserved exact binary.
set -euo pipefail
: "${XSTAGE:?pinned xdie stage}"
: "${CAL_DIR:?actual corrected calendar directory}"
: "${LINKS:?source-bound link capture}"
: "${REFERENCE:?preserved one-WN rank directory}"
OUT=${OUT:-wn_phase_replay}
mkdir -p "$OUT/plans"
O=$(realpath "$OUT"); R=$(realpath "$REFERENCE")
python3 tools/s81_dv/tokfunc/mu_hop_plan.py --cal-dir "$CAL_DIR" --links "$LINKS" \
  --hops 1 --modes mtp --preserve-idle --out "$O/plans" > "$O/compile.log"
P="$O/plans/mtp_h001_R001A_R002A.json"
(cd "$XSTAGE" && python3 tools/xdie_s81_2/gen_golden.py --xl5 --reserve-mu-tag \
  --per S=1.345,N=1.345,H=1.345 --gap 100 --mu-hop-plan "$P" --out "$O/golden") > "$O/generate.log"
python3 - "$O" "$R" "$CAL_DIR" <<'PY'
from pathlib import Path
import collections,hashlib,json,sys
o,r,c=map(Path,sys.argv[1:]); h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((o/'plans/mtp_h001_R001A_R002A.json').read_text())
g=json.loads((o/'golden/golden.json').read_text())
cal=json.loads((c/'calendar_rel241_G4_mtp.json').read_text())
assert p['phase_preserved'] and p['absolute_rebase']%4==0
assert p['gap_compress']['gaps_compressed']==0
offsets={x['start']-m['T'] for x,m in zip(g['instances'],p['msgs'])}
assert len(offsets)==1 and next(iter(offsets))%4==0
msgs=sorted((m for pos in cal['position_graph']['positions'] for m in pos['links']
             if m['sender_index']==1),key=lambda m:m['send_start'])
assert [m['send_start'] for m in msgs]==[m['T'] for m in p['msgs']]
stim=[]
for line in (o/'golden/stim.hex').read_text().splitlines():
 w=int(line,16)
 if (w>>1104)&255!=2:continue
 inst=(w>>1088)&255
 deadline=g['instances'][inst]['start']+msgs[inst]['receive_complete']-msgs[inst]['send_start']
 w=(w&((1<<1144)-1))|(deadline<<1144)
 stim.append(f'{w:0294x}')
cmds=[x for x in (o/'golden/mu.hex').read_text().splitlines() if int(x[8:10],16)==2]
assert len(stim)==3840 and len(cmds)==48
oldstim=(r/'stim.hex').read_text().splitlines(); oldcmd=(r/'mu.hex').read_text().splitlines()
assert len(stim)==len(oldstim) and len(cmds)==len(oldcmd)
for a,b in zip(stim,oldstim):
 a,b=int(a,16),int(b,16)
 assert a&((1<<1112)-1)==b&((1<<1112)-1), 'payload/dp changed'
 assert ((a>>1112)&0xffffffff)-((b>>1112)&0xffffffff)==2
for a,b in zip(cmds,oldcmd):
 a,b=int(a,16),int(b,16)
 assert (a&((1<<48)-1))==(b&((1<<48)-1))
 assert (a>>48)-(b>>48)==2
(o/'stim.hex').write_text('\n'.join(stim)+'\n');(o/'mu.hex').write_text('\n'.join(cmds)+'\n')
capacity=json.loads((r/'projection.json').read_text())['capacity']
last_deadline=max(int(x,16)>>1144 for x in stim)
assert last_deadline+2000<=capacity['MAXCYC'], 'existing binary cannot cover actual deadlines and drain'
receipt=dict(grade='isolated one-rank transport component; not full token or production descriptor provenance',
 phase_quantum=4,graph_to_bench_offset=next(iter(offsets)),phase_preserved=True,
 changes_from_reference='all issue/command clocks +2; identical payload/tag words; deadlines now actual graph receive-complete bounds',
 reference=str(r),binary=str(r/'build/obj/Vtb_mtp_wn_positions'),
 binary_sha256=h(r/'build/obj/Vtb_mtp_wn_positions'),
 source_manifest=(r/'build/sources.sha256').read_text(),
 calendar_sha256=h(c/'calendar_rel241_G4_mtp.json'),graph_sha256=cal['checker']['position_graph_sha256'],
 plan_sha256=h(o/'plans/mtp_h001_R001A_R002A.json'),
 inputs_sha256={n:h(o/n) for n in ('stim.hex','mu.hex')},
 beats=len(stim),commands=len(cmds),positions=6,capacity=capacity,
 actual_required_end=last_deadline+2000,
 messages=[dict(inst=i,label=p['msgs'][i]['label'],graph_send=m['send_start'],
  issue=g['instances'][i]['start'],first_allowed=g['instances'][i]['start']+m['receive_first']-m['send_start'],
  complete_deadline=g['instances'][i]['start']+m['receive_complete']-m['send_start']) for i,m in enumerate(msgs)],
 provenance='deterministic diagnostic payloads/MU positions from existing gen_golden; real HOST/PW descriptor anchor remains unbound')
(o/'phase_projection.json').write_text(json.dumps(receipt,indent=2)+'\n')
PY
(cd "$O" && /usr/bin/time -v -o time_run.log "$R/build/obj/Vtb_mtp_wn_positions" \
  +NS=3840 +NM=48 > run.log 2>&1)
python3 - "$O" <<'PY'
from pathlib import Path
import collections,hashlib,json,re,sys
o=Path(sys.argv[1]);r=json.loads((o/'phase_projection.json').read_text());text=(o/'run.log').read_text()
rows=collections.defaultdict(list)
for line in text.splitlines():
 m=re.fullmatch(r'WN_LAND (\d+) (\d+) (\d+) (\d+) (\d+)',line)
 if m:
  inst,k,issue,land,deadline=map(int,m.groups());rows[inst].append((issue,land,deadline))
bad=[]
for m in r['messages']:
 a=rows[m['inst']]
 if len(a)!=320:bad.append(dict(inst=m['inst'],reason='inventory',got=len(a)));continue
 m.update(first_land=min(x[1] for x in a),complete=max(x[1] for x in a))
 if m['first_land']<m['first_allowed'] or m['complete']>m['complete_deadline']:
  bad.append(dict(inst=m['inst'],reason='actual receive outside graph reservation'))
 if any(x[2]!=m['complete_deadline'] for x in a):bad.append(dict(inst=m['inst'],reason='deadline provenance'))
r.update(result='PASS' if not bad and 'PASS mtp_wn_positions:' in text else 'FAIL',errors=bad,
 run_log_sha256=hashlib.sha256((o/'run.log').read_bytes()).hexdigest(),
 stats=[x for x in text.splitlines() if x.startswith('WN_STATS ')])
(o/'phase_receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['result'],r['stats'],r['errors'])
if r['result']!='PASS':sys.exit(2)
PY

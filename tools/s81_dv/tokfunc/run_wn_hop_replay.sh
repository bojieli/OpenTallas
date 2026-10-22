#!/bin/bash
# STEWARD-TOKb-RATE1 (10-21), fleet-only: replay ONE calendar LINK5 resource (all its users' messages, every MTP position,
# exact graph dates, no idle compression) on the real WN rank circuit RTL -- the same bench, sources and Verilator
# flags as Codex's WN phase2 component run (run_mtp_wn_rank.sh / run_mtp_wn_phase.sh, tb_mtp_wn_positions) -- with a
# capacity sized for the multi-user inventory.  Every beat's deadline = its own graph message's receive_complete
# (bench issue + rx_complete_age); first landings are checked against receive_first post hoc.
#   XSTAGE   source-pinned xdie stage holding the WN bench sources (rtl/test/xdie_s81_2/tb_mtp_wn_positions.sv ...)
#   SOURCES  sources.f of the reference WN rank build (byte-identical source list, paths relative to XSTAGE)
#   CAL_DIR  calendar directory (calendar_rel241_G4_{ar,mtp}.json);  LINKS  captured links json (mu_hop_plan --links-out)
#   MODE ar|mtp  HOP sender index  RES resource tag of the plan file (e.g. R001A_R002A)  OUT output dir
#   PLAN_ARGS extra mu_hop_plan args (negatives: --inject-busy U:K --inject-mode rtl --first-msgs N)
#   EXPECT PASS|FAIL (a negative must FAIL with late > 0 and otherwise clean data/tags)
set -euo pipefail
: "${XSTAGE:?}" "${SOURCES:?}" "${CAL_DIR:?}" "${LINKS:?}" "${MODE:?}" "${HOP:?}" "${RES:?}"
OUT=${OUT:-wn_hop_replay}; EXPECT=${EXPECT:-PASS}
mkdir -p "$OUT/plans"
O=$(realpath "$OUT"); XS=$(realpath "$XSTAGE")
python3 tools/s81_dv/tokfunc/mu_hop_plan.py --cal-dir "$(realpath "$CAL_DIR")" --links "$LINKS" \
  --hops "$HOP" --modes "$MODE" --preserve-idle ${PLAN_ARGS:-} --out "$O/plans" > "$O/compile.log"
P="$O/plans/$(printf '%s_h%03d_%s' "$MODE" "$HOP" "$RES").json"
test -f "$P"
(cd "$XS" && python3 tools/xdie_s81_2/gen_golden.py --xl5 --reserve-mu-tag \
  --per S=1.345,N=1.345,H=1.345 --gap 100 --mu-hop-plan "$P" --out "$O/golden") > "$O/generate.log"
python3 - "$O" "$P" <<'PY'
from pathlib import Path
import hashlib,json,sys
o,pp=Path(sys.argv[1]),Path(sys.argv[2]); h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads(pp.read_text()); g=json.loads((o/'golden/golden.json').read_text())
assert p['phase_preserved'] and p['absolute_rebase']%4==0 and p['gap_compress']['gaps_compressed']==0
assert len(g['instances'])==len(p['msgs'])<=255
offsets={x['start']-m['T'] for x,m in zip(g['instances'],p['msgs'])}
assert len(offsets)==1 and next(iter(offsets))%4==0, offsets
stim=[]
for line in (o/'golden/stim.hex').read_text().splitlines():
    w=int(line,16)
    if (w>>1104)&255!=2: continue                       # rank 0 WN port (dp 2): one real A/B circuit
    inst=(w>>1088)&255
    dl=g['instances'][inst]['start']+p['msgs'][inst]['rx_complete_age']
    stim.append(f'{(w&((1<<1144)-1))|(dl<<1144):0294x}')
cmds=[x for x in (o/'golden/mu.hex').read_text().splitlines() if int(x[8:10],16)==2]
assert len(stim)==320*len(p['msgs']) and len(cmds)==4*len(p['msgs'])
(o/'stim.hex').write_text('\n'.join(stim)+'\n'); (o/'mu.hex').write_text('\n'.join(cmds)+'\n')
last_dl=max(int(x,16)>>1144 for x in stim)
cap=dict(NSMAX=len(stim)+1,NMMAX=len(cmds)+1,QD=len(stim)+1,MAXCYC=last_dl+2000)
rec=dict(grade='real WN rank A/B circuit RTL (4 lanes, PHY/relay/landing legs); exact calendar LINK5 resource schedule; '
               'deterministic diagnostic payloads; not whole stage / token',
         plan=str(pp),plan_sha256=h(pp),graph=p['graph'],mode=p['mode'],hop=p['hop'],resource=p['resource'],
         users=p['users'],users_shift=p['users_shift'],period=p['period'],overlaps_in_plan=p['overlaps'],
         negative=p['negative'],same_user_adjacent=p['same_user_adjacent'],phase_quantum=4,
         graph_to_bench_offset=next(iter(offsets)),beats=len(stim),commands=len(cmds),capacity=cap,
         inputs_sha256={n:h(o/n) for n in ('stim.hex','mu.hex')},
         messages=[dict(inst=i,user=m['user'],position=m['position'],label=m['label'],graph_send=m['T'],
                        claimed_send=m.get('claimed_T',m['T']),issue=g['instances'][i]['start'],
                        first_allowed=g['instances'][i]['start']+m['rx_first_age'],
                        complete_deadline=g['instances'][i]['start']+m['rx_complete_age'])
                   for i,m in enumerate(p['msgs'])])
(o/'projection.json').write_text(json.dumps(rec,indent=1)+'\n')
print(cap['NSMAX'],cap['NMMAX'],cap['QD'],cap['MAXCYC'],file=open(o/'cap.txt','w'))
PY
read -r NS NM QD MC < "$O/cap.txt"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p "$O/build"
(cd "$XS" && sha256sum $(cat "$SOURCES") > "$O/build/sources.sha256"
 /usr/bin/time -v -o "$O/build/time.log" "$V" --binary --timing -O1 -Wno-fatal \
  -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
  +incdir+rtl/dsrom_sys/s81_link +define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 \
  --top-module tb_mtp_wn_positions -Mdir "$O/build/obj" -f "$(realpath "$SOURCES")" \
  -GNSMAX="$NS" -GNMMAX="$NM" -GQD="$QD" -GMAXCYC="$MC" -GD_ST=258 \
  --build-jobs ${JOBS:-8} -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0') > "$O/build/build.log" 2>&1
"$V" --version > "$O/build/verilator_version.txt"
set +e
(cd "$O" && /usr/bin/time -v -o time_run.log build/obj/Vtb_mtp_wn_positions +NS=$((NS-1)) +NM=$((NM-1)) > run.log 2>&1)
echo $? > "$O/run_exit"
set -e
python3 - "$O" "$EXPECT" <<'PY'
from pathlib import Path
import collections,hashlib,json,re,sys
o,expect=Path(sys.argv[1]),sys.argv[2]; r=json.loads((o/'projection.json').read_text()); text=(o/'run.log').read_text()
rows=collections.defaultdict(list)
for line in text.splitlines():
    m=re.fullmatch(r'WN_LAND (\d+) (\d+) (\d+) (\d+) (\d+)',line)
    if m:
        inst,k,issue,land,dl=map(int,m.groups()); rows[inst].append((issue,land,dl))
st=re.findall(r'^WN_STATS beats (\d+) landed (\d+) mismatch (\d+) extra (\d+) late (\d+) tags (\d+)/(\d+) tagbad (\d+) '
              r'fault ([01]+) live ([01]+) minage (\d+) maxage (\d+) last_cycle (\d+)$',text,re.M)
bad,late_msgs=[],[]
for m in r['messages']:
    a=rows[m['inst']]
    if len(a)!=320: bad.append(dict(inst=m['inst'],reason='inventory',got=len(a))); continue
    m.update(first_land=min(x[1] for x in a),complete=max(x[1] for x in a),age=max(x[1] for x in a)-m['issue'])
    if m['first_land']<m['first_allowed']: bad.append(dict(inst=m['inst'],reason='landed before receive_first'))
    if m['complete']>m['complete_deadline']: late_msgs.append(m['inst'])
    if any(x[2]!=m['complete_deadline'] for x in a): bad.append(dict(inst=m['inst'],reason='deadline provenance'))
    if m['issue']-m['graph_send']!=r['graph_to_bench_offset']: bad.append(dict(inst=m['inst'],reason='clock offset'))
s=st[0] if len(st)==1 else None
clean=s is not None and tuple(map(int,s[:4]))==(int(s[0]),int(s[0]),0,0) and s[5]==s[6] and s[7]=='0' and s[8]=='0' and s[9]=='1111'
late=int(s[4]) if s else -1
rtl_pass='PASS mtp_wn_positions:' in text
if expect=='PASS':
    verdict='PASS' if rtl_pass and clean and late==0 and not bad and not late_msgs else 'FAIL'
else:   # negative: the moved message must miss its claimed deadline on the real circuit, everything else clean
    neg=r['negative'] or {}
    want=[i for i,m in enumerate(r['messages']) if m['claimed_send']!=m['graph_send']]
    verdict=('FAULT_AS_EXPECTED' if (not rtl_pass) and clean and late>0 and late_msgs and set(want)<=set(late_msgs)
             and neg.get('result')=='FAULT' and not bad else 'NEGATIVE_NOT_DETECTED')
r.update(result=verdict,errors=bad,late_messages=late_msgs,run_exit=int((o/'run_exit').read_text()),
         stats=[x for x in text.splitlines() if x.startswith('WN_STATS ')],
         last_cycle=int(s[-1]) if s else None,age_min=min((m.get('age',10**9) for m in r['messages'])),
         age_max=max((m.get('age',0) for m in r['messages'])),
         binary_sha256=hashlib.sha256((o/'build/obj/Vtb_mtp_wn_positions').read_bytes()).hexdigest(),
         sources_sha256=hashlib.sha256((o/'build/sources.sha256').read_bytes()).hexdigest(),
         run_log_sha256=hashlib.sha256((o/'run.log').read_bytes()).hexdigest(),
         verilator=(o/'build/verilator_version.txt').read_text().strip())
(o/'receipt.json').write_text(json.dumps(r,indent=1)+'\n')
print(verdict,r['stats'],'late_msgs',late_msgs,'errors',bad[:3])
sys.exit(0 if verdict in ('PASS','FAULT_AS_EXPECTED') else 2)
PY

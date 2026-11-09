#!/bin/bash
# TYPE-SAFE-3 QC rebase on plan_qc53v4w_ctlmfq: event -> bind -> R8 re-derive -> strict bind -> miter (--r8)
set -u
Q=/srv/opentallas-scratch2/claude/type-safe-3b/qcw
D=/srv/opentallas-scratch2/claude/qct10/ctlm
T=/srv/opentallas-scratch3/claude/type-safe-3b/qc/tools/die_plan
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
cd $Q
R=$(readlink -f $D/src_ctlmfq); test ! -L "$R"
[ -d src ] || cp -al "$R" src
find src -type d -exec chmod u+w {} +
mkdir -p plan/gen_lat
[ -e plan/cores ] || cp -al $(readlink -f $D/plan/cores) plan/cores
[ -e plan/macro_pins ] || cp -a /srv/opentallas-scratch3/claude/type-safe-3b/qc/plan/macro_pins plan/macro_pins
python3 -I - <<P
import json,os
D='$D'; Q='$Q'
d=json.load(open(f'{D}/plan/plan_qc53v4w_ctlmfq.json'))
b=open(f'{Q}/bound.tsv','w');n=0;miss=[]
for t,v in d['partition_types'].items():
    m=v.get('module',t)
    for cand in (f"{D}/bind_ctlmfq/rtl/{m}.sv",f"{D}/bind_ctlmfq/rtl/{m}__{t}.sv",f"{D}/bind_ctlmfq/rtl/{t}.sv"):
        if os.path.exists(cand):
            b.write(f'{t}\t{cand}\n');n+=1;break
    else: miss.append(t)
print('bound',n,'of',len(d['partition_types']),'miss',miss[:6])
a=json.load(open(f'{D}/src_ctlmfq/$RT/asbuilt_reach.json'))
open(f'{Q}/native.txt','w').write(','.join(a.get('internal_stations_types',[])))
print('native',len(a.get('internal_stations_types',[])))
P
python3 -I -B $T/ts_relay_event.py $D/plan/plan_qc53v4w_ctlmfq.json $Q/plan/plan_w_ts3.json $Q/event.json --pins-root $Q/plan --regen-latency --min-stations 's[lw][ew]_su_l[01].*:x_su_c_p1_i=3' --bound-list $Q/bound.tsv --skip-types coll_ftn --native-types "$(cat $Q/native.txt)" 2>&1 | tail -n 3 | cut -c1-400
echo EVENT rc=${PIPESTATUS[0]}
python3 -I -c "
import json
e=json.load(open('$Q/event.json'));print(e['base_plan_sha256'][:12],e['plan_output_sha256'][:12],e['totals'])"
cat > bind_once.sh <<B
#!/bin/bash
set -u
cd $Q
python3 -I - <<P2
import json
d=json.load(open("src/$RT/asbuilt_reach.json"));e=json.load(open("event.json"))
d["internal_stations_types"]=sorted(set(d.get("internal_stations_types") or [])|set(e["native_out_types"]))
d["land_r8"]="$RT/r8_ts3.json"
open("src/$RT/asbuilt_w_ts3.json.tmp","w").write(json.dumps(d,indent=1))
P2
mv -f src/$RT/asbuilt_w_ts3.json.tmp src/$RT/asbuilt_w_ts3.json
mkdir -p bind_new
for f in asbuilt.json asbuilt_sources.json asbuilt_lib_stubs.sv asbuilt.ys provenance_elab.json asbuilt.yosys.log die_r56.v bind_elab_keep.sv; do [ -e bind_new/\$f ] || ln $D/bind_ctlmfq/\$f bind_new/\$f; done
cd src
python3 -I -B tools/die_plan/bind.py bind ../plan/plan_w_ts3.json --out ../bind_new --strict --all-gaps --asbuilt $RT/asbuilt_w_ts3.json > ../bind_new.log 2>&1
echo BIND rc=\$?
tail -n 3 ../bind_new.log | cut -c1-300
B
rm -f src/$RT/r8_ts3.json; cp src/$RT/r8_reach.json src/$RT/r8_ts3.json
bash bind_once.sh > pass1.out 2>&1; cat pass1.out | cut -c1-300
grep -c R8_STALE bind_new.log
mkdir -p r8; (cd src; python3 -I -B tools/die_plan/r8.py pads ../plan/plan_w_ts3.json ../bind_new/bus_groups.json --out $Q/r8 > $Q/r8/pads.log 2>&1; echo PADS rc=$?)
tail -n 2 r8/pads.log | cut -c1-300
rm -f src/$RT/r8_ts3.json; cp r8/qwen_compute_r8_landing.json src/$RT/r8_ts3.json
python3 -I r8x.py $RT 2>&1 | cut -c1-1100
mv bind_new bind_p1; mv bind_new.log bind_p1.log
bash bind_once.sh > pass2.out 2>&1; cat pass2.out | cut -c1-300
python3 -I -B ts_relay_miter_tip.py plan/plan_w_ts3.json event.json $D/bind_ctlmfq/rtl bind_new/rtl miter.json --r8 r8_extra.json > miter.out 2>&1; echo MITER rc=$?
python3 -I -c "
import json
m=json.load(open('$Q/miter.json'));print({k:(v if not isinstance(v,(list,dict)) else len(v)) for k,v in m.items()});print([x[:200] for x in m['undeclared_changes'][:8]])"

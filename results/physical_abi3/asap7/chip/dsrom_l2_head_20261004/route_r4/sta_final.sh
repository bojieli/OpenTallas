#!/bin/bash
# usage: sta_final.sh ROUTEDIR  -- post-route SS setup per endpoint (reg-to-reg, ICG enable listed separately)
R=$(cd $1 && pwd); B=$(ls -d $R/work/orfs/results/asap7/*/base); M=$HOME/dsrom-l2head-20261004/r4/src/physical/asap7_memory_macros/ot_rom_4096x274_m8
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
cat > $R/sta_final.tcl <<TCL
foreach f {asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_DFFHQNH2V2X_RVT_SS_nldm_FAKE.lib asap7sc7p5t_DFFHQNV2X_RVT_SS_nldm_FAKE.lib} { read_liberty $L/\$f }
read_liberty /m/ot_rom_4096x274_m8_ss.lib
read_db /b/6_final.odb
read_spef /b/6_final.spef
read_sdc /b/6_final.sdc
puts "OTC wns [sta::worst_slack_cmd max]"
report_checks -path_delay max -group_path_count 100000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /r/sta_ends.rpt
TCL
docker run --rm -v $B:/b:ro -v $M:/m:ro -v $R:/r -w /r openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /r/sta_final.tcl > /r/sta_final.log 2>&1; chmod a+rw /r/sta_*"
python3 - $R <<'PY'
import re,sys,json
r=sys.argv[1]; ends=open(r+"/sta_ends.rpt").read(); st={}
for m in re.finditer(r"^(\S+)\s+\(\S+\)\s+[-0-9.]+\s+[-0-9.]+\s+([-0-9.]+)", ends, re.M):
    n=re.sub(r"\[\d+\]","",m.group(1)).split("$")[0].rsplit("/",1)[0]; st[n]=min(st.get(n,1e9),float(m.group(2)))
items=sorted(st.items(), key=lambda kv: kv[1])
icg=[kv for kv in items if "u_icg" in kv[0]]; reg=[kv for kv in items if "u_icg" not in kv[0]]
neg=sum(1 for m in re.finditer(r"\s(-[0-9.]+) \(VIOLATED\)", ends))
out=dict(wns_all_ps=items[0][1] if items else None, icg_enable_ps=icg[0][1] if icg else None,
         wns_reg2reg_ps=reg[0][1] if reg else None, violating_endpoints=neg, worst_by_stage_ps=dict(reg[:30]))
json.dump(out, open(r+"/sta_final.json","w"), indent=1); print(json.dumps(out)[:1500])
PY

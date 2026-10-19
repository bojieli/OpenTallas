from pathlib import Path
import json,subprocess,hashlib,datetime
cid="a74679d0aba72cc0b8eac92abfc576d0f9f47f555cdd7eac10d041074cb47866"
r=Path("/srv/opentallas-scratch/claude/ref_gate/dscoll_lane_w_ltr-20261019-075813")
c=json.loads(subprocess.check_output(["docker","inspect",cid],text=True))[0]
assert c["Id"]==cid and c["Name"]=="/gate_grt_dscoll_lane_w_ltr-20261019-075813" and c["State"]["Running"]
assert any(m["Source"]==str(r/"src") and m["Destination"]=="/src" and not m["RW"]for m in c["Mounts"])
assert any(m["Source"]==str(r/"routes/gate/work/orfs") and m["Destination"]=="/work"for m in c["Mounts"])
expected={'physical/ref_tile/dscoll_lane_w_ltr/spec.json': '41a5e1a17602c3e5e01de2c767fb7acaac8da250f8c05d24e9123a9f054d0b95', 'rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv': 'b7576ac90d28435b1232bd24c477bcd96367aeaefe73846a109618ff90e38ffe', 'rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv': '93e76d1463224171114cc244caccd866ce012416fc6083db453c06e380c94086', 'rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv': '1826102edf211742df583b4aa6a229c6ce410b30508a76e4f061fc2efcdadb9c'}
checks={p:{"expected":h,"actual":hashlib.sha256((r/"src"/p).read_bytes()).hexdigest()}for p,h in expected.items()}
assert all(x["expected"]==x["actual"]for x in checks.values())
ld=list((r/"routes/gate/work/orfs/logs/asap7").glob("*/base"))[0];failure=(ld/"4_1_cts.log").read_text();assert "OT_SPINE: no legal site near 471006 257310"in failure
assert not list((r/"routes/gate/work/orfs/results/asap7").glob("*/base/4_1_cts.odb"))
top=subprocess.check_output(["docker","top",cid,"-eo","pid,ppid,etime,pcpu,args"],text=True);assert "do-4_1_cts"in top
print(json.dumps({"verified_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"container":cid,"name":c["Name"],"source_start_commit":"c531449dfa4bf1fc9be9baefe2f06c729dad632f","source_checks":checks,"original_failure_tail":failure.splitlines()[-3:],"repeat_processes":top,"authorization":"ROOT via s81_coordinator: stop ONLY legacyW717394 exactcontainer after preserving receipt; P1W/E untouched","validated":True},indent=2))

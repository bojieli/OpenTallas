"""Read-only selected-die fault wiring extraction; run against frozen GEN7."""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

path=Path(sys.argv[1])
blob=path.read_bytes()
assert hashlib.sha256(blob).hexdigest()=="18464a8b31042bea03b3fc5779d42803ab7b05bebbaab733a4d83d4a714c1ea6"
receipt_path=path.parent.parent/"source_verified.json"
receipt_blob=receipt_path.read_bytes()
receipt=json.loads(receipt_blob)
assert receipt["status"]=="PASS" and receipt["actual_git_commit"]=="4db0974030714ac3f3745ccadd6c0a234dfeb3c4"
binding=json.loads((path.parent/"port_bind_v2.json").read_text())
for master in ("qkd_kvs_pc","qkd_kvs_pc_h","qkd_kvs_grp","qkd_kvs_grp_h"):
    assert binding["masters"][master]["rtl"]=="rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv"
instances=[]
for line in blob.decode().splitlines():
    m=re.fullmatch(r"\s*(\w+)\s+(\w+)\s*\((.*)\);\s*",line)
    if not m:
        continue
    ports=dict(re.findall(r"\.(\w+)\((.*?)\)(?=,\s*\.|$)",m[3]))
    instances.append(dict(master=m[1],instance=m[2],ports=ports))
pcs=[i for i in instances if i["master"] in ("qkd_kvs_pc","qkd_kvs_pc_h")]
assert len(pcs)==128
groups=[i for i in instances if i["master"] in ("qkd_kvs_grp","qkd_kvs_grp_h")]
assert len(groups)==32
relays=[i for i in instances if i["master"]=="qkd_rlys_36"]
result=[]
for pc in pcs:
    net=re.fullmatch(r"(\w+)\[304:0\]",pc["ports"]["o_grp"])[1]
    matching=[r for r in relays if net+"[304:296]" in r["ports"].get("a","")]
    assert len(matching)==1
    relay=matching[0]
    target=re.search(r"(\w+)\[304:296\]",relay["ports"]["b"])[1]
    sinks=[(g,p) for g in groups for p,x in g["ports"].items()
           if p in ("i_pc0","i_pc1","i_pc2","i_pc3") and x==target+"[304:0]"]
    assert len(sinks)==1
    group,group_port=sinks[0]
    assert pc["ports"]["ck"]==relay["ports"]["ck"]==group["ports"]["ck"]
    result.append(dict(instance=pc["instance"],master=pc["master"],
        clock=pc["ports"]["ck"],reset=pc["ports"]["rst_n"],
        pc_group_output=pc["ports"]["o_grp"],candidate_core_fault_bit=301,
        relay=relay["instance"],relay_master=relay["master"],relay_data_bit=5,
        relay_output_net=target,group=group["instance"],group_master=group["master"],
        group_input=group_port,group_reset=group["ports"]["rst_n"],
        group_fault_output=group["ports"]["o_ctl"],group_fault_bit=17,
        host_STATUS_and_retirement_path_complete=False))
print(json.dumps(dict(schema="opentallas.pc.selected_fault_model.v1",die=str(path),
    sha256=hashlib.sha256(blob).hexdigest(),source_bytes=len(blob),
    source_receipt=receipt,source_receipt_sha256=hashlib.sha256(receipt_blob).hexdigest(),
    counts=dict(collections.Counter(i["master"] for i in pcs)),groups=len(groups),
    core_clock_match=True,instances=result,
    inventory_357_membership_reconciled=False,new_unique_health_source_total=None,
    note="128 selected PC objects; source fault omission proved separately, no new source or timing qualification"),indent=2))

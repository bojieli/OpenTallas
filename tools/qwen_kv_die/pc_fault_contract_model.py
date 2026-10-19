"""Bind selected GEN7 source equations to the read-only 128-PC wiring trace."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

repo=Path(__file__).resolve().parents[2]
assert subprocess.check_output(["git","-C",str(repo),"rev-parse","--show-toplevel"],text=True).strip()==str(repo)
out=repo/"results/arch/kv_pc_safe_model_1019"
trace=json.loads((out/"selected_fault_trace.json").read_text())
commit="4db0974030714ac3f3745ccadd6c0a234dfeb3c4"
sources={}
def source(path):
    data=subprocess.check_output(["git","-C",str(repo),"show",commit+":"+path])
    sources[path]=hashlib.sha256(data).hexdigest()
    return re.sub(r"//[^\n]*","",data.decode())
def module(text,name):
    return re.search(r"module\s+"+name+r"\b.*?endmodule",text,re.S)[0]
tile_path="rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv"
tiles=source(tile_path)
for name in ("qkd_kvs_pc","qkd_kvs_pc_h"):
    text=module(tiles,name)
    for fault in ("chain_fault","es_merge_fault"):
        assert len(re.findall(r"\bw_pc__"+fault+r"\b",text))==2
        assert "."+fault+"(w_pc__"+fault+")" in text
    fields=re.search(r"assign o_grp\s*=\s*\{(.*?)\};",text,re.S)[1].split(",")
    widths={"w_pc__actual_data":256,"w_pc__actual_epoch":16,
            "w_pc__actual_layer":6,"w_pc__actual_sector":10}
    offset=0
    for field in reversed(fields):
        field=field.strip()
        if field=="w_pc__return_fault_core":
            assert offset==301
        offset+=widths.get(field,1)
    assert offset==305
for name in ("qkd_kvs_grp","qkd_kvs_grp_h"):
    text=module(tiles,name)
    for pc in range(4):
        assert re.search(r"drain__ring_fault_core__\d\s*=\s*i_pc"+str(pc)+r"\[301:301\]",text)
    assert ".ring_fault_core({drain__ring_fault_core__0," in text
    assert "{w_drain__fault, w_drain__drained," in text
chain=source("rtl/qwen_sys/static_embedding_20261014/qkd_kv_pc_chain_station_b.sv")
assert set(re.findall(r"land_er\[(\d+)\]",chain))=={"0","259","260"}
assert "|| bfault ||" in chain
assert set(re.findall(r"\bfault\s*<=\s*(.*?);",chain))=={"1'b0","1'b1"}
assert "always @(posedge ck) rs_q <= rst_n;" in chain
return_path=source("rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv")
assert "always @(posedge ck)fault_core<=rs_a && (fault_core_s || fault_core_set);" in return_path
guard=module(source("rtl/qwen_sys/static_kv_20261014/qkd_static_kv_ownership.sv"),"qkd_static_kv_drain_guard4")
assert "fault_core_q <= {ctrl_fault_core, ctrl_completion_fault_core, ctrl_intake_fault_core, ring_fault_core};" in guard
assert "if (MUT != 2 && ((|fault_sync) || (|fault_core_q) || upstream_fault_q)) fault <= 1;" in guard
relay=source("rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv")
assert "always @(posedge ck)" in relay and "r <= a;" in relay
model=dict(status="MODEL_ONLY_ROOT_REVIEW_REQUIRED",selected_commit=commit,
    selected_die_sha256=trace["sha256"],source_sha256=sources,
    actual_PC_instances=128,pc=124,pc_h=4,
    selected_source_omits_chain_fault=True,selected_source_omits_es_merge_fault=True,
    proposed_scope="chain_fault only; es_merge_fault separately requires complete child fault/reset lifetime proof",
    source_domain="ck",source_reset="rsi -> rs_q single local capture; source fault asynchronously clears low rs_q",
    proposed_pin_D_equation="fault_core <= rs_a && (fault_core_s || fault_core_set || chain_fault)",
    existing_pin_FF="u_pc.u_pce.u_path.u_return.fault_core",
    selected_pin="o_grp[301]",prototype_split_pin="o_grp[293]",
    same_domain_sticky_OR_only=True,health_readiness_idle_OR_permitted=False,
    physical_pin_owner_and_face_requalification_required=True,
    source_fault_Q_to_export_delay_core_edges=1,
    existing_return_fault_export_additional_edges=0,
    arithmetic_or_HBM_calendar_additional_edges=0,
    additional_pipeline_registers_for_aggregation=0,
    formerly_dead_chain_state_to_restore=dict(ler_v=1,ler_cr=1,ler_f=1,bo=3,bfault=1,fault=1),
    restored_state_FF_lower_bound_per_PC=8,restored_state_FF_lower_bound_total=128*8,
    complete_extra_comb_area_um2=None,complete_reset_and_upstream_copy_cost=None,
    edge_ledger=["E0 land_er bad captured by ler", "E1 bfault set", "E2 chain fault set",
        "E3 existing registered return fault pin exports chain cause", "E4 selected qkd_rlys_36 bit5",
        "E5 group drain fault_core_q capture", "E6 group drain sticky fault, o_ctl[17]"],
    downstream_host_STATUS_retirement_future_admission_delay=None,
    inherited_relay_arbitrary_initialization_and_reset_epoch_proof_required=True,
    unique_chain_cause_producers=128,additional_es_merge_cause_producers_pending=128,
    original_357_inventory_membership_reconciled=False,new_inventory_total=None,
    not_authorized=["RTL change", "gate", "same-slot OR across HBM clocks", "fault visibility assumed instantaneous",
        "literal output or dead input waiver", "485-source headline before set-union reconciliation"])
(out/"fault_contract_model.json").write_text(json.dumps(model,indent=2)+"\n")
print("SELECTED_FAULT_SOURCE_MODEL_PASS 128 PCs, source omission and current core field301 consumer bound; MODEL ONLY")

#!/usr/bin/env python3
"""HBM-CONS-2/KSH d44v part 56 packaging (after mk_split.py + package.py): tile recipes, reset contract modules, pin-cycle rows, compiler pending row,
event record, README line, SHA256SUMS.   fin_p56.py REPO RTL_COMMIT"""
import gzip, hashlib, json, sys
from pathlib import Path
R, RC = Path(sys.argv[1]), sys.argv[2]
D = R / "physical/die_plan/hbm/plan_of_record/d44v"
CORE, M0, M1 = "ot_hbm_svc_vm_kshare_splitstrap__v8e478a", "ot_hbm_svc_vmks_t0", "ot_hbm_svc_vmks_t1"
LAT = "corelat/cycles_kshare_v8_1106.tsv"
Q = "results/die_hbm_1104/reform_b/split_p56"
S_ = "rtl/hbm_accel/loader/service_native/"
sha = lambda b: hashlib.sha256(b).hexdigest()
rp = R / "physical/die_plan/hbm_arch_cores/recipes_b2.json"
REC = json.loads(rp.read_text()); assert M0 not in REC and M1 not in REC
FILES = [S_ + f for f in ("ot_hbm_svc_vmks_forms.sv", "ot_hbm_svc_async_fifo.sv", "ot_hbm_svc_pc_ctrl_leaf.sv", "ot_hbm_svc_ring_h9b_ff.sv")] + ["rtl/lib/ot_reset_sync.sv"]
for m, what in ((M0, "window control + lanes 0,1"), (M1, "lanes 2,3")):
    REC[m] = dict(top=m, files=FILES, defines=[], params={}, macros=[], source_commit=RC, read_at_commit=True, util=0.40,
                  source=f"HBM-CONS-2/KSH d44v part 56: {what} of {CORE}; bench {S_}run_vmks_forms_bench.sh; glue {Q}")
rp.write_text(json.dumps(REC, indent=1 if rp.read_text().startswith("{\n \"") else 2) + "\n")
cp = R / "physical/die_plan/hbm/reset_contract.json"
C = json.loads(cp.read_text()); C["modules"] = sorted(set(C["modules"]) | {M0, M1}); cp.write_text(json.dumps(C, indent=1) + "\n")
(D / LAT).write_text("core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote\n"
    + f"{CORE}\t\tfill_v,fill_bank,fill_slot,fill_epoch,fill_data\tport\t1\tpart 56 fill stage ahead of the fill CDC FIFO (COORD 11-04 15:36 fill_* +1); one-way, no credit\n"
    + f"{CORE}\t\twbw_v,wbw_base,wbw_total\tport\t1\tpart 56 two-stage lane count; valid and data move together; one-way, lanes wait on w_k_rdy\n"
    + f"{CORE}\tu_t1\tlanes 2,3 window start / norm\tseam\t2\tpart 56 seam, +1 out +1 in face flops: window start of lanes 2,3 +2 hbm edges, far norm +2 at control; variable latency (window start already waits on lane drain), not a pin contract\n"
    + f"{CORE}\t\tall other ports\tport\t0\tsame order and content per lane and class on the trace bench\n")
pc = D / "compiler_core_delta.json"
if pc.exists():
    P = json.loads(pc.read_text())
    P["pending_not_folded"]["HBM-CONS-2/KSH kshare v8 (part 56)"] = (f"{CORE} fill_* +1 and wbw_* +1 ({LAT}): VM read result and WB window start 1 stream edge later; "
        "fold at the next ext_census regen (TOK lane). Owner 12.21 tok/s loss from closure fixes accepted")
    pc.write_text(json.dumps(P, indent=1) + "\n")
ev = json.loads((D / "split_event.json").read_text())
base_ev = sys.argv[3] if len(sys.argv) > 3 else None
(D / "part56_event.json").write_text(json.dumps(dict(ev, schema="opentallas.hbm_plan_event.part56", by="HBM-CONS-2/KSH 11-06, COORD ruling 22:01 (5)", rtl_commit=RC,
    pin_cycles=LAT, replay=f"{Q}/replay_p56.sh",
    proof=f"{S_}run_vmks_forms_bench.sh: lock-step vs master (one tile) and per-lane per-class trace vs master (two tiles + seam model), mutants FAIL. No yosys equivalence: the seam changes cycles"), indent=1) + "\n")
if base_ev and Path(base_ev).exists():
    (D / "split_event.json").write_bytes(Path(base_ev).read_bytes())
else:
    (D / "split_event.json").unlink()
rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 56 (HBM-CONS-2/KSH, COORD 11-06 22:01 (5), plan owner DIE-HBM-83 to approve): ot_hbm_svc_vm_kshare_splitstrap__v8e478a (2 instances, "
              "q_hub_nw/q_hub_ne u_vmks_Q1, slot 445.824x506.304 kept) -> ot_hbm_svc_vmks_t0 221.184x506.304 (control + lanes 0,1) + ot_hbm_svc_vmks_t1 212.544x506.304 (lanes 2,3); "
              "seam 118 bits, registered faces; PIN CYCLES fill_* +1, wbw_* +1 (corelat/cycles_kshare_v8_1106.tsv); pins of lanes 2,3 on the slot W face move to t1 N/S; part56_event.json.\n")
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
cur = {}
for f in list(D.glob("*")) + list(D.glob("cores/*")) + list(D.glob("corelat/*")):
    if f.is_file() and f.name not in ("SHA256SUMS", "README.md"):
        b = f.read_bytes(); cur[str(f.relative_to(D)).removesuffix(".gz")] = sha(gzip.decompress(b) if f.name.endswith(".gz") else b)
names = {n for _, n in L}; ch = 0
for i, (a, n) in enumerate(L):
    if n in cur and cur[n] != a: L[i] = [cur[n], n]; ch += 1
add = sorted(n for n in cur if n not in names and (n.startswith("cores/ot_hbm_svc_vmks_") or n in ("part56_event.json", LAT)))
L += [[cur[n], n] for n in add]
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS changed", ch, "added", add)

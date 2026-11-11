import sys, json
from collections import defaultdict
from types import SimpleNamespace as NS
W = sys.argv[1]
sys.path.insert(0, W + "/physical/die_plan/hbm/bind"); sys.path.insert(0, W + "/tools/die_plan")
import hbm_param_regen as H
import core_pin_cycles as CPC
TSV = "physical/die_plan/hbm/plan_of_record/d44v/corelat/cycles_vecd4ae_rd1_1111.tsv"
BANK = "hfd_vms_bank_native_q0_faces"
cells, sinks = [], {}
def cell(path, module, **params):
    cells.append(NS(path=path, module=module, params={k: str(v) for k, v in params.items()})); return len(cells) - 1
def wire(src, sport, dst, dport, n=1):
    for i in range(n):
        sinks[(dst, dport, i)] = ("x", "p", src, sport, i, 0, "p")
banks = {}
for q in ("NW", "NE", "SW", "SE"):
    for b in range(8):
        banks[q, b] = cell(f"vmb_{q}{b}", BANK)
for q in ("NW", "NE"):
    for k in range(4):
        t = cell(f"su_{q}{k}.g_tap_r8b.u_tap", "ot_hbm_vm_lg_pair_tap", READ_RETURN=25, WRITE_RETURN=22)
        wire(banks[q, 2 * k], "rr0", t, "near_rr", 3); wire(banks[q, 2 * k], "wq_done0", t, "near_w_done")
ctl = cell("hb_idx__ctl", "ot_hbm_idx_rootctl_static_am", VM_RT=75, CR_RT=36)
for b in range(8):
    wire(banks["SW", b], "rr4", ctl, "vm_rr", 2)
hub = cell("hb_vms_SW", "hfd_hgi_vms_glue_sw_t")
for b in range(8):
    wire(banks["SW", b], "pr", hub, f"b{b}_pr", 2); wire(banks["SW", b], "status", hub, "bank_status", 1)
dbk = cell("hb_dbk_NE", "ot_hgi_dma_back_static_vp4_banks_cp", RR_RT=80); wire(banks["NE", 0], "rr1", dbk, "rr", 2)
xl = cell("xl_NE_ctl", "ot_hgi_sm_xload_cl2_ctlx", RD_LAT=3327107059280522282); wire(banks["NE", 1], "rr2", xl, "rr", 2)
opne = cell("hb_idx__op_NE", "ot_hbm_idx_vm_query_static_n12", VM_RT_EXTRA=171); wire(banks["NE", 2], "rr4", opne, "vm_rr")
nwsh = cell("hb_idx__nwsh", "ot_hbm_idx_vm_share2_static_r", BANK_RT=54); wire(banks["NW", 3], "rr3", nwsh, "vm_rr")
opnw = cell("hb_idx__op_NW", "ot_hbm_idx_vm_query_static_n12", VM_RT_EXTRA=173); wire(nwsh, "a_rr", opnw, "vm_rr")
cut = sys.argv[2] == "cut"
if cut:
    cr = cell("hcollrs_NE", "ot_hbm_idx_vm_share2_static_r", BANK_RT=7); wire(banks["NE", 4], "rr3", cr, "vm_rr")
    cc = cell("hb_coll_NE.__cut_vm", "hb_coll_NE__cut_vm"); wire(cr, "a_rr", cc, "vmasm_rd_il")
ab = {"core_pin_cycles": [dict(tsv=TSV, core="hnx_vms_bank_q0_faces__vecd4ae", module=BANK)]} if sys.argv[2] != "off" else {}
ctx = NS(F=NS(cells=cells), sinks=sinks, ab=ab, base=W)
rules = CPC.load(ab, W)
px, clients = H.pin_cycles(ctx, rules) if rules else ({}, {})
xr = H.pin_plan(ctx, px, clients, defaultdict(dict))[0] if px else {}
L = lambda sels: {2}
legs = defaultdict(list)
params, rec, err = H.derive(L, legs, {"read_k": 3, "write_k": 3}, xr)
if px:
    params = defaultdict(dict, params)
    _, rows, prec, perr = H.pin_plan(ctx, px, clients, params); err += perr
    rec["core_pin_regen"] = rows
pick = ["su_NE0.g_tap_r8b.u_tap", "sfu_NE0", "hc_NE0", "hc_NE.u_q", "hb_idx__ctl", "hb_idx__op_SW", "hb_dbk_NE", "xl_NE_ctl",
        "hb_idx__op_NE", "hb_idx__nwsh", "hb_idx__op_NW"]
print("MODE", sys.argv[2], "xr", xr)
for p in pick:
    print(" ", p, dict(params.get(p, {})))
print("  check", rec["check"]["hb_argmax"]["VMX"], rec["check"]["hb_argmax"]["ACK"], "bridge", rec["variant_values"].get("sfucore_NE.__cut_ctl"))
for e in err:
    print("  ERROR", e)

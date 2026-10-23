"""SQC-CB8 10-22: per-cluster names of the CB16 physical chain (qc_kit diag -> qc_fullm_kit -> fullm_* -> ring_tile_place_b
-> qc_ring_parent(_kit) -> sqc_rg_finish).  OT_QC_CLUSTER selects the cluster:
  b16 (default): qfd_c_b16_dv, every path / name exactly as before (CB16 runs unchanged)
  b8:  qfd_c_b8_dv  (CB8 2 x 4 MAIN, T band = the centre row gap)   PENDING-COORD
  b8n: qfd_c_b8n_dv (CB8 2 x 4 ALT,  T band under the N strip)      PENDING-COORD
"""
import os

CLUSTER = os.environ.get("OT_QC_CLUSTER", "b16")
_T = {
    "b16": dict(master="qfd_c_b16_dv", pre="qfd_c_b16", diag="qfd_c_b16_dv_diag16rt", nc=4, nr=4,
                contract="results/arch/qwen_cluster_1017/cluster_contract_dv.json",
                relay="results/arch/qwen_cluster_1017/relay_sites_dv.json",
                plan="results/arch/qw_cb16_legal_bays_1020/grid43", reg="results/arch/qw_cb16reg_1020",
                owner="Claude:SQC-CB16", branch="claude/sqc-cb16-1022"),
    "b8": dict(master="qfd_c_b8_dv", pre="qfd_c_b8", diag="qfd_c_b8_dv_diagrt", nc=2, nr=4,
               contract="results/arch/qw_cb8_1022/cluster_contract_b8.json",
               relay="results/arch/qw_cb8_1022/relay_sites_b8.json",
               plan="results/arch/qw_cb8_1022/grid43_b8", reg="results/arch/qw_cb8_1022/reg_b8",
               owner="Claude:SQC-CB8", branch="claude/sqc-cb8-1022"),
    "b8n": dict(master="qfd_c_b8n_dv", pre="qfd_c_b8n", diag="qfd_c_b8n_dv_diagrt", nc=2, nr=4,
                contract="results/arch/qw_cb8_1022/cluster_contract_b8n.json",
                relay="results/arch/qw_cb8_1022/relay_sites_b8n.json",
                plan="results/arch/qw_cb8_1022/grid43_b8n", reg="results/arch/qw_cb8_1022/reg_b8n",
                owner="Claude:SQC-CB8", branch="claude/sqc-cb8-1022"),
}
T = _T[CLUSTER]
IS16 = CLUSTER == "b16"
MASTER, PRE, NC, NR = T["master"], T["pre"], T["nc"], T["nr"]
NT = NC * NR
FAB = f"rtl/physical/qcluster/{MASTER}_fabric.sv"
TOPSRC = f"rtl/physical/qcluster/{MASTER}.sv"
DIAG = f"tools/ref_tile/specs_qcluster/{T['diag']}.json"
DIAG_SDC = f"physical/qcluster/{MASTER}_quadrants.sdc"
DIAG_SITES = f"physical/qcluster/{MASTER}_sites.tsv"
PLAN = T["plan"]
REG = T["reg"]
CONTRACT = T["contract"]
RELAY = T["relay"]
FULLM, FULLMB, FULLN, RGX = f"{PRE}_fullm", f"{PRE}_fullmb", f"{PRE}_fulln", f"{PRE}_rgx"

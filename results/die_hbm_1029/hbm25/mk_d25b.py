#!/usr/bin/env python3
"""DIE-HBM-25 HBM-047/048 (B) plan follows source: d25a -> d25b, root type only, 3 hard-core declarations get
reset_from_master (no geometry, no pins, no cycles).  Fail-closed.
  u_tkm_SW_root            kind port:     ot_hgi_coll_tkm_m_tp192_p rst_n -> ot_hgi_coll_tkm_static_p u (root logic flops
                                          + u_buffer) only; the 32 tiles have no reset (rst_clr data) -> the piece reset
                                          is the master port (wavefront drives as-built leaf tkm_SW.rst_n at tap 108).
  u_hc_eng_tail{0,1}_sk_steady kind internal: ot_hbm_hc_root_static_s rst_n -> ot_rst_relay u_rst -> rst_c = rn[0] ->
                                          tail units u_t -> sinkhorn u_ss rst_n: a master-internal relayed net, not a die
                                          wavefront consumer (the master port u_hc_eng.rst_n stays a partition consumer)."""
import json, sys, hashlib, os, shutil
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
p = json.load(open(src / "die_plan.json"))
t = p["partition_types"]["root"]
B = "/srv/opentallas-scratch2/claude/wt/codex-hbm-sourcefull-0310/"
SET = {
 "u_tkm_SW_root": dict(kind="port", content="u_tkm_SW", pin="rst_n",
   source="rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192/ot_hgi_coll_tkm_m_tp192_p.sv u.rst_n; "
          "ot_hgi_coll_tkm_static_p.sv:116/127/178 (root flops + u_buffer; tiles reset-free)"),
 "u_hc_eng_tail0_sk_steady": dict(kind="internal", content="u_hc_eng", pin="rst_n",
   source="ot_hbm_hc_root_static_s.sv:109-110 u_rst ot_rst_relay rst_c=rn[0] -> :260 u_t.rst_n(rst_c) -> sinkhorn u_ss"),
 "u_hc_eng_tail1_sk_steady": dict(kind="internal", content="u_hc_eng", pin="rst_n",
   source="ot_hbm_hc_root_static_s.sv:109-110 u_rst ot_rst_relay rst_c=rn[0] -> :260 u_t.rst_n(rst_c) -> sinkhorn u_ss"),
}
insts = {d["inst"] for d in t["contents"]}
done = []
for h in t["hard_cores"]:
    if h["inst"] in SET:
        assert "reset_from_master" not in h and SET[h["inst"]]["content"] in insts
        h["reset_from_master"] = SET[h["inst"]]
        done.append(h["inst"])
assert sorted(done) == sorted(SET), done
assert not dst.exists()
shutil.copytree(src, dst, copy_function=os.link)
(dst / "die_plan.json").unlink()
(dst / "die_plan.json").write_text(json.dumps(p, indent=1))
rep = dict(source_plan_sha256=hashlib.sha256((src / "die_plan.json").read_bytes()).hexdigest(),
           plan_sha256=hashlib.sha256((dst / "die_plan.json").read_bytes()).hexdigest(), changed=SET, cycles_added=0, rtl_changed=False)
(dst / "reset_from_master_report.json").write_text(json.dumps(rep, indent=1))
print(rep["source_plan_sha256"][:12], "->", rep["plan_sha256"][:12])

import json, sys
def spec(name, pins, cols, why):
    return {
 "name": name, "top": "dsdv_idx_qf", "kind": "tile",
 "sources": ["rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv"],
 "params": {},
 "clock_port": "ck", "reset_ports": ["rst"],
 "outline": {"w": 259.2, "h": 432.0, "exact": True},
 "macros": [],
 "pins": pins,
 "recipe": 4, "hold_budget": "die", "inhold": False, "outhold": False, "clock": "cts", "layer_cap": "M5",
 "route": {"pd": 0.5, "threads": 8, "peak_ram_gb": 16, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
           "pin_balance": {"group_max": 1, "h": "M4", "v": "M3 M5"}},
 "structural_change": ("TOK-FUNC2-IDX_QF 10-21: G8IQ stand-in master dsdv_idx_qf (1 inst u_iqf, die72 G8IQ 553741303, "
   "slot 259.2 x 432 dv_plan IDX_QF) had no view. RTL successor of blob c31c5c582 (NAT32, same ports / function / "
   "latency: bench tb_dsdv_idx_qf MUT0 PASS, MUT1+MUT2 FAIL; random lockstep vs c31c5c582 12 seeds ~297k cycles "
   "nerr 0): qs_r[0]/ql_r[0] (513 loads each) -> 16+16 kept slice copies; s1[0] (qr rewrite select 512 + framing) -> "
   "18 kept copies; w_hit (107-bit spec mux) -> 5 kept uid copies with replicated entry compare; rn (~45 async pins + "
   "hold enables of spec/hdr) -> rst -> rs0 (1 sink) -> 4 kept rnk copies; spec/tag/user plain enable regs. " + why),
 "pin_regs": {"enable": False, "reason": "Source-registered: qs / ql / uid land in flops at the pin (qs_d/ql_d/qs_v0/ql_v0/qs_vk/ql_vk/mek), qr / qc0 / qc1 / st leave flops; the die calendar prices pin -> pin 3 edges, recipe pin_regs would add an unpriced stage."},
 "reset_landing": {"enable": False, "reason": "the RTL lands it: rst -> rs0 (only sink) -> 4 kept copies rnk (<= 28 async pins each); kit landing would add 2 unpriced release edges."},
 "keep_pin_regs": True,
 "pin_reg_split": True,
 "pin_reg_split_why": "qc0 / qc1 are identical registers (both = s1): one dedicated launch flop per output pin so each face's flops anchor at their own pins.",
 "io_flop_at_pins": {"cols": cols, "allow_none": True},
 "fill_reason": {"pin_bound": "Pin-bound: 2,565 signal pins (qs 513 N, qr 513 E, ql/qc0/qc1 1,539 + uid/st die ports S/W) on the fixed die slot 259.2 x 432 (dv_plan IDX_QF_W/H, block iqf at x 8320.96 y 100); logic = ~3.7k flops + ~1.2k muxes (~2k um2), fill well under 45%."},
 "job": {
  "owner": "Claude:TOK-FUNC2-IDX_QF", "branch": "claude/tokfunc2-idx-qf-1021", "tag": name,
  "purpose": "TOK-FUNC2 G8IQ stand-in: dsdv_idx_qf (S81 IDX query fan-out, NAT32 successor) to closure (TT setup / FF hold / DRC 0 + native audit) -> lanes/S81-DIE9.md G9 bind.",
  "extra_paths": ["rtl/dsrom_sys/s81_dv/idx", "results/rtl/tokfunc2_idx_qf_1021"],
  "benches": [
   {"name": "qf_bench", "cmd": "bash rtl/dsrom_sys/s81_dv/idx/test/run_idx_qf.sh {RUN}/qf", "expect": "pass",
    "threads": 8, "peak_ram_gb": 4, "pass_regex": "^QF_BENCH PASS$"},
   {"name": "qf_eq_c31c5c582", "cmd": "bash results/rtl/tokfunc2_idx_qf_1021/run_eq.sh {RUN}/eq 0", "expect": "pass",
    "threads": 8, "peak_ram_gb": 4, "pass_regex": "^QF_EQ PASS seeds 6$"},
   {"name": "qf_eq_mut2", "cmd": "bash results/rtl/tokfunc2_idx_qf_1021/run_eq.sh {RUN}/eqm2 2", "expect": "fail",
    "threads": 8, "peak_ram_gb": 4, "fail_regex": "^QF_EQ FAIL ", "fail_witness": "results/rtl/tokfunc2_idx_qf_1021/eq_mut2.log"}
  ],
  "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}"
 },
 "children": [], "inter": []}
A = spec("dsdv_idx_qf", {"N": ["qs"], "E": ["qr"], "S": ["qc0", "uid", "st"], "W": ["ql", "qc1", "ck", "rst"]}, 4,
  "MAIN faces: N qs 513 (1.98/um), E qr 513 (1.19/um), S qc0+uid+st 525 (2.03/um), W ql+qc1+ck+rst 1,028 (2.38/um).")
B = spec("dsdv_idx_qf_f", {"N": ["qs"], "E": ["qr"], "S": ["qc0", "qc1"], "W": ["ql", "uid", "st", "ck", "rst"]}, 6,
  "FALLBACK faces: N qs, E qr, S qc0+qc1 1,026 (3.96/um), W ql+uid+st+ck+rst 527 (1.22/um), io_flop cols 6.")
for s in (A, B):
    json.dump(s, open(f"/tmp/qfspec/{s['name']}.json", "w"), indent=1)

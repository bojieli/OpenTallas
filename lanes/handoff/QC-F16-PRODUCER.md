# QC-F16-PRODUCER handoff (one job: tt_ctlm f16_obs[38] / init_u0 producer)
## Findings (11-24 ~01:20 PST)
- Compose core = F5 qfd_tt_ctlm_dv_hp13_rrloc_native32_f5_cpub39_1 1166f7d9630f (rs1 resynth e9be4831f164 same ports).
- f16_obs = DEAD in F5: 0 loads (grep + yosys proc/opt no_fanout 38/38); constructor record unused_inputs_removed=[dh_user,f16_obs];
  the typed observer is local (GI SU issue). LIVE in old cpub39_1 (non-F5, C4/V4) -> that form stays REAL/held.
- init_u0 = TIE 0 (declared strap): INIT_U0=1 INIT_FIRST=52 INIT_CNT=3 compiled in; composed media_rank0 stage-0 descriptor (0,70),
  no INIT event in sys_face T calendar; asserting it would play 52..54 of the 70 stage-0 entries. Reset value of init_u0_q is 0.
  Bench (intel1 /tmp/f16p_bench.py on F5 cone, 32 flops): tie0 -> init_u0_q never 1 after reset (0/200 seeds); controls fire, pulse +4 edges.
- f16_st: present (17 regs, from local witness + f16_auth), open on die; its fault also reaches dc/cf inside the core. No consumer needed.
- Consumers depending on f16_obs: NONE (forward cone 38 nets, 0 outputs). init_u0 forward cone reaches all command outputs
  (tl, native_cmd, cmd, hr, table_req, emb_*, native_tok/pos, dc, cf, f16_st) -> consumers count only with the tie row in the plan.
- Side note: die_r56 tt_ctlm instance leaves table_req (and f16_st) open; table_req is handled by the plan_rewires_treq.json rewire.
## Row
- script epyc7/epyc10 /srv/opentallas-scratch2/claude/QC-F16-PRODUCER/rows/f16p_row.py TREE OUT RT; bind f16p_bind.sh C
- built on cS base (18d22fbde479): proof bef4ffc628a5, die_r56 94afcbf4a73f, asbuilt 4d9fac2cad9f, plan 469c19a9143a (epyc10 mini/row)
- rebasing on C1g 96cce77c1e2f: fork epyc7 QC-F16-PRODUCER/c1g/tree, then f16p_bind.sh (PRE + elab + strict --types tt_ctlm)

## 11-24 03:2x TT-TOKBENCH (job 2)
- Tool on main e0ce58397587: tools/qwen_tokfunc/tt_ctlm_token_bench.py (+ tests/test_tt_ctlm_token_bench.py). Runner epyc7 QC-F16-PRODUCER/tok/ttb_runs.sh R1|R2|R3 (TREE=, OUTN=).
- C1h verdict FAIL: XPF records margin 23 (program T=20) vs core XPF_TRANSPORT_EDGES=21 (needs 24) -> u_go xpf_schedule_fault at seal, cf 1078. RTL@T=20 PASS (tok/r3); repriced program -> witness digest fault (tok/r2). Needs core rebuild (T match or new program + digest); ruling asked of QC-ALLFIX.
- Recovered old harness code: epyc7 QC-F16-PRODUCER/harness_src (from epyc10 delete-manifests/2026-11-24/071108 inputs tarball); data was not kept.
- Lane clone epyc7 QC-F16-PRODUCER/clone (branch claude/qc-f16-tt-tokbench-1124, pushed).

## 11-24 04:2x TT_CTLM-REBUILD (job 3, hub e702d0c2; ruling 5df0ac68: keep program be4977f1, core at XPF=20, ALLFIX pads lanes)
- epyc10 /srv/opentallas-scratch2/claude/QC-F16-PRODUCER/regen: regen.sh OUTDIR T (recovered gi frontend + template.ys), bench.sh NET OUT XPF MODES, lec.sh GOLD_T GATE_T OUT.
- Recipe fidelity: t21 staged == bound 6a5f5323 byte-identical (staging = genblk10 calrom rename + INSTANCE params on 3 f5_opseg ROMs; see tmp/*.staged.sv).
- T=20 staged netlist 43059362f4bf, at regen/bench/qfd_tt_ctlm_dv_hp13_rrloc_native32_f5_cpub39_1_t20.sv. Bench out regen/bench/t20, LEC regen/lec/{pos,neg}.
- Still to do: post bench + LEC verdict; hand off to QC-TTC-R2; post PASS/FAIL to QC-ALLFIX + FABLE-RC-QC.

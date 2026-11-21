# FAM-S81-SERDES handoff (stand-down 2026-11-21 ~05:00 PST, successor needed: Sonnet/Opus FAM-S81-SERDES-R2)

## Findings (all posted)
- OT_PLACE_REGION_DROP (main 124d829f45f) works: serdes__t2 a5 placed, 0 DPL-0033, GRT 0 overflow. t2 is small (not >400k).
- FALSE PLACE-SETUP-STOP: t2 a5 (-404,673 ps), t12 a9 (-385,764), t14 a6 (-464,138) stopped at post-place; measure used propagated clock on unbuilt clock network. Fixed eda19506a55 (tt_setup_repair.tcl), in rt 18ff3f60c26, NOT in f453583d583. Retry form: item@N:fix=eda19506a55.
- t16 a17 CTS crash "cts.tcl 89 can't read tb_cdirect" fixed 5294e088f55.
- t4 = 407,738 cells (over cap). Census (cone attribution of 1_2_yosys.v): u_dec 131k, u_enc 73k, u_rm 18k, ring 7k, u_txl 5k, lpad 5k, +121k in landing/ist/cas submodules.

## Rows handed over
- lanes/handoff/FAM-S81-SERDES-j7-split-rows.json (ef9ae3bd5fc9): split t4 into hard cores u_dec + u_enc on FF->FF bundles (rxf_q->dec 545, dec->rm 513, lpad->enc 512, enc->txl 545). 0 cycles. Shell ~153k.
- Relaunch rows in kit_wave config (retry list): t12@9:fix=eda19506a55, t2@5:fix=eda19506a55 (t2 a6 launched 03:48, gen), t16@17:fix=5294e088f55, t13@6 (a7 launched 02:02, place). Caps unblocked by posts for t4, t13, t12, t2, t16, t1clfe.

## State at 05:00
- J6 event dc92652f0d5 (src d8j6) launched serdes__t4 a1 (unit kw-s81-serdest4-1-63632, gen) at 04:20: this is the new representative run; J6 removes the region.
- Old-rt route jobs (event 224567138ab): t4 a15 (epyc10 job serdes__t4-route-civil-redfish-1600687-...; waiter bdr287ry6 armed, dies with the job), t15cla21 a7, t15cla3d a5, t1clb45 a7, t1clfe a9 ENQUEUED/route. They will false-stop like t14: relaunch each with `item@N:fix=eda19506a55` via kit_wave_edit (patch add /dies/s81/retry/-) once classified; do not cancel.
- t14 a6 false-stopped 04:39: needs `serdes__t14@6:fix=eda19506a55` (NOT yet added) + `unblock serdes__t14 cap` if held.
- t12 and t16 relaunch rows added 03:5x but no LAUNCH line seen by 05:00: check log.txt, BLOCKED-CAP, tick.
- t3: DPL-0033 on old rt, held for J6.

## Core kits (COORD 04:5x: build u_dec/u_enc core kits now, non-epyc9, private strict bind+LATCHECK 0 cycles, price the 4 channels, refine outlines, then census other serdes types) - NOT started beyond:
- Lane clone created: epyc7 /srv/opentallas-scratch2/claude/fam-s81-serdes-core (cone tools,rtl,physical/ref_tile). Check git status; widen cone with git -C ... sparse-checkout add if needed.
- Flow: tools/ref_tile/README.md (gen spec.json -> physical/ref_tile/<name>, pre_route_gate.py, job). Example: tools/ref_tile/examples/s81dv_rg3b_xm6_tp.json (source-registered faces: pin_regs.enable=false, keep_pin_regs, io_flop_at_pins). Previous svc core recipes: recipe mm5/mm6 (FABLE-FIX-S81-SVC2.md lines 67-85).
- enc: module ot_s81_kp4_enc (rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv): in clk, rst_n, tx_v, tx_d[511:0]; out p_v, p_d[543:0], fault; includes ot_s81_gf1024.svh and ot_s81_kp4_rst. Single clock.
- dec: module ot_s81_kp4_dec_native_flat_lp (rtl/dsrom_sys/s81_link/lp/): in rst_n, p_v, p_d[543:0], ck_syn/ck_dly/ck_chn/ck_out (FOUR clock pins, all pma_rck in col form -> needs clock_entry_domains or tie to one clock_port); out q_v, q_d[511:0], q_first, q_unc, q_nerr[4:0], q_seq[7:0], lock, n_corr/n_unc/n_relock[31:0]. Pin regs must NOT add a cycle (pin_regs disabled; both sides are already FF).
- Open design questions: dec's four ck_* pins (one root vs landed regions), status outputs n_*[31:0] (96 bits + others) are extra ports beyond the 544/512 data bundles: price them; reset entry pins rn_t/rn_r.
- Steps remaining: (1) write enc spec + dec spec, gen, pre_route_gate --cts on a non-epyc9 host; (2) build via ot-run; read CTS post-hook (tools/die_plan/cts_read.py); (3) strict bind + LATCHECK private plan with hard_cores rows, 0 added cycles; price 545/513/512/545 channels; (4) shell kit census < 400k; (5) census other serdes types (t1*, t12, t13, t14, t15*, t16, t2, t3) with tools like /tmp cone.py (scratchpad cone.py: FF-cone attribution of 1_2_yosys.v); (6) hand proven rows to S81-J6-ASSEMBLY-R2 (J7).
- Scratch scripts: /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/{cone.py,st.py,cen.py,chk.sh}.

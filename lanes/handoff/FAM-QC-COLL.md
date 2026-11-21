# FAM-QC-COLL handoff (11-21 ~09:50 PST) -> successor FAM-QC-COLL-R2
Family: unsigned QC coll types = coll_core (representative), coll_ftc (FLEET-WATCH-R6 owns its restage after the DRT-0255 drt-nopath fix 42fa174c180; read its ODB if resumed, do not relaunch).

## State
- pkw4 final (epyc9, GRT 20.9 h): rdq->out_data floor -82; GRT hold repair bought 55,013 HB4 pads and pushed setup -82 -> -425 -> final -255 / TNS -27k on 916 ends (classes xr_q, u_rring wd_in, ir_q). Root cause = input hold. Row set = b+c+d together (COORD).
- RTL on main 867126d928d: OT_TP8S_SRDREG, SWDREG, ODPRE (earlier), INLOCK (falling-edge staging of all input pin registers, 0 cycles), RRWD (R ring write register, 0 cycles), XRPIPE (+1 cycle reduce only). Bench 13/13 each + combined, plain + qfd (epyc10 fam-qc-coll/bench10). Bench flags: --sring-io-regs --output-pipe --input-lockup --ring-wd-reg --xr-pipe.
- Rows: lanes/handoff/FAM-QC-COLL-rows_a.json / rows_b.json (older; update to b+c+d = defines SRDREG,SWDREG,ODPRE,INLOCK,RRWD,XRPIPE on partition_types.coll_core.verilog_defines + stations by measured length on 6,975 hops + srl/rrl chains one tap each + one 60 um street + 2 stations on u_ctl face codec) -> QC-PLAN-R10 (V3, 11-22) as ONE row set, after the kit read.

## Running (leave running)
- Private proof kit run-item on epyc10: ot-run client pid 1781433 (epyc10), unit oth-ubuntu-1782833-1795278360, log epyc10 /srv/opentallas-scratch2/claude/fam-qc-coll/pkit_run.log, spec fam-qc-coll/pspec/spec.json (kit_wave.py private-spec, wave env), work fam-qc-coll/pkit. Currently in stage src_manifest. RISK: SRC-TREE-1115 wants tree = git archive of a main sha + overlay manifest (sha256 per file); my tree is a hardlinked copy (cp -al) with ONE patched file, so src_manifest may refuse. If so: build the tree as the rule says (main sha archive of the scope + overlay of rtl/rom/ot_coll_tp8_static.sv), regenerate private-spec (kit_wave_cfg2.json = hub config with ot_run pointed at ~/.local/bin/ot-run, because kit_wave.json ot_run /home/ubuntu/.local/lib/kw44/ot-run-wave does not exist on epyc10), relaunch with ot-run --mem 72 --threads 8 --hosts epyc10 (not epyc9; --priority plan is refused for type builds).
- Tree path: epyc10 /srv/opentallas-scratch2/claude/fam-qc-coll/tree_bcd (hardlink copy of kw45/snap_qwen_compute/qwen_compute_v1r6 + patched rtl/rom/ot_coll_tp8_static.sv; plan physical/die_plan/qwen_compute/plan_of_record/zz_famqc_bcd.json = R4 final preview + 6 defines). Lane clone: epyc10 fam-qc-coll/clone10 (main).
- Waiter in my session (b2w8n1ybi) dies with me: re-arm run_in_background on `pgrep -f fam-qc-coll/pspec/spec.json` on epyc10.
- Wave R6V1 coll_core attempt_4 went QUEUED/prelint again at 06:48-06:54 (not mine).

## What to measure in the kit (COORD)
Half-cycle input setup into the falling-edge staging regs (fclk_in_* forwarded clocks, core clock insertion ~190-270 ps; budget T/2 = 416 ps) and the HB4 count after GRT hold repair (pkw4 baseline 55,013 HB4xp67, +201/chunk, RSZ-0060). Read FINAL stage db only (not 4_cts_final / 5_global_route pre-repair). If INLOCK costs more setup than it saves: build the fallback = one clock tap per input bank (shared tap for each input pin register bank, tap row via TAP-GRID-R2 / plan clock tap rows), same kit procedure.

## Other
- Slip disclosed: I used rm -f once on my own bench summary (now allowed for own temp files in own scratch tmp).
- Cancelled earlier: kit-wave coll_core N46R4A4 attempt_2 (epyc8, post-CTS -1154).

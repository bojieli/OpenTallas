# QC A0 B-hop proof continuation

Source baseline: `7946a8448d0`. Physical owner uses REGROOT_MODE=3;
the inherited operational test used 9. The bench now accepts REGROOT=3
without changing its default (9), and prints the exact selected form.
No accelerator RTL, data cycles, gating depths or clock budgets change here.

The original ROM-only mutant8 and NL drain-drop mutant3 remain survived
controls, exactly as the inherited logs record. They are never called caught.
The ROM K=2 choice still rests on the conservative structural s=3 bound.
`tb_hop_bound.sv` directly instantiates the production ot_a0_icg_hop: with
a first required capture at s=3, K=2 captures 32/32 wakes correctly, while
the simulation extra-hop K=3 control misses 32/32. Run through ot-run
intel2 unit2253454; exit0. This tests the actual bound mechanism, not a claim
that the full ROM protocol reaches its conservative earliest stage.

NL drain survivor diagnosis: engine idle_c covers acc, pending issue,
multiplier/valid/post/tree/result-write stages; idle is then registered.
After that boundary the NL output has TOREG plus outer t_out_q stages,
and its K_FA2=2 gate retains two trailing edges. The drain=64 guard remains
unchanged and conservative. This is a structural explanation of the survivor,
not a general formal proof that drain can be removed. The production control
is kept; existing mutant7 remains the meaningful operational negative control.

Actual REGROOT3 NL/NK operational builds are running in own epyc2 run dirs
`/srv/opentallas-scratch2/claude/codex-qc-proof-0831/b_{nl,nk}_m3`.
Admission units2583258/2584210; source staging manifest is stage_files.txt.
Both are old-source semantics before the A0 owner's declaration-order fix.
That fix only moves wire declarations for slang connectivity and is validated
by the physical owner; simulation source equivalence must be checked before
sharing these receipts with that successor.

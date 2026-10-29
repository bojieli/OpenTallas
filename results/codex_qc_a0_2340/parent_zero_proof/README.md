# NL parent zero-global-KV source and native proof

Source candidate: `0bb45b731ccf3471e3d2a17d0c89a39d2c6d0847`, only the shared RTL file
`rtl/physical/a0_rc15_selected_2000/ot_qwen_rom_tile_w12_land32.sv` changes. `GLOBAL_KV_CONST0`
defaults off. Only the ROM wrapper, whose existing global KV input is hardwired zero, opts in
with `OT_ROM_CONST0_KV`; request/valid scheduling and data cycles remain unchanged.
The minimum 2048-bit conditional-capture/delay miter has 1751 valid comparisons and catches
1751 wrong-data controls. This is a source specialization for the already mapped zero port.

The actual unchanged mapped netlist is intel1:
`/srv/opentallas-scratch2/claude/codex-qc-a0-2340/parent_zero/run/results/asap7/kq_qfd_tile_nl_a0c_a0p10r3/base/1_2_yosys.v`.
Frozen native AIG/model source and proof are
`/srv/opentallas-scratch2/claude/codex-qc-nl-lec-1029/zero_target`.
The original normal proof's seven remaining counter differences remain preserved at
`/srv/opentallas-scratch2/claude/codex-qc-a0-2340/parent_zero/lec_zero_kv`.

`hints.json` contains seven untrusted loaded relations for nb_t[6:0], guarded by
(active OR pend). GO clears nb_t before either state begins; active increments are multiples
of 128. The existing proof engine proves the reset-false base and joint loaded relation;
no environment assumption is added. `joint.json` proves all 12570 joint obligations,
`compare.json` proves all 31742 full comparison points with zero differences or undecided,
and `wrong_value.json` catches one wrong loaded value (nb_t[0]=1). `proof.log` is the native
ABC transcript, collected by the independent HBM/LEC worker. No repeat proof is required.

For the ordinary kit proof, copy `hints.json` to `KIT/lec_hints.json`, or use:
`python3 tools/die_plan/lec.py KIT --netlist ACTUAL_MAPPED_OR_ROUTED_NETLIST --out FRESH_OUT --hints results/codex_qc_a0_2340/parent_zero_proof/hints.json`
through ot-run. Do not overwrite either original failed proof directory.

This source/proof packet is READY for shared review. It does not adopt a parent placement:
the independent placed parent currently fails reach and is being physically redistributed.

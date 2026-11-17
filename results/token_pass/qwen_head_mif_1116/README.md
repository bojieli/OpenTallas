# Current-source Qwen HEAD memory profile3/1

The actual current H/J native SUVM and eight heads, with the production BF16 stream tile, pass48 cases,16384 FP32 outputs and256 BF16 beats using all4096 genuine gain values. Gain, user and raw-X controls are caught. The HEAD stage data is the existing committed03fa2dcf payload; the native source packet is newly copied from the current52ba5009 source projection. No old RTL or ELF is reused.

Receiver ages start at the actual posedge sampling of the component cmd_i port: first memory request19, native S2 operand capture32, VM write61 and BF16 receiver72. The first packing response is11 edges; the tail is4 after the last VM write. Upstream CALR/FDN/RP/CTL transport is excluded. The old selected825 HEAD contract remains3/0. Neither this component pass nor the date-join helper activates a programme or closes a whole-token gate.

Replay the pinned source packet through normal ot-run admission, then collect its real dates:

```sh
bash results/token_pass/qwen_head_mif_1116/source_packet/run_gate.sh
python3 -I tools/qwen_layerbench/collect_head_apply_gate.py --packet results/token_pass/qwen_head_mif_1116/source_packet --out NEW_emission_profile_3_1.json
```

The separate HEAD_BAD_REPLY=1 source-ready build was not run. The same-ELF gain/raw-X/user controls were run. Existing completed native SU old-reply controls remain separate evidence.

Join this measured profile into the existing HEAD calendar relocation object only with actual delivered-command edges and per-user memory leases:

```sh
python3 -I tools/qwen_layerbench/head_apply_date_join.py \
 --profile results/token_pass/qwen_head_mif_1116/emission_profile_3_1.json \
 --allocation-source results/token_pass/qwen_head_resident_lease_1101/actual8rank_census.json \
 --head-object ACTUAL_HEAD_CALENDAR_OBJECT.json --delivered ACTUAL_DELIVERED_COMMANDS.json \
 --out HEAD_CALENDAR_WITH_MEASURED_WINDOWS.json
```

The helper documents the input schema. It emits exact native receiver windows; a HEAD_APPLY issue symbol resolves only when actual CALR issue and CALR-to-cmd_i ages are supplied as well. Other installation, Xfill/ME readiness and global programme obligations remain explicit. Eight fail-closed guard controls use actual packet metadata and explicitly synthetic edge values; they add no hardware qualification.

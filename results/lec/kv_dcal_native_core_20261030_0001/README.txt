SharedLEC-requested source-isolation coupon, native ROM64 calendar core.
Actual source intel1codex-kv-kits-1355/sysc_fix/kit/rtl/ot_qwen_d2d_cal_seq_rom64_core.sv.
ADM1/AUTO1/EP_SKEW1, defaultsNE32/NL36/TW20/GO0, actual spare resetbank15unused.
Source unchanged; synth uses read_verilog-defer + hierarchy-chparam before elaboration
because invalid defaultADM0/AUTO0 would trigger actual initial$fatal before chparam.
Approved-main tool supplied by sharedLEC: codex-lec-2249/src/lec_preseed_main.py.
Generic synthesis vs independentgoldSlang:282/282 functionsEQ0diff0undecided;
verdictKEEPFAIL4/66 declaredkeptbits (ep_q_copy1/init_copy2/running_copy0/2).
cal_start next-D inversion negative:281/282EQ+1actualcompareDIFF, sameKEEPFAIL4.
Units3763517/3769115 terminal1. No keep waiver, no canonical EQUIVALENT/SIGNEDclaim.
This small core has no direct221-class functional failure seen in fullSYS_C.

Followup RVT mapping lives intel1 /srv/opentallas-scratch2/claude/codex-kvtok-2249/dcal_lec.
V1 invalidmethod (unprocessed RTLIL clockprocesses),217diff base/mut retained NOTADOPTED.
V2 proc fixed, ABC then rejected missinglookup templates in handmergedRVT library.
V3 adds actualRVT-TT library templates + proc; map_run_v3.sh -> lec_rvt_v3 and
lec_rvt_mut_v3. It may remain live at reset; sharedLEC owns collection.
No route or production source change. Ordinary keep checks remain enabled.

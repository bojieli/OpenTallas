# dsdv_mu_hwin_c22r (FALLBACK, S81-ELEM2-HWIN 10-21)

Structural successor of dsdv_mu_hwin c21q/c21r (daemon NEEDS_RTL: TT -148.19 / -141.73, FF -8.26 / -11.76, DRC 0).
Top `dsdv_mu_hwin_capture_1019`, NEV 16, LOCAL_RECORD=1 (codex/s81-hwin-struct-1021@adf49d4f8), outline 561.6 x 388.8, 84 SRAM 64x16, pd 0.55.

S81-ELEM2-HWIN successor of dsdv_mu_hwin_c21r (daemon NEEDS_RTL: c21q TT -148.19 / FF -8.26, c21r TT -141.73 / FF -11.76, DRC 0). Failing class: g_compare_copy.cmp_r -> 47-entry identity compare + OR reduce -> global duplicate flag udup -> distributed to all 16x2 event rec_r + slot record_group across the 561.6 um band (two 113/148 ps buffer hops, arrival 1222.75 vs required 1081.02). Fix (RTL, codex adf49d4f8 LOCAL_RECORD=1): each of the (NEV/4 event + 6 slot) record consumer groups gets its own kept duplicate-region cone (2 local 10-bit user landing flops, 47 compares, 8-entry partial ORs), so admission drives <= 8 local record flops instead of a band-wide broadcast; 0 cycles added (waveform miter vs frozen HWIN21cb + anchor). NEV 16 fallback on the unchanged c21r 84-SRAM geometry (superset of the die's 8 events). Physical: c21j hash-locked native manifests/fences dropped (cannot qualify changed RTL); c21h row-pruned band + GPL row envelope instead; pd 0.55; OPT_POST_GRT_WNS=0 pre_grt kept (EST-0104 class).

Benches (kit job): `NEV_KIT=16 run_c22_bench.sh OUT {ns47|ns2|norelay|eastcopy|mut2|eastdue}` = tools/s81_dv/hwin_struct_1021/run.sh
(DUT LOCAL_RECORD=1 mitered every cycle vs frozen HWIN21cb + anchor dsdv_mu_hwin at the same NEV); mutant witnesses results/arch/s81_hwin_struct_1021/benches/.
Regenerate: `python3 tools/s81_dv/hwin_struct_1021/mk_c22_kits.py && python3 physical/ref_tile/dsdv_mu_hwin_c22r/regen.py`.
Binding: a CLOSED view of this kit is the hwin child of the successor master dsdv_seq_host_mux_h with EXACTLY these parameters
(capture_1019, NEV 16, LOCAL_RECORD=1, ...); never aliased onto the G8IQ dsdv_mu_hwin source.

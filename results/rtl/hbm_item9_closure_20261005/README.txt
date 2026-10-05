Mandatory original item9 baseline closure; no adoption or headline clock credit.
Selected mask lineage: pinned ot_gpu_coll_endpoint_f12_txmask ONLY, not Claude r7.
New opt-in endpoint f12_cuts derives that source, RXOH=0 default. New mux
owner64 selects pinned f12 ODUP16 when OWNER64=0, ODUP64 when enabled.

Concrete result: full NL128 NSM2/4 mux lockstep PASS, 800000 configuration-cycles,
86764 grants total, zero mismatches, zero added cycles (exact_r1/result.json).
Completed r7 reused ODB/SPEF diagnostic: 33 reported negative endpoint paths,
four actual classes; prior pin-count record 34. SS worst -20.47ps FF +5.24ps
remain FAIL, with false-IO historical wrapper and two slew violations.
RX onehot/tag successor PASS full NL128, 3 seeds each off/on: 984 cases,
zero mismatches, measured latency identical (endpoint_r2/result.json).

Prebuild cost at full NL128/NSM2: owner copies +48 FF; RX decode +7680 FF;
RDUP8->16 payload copies +4096 FF and control/CDC replicas +468 FF; split tag
checks +5 FF. None adds a serial stage; XREG's historical +2 cycles stays paid.
Actual cell area, parent rectangle/channel/macroloads/clock insertion and
current token composition remain unqualified. No inferred parent fit credit.

route.sh driver: tools/hbm_item9_route.sh FRESH_ROOT LABEL EXACT_ENDPOINT_JSON EXACT_MUX_JSON.
All IO timed, clocks833ps SS60 FF25. Uses existing540um characterization
wrapper footprint, not an assertion about Turing's actual outer allocation.
No new launch before source exactness and Kant's fresh headroom admission.
Existing Goodall/Einstein/Claude jobs are preserved, never killed or restarted.
No editing of original RTL, peer child modules, pinned failure records, docs,
or central measured scoreboard. Unresolved far(-329ps) vehicle identity has
been requested; its path classes are not inferred from this r7 diagnosis.

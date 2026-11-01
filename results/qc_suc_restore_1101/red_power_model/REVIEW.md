# RED lower clock-capacitance model pair

MODEL ONLY, no CTS/P&R/source/default/view/parent+1 adoption. Actual initial PLACE source has34225sinks (33914HQN+311ASRHQN), exact typed TT/FF CLKcaps; root input slew0 remains hypothesis. Common250TT/202.5FF clock reference remains unchanged; model means are INFO outside that band, not absolute parent frame qualification.

Five-level2245cells/7stages FAIL: TT275.27/window22.03>20; FF230.05/window20.53>20. Slew34.2/29.3, coverage34225/0missing/0dup. Converter refused physical build. Commandrc0 only means the model command completed; checks.json FAIL is authoritative. Unequal actual leaf loading causes the remaining window miss.

Six-level8269cells/8stages PASS model: TT297.53/window13.02/slew25.1, FF232.90/window10.21/slew19.3, leafspread4.17, exact coverage, converterPGclearancePASS. One BUFx8 per level, same symmetric geometry/topology/stages as previous mixed-master lattice; no per-driver sizing, padding or dummy loads. The inputcap objective halves buffer inputcap:7.046pF TT/7.758pF FF (49.12/49.42% lower); still43.37/43.44% above native DFF cap before wire/internalpower. Clock area1446.74424um2; actual placed nonclock217427cells/27443.91942um2 plus8269tree cells gives225696cells/40.272% core fill. C*V2*f proxy remains an estimate, not measured clock power.

Personally LOOKED six/qfd_dv_s5_red2_leaf_r13.png: symmetric complete quadrant tree covers broad actual sink placement, short final leaves, clear center entry and no macros/walls. PASS-COND for a reviewed fresh PLACE-only prototype after actual fixed faceFF/TAP/body collision review. No CTS until fresh actual placement/sink/typed-load/model review; old649clockseed placement cannot qualify8269newgraph. Signal ceilingM5 retains parent M6/M7 crossings.

Fresh STAGED kit intel2:/srv/opentallas-scratch2/claude/codex-qc-red-lattice8-kit-1101/qfd_dv_s5_red2_leaf_pin1lat8, hash66a42afd81f4c8f0.354pins/ck/rst_n/0macros generatorPASS. New slice clockBTerm uses actual legalM5x138.252 while geometric root center stays138.24;12nm phase correction only, no stage/frame compensation. No physical launch.

Runtime epyc2:/srv/opentallas-scratch2/claude/codex-qc-red-power-1101/model_{five,six}/qfd_dv_s5_red2_leaf. Normal4GB1T unitoth-ubuntu-1271195-1793574396 exit0, dispatcher1497631. Earlier attempt refused for missing placed_input before any model, preserved NOTRUN logs; exact126MBactualODB/context copied then rerun.

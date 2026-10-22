Parent hard-packing and native-pin reach diagnostic — NOT a parent candidate for adoption

A corrected constructive shelf recipe fits all413hard children plus16A0tiles at3153.6x5227.2um, area16.484498mm2 (28.98% above original outline). Both recipe and an independent CP incumbent pass packing/lattice43.2/20umchannel checks with0violations. This is not a minimum-area result. Actual selected A0 LEF/native TT/FF views remain unavailable; no standin was upgraded to evidence.

Recipe:216landing halves occupy9vertical columns in the3inner corridors,24slots each at4gridrow pitch.16column stations occupy2outer columns,8slots each at4gridrow pitch. Plain90.72x64.8 stations use the remaining inner/outer shelves and21of36available A0-width horizontal gap slots. Inner corridors have3landing or2plainstation columns; outer strips hold1column. All shapes/layout obligations remain as the component diagnostics.

The initial hint used row gap origins offset by21.6um and failed42tile-clearance checks; it is preserved as initial_hint_rejected.json. The corrected recipe derives gap origins from actual A0 rows86.4/1382.4/2678.4/3974.4 and passes independent checks. The CP solver repaired the initial hint and produced legal complete incumbents; current optimization continues.

cb_shelf_incumbent.png was personally viewed. It is a diagnostic packing view with explicit reach/clock/reset/native warnings, not a visual-review request for parent routing. Blue/green landingW/R; orange column station; purple plain station; gray A0.

Independent enumeration of this immutable incumbent:614known child bus bindings,226534paired native pin bits;397buses/142700bits exceed405um, longest4646.772um.121A0/boundary endpoint occurrences remain unqualified. Manhattan lengths exclude obstacle detours; they are lower bounds. Per-edge ceil(distance/405)-1 values are geometric lower bounds only, not selected stages, aggregate calendar latency, or throughput. No new stage hardware, storage waiver, constraint exception, or compiler change is adopted.

Soft-reach CP is minimizing positive edge overruns while hard packing remains mandatory. Strict native reach feasibility searches run independently. All parent reach/clock/absolute age/reset+2/compiler/native timing/route obligations remain open.

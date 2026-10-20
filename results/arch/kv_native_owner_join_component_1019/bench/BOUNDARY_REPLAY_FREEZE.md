Boundary and current-event replay fixture freeze

Separate H93/D93 build, baseline H512/D384 unchanged. Actual scheduler RC_AB=$clog2(H_CUTOFF_EDGES+1), pending_age[RC_AB-1:0]: H512=10 bits, H93=7. Declared added state therefore 1830 versus 1827 bits; only age width changes. No production H or timing qualification follows.

Case20 requires the actual first prompt native_certificate_attempt_v, raw_done_v, certificate_key_ok and native_certificate_v on the SAME sampled edge in H93/D93. It must fail if that boundary is not reached; trace subtraction alone does not prove boundary eligibility. Existing public producer timing and four-step gold remain unchanged.

Cases16/17 replay the actual previously captured raw descriptor tuple on the first prompt certificate attempt, respectively unchanged (duplicate) and position bit0 inverted (invalid). Cases18/19 replay the actual previously captured terminal tuple, unchanged and epoch bit0 inverted. Capture sources are genuine raw_done_v and terminal_accepted with their actual payloads; no owner or allocation is synthesized. These are COMPONENT join-input fixtures, not native producer fault injection. Only join input wires are selected; scheduler cleanup, codecs, POST and endpoint credits retain their untouched real event paths. Each fixture must establish its genuine capture before replay and prove same-edge no mirror/certified-event advance plus sticky rc_bad.

A causal private DUT control removes only the current_events_valid conjunction in prospective certificate eligibility. The unchanged accepted-event protocol checks may fault later; the committed-state invariant must still catch any same-edge advance. No RTL holding state or functional scheduling change is introduced by these bench controls.

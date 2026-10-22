# S81 copy A/B regional endpoint

Pre-build microarchitecture model: MODEL.json. The selected architecture duplicates the existing native32 pair-A endpoint into independent A/B clock regions and performs dispatch/merge in the centre. All regional buses cross D4/K2 fixed-latency landing rings. Lane data/valid and reverse credits receive matched two-edge relays. Credits and SRAM-backed RX depth rise together to12. Existing tops/defaults remain unchanged.

The old 475.2x1900.8 slot is a reservation, not a qualified fit. Native mapped area and census precede any gate. Layout must place the relay stages at <=405um intervals and generate the explicit ring SDC. No pin-clock exceptions or clock-group cuts may replace these rings.

Production exactness uses NB80 messages, both lane pairs, tagged cut-through and land/replay, untagged payload, skewed lane arrival, window errors and credit exhaustion/wrap. Causal mutants must fail with committed logs before submission.

Pricing is per-hop, not a single final ri offset: centre dispatch1 + forward landing3; receive landing3 + one-hot output2; two outer relay edges in each data direction; reverse credits2, hence +4 credit round trip and12 slots. Calendar/die owner must compose these costs before binding.

Source 521409e29 validation (candidate, no physical qualification)

Fleet ep5 /srv/opentallas-scratch/claude/codex-s81-standard-lep-native32-1020. Verilator 5.050 (2026-07-01). Full DT512 / DR8 standard components: LEP seed1, host seed3, NH seed5, NHR seed7 PASS. Seven causal mutants stdsel/vskew/swap/nopair/ksoff/hdrop/nhacc fail with semantic mismatch witnesses; source and driver summaries accompany logs.

Immutable 23fd77ae5 reference core versus full-shape candidate, with only outward inputs delayed one edge: HOST=1 and HOST=0 each PASS 1779 checked cycles. Successor-only stdsel and valid-bank-skew mutants fail 263 and 440 checked outputs. RX phase is unchanged; outgoing +1 remains a priced candidate edge.

Standalone ORFS ASAP7 mapped census at BC: host 42451 roots examined; NH 37612; maximum dynamic loads 32 both, no violations or role errors. BUF/INV-transparent audit includes combinational, macro, reset and top output loads. These BC receipts establish control structure only. Final WC/SS libraries and actual gate SDC preflight remain required. No setup/hold/clock/reach/PG qualification is claimed.

The initial broad-row geometry is rejected. Candidate must use a source-coupled full-width cell band; exact mapped SRAM/top pin cuts, terminal-to-band reach, clock/PG and all-cell ownership remain pre-gate work. Shared RX write address/enable copies may require another same-age per-bank source change before that model can pass.

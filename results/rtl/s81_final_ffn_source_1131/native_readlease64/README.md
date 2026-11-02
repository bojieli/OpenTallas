# S81 final FFN source: native 64-word read lease (receipt)

Gate run by Codex 11-01 (intel2 unit oth-ubuntu-2956857-1793585330, 833 ps), packaged by TOK-DS-2 without a rerun.
Status `PASS_SELECTED_NATIVE64_READ_LEASE` (check.json):

- one selected native leaf, full 64-word capture slot, n8 RDOUT pairs; unchanged leaf sources and pins, stimulus only;
- earliest safe issue index 24; index 23 is rejected (2 same-address collisions, 2 stale, 2 errors);
- safe run: registered RDOUT CV 180, writes 158..189, SRAM reads 183..190 (CV+3..10), native LO 185..192 (CV+5..12),
  public 186..193; 16 read events over two banks, 0 collision/stale/error, 8 native + 8 public payloads;
- controls caught: early old version (issue_0), payload mutation (mut_payload_31).

Not qualified here: same-address read-during-write in silicon, global source/issuer epochs, production RD group/issue,
interframe FIN/CFG lifetime, the other native profiles. 0 added RTL cycles; not a full-token result.

runner/ holds the exact bench, runner and inputs; `source/` (copies of repo RTL) is replaced by source_copies.sha256.

# KV existing native proof collection

Read-only collection from the original ep6 jobs, following e27a57fbf. No proof rerun, helper change, source change or receipt. Four new terminal audits and byte-exact logs are archived in new_terminal.tgz; each log SHA256 matches its original audit.

- lane8: 13,139/13,155 comparisons proven, 16 err-state comparisons unresolved.
- ktree: 10,882/10,898 comparisons proven, 16 err-state comparisons unresolved.
- Both record a changed ot_hdc_fp32_mul_lat.sv source dependency relative to the frozen closure; no identity refresh or parameter qualification follows.
- PVslice positive and MUT1 both stop because the SRAM ot_sram_1r1w_32x128_m1 lacks a SAT model. Neither yields a completed equivalence verdict; MUT1 is not a causal negative witness. Raw audit proven=false must not be presented as a detected mutation.

Coverage now 32 terminal audit files, 16 positive files, 12 positive PROVEN files and 11 unique PROVEN modules (t1 duplicates ASTK owner). Original unexpected universal-MUT1 PROVEN controls remain preserved in the predecessor packet.

PV916 joint induction/reset-base/CEX observer evidence was not rerun. The e01bf789a reset graph is conditional behavioral evidence; actual physical reset/clock continuity/aperture and expanded selected GEN8 identities remain open. No native strict bundle is qualified.

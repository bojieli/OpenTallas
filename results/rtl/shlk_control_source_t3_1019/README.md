# SHLK control source prototype: REFUSED for adoption

Exact ancestor: `7e92217f5`, native source from ep5
`/srv/opentallas-scratch/claude/ref_gate/dsdv_sh_lk_s10c-20261019-163714/routes/gate/work/orfs/results/asap7/opentallas_dsdv_sh_lk_asap7_ref_gate/base/1_2_yosys.v`.
Native SHA256 `09e4d62c6a4032dead6ad208228555c3c53e3d35d2fcf81e715d227e3f7b7266`.
The original failure remains immutable. This is an inactive source experiment;
it changes no production source, helper defaults, timing constraints or schedule.

The mapped-source generator replicates actual same-master logic and reset FFs,
not a buffer tree behind the original driver. It partitions terminal sinks
through separately replicated BUF/INV paths and recursively accounts for added
input demand. It never clones an unreset FF or a memory. Every actual pin of
all surviving original cells and replicas is compared with the original after
substituting replica-net ancestry: 0 structural mismatches. This certifies a
conditional structural quotient, not behavioral or preassertion equivalence.
Reset FF clones require a common real asynchronous assertion and explicit
first-observation authority; neither arbitrary initial equality nor valid-low
waivers are assumed. No new data edge is introduced.

Final generated source has 68,683 cells versus 67,046 original, net +1,637 cells,
including +239 reset FFs and +3,274 standard-cell PG terms. The scalar primitive
transparent census reduces 712 over-limit outputs to 34 stages rooted in
**12 unreset FFs**, not the initially reported 11: recursive replication raises
p_kind[0] to 35 loads. p_kind[1] remains 513. Full list is in SUMMARY.json.

**The census is incomplete for memory vector pins.** Concatenated macro ports
are aggregate expressions and rd_out directions are not resolved by this
prototype. The 712/34 counts apply only to scalar primitive sinks. They cannot
establish full all-driver closure, complete ties, raw-input or macro contact
counts. The generator now explicitly forces whole_closure=false. A follow-up
must expand each vector port with source-owned directions before any admission.
This defect was caught while sealing and no new engine job was started.

No source RTL behavioral equivalence bench, causal mutant, native synthesis,
placement, timing, source-to-native qualification or physical grant exists for
this prototype. No all-driver, PG, clock, startup or timing PASS is claimed.
The first generated v1 wasted a transparent-path copy per terminal (+51,327
cells); v3 shares each original transparent prefix within its <=32-sink chunk.
Old intermediate receipts remain under `/home/ubuntu/artifacts/shlk-all-driver-1019`.
The final finite generation ran on ep8 unit
`oth-ubuntu-337011-1792457033`, exit 0, wall 10.37 s, peak 334,868 KiB.
This exit means source generation completed, not that the circuit closed.

For the proposed standalone SD child, the named native subset contains 578
plain FFs, 43 reset FFs and one SRAM. The FF area floor is 184.84524 um2.
The scalar boundary-truncated fanin candidate has 1,679 cells and 264.97692 um2
standard-cell Liberty area, excluding the SRAM. This is an ownership-uncertain
estimate, **not a complete standalone synthesis area or guaranteed bound**;
vector inputs and ABC cross-hierarchy sharing require a clean child synthesis.
Liberty area is already physical um2; no 1e6 scale division applies.

Independent usable RTL change `0b824c5d9` adds default-off `OT_S81_SH_P192` to
select the truthful SD 16x289 p192 macro, with unchanged synchronous contract.
The parent owns its macro-source binding and actual bench/native qualification.
No selector is enabled by this packet.

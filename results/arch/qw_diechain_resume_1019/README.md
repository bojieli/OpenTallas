# Qwen diagnostic resume proposal — HOLD

No heavy job was launched. This packet preserves the independent saved-clock resume patch and the blocking current relay result. Original dh2 outputs are unchanged.

The new question is first actual GRT congestion and TT/FF timing for the existing die. The previous GRT never opened an ODB: protected root ownership prevented hard-linking the saved clock. The old spine remains physically FAILED (43/55 neighbour pairs exceed80ps, ~24.6ns insertion). Copying that ODB is a file-handling repair, not a physical clock repair. No result from this proposed diagnostic can qualify the die or adopt the spine. Regional roots and source-qualified landed links remain the successor.

## Exact identity and saved stages

Remote original: ot-epyc6:/srv/opentallas-scratch/claude/mu-die-qw/dv2f18dh2.
Original source claim:0d4c9808f; original die.v SHA2567b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7 matches local archived qw-l1seam/dh2/die.v.
Saved clock ODB SHA256e9f9d4fc741c47548d6bc6daa2d40e01b3dc1d07be54009db2b45ce4b0af7a3b.
Saved TT latency SHA256acb656d65c44d0f77c8451017256c4c40d678e83e2a0319ae63457c9c2ea5d52.
Saved FF latency SHA256a42cb6170c882927cc20cab168fc966d867ec9e580e4478fa4f8da3dfae626fe.
Original PDN ODB939MiB, clock984MiB; chain4.2GiB, source20GiB. No ckpt_grt.odb or SPEF exists. The original failed grt directory and logs must remain unchanged.

## Actual blocker

The remote compiled_L1 is stale dv2f14bq. Historical4d2cb6301 provides corrected compiled/netlist tables and a historical PASS receipt. Running its corrected tables through the current58fc3dbc1 checker produces current_relay_FAIL.json: five effective-age differences and torn C.rx_record. Raw relay counts must not be rewritten to force PASS.
The differences: kv_x3_slot compiled3/raw2; rx_payload2/raw1; x3/identity/generation2/raw1. Actual record_bundles audit describes forwarded E+1 rather than hop counts (rx payload n2/E1/K2 gives2), but this alone is not current full source-to-pin proof. Next owner must derive real I/O registers, source banks/publication phase, actual D2D parameters and forward landings for every record field; compare the GEN manifest, static F16 programme and TXDP. Root requires HOLD until this common source-age truth passes. Historical PASS and current FAIL are both retained.

## Source patch and proposed admission after approval

original_die_chain.sh is the exact remote script. resume_die_chain.sh independently replaces protected hardlinks with checked reflink copies and requires OT_FROM=grt/OT_DIE_CLOCK_REUSE=1. It reuses saved TT/FF latency files and never rebuilds the rejected spine. It retains strict relay checks; no bypass or data exception was added. bash -n passes. This script is a proposal, not an installed shared helper.

After source-age proof and ROOT review, clone source and completed chain to a distinct diagnostic directory using ordinary copies/reflinks (never mutate original); overlay exact approved script and source-age checker/tables; verify ODB/latency/netlist hashes; clear only the new copy's old failure outputs; retain original library/view bindings and stand-in ledger. Run the existing chain from GRT with TT/FF, measured latency files, original12 routing iterations and repair settings. Report every original clock/stand-in failure. Do not regenerate the die or rebalance its spine.

Measured ep6 headroom:785GiB available,5.7TiB free scratch. A future unpinned ot-run --priority die --mem240 --threads16 --disk120 --dir <new staged diagnostic> admits the existing GRT160GiB/STA110GiB model with80GiB reserve; data locality can restrict eligibility without --hosts. New scratch estimated <60GiB (24.2GiB source/stages plus <36GiB route/STA copies), reserve120GiB. No CPU-load hold. Recheck actual memory/disk at admission. Root has not approved this launch.

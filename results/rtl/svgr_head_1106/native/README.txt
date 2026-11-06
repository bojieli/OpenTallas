Native RF1 whole service/SM proof vehicle, 2026-11-06

Source: candidate_split.sv and ot_svgr_rf1_skid_head.sv exact pristine
snapshots retained in inputs. prepare.py applies bench-only transformations:
existing native p26 face-shell composition + current split source;
SKID_HEAD1 is the actual data path into landing/cache/feed and the real SM.
A complete independent SKID_HEAD0 RF1 owner receives identical face inputs.
At each HBM edge, all controls/handshakes are compared. Every accepted
285-bit landing word and every valid request identity is compared on the
same edge. No output shift or throughput change is permitted.

Three tiny mutant helper shadows per PC receive actual main-owner push/pop
histories; their accepted head words/OK bits are compared against HEAD1.
MUT8 drops tail promotion, MUT9 drops push payload, MUT10 overwrites a held
head. Each must be caught somewhere in the actual native streams. This
avoids cloning the full SM for mutants. Whole original RF1 mutant1..7 proof
artifacts remain historical controls for unchanged mechanisms.

One full Verilator build is reused for ordinary landing, controlled landing
stalls, and controlled stalls plus a warm-reset/reinstall/replay. The fixed
host, x-load, router IDs, four real controller leaves, DRAM timing fixture,
face shells, feed, calendar, real die SM, and native golden output checker
are retained. L00 fixture contains the native20op suite. Each replay epoch
is checked separately for every golden output, every fixed GO calendar
slot, fault-free completion, and run count.

Heavy command: ordinary ot-run EP5 mem24GB threads4 disk15GB. ot-heavy
recognized run_native.sh measured peak11.7GB class (n3), charged20GB under
24GB cap. Actual dedicated scratch device2305 vsroot2304,220GBfree at
launch. No threshold overrides. Full old native compile measured1753s at
4threads; one build only, no arbitrary deadlines or additional sweeps.

EP5 root /srv/opentallas-scratch2/claude/codex-svgr-head-native
intel2 client log ~/hbm-gaps-5/codex_svgr_head_native.otrun.log
Completed PASS. summary.json retains native golden verdicts for all four epochs.
counts.json recomputes from raw logs: 51,048 same-edge old/new checks,
23,952 accepted 285-bit words, zero extra edges; each epoch has 20/20 ops,
81 output rows, 29 exact fixed GOs and 12,764 cycles. MUT8/9/10 are each
caught at every PC in stalled and warm-reset cases. Ordinary only sensitizes
MUT9. All three runtime cases exit0; ot-run RAN exit0.
Binary SHA256 efafaa9500caab6c63c9de150af29ccd6f30fade5187dbaa21a5a1af2fed7132.
Build1643s; complete command33m40; measured peakRSS24,039,816KB.
Guard capped build-j4 to-j2 using measured memory; memory.events allzero.
Source40139073ec3/alias9a0d2386bea. inputs/source_equivalence.json proves
tested60684b48 and packaged8fa8449f source tokens equal after removing
the helper include directive (explicit recipe module file instead).
No physical or timing qualification is implied by this source proof.

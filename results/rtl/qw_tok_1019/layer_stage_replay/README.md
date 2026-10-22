# Existing-binary Qwen vector layer replay

This packet restores missing staging inputs for the original REFILL-1225/QWLAYER campaign, preserving its failures. It changes no production RTL, lowering code, timing metadata, fixtures, compile flags, or closure helpers.

The original N12 Verilator 5.050 builds succeeded, but all 20 case outputs raised `FileNotFoundError` before RTL execution: their source snapshot omitted the entire `results` directory. In particular, the six negative controls returned 1 because Python failed; those were never causal negative witnesses. `original_failures.tar.gz` retains all 20 original outputs and both original outer logs. The original source, object files and binaries remain on ep7 at `/srv/opentallas-scratch/claude/refill-1225/QWLAYER`.

`dependencies.json` pins all six restored inputs. Five are byte-identical at the declared base `0d4c9808f` and overlay `416cd1a11`; the vector age file exists only in the overlay. These include the original historical die/relay/age metadata: this replay tests that exact lowering contract against the current staged RTL, without rewriting its ages or substituting a newer mapping. `dependencies.tar` holds the exact blobs.

`source_hashes.json` hashes every staged source file (19,731 files). `source_ancestry.json` compares the 40 compiled/runtime source and data files actually used to the two declared commits; all match. `compiled_sources.txt`, the two original build logs and `Vtb__verFiles.dat` records pin the N12/MUT0/NU1-or4 commands. `fixtures.json` pins the unchanged recorded TP8 NPZ operands and ISA expected results.

`stage_preflight.py capture` creates a new, isolated source snapshot and copies the old failure receipts. After extracting the dependency archive into that snapshot, its default mode lowers all 20 cases without running a simulator. All 20 preflights passed. `runtime_reads_preflight.json` records the opened source and input files.

`replay.py` uses four isolated processes. Its build entry returns an explicit existing binary only after checking its exact SHA256, so no rebuild is possible. Every invocation prints an `RTL_EXEC_BEGIN` marker and writes actual event and RTL log files in fresh case directories under `staging_replay_1019`. The two executables are:

- NU1: `7ba89595a8c4d2e77ba02e76479b2703237c426caf994cc8f2911ec698b8ce86`.
- NU4: `2b1db9ca2ff412ea081c66d66d135278960ed3044157e2af8cac96e295d073e1`.

Replay uses unpinned `ot-run --mem 16 --threads 4 --dir /srv/opentallas-scratch/claude/refill-1225/QWLAYER -- python3 replay.py`, unit `oth-ubuntu-93396-1792443790`, admitted on ep7 with measured capacity 963 GB. Preflight was unit `oth-ubuntu-91988-1792443761` (8 GB/one thread, exit 0).

`classify.py` requires actual nonempty RTL/event logs, the expected bench verdict and return code, complete positive ISA word comparisons, and byte-identical raw RTL/event traces between NU1 and NU4. Traceback return codes cannot count as causal witnesses. The three original controls alter the compiled AR-window timing, omit the SiLU normalization operation, and reverse RoPE signs. They exercise actual unchanged RTL through faulty command/program images; they are not new RTL mutation builds.

Scope: seven recorded vector cuts (L0/L1 residual1, SiLU, QK, plus L0 residual2), each in NU1 and NU4. NU4 is the per-user-capable configuration; these stimuli do not establish four independent request lifetimes or full token exactness. Matrix QKV/GU/OD cuts still require the compiler STN `kc` port.

## Terminal results

All 20 replays completed at 14:08 PT: 14 positive cases PASS and six causal controls FAIL for the required numerical reason. Classifier unit `oth-ubuntu-99383-1792444127` exited 0. All ten NU1/NU4 pairs have byte-identical complete raw RTL logs, event files, and bench verdicts. Each configuration compares 16,899 ISA words across its seven positives (33,798 total), all equal.

| Recorded cut | Positive checks per NU | ISA words per cut | Measured span (cycles) |
| --- | ---: | ---: | ---: |
| L0/L1 residual1 and L0 residual2 | 28/28 each | 4097/4097 each | 1109 |
| L0/L1 SiLU | 2/2 each | 1536/1536 each | 814 |
| L0/L1 QK | 7/7 each | 768/768 each | 926 |

Both configurations reject AR-window timing (`resid FAIL 4/28`, slice0 RB `0x41a6594a` vs `0x412e3b9a`); omitted normalization (`silu FAIL 1/2`, 24/24 words wrong/off-edge); and reversed RoPE signs (`qk FAIL 5/7`, Q512/512 and K109/128 mismatches). Every negative has actual RTL logs and the specific causal regex, with no traceback.

`classification.json` records all checks, fail regexes and per-log hashes/counts. `replay_results.json` hashes every generated case artifact; `replay_raw.tar.gz` retains all lowerings, stimulus, RTL logs, bench outputs and runtime read manifests. `raw/` exposes the twenty short bench receipts directly. All original object files remain intact, and no fleet job from this replay remains live.

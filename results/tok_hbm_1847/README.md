# Native finite-VM publication fragments, 2026-10-29 18:47 takeover

`tools/hbm_next/vm_phase_publication.py` now follows each SU1470 input row to its
actual final producer: A from SU1461, B from COLL1465. It slices those actual
producer records into three two-row fragments, checks the expanded source rows
are identical, and emits six native DMA.STORE + six native DMA.LOAD records.
The native DMA records retain each original source row stride (A20480/B25600),
pack scratch rows contiguously and reload the existing candidate workspace.
The actual input payload is245760 FP32 words and1,966,080 transferred bytes.
This constructs the previously missing producer/publication records; it does not
install a complete programme or establish old-VM capacity closure.

A concrete scheduling failure was caught during payload replay: workspace178224
intersects B source rows, including rows belonging to later phases. Reloading A
before all B publication completes destroys required producer values. The packet
therefore requires one complete publication epoch (all producer/store fragments,
DMA drain/fence) before any workspace reuse. Each phase subsequently reloads BOTH
operands, drains DMA, consumes, and drains the consumer before reuse. The native
records carry producer-unit/DMA wait masks; whole-programme schedule composition
and actual drain dates remain required.

`check_publication.py` decodes the emitted native records and replays all245760
payload words at their real source/destination addresses. Wrong HBM word, wrong
row stride, wrong VM destination, undersized scratch and unaligned scratch
controls are all caught. Producer row expansion preserves actual arithmetic,
rounding template, immediates, descriptors and slot identity. No RTL changes,
clock changes or added compute cycles are introduced here. Added DMA transfer
cycles remain unpriced pending the composed finite-phase schedule.

The scratch interval[0xF000000000,0xF0000F0000) is a CANDIDATE within the40-bit
native address field. It is explicitly unreserved: `scratch_ownership_confirmed`
is false. Producer descriptors intentionally retain the original source ABI,
including out-of-capacity VM addresses. The prerequisite still open is full
producer dependency/live-set relocation into the262144-word VM and allocator
reservation of disjoint HBM scratch, followed by downstream scalar-consumer
rebasing and model/RTL schedule composition. `executable=false` and
`full_programme_fits=null` prevent the fragment packet claiming fullfit/G5.

Reproduce from this branch:

```sh
PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 tools/hbm_next/vm_phase_publication.py \
 --image /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r \
 --compiler-tools /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools \
 --preparation results/tok_hbm_1355/phase_1470.json \
 --scratch-base 0xF000000000 --scratch-bytes 983040 --out /tmp/native_publication.json
PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 results/tok_hbm_1847/check_publication.py
```

The owner's18:25 option(a) already accepts HBM~1812–1830 tok/s for closure.
EP_S1 restation remains optional; this work does not replace that rate with an
unmeasured finite-phase claim. No new owner decision is needed.

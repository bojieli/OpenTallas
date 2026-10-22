# Conditional HBM P40 / R18 price

This receipt extends `hbm_price_qdq54_hc17_1021` without changing its scheduler.
The old result is incomplete for XR12 transport. These are model compositions,
not a new full-token functional qualification. Single-user AR only; HBM MTP is
still deferred, and no MTP rate is inferred from an AR count.

The original measured HC law is 1055 edges for the entire K20480 engine plus VM
legs. The P40 G22 post-only lowering has **absolute** after-launch offsets
gather row zero 51, tail launch 83, result 583. They are not additive penalties.
`hc_layer_lower_1021.root_rows` computes tail=g0+32 and result=tail+496+4.
Adding 51+83+583 to the full HC law would count the same work multiple times.

For the conditional P23 to P39 / QCHX11 to QCHX12 adoption, expose 16 extra
first-capture edges and one extra subtree edge once per HC record. Keep the
already priced k4 tail penalty495. Thus HC 1055 ->1567 (+512 total, +17 beyond
the previous receipt). There are80 DS HC records; extra occupancy1360 edges.
The +1 must not be charged again as an independent SYS and RAW cost: both are
derived from the same QCHX parameter. GATHER_PERIOD40 does not add a P6 train
cost to the P1 AR law.

R18 notice19:27 gives QDQ read round trip+75 and write/done+45 versus the
original law58 at RL7. The serialized read then write record is178 (+120),
replacing the previous105 (+47). There are40 DS QDQ records: total extra
occupancy4800 edges, or2920 beyond the previous receipt. Read/write/done are
not three independent write terms. `qdq_split_price.py` pins XR12/RL54:
RLI82,WCI18,rq offset15,wq/beat_done/record_done offset45.

Both terms have zero Qwen records. This does not mean Qwen is immune to the
separate L12 SU/SFU/xload/collective/index geometry repricing.

`run.py` reruns the existing `info_banklat_all` DS and Qwen scenarios for the
release h9b base and next-release m_xl_i8, once with the previous495/47 and once
with512/120. A third512/141 case is an explicit **sensitivity** if the selected
QDQ external RL54 becomes75; it is not evidence that R18 actually selected75.
Rates must be composed from the schedule difference with DS landing factor
0.9887 and Qwen0.9993, preserving the original receipt's baseline token cycles.

| Conditional source row | DS AR before -> after (tok/s) | Added DS token edges | Qwen AR (tok/s) |
|---|---:|---:|---:|
| Release h9b, P40 + R18 XR12/RL54 | 993.7 -> 993.7 | 0 | 537.4 unchanged |
| Next m_xl_i8, P40 + R18 XR12/RL54 | 1325.7 -> 1324.6 | 793.264 | 1001.5 unchanged |
| Release h9b, external RL75 sensitivity only | 993.7 -> 993.7 | 0 | 537.4 unchanged |
| Next m_xl_i8, external RL75 sensitivity only | 1325.7 -> 1323.4 | 1557.904 | 1001.5 unchanged |

The actual next-release schedule moves872584.7->873369.0 (+784.3), with
8 critical HC records and36 critical QDQ records. The prior receipt's
four-record QDQ slack slope cannot be extrapolated through this new schedule;
the fresh sweep, not the linear forecast, determines the table.
The release pair is1141116.4->1141116.4. Qwen schedule totals are byte-equal
within each paired case (2175485.0 release,1166485.5 next).

Validation: fleet ot-epyc7 unitoth-ubuntu-3661291-1792638901 exited0;
six existing census runs, per-record HC/QDQ counts80/40, occupancy changes
1360/2920, Qwen zero-record invariance, and result composition assertions PASS.
`census/` retains the12 underlying production-scenario census JSONs;
`sweeps.json`, `result.json`, and `fleet.log` retain the compact results.
Source baseline is052f71f2c; absolute re-run totals differ from the earlier
receipt, so only each freshly paired schedule delta is added to its preserved
token rate of record. No absolute current-die throughput qualification is made.

Run from the repository root on the fleet:
`python3 results/token_pass/hbm_price_p40_r18_1021/run.py /tmp/p40-price`.
Copy its `sweeps.json` beside `compose.py`, then run `compose.py`.

Existing proof is composable at component scope: emitter033af8d1e makes k31
P40 G22 post arithmetic/programme replay PASS12/12 on its unchanged binary;
candidate dc7b59b93/kit159e1454c has target positive and mutant1 fail evidence.
The k31 binary itself is SAFE0/QCHX11, so it is not a literal SAFE2/QCHX12
binary receipt. The candidate's kept s_i register explains the additional
subtree edge; coordinator adoption must preserve the explicit39/40 programme
and rootQCHX12 source binding. Physical c8p40/c8p40b gates remain separate.

## L12 geometry status

The19:35 notice is an illustrative r16q geometry, and explicitly says final
per-chain values come from each chain's S8 file. A full R18 rate cannot be
identified with a class-wide increment: bank-specific xload waves, selected
tap clients and read/write concurrency matter. Current measured laws replace
the whole record cost, so merely changing `rp_added` model knobs silently
leaves measured records unchanged. No full L12 rate is claimed by this receipt.

Outstanding deltas to map to selected production records: IDX VM+9/selector+10;
nw share+12; hcollrs SW+25/SE+5; SU read/write+4; xload bank vector increments
[3,3,0,0,9,10,0,0] plus R18 functional+1 every bank; argmax+10;
collective q2+5/q3+21/issue+20; SFU tap+8/terminal+12; QDQ RL59->75 in the
illustrative old geometry. Overlapping producer paths must be recomposed, not
blindly summed. Final source/geometry mapping is the missing input, not an
additional qualification campaign.

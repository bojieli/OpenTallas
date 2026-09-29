# Packed attention service boundary

The local service module `ot_chip_v41x_packed_attn_service` joins the packed
WINDOW HBM client, its four-bank stage, the ordered WINDOW/selected-CKV row
merger, and `ot_hdc_v41x_attn`. The 4 × 4,224-bit packed WINDOW response and
4 × 16 × 265-bit attention input remain inside that module. The selected CKV
source and remote row transport remain explicit external interfaces. They are
not implemented by this service wrapper.

## Job order and user lifetime

The scheduler latches the user, absolute first row and WINDOW row count when
it accepts a job. It issues one packed WINDOW HBM prefetch per row and waits
for `kv_ok` after each completed 17-sector transfer. Only after all WINDOW
rows are staged does it start the merger and attention engine on the same
clock edge. Incoming prime and block writes are backpressured throughout the
job, so they cannot overwrite the active user's ring tags. The bank stage
checks user and absolute-row tags on every read. A fault stops the job until
reset. The directed scheduler gate covers absolute rows 126–129, ring reuse at
254 for another user, and the last valid context row 1,048,575.

## Capacity and shared HBM demand

| Quantity | Value | Meaning |
| --- | ---: | --- |
| WINDOW packed payload | 528 B/row | 512 FP8 codes and 16 E8M0 scales |
| HBM row pitch | 544 B/row | 17 sectors of 32 B |
| Stage payload | 67,584 B | 128 rows for the active user |
| HBM slice per user | 69,632 B | 128 rows at sector pitch |
| Four-row engine beat refill | 68 sector requests | Serialized, one outstanding request in this RTL |

The adopted K channels also serve the pooled indexer and selected compressed
KV. RoPE table reads, if adopted, add another client. This wrapper does not
reserve channels or credit overlap against those clients. Its stage can read
four *already loaded* WINDOW rows per cycle. Its serialized refill path does
not establish a sustained four-row-per-cycle rate from HBM. The selected CKV
rows are separate 288 B FP4 rows and require ordered local/remote delivery.

The current ASAP7 256 × 256 SRAM profile would provision 68 macros for the
stage's 540,672 useful bits: 4,456,448 provisioned bits, 8.24× depth waste,
and about 0.482 mm² macro area. The bounded physical attempts reached global
route with estimated slack but failed detailed route at SRAM pin access; no
routed timing, DRC or power is established. Further route attempts should
change the macro abstract or placement channel before retrying.

`results/rtl/v41x_packed_attn_service.json` pins the scheduler simulation and
the composed module's interface lint to source. That lint uses an interface-only
attention-engine stand-in to keep the gate bounded; it does not elaborate the
full engine. Separate exact HBM WINDOW and row-merger
records are cited there. This is a functional integration boundary; it does
not yet prove a full mixed token or a final throughput number.

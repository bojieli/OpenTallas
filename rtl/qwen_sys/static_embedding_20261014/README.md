# Selected HBM embedding static successors

The selected embedding remains the existing W8 table in external HBM, initialized
by `qkd_embgw_splitboot` / HOST `hb283` / four `qkd_land_emb_ifw` paths. The format
is 128 little-endian 256-bit INT8 code sectors per 4096-element token row, then one
BF16 scale per row packed sixteen per scale sector. Scale sectors start at logical
E=19447808. No new quantization or resident embedding ROM is introduced here.

These modules replace specific normal-execution mechanisms; they do not replace
or alter the initialization exception engine or the historical closed modules:

* `qkd_embedding_static_map` reproduces the selected sector/stack/PC/bank/column/
  row mapping, including the scale region at HBM row 24427+148.
* `qkd_embedding_static_pc` emits a read on the persistent controller's actual
  es288 face on the compiler issue cycle. It retains the issued token, word,
  half, scale and epoch. The separately compiled return slot must coincide with
  actual er261 valid. No readiness, credit or pending bit postpones issue or
  return. One outstanding read per PC is an asserted capacity contract.
* `qkd_embedding_static_join` receives actual code low/high halves in reserved
  transfer order, checks their issued identity, and registers one 512-bit code
  word. A scale beat selects the actual token's BF16 lane. This adds one edge.
* `qkd_embedding_static_preload_face` registers that producer into the SU preload
  ports and verifies actual token/word/scale/epoch against the compiler slot.
  It forwards actual producer epoch and the compiler's fill epoch. This adds
  one edge; missing data never creates a delayed launch.
* `ot_qfd_su_embed_static` uses the existing exact 64-lane INT8 decode and the
  actual `ot_sram_1r1w_64x512_m1_r2c2` row buffer. The compiler fills 64 code words
  plus a scale before GO. GO passes at its compiled edge; a missing, duplicate,
  wrong-token or late preload faults instead of holding GO.

The consumer alone passes eight released full rows (32768 exact FP32 results),
with failing missing-preload, wrong-token and early-GO controls. The word join,
epoch face, mapped SRAM and decoder composition passes the same rows, with
failing wrong-epoch and missing-actual-beat controls.

The persistent-controller component test uses real es CDC, shared scheduler,
SROW, physical PO register, PC port/ECC and er CDC. Its only HBM substitute is an
explicit external raw PHY/memory model populated from the released image. A
PROFILE1 process records legal column and actual return slots; a separate fresh
PROFILE0 process consumes only the frozen calendar. Eight code-half reads and
one packed scale-sector read pass with declared core 833.334 ps / phase 137 ps
and HBM 1024 ps clocks. Shifted column slot, shifted core return slot and missing
raw PHY valid all fail. The measured code-read issue-to-return spans 72..92 core
edges; no constant latency is inferred. These are declared component clocks,
not the as-yet-unbound production die clock phase.

This evidence does not establish a full 128-PC embedding calendar, routed native
pins/clock phase, the normal PC-to-gateway transport, or a full-token result.
The old splitboot gateway and landing runtime contain credit/FIFO readiness and
remain historical for normal production until the static successors are bound.
Boot exception flow control remains the selected initialization mechanism.
The die lead must assign the static transport geometry and source contracts;
no additional physical route or alternative resident ROM is claimed.

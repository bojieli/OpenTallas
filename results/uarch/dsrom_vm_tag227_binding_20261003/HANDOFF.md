Usable minimal component TAG227 interface for Popper/Cicero

This is COMPONENT_TAG227_V1, a NEW explicitly named component-experiment packing. It is not a recovered released production full169 encoder or wholeC8 qualification. The existing logical169 field list is a software proposal; no authoritative production wire encoder was found in the scoped search. The backend accepts opaque TAG_W227. Its 47-bit installed stage identity does not prove the production context.

Header: tools/native/dsrom_vm_tag227.hpp, namespace dsrom::component_tag227.
Source hook: tools/native/dsrom_vm_tag227_source_hook.hpp.

Bits LSB first:

    0..46 identity47 = {epoch16,user10,position21}
    47..63 token17
    64..70 stage7 (0..80)
    71..72 rank2
    73..84 pair12 (0..2416; NEVER expert9)
    85..94 phase10
    95..108 entry14
    109..168 RESERVED ZERO (60 bits; not claimed owner payload)
    169..200 reset_era32
    201..216 batch16
    217..226 request_id10
    227..255 storage padding ZERO

Root authorizes epoch1/user0/position0/token0, identity47=1<<31, resetera1 for THIS experiment. Stage/rank/pair/phase/entry must come from the actual compiled selection and held source offer. No stage37/default/local-expert assumption. `experiment_context(stage,rank,pair,phase,entry)` validates the choice but does not prove its source. The installed native phase/pair/cfg callbacks must be enrolled by Popper/Cicero.

Integration sketch (names below are caller-supplied ACTUAL fields, not library getters):

    using namespace dsrom::component_tag227;
    SourceOffer offer{actual_identity47, actual_token17,
                     compiled_stage, compiled_rank,
                     actual_pair, actual_phase, actual_entry};
    SourceOfferHook ids(offer, actual_reset_era, actual_batch);
    auto tag = ids.tag_for_offer(offer);  // immutable while request blocked
    copy_to(tag, dut.rd_owner);          // read tag, 8 little-endian words
    copy_bank_to(tag, bank, dut.wr_owner); // write tag, 227*bank BIT offset
    // PRE-edge, rst_n and true backend accept strobe, once per accepted command:
    ids.on_backend_accept(actual_rst_n, actual_accept, offer, sampled_tag);
    // Matching QUALIFIED retirement, not raw N+3 receipt:
    ids.on_qualified_retirement(returned_tag);

The four-bank bus is 4*227=908 bits /29 words. Tags cross storage-word boundaries; NEVER copy bank b into word8*b. Initialize unused bus storage to zero. `read_bank_from` extracts an ACK tag using the same bit offset, preserving all other bank fields. Root/physical shard/direction/source-family/writer-winning/address/mask/debt qualification is separate: this minimal tag does not manufacture it or claim route metadata inside reserved bits.

Request IDs increment only on actual accepted source requests. Blocked offers keep the same tag. A duplicate/stale accept or retirement rejects before ledger mutation. Request ID1024 refuses another offer; all own accepted debt must retire before advancing batch. Batch65536 and era2^32 reject, never wrap. Era advancement also requires source quiescence; a local empty ledger alone does not prove whole-provider reset safety. No source credit, VM lease or publication debt is released merely by packing a tag or matching raw data.

18 focused tests pass: exact integer-oracle packing, all field overflows, stage81/pair2417 rejection, pair2416 preserved, nonaligned four-bank slices, high reserved/padding rejects, held-source change, no acceptance on reset, duplicate/stale tags, live-debt batch/reset rejection and ID/batch/era exhaustion. Initial compiler indentation failure is retained separately; no warnings waived. Run:

    python3 -m pytest -q tests/test_dsrom_vm_tag227_binding.py

No provider/whole-array build, proof campaign, RTL change or peer-file edit. Actual source hooks/trace enrollment and qualified visibility remain owned by Popper/Cicero. This header is usable independently and requires no provider linkage or Verilator headers.

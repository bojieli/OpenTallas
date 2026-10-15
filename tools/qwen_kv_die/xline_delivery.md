CURRENT STATUS (2026-10-14): HISTORICAL SNAPSHOT UNIT ONLY; NOT ADOPTED.
The descriptions below preserve the original two-root512-line experiment.
Current native delivery candidates use actual accepted IB/context/version,
40-bit per-query identity and one128-bit cache response per tile query.
They must preserve changing k/j address and captured normalization mode.
No snapshot cost, old508-bit packet, two-root route or dictionary149-bit
lower bound qualifies the current production transport.
See results/arch/qwen_delivery_lifetime_1014/contract.json and the
source-hashed current_native_inventory_index.json in
results/arch/qwen_tp8_native_abi_1013 for current obligations and open gates.

CRITICAL SCOPE CORRECTION (2026-10-13): this unit protocol proves one snapshot
of512quad lines only. It is NOT a full matvec delivery implementation.
ot_qwen_w12_matvec.sv changes x_addr on every active issue edge according to
xbase+c*xcs+k*xks+j*xjs. Holding one xl perEXEC gives incorrect products for
nonconstant k/j addresses. Production integration must wait for a multiepoch
cache/replay or sufficient parallel continuous delivery, plus exact full ME
bench. The measured515+D_t is one snapshot latency, not full instruction cost.

TP8 distinct x-line delivery (2026-10-13)
======================================

rtl/hdc/ot_qwen_me_array_w12.sv selects xl_d[(tile_id % NXL)*128 +:128],
NXL=512. tp8b has 768 tiles (48 columns x16 rows); broadcasting one selected
quad line to all tiles does not implement this expression.

The existing 508-bit corridor can carry a LOAD stream without pin changes.
The packer always sanitizes an inactive packet to zero. LOAD is go=0,
ib[378]=1, ib[377:9]=0, ib[8:0]=line index, xl=selected quad line. EXEC is
go=1 with all379 instruction bits preserved. The line marker has no meaning
when go=1. Existing core ignored instruction operands while go=0; this is a
new explicit protocol at the ctl pin, not a claim about arbitrary legacy
inactive ib values being compatible.

Each root requests all512 indices sequentially. Tagged, single-edge VM
responses are encoded as LOAD. Each tile captures only its tile_id[8:0]
line. Root emits EXEC on the edge immediately following its512th accepted
response. Local captured line is stable before EXEC arrives at every tile
because LOAD and EXEC follow the same station/relay path. No global-path
flush is needed. The tile helper feeds the existing core IREG inputs directly
and invalidates its cached line on EXEC. Missing/replayed line suppresses
go and raises sticky fault; malformed LOAD faults and does not update cache.
Reset clears data, valid and fault. Root detects response reordering and
repeated start; missing VM responses require existing reset/recovery, with
no silent timeout completion. Instruction scheduler must wait for normal
compute completion before accepting a new instruction.

VM split/descriptor must be latched before the first request and its line
store must remain stable through selection of all512 lines. Root response
valid is a pulse in the die clock domain; an enabled-edge VM implementation
must not repeat a held valid when me_en is low. VM tags traverse the exact
same enabled stages as data. Current root assumes one request each die edge
and VM remains enabled throughout the512-request burst. Any stalls increase
wall-clock cost and must be priced, not collapsed into enabled-cycle counts.

Measured with Icarus benches:
  tb_qwen_xline_roots: 512 requests; W select3 => EXEC515 edges from first
  request; E select5 => EXEC517 edges. Independent response paths verified.
  tb_qwen_xline_delivery: 768 tile IDs, all512 distinct quad lines,2 epochs,
  1536 executions through real ot_qwen_die_station paths1..31; at each tile
  EXEC consumes the exact line and full379-bit instruction. Stream512 edges,
  no extra capture edge, measured tail543 edges from first LOAD on path31.
  MUT_IGNORE_ID=1 broadcasts the last line and MUST fail the exact scoreboard.

Production selection latency3 gives request-to-EXEC at tile515+D_t edges,
where D_t is the actual root->station->relay->tile tap depth. Existing ctl
IREG/compute/tree latencies follow unchanged. Difference versus delivering
one already-selected line then EXEC is511 extra streaming edges per issued
ME instruction, plus any selection/setup/changed path costs. Absolute
XREAD/ME price requires the actual die depth table and full layer simulation.
There is no measured native TP8 token-rate qualification here.

The512 stream is deliberately geometry independent: every tile ID modulo512
receives its required line even when both halves need overlapping line sets.
A384-edge optimization is legal only after verifying the actual physical
tile_id straps and per-root unique ID sets. c*16+r is not assumed: generator
currently publishes no authoritative tile_id strap connection for ROM tiles.
The die binding must carry the same16-bit tile_id as the functional array.

Integration: add ot_qwen_xline_capture inside ot_qwen_tile_ctl (130 flops),
raw xl/ib/go pins -> helper -> u_logic IREG inputs; OR helper fault into ctl
fault register. Station and relay views remain unmodified. Instantiate
ot_qwen_xline_roots in VM/control-side composition, couple VM independent
W/E selections (same index sequence, independent responses), and replace
raw instruction broadcast with its xw_d/xe_d packet outputs. This helper
commit is an executable protocol unit; production root/ctl integration,
new tile physical view, actual-depth measurement and end-to-end layer proof
remain mandatory.

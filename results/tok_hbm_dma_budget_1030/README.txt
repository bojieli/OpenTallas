Current interpretation supersedes the service scope of the earlier v1 receipts.

The earlier budget.json/budget_physical_capacity.json/budget_mtp_tail_unreserved.json
inventory exact native command bytes, but their148033/149811cycle sums assume a
GENERIC ot_hgi_dma_mover with32B/cycle LOAD and optional64B/cycle KVW STORE.
Those are hypothetical engine numbers, not the CURRENT native source service.
They must not be used as a current-native floor, additive token cost or rate.

Current d31t/b31t asbuilt source top_native.sv directly instantiates two
static_vp4_banks_cp BACK engines hb_dbk_NE/NW, both stk2, RR_RT80, with eight
256bit bank responses (maximum256B/cycle port width). Their source-consumption
calendar differs. Current LOAD dispatch and VM namespace ownership are unproven.
Scratch encoded for stack3 has no established dispatch/VM ownership in that source.

The physicalcapacityFAIL for old stack3local28GiB remains exact: actual static
BACK, generic FRONT/BACK and source model all use22,500,000,000byte STACK_BYTES.
The new0x1d11000000tail fits capacity but remains UNRESERVED and nonexecutable.
Only the v2 scoped receipts express the current source interpretation explicitly.

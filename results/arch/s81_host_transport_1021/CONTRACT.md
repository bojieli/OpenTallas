# S81 HOST transport disposition, 2026-10-21

Status: **HOST(b) remains unimplemented; preserve existing host-capable source**. This packet does not authorize HOST_EN=0, a circuit reroute, or a release closure claim. No canonical RTL, hard views, pins, calendar, or rack file is changed. Source base is aff1c1ca862cc0cda48be402cbd5d993171a0ea9; actual head contract is HD-CTL b4f571642. The source snapshots under source_head are byte-for-byte git objects from that head commit.

## Actual head contract

HSF0 consists of 553-bit lane flits: last[552], type[3:0], rank[5:4], group[7:6], reserved[15:8], payload starting16. Host1 CSRW type6 configures only head-local state (addr[23:16], data[87:24]); it does not target stage seq_host. Host0 HFWD type7 transports 512 data bits [527:16]. HD-CTL emits this payload in a ring beat: v[0]=1, kind[3:1]=6, hops[8:4]=1, payload[532:21]. It emits dsfd_mtp_seq output in the same envelope, kind5. STATUS type8 is head-local fault/accumulator state. RESULT type9 copies the head-generated token flit to host0.

The MTP token-output stream contains both RESULT (inner type[19:16]=2) and DRAFT (inner type4). RESULT token is the 21-bit IDX field[81:61], position[60:40], user low[39:32] and user high[152:151]. HDR_TOK[134:114] is a distinct field and must not be mistaken for RESULT token. DRAFT stores count[250:248] and token list starting256. Therefore a generic kind5 -> f_ks splice is incorrect. An implemented receiver must distinguish RESULT from DRAFT, preserve all user bits, associate the RESULT position with the next start, and retain its token until each stage's static start edge. For later stages the needed token is the input token for that position, not that stage's KIT output.

## Existing host path, explicitly preserved

s_7N host-capable endpoint ot_s81sl_lep_mu_h / ot_s81sl_slice_lepe_mu_72 implements HOST_EN=1. Legacy link frames are **not ring beats**: bit0=0, type[3:1]=1 HOST or2 KS, payload starting4. HOST payload is514 bits = {class2,data512}; KS is53 bits = {start,user10,tok21,pos21}. PairB cannot receive these frames. The current release die binds f_ks to both seq_host and Engram, via its existing hf_7N / eks_7N chains. Existing t_kd preserves {done,tok21,user10,pos21,0} in MU mode, and THOST/TKD non-ring frames leave the same host-capable endpoint.

HD-CTL HFWD kind6 is accepted by the endpoint as ring traffic, not as legacy HOST. Its512 bits also omit the legacy class2. Neither HFWD nor head CSRW currently defines a stage-address/class envelope. HD-CTL forwards inbound non-XB ring beats unchanged; it does not collect returned stage status or KIT records into its host STATUS/RESULT lanes. Merely retaining host RTL does not fix the rack's missing host peer; existing LINK5 circuits connecting s_7N to a stage peer are not a functional host service.

## Required completion before removing the legacy path

1. A source-bound ring tap plus token context store at every stage, feeding both existing seq_host and Engram f_ks on a local static start. Forwarding must not alter XB or lose the full21-bit token or10-bit user.
2. A defined destination/class/length/identity envelope within HFWD's512 data bits, plus stage RX tap and forward. With no metadata in existing HSF0 there is no implicit mapping to514-bit f_host. Boot CSR sideband needs actual die CSR wiring and a boot/write-vs-active check.
3. KV-ingest transport preserving class, descriptor/address/data/marker ordering and production write bandwidth. Management sideband is a possible source only with an explicit measured rate and prefill cost; it is not a decode-rate argument.
4. Fixed-calendar return injection for stage t_kd / t_host, a collector at the head, and explicitly defined host egress messages. Existing HSF0 RESULT has a different meaning; do not silently reinterpret it as stage KIT.
5. Real die bind/landing changes, preserved original endpoint view or separately gated new masters, a collision-free calendar, and a minimum RTL bench covering head->stage(s)->head with invalid class, wrong user, wrong destination, late token and missing return controls. New physical masters require the binding safe-design review and SS/FF qualification.

These changes span independent masters and die pins/landings; they are not a bounded local-start/CSR edit. This lane therefore produces a concrete non-adoption packet and a source-pinned preserved-path bench, rather than an unbound default-off module presented as a complete transport.

## Costs and limits

* Actual source change cost in this packet: **0 cycles,0 added dies,0 added hardware**. This preserves functionality already present in source, not host connectivity/physical closure.
* The proposed minimum token forwarding cost is one extra ring beat/user/token/hop. Against the LINK5 321-beat h crossing that is1/321=0.3115% more beats for that message, not zero transport work. Its impact on the complete AR/MTP slot needs the actual calendar; LINK5's ~0.006% slot estimate is a MODEL, not this bench's measurement.
* Current release has241 stages x4 TP ranks =964 stage dies. A dedicated retained-host pair per stage die would require964 additional host circuits /1928 lane endpoints on stage dies, plus host-side endpoints and cabling. At the head spec's518.4x3844.8um SerDes outline, two extra stage-side slots cost3.98628864mm2/die,3842.78224896mm2 across964 dies. This is a conditional minimum geometric cost, excluding controller, lanes, channels, host-side silicon, power and reticle rearrangement. No approval or fitted rack proposal is claimed.
* A management path of R bits/s carrying B bytes has unavoidable wire time8B/R seconds, excluding framing: per MiB,8.388608ms at1Gb/s or83.88608ms at100Mb/s. No management rate is specified by current sources. Do not substitute a guessed rate or zero KV-ingest time.
* Existing LINK5 head-host cost134 cycles/user/token =111.67ns at1.2GHz is a MODEL estimate. This bench checks bit/cycle protocol correctness at the endpoint, not that system latency or sustained prefill rate.

## Reproduction

Run tools/s81_dv/host_transport_1021/run.sh OUTDIR from this source commit on an admitted fleet host. The bench uses the actual ot_s81sl_lep RTL plus its real lane/PHY wrappers, and the existing production-shape host test. It adds explicit HD-CTL kind5/kind6 envelopes, verifies they stay ring traffic with no accidental f_ks/f_host event, and checks the legacy53-bit KS and514-bit HOST paths using full-width token/user/class values. All normal bidirectional THOST/TKD/status-merge traffic remains enabled. A PASS demonstrates preservation and the protocol distinction; it does not demonstrate HOST(b).

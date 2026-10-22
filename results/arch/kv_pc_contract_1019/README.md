# PC / PC_H source contract model pickup

Status: **INCOMPLETE model audit; no RTL, synthesis, CTS, route or submission.**
Claude returned during this finite task. Stop instructions arrived after the read-only existing-ODB metadata extraction was admitted. The fresh owner must collect and independently review it. The original terminal packet is commit `1248d0585`, branch `codex/kv-pc-terminal-1019`, stable `/home/ubuntu/artifacts/kv-pc-terminal-1019/README.md` and `remote_objects.json`. Original routes remain untouched. Both tiles require structural repair; PC WARN, PC_H FAIL with TT hclk boundary spread 81.1 ps. Neither gate qualifies a successor.

## Frozen source facts actually read

Frozen gate source snapshot started at `0eed5271d3e716b89aa2fc6c21841cbd61b74f51` with daemon overlays; use the terminal manifest, not revision identity alone. Source: `src/rtl/qwen_sys/static_kv_20261014/qkd_kv_hbm_elastic_front_mc.sv` under the immutable PC gate below.

* Defaults NBLK=4, BLK=8 give DEPTH=32 and a 297-bit `{epoch16, co[281:1]}` word: 9504 declared storage bits. The prior mapped report records only 9216 storage FF; **the 288-bit difference has not been traced** and must not be silently equated with this declaration.
* Four banks have LO=bank*75 and WD=min(75,297-LO), hence widths 75/75/75/72. Each writes `bank_mem[wp[AW-1:0]] <= land_d[LO+:WD]` on its own `posedge pll_hbm_data[bank]`, conditional on `land_v`. The source explicitly assumes four independently delivered phase-aligned storage clocks. These are real source clock ports, not interchangeable with ck/hck.
* Reads are asynchronous `mem_rd[LO+:WD]=bank_mem[ra_c[AW*(bank*4)+:AW]]`. Although NG=16 kept pointer instances are generated, bank indices use only copies **0,4,8,12**. This explains why merely seeing sixteen declared copies is insufficient to establish distributed mux selection.
* Each pointer copy obeys `if(!rst_n) q<=INIT; else if(adv) q<=q+1`. Its data/reset/polarity and enabled hold behavior must all remain exact, including uninitialized storage and arbitrary reset edges.
* `out_q` captures mem_rd on `posedge pll_hbm` when `take`; source says first put is three edges after blk_go and supports back-to-back last-take/start. No storage redesign may silently add a read edge.
* Source orders `pending <= pending + go_q - start`, increments wp on land_v, increments rp and cnt on take, and separately handles start after emitting logic. Simultaneous priorities, overflow/go sticky faults, hold, drain idle, epoch, and storage collision behavior belong to equivalence, including invalid payload where the interface demands it.

## Bounded proposal before implementation

An opt-in exact mapped fork can partition true high-load semantic roots into kept state copies, using actual driver equations rather than buffer exceptions. Preserve the frozen original module/defaults. For each copied FF, record original primitive, D equation, clock edge/net, async set/reset polarity, initialization and simultaneous-control priority. Enabled copies require identical hold/feedback equations; any proof relying on zero initialization is invalid for unreset storage/control. Every cloned load must be reassigned explicitly, and all upstream logical-pin loads recomputed through BUF/INV after the change. Recursive copying may increase upstream load and must converge with a complete certificate.

Using a target 24 logical pins solely as a **lower bound**, the already reported roots need at least ceil(2405/24)=101 copies (+100), ceil(2179/24)=91 (+90), and ceil(1994/24)=84 (+83), respectively. These are individual-root lower bounds, not a full block estimate or proof that total +273 suffices. Clock sinks, feedback, comb-driver splitting, reset loads, constants, area and mux-select/data reach require the uncapped actual census. No copied area or timing estimate is claimed before that accounting.

The >2 kb runtime-indexed storage must be resolved separately. Preferred model candidate is four width-banked 32-entry SRAMs retaining their exact storage-clock domains. Existing async-read behavior captured by a distinct pll_hbm clock cannot be replaced by a synchronous-read macro without proving a legal read phase, collision semantics and unchanged take/output ages, or pricing an explicit added edge throughout the static schedule. No suitable macro/view or no-edge replacement is identified here. Flop copying alone does not satisfy the storage rule; no storage waiver is proposed.

## Completed metadata extraction / next pickup

Completed exit 0 (11:24 PDT), output copied to `/home/ubuntu/artifacts/kv-pc-contract-1019/{pc,pc_h}`: **ot-heavy unit 1082638-1792434202**, local exec session **80289**, host **ot-epyc8**. Local log `/home/ubuntu/artifacts/kv-pc-contract-1019.log`. Remote lane `/srv/opentallas-scratch/claude/kv-pc-contract-1019`, script `native_census.py`, outputs `pc/` and `pc_h/`. Container image `openroad/orfs:asap7lock` ID `sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`. All own fleet jobs are terminal; no extraction should be duplicated before reviewing these outputs.

The committed script reads immutable `1_synth.odb`, never writes it, and proposes complete driver records plus canonical BUF/INV-transparent component endpoints and first-FF boundary ownership. Its output is **unvalidated**. In particular verify ODB direction enum strings; identify every native FF/macro/constant master; check clock classification and multi-driver/cycle handling; distinguish clock/reset endpoint roles rather than relying only on net names; compare primitive inventory with the original mapped Verilog; bind each fixed boundary bit to actual physical faces and detect shared FF across faces. The script's first-FF traversal may include combinational cones; a large owner set does not prove registered pin ownership or reach. No claim of complete uniform census, source safety, fixed-face closure, or no-edge equivalence is made by this pickup.

Immutable gate bases on ot-epyc8:

* `/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_pc_rl1-20261019-064619`
* `/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_pc_h_rl1-20261019-064619`

Within each: raw/mapped Verilog `routes/gate/work/orfs/1_2_yosys.raw.v`; synth ODB `routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_{pc,pc_h}_asap7_ref_gate/base/1_synth.odb`; terminal GRT ODB same base `5_1_grt.odb`. Exact SHA256s are pinned in copied `remote_objects.json`.

Fresh owner should finish full census and source/storage model, then obtain ROOT source-model review before any opt-in RTL implementation. Actual native reach, geometry, clock insertion/spread, reset propagation, TT setup/FF hold, producer throughput and compiler/parent ages remain open.

Raw unreviewed synth-ODB census: PC 181331 cells/39989 DFF-name FF, PC_H 180521/39690; FF logical maximum2405 with188/184 FF drivers above32, top input maximum3/reset2. These differ from prior textbook41933/41634 FF: reconcile stage/master coverage before using aggregate costs. Raw comb counts include BUF/INV intermediates by design, and top-clock classification currently uses a port-name heuristic (10ports). Do not present these diagnostic role summaries as the requested fully classified uniform census. Compressed full drivers/roots/cells/boundary outputs are retained at the exact remote and stable local paths with artifact_manifest.json SHA256s.

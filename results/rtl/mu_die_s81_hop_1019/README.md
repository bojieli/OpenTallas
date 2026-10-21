# MU-DIE-S81/HOP (10-19): the end-slice stage hop is lowered as XB beats

Branch `claude/mu-die-s81-hop-1019`, off MUWIN `claude/mu-die-s81-muwin-1019` @2244fc3c0.

## The gap and the decision
MUWIN found three problems:
- `substage_hop<i>` was still a GAP op;
- where the hop was planned, it used RD beats, but the MU window of the lep accepts only XB / XQ beats (the MU tag
  rides in spare bits [1077:1045], MU-S81/LINK 258c9894b);
- the endpoint `.fault` is unconnected in die.v.

The parent decided to lower the hop as XB/XQ beats, with no RTL change.

## What changed
`tools/s81_dv/layer_prog/lower_vpx.py` now has `lower_hop`, which lowers every `substage_hop<i>`. Per end slice
(s_7N / s_7S E, s_0N / s_0S W):
- one send config (CTL target 4): kind 2 XB, hops 1, outward dir, 3 pairs a beat;
- then two vp RDOUTs of 120 row pairs each. A vp command can step at most 128 pairs (vp rows step by `si[6:0]`), and
  the second RDOUT goes one edge after the first completes, so it never hits a busy vp.

The xr packer emits 80 XB beats, one every 3 cycles, onto the lep `ro` at fixed edges. Each beat carries
`hop` / `beat` in the schedule events.

On RTL as built, only the xr send packer can drive the outward port with an explicit hop count. vq's own XB beats take
the line-default hops and never leave an end slice.

**Why 3 pairs a beat (a finding, not a choice):** xr packs the pairs at beat [1075:52], which is the RD layout.
- With 4 pairs, the bits of pair 3 at [1077:1045] are overwritten by the window stamp and zeroed by the RX strip.
- Worse, an unstamped data bit 1045 = 1 is taken as a tag (`tagd`). A single-user beat would then be landed or
  stripped.
- With 3 pairs (768 b at [819:52]), the tag field is zero.

**Rows.** The 4 end slices share 8 V rows per hop. Per tier, each RDOUT is one CTL beat slice-masked to both end
slices; each end slice has its own config, one edge apart. 12 rows split the L0 calendar inside the hop. `split_jobs`
now never cuts inside an atomic op: the hop's rows stay in one issuer job.

**`dv_mu_win`.**
- The TX window is anchored on each end slice's first lowered beat (LEAD_TX 4).
- The window closes after its NB-th beat.
- New check `hop_beats`: exactly NB 80 lowered beats per window.
- `port_alone` excludes the window's own beats.
- The replay stays anchored on the priced hop end: the receive side is elastic and offdie.
- Status: `TX LOWERED`.

**`dv_cut_replay`.**
- `--mu-win-kinds` (default `tx,replay`).
- New mutant `mu-win-ab:<ev>` (wrong copy).
- With a compiled + lowered table, the replay is SCHEDULE instead of DIAGNOSTIC.
- `gen` writes `ep_expect.txt`: every ring beat the probed lep core must push, as (edge, pair, kind, MU tag
  {pos, user, land, 1}).
- New `epcheck` compares it against the bench probe output.

**`dv_slice_tb --ep-probe INST`.** At the end-slice instance, the bench observes:
- the lep core frame mux: `EPB` lines with the edge, pair, kind and tag of every beat on the `ro` pin flop;
- the fault sources: `EPF` lines for ep (master `.fault`), te (TX window), land, mcol, sl, ln and io.

The die leaves `.fault` unconnected, so the bench is where these are seen. Without `--ep-probe`, the tb is
byte-identical to TOK's.

## Single-user output (`compiler/su_diff.json`, vs the LINECOL SU programmes, same tree)
For L0 / L14 / L20, the non-hop calendar rows (absolute edge, engine, resolved CTL / gunit payload) and every non-hop
schedule event are identical. Only these change:
- `substage_hop0` goes from GAP to PARTIAL;
- 8 hop rows and 332 hop events are added;
- the job split point moves (job 1 starts at L0 11,166, L14 19,640 and L20 25,539).

## MU tables (compiler/prog_*/mu_win.json, tree = TOK tree_mu, calendar_ar_q4, fixtures layerbench-s81)
| layer / copy | nw | RL | TX D (ep 0..3) | first..last beat (ep 0) | replay D | verdict |
|---|---|---|---|---|---|---|
| L0 A | 46 | 10,589 | 8,061 / 8,091 / 8,100 / 8,102 | 8,123..8,361 | 8,983 / 9,005 / 9,007 / 9,002 | PASS |
| L20 A, B | 23 | 24,960 | 22,432 / 22,462 / 22,471 / 22,473 | 22,496..22,734 | 23,354 / 23,376 / 23,378 / 23,373 | PASS |
| L14 A, B | 23 | 19,268 | 19,715 / 19,745 / 19,754 / 19,756 | 19,710..19,948 | 20,637 / ... | **FAIL d_range** |
| L2 | | | | | | not compiled: waits on hwin NEV 16 (MU-S81-2) |

**L14 cannot hold its hop in issuer job 0.**
- L14 has 120 non-hop rows before the hop. With the hop's 8 rows that is 128, over the NOPS 128 - 2 row cap.
- The hop therefore runs whole in job 1, which starts at layer edge 19,640, after job 0's KIT (age 19,261 from layer_issue0 -64).
- The hwin D is measured from the job-0 f_ks capture, and RL = the job-0 KIT age + 7. So no MU event can come after
  job 0 ends, and the compile refuses.
- This is MUWIN's "multi-job layers" item, now binding. It needs a per-job MU start (f_ks per job), a bigger NOPS, or a
  hwin row mode measured from job 1.

## cut_7 replays (TOK's cut_7 on the mu1 die.v, kit K_cut_7 + the probed tb; Verilator 5.050, fleet ot-epyc7)
`R_cut_7_L0_hop012` drives users 0/1/2 at 0 / 21,312 / 42,624 with the compiled TX windows (`--mu-win-kinds tx`). The
generator identity check passes.

The expected endpoint traffic at u_s_7N and u_s_7S is 564 beats:
- 480 hop beats, all tagged (2 ends x 80 x 3 users);
- 84 untagged a_allgather RD beats.

Before this branch, MUWIN's cut_7 replay checked 0 lanes.

**Why the replays are not driven.** The cut's RX link lanes have no peer die. A landing replay would read an empty
slot, which is a correct `dsdv_mu_land` fault. RX landing and replay are proven in the LINK pair bench (258c9894b).

| run | stimulus / build | expect |
|---|---|---|
| out_base | base | epcheck PASS: 480/480 hop beats on edge and tag, no te / land / mcol |
| out_base_tagdrop | `mu-win-drop:0`: the u_s_7N TX window is never opened (tag dropped) | FAIL: the 240 u_s_7N hop beats are untagged |
| out_base_wrongcopy | `mu-win-ab:1`: the u_s_7S command carries ab = 1 (copy B) on an AB_EN 0 endpoint | FAIL: te fault |
| out_rtl_tagdrop | base stimulus on a `+define+OT_S81SL_LEP_MUT_TAGDROP` build | FAIL: every hop beat untagged |

The RTL WRONGCOPY mutant cannot fail on cut_7: both of its masters are AB_EN 0, so `wab` is 0 either way.

Runs: `bench/fleet_cut7.sh` (two ot-run jobs, --mem 300, Verilator 5.050). Collection and checks: `bench/chain_ep.sh`.
Its results go to `/home/ubuntu/scratch/mu-die-s81/hop/runs/out_*/{epcheck,check}.json`, and its log is
`logs/chain_ep.log` in that scratch dir. The verdicts are owed (see pending_results).

## Owed (parent / RTL)
1. **h payload layout.** XB beats from the xr packer carry 768 b clean of the tag field. So NB 80 beats move 7,680 B of
   the 10,240-B share. The peer gather also reads an XB beat in the vq layout (gidx [20:13], bf [1044:21]), so the hop
   beat arrives 31 b shifted with gidx 0. Exact h transport needs one of:
   - an xr XB-layout pack mode (pk at [1044:21] for kind 2 / 1), an RTL change to the critical slice;
   - NB 107 (lep_core + dsdv_mu_land parameters) plus a re-laid receive.
2. **h rows.** The on-die move of the 16 slices' h to the end slices is not compiled; leaf 0 rows 0..479 stand in.
3. **Multi-job MU** (L14 above), and L2 needs hwin NEV 16.
4. **Die fold.** The endpoint `.fault` is still unconnected in the mu2 die.v; folding it into the die status is the
   parent's job.

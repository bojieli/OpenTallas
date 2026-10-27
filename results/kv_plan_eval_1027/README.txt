KV-PLAN-EVAL 2026-10-27 (lane file ~/coord/lanes/CLOCK-KV.md). Compares the adopted KV kit plan hm_r26q2 1d257518
(intel2 /srv/opentallas-scratch2/claude/kv-kits-6-1027/pd) with the UNADOPTED Codex event codex/kv-clock-1027@3cb5395c6
(plan f1daa8ad). These are read-only diagnostics. Nothing is written into either plan.

(a) TOKEN PRICE of the event's lane cycles (lat_delta.json, price_rerun.json)
  - plan latency tables, event vs q2: 130 lanes change cycles, sum +210 (68x+1, 47x+2, 12x+3, 3x+4). All of it comes
    from stations, with 0 non-station cycle change (CHECKED). The 125/205 subset is Codex capsule b4a705f520. The 5 lanes
    only in the event are L356 dcal.dob, L749 host.lrc, L750 host.program_begin_v (boot), and L2047 serdes_E.tx_up and
    L2048 serdes_W.rx_flit (+1 each).
  - Codex price 674cd499f was re-run here from its committed inputs and reproduces byte-for-byte numbers (CHECKED).
    Most of the changed lanes are 89 PV exact-calendar join members (pvw_*_u_s*_j); their calendar holds them, so they
    cost 0 per token. Inbound RX/KVN stays at age 56 (0 per token). The outgoing attention TX bundle goes +1 per layer,
    which gives direct +36 cycles/token: accepted_cost DAG 249431 -> 249467, fully exposed; QCE 296341 -> 296377,
    -0.0121 % tok/s, 4051.0 -> 4050.5. Serial-family sensitivity (vport_slg 2, ahub_astk 1, seq_hroot 2, acal 1 per
    layer, + embed 3) gives +255: 296596, -0.0860 %, 4047.5 tok/s.
  - The 5 extra event lanes: boot/host/dcal cost 0 per token. Worst case for SerDes tx_up/rx_flit is +1 each per layer
    = +72/token (UNCHECKED: role on the per-layer path not traced). Worst total +327 = -0.110 %. Added latency per token
    is +30 ns direct to +272 ns worst on 246.9 us/token (833 ps).
(b) DIE GRT on hm_r26q2 (grt_q2/)
  - die_trial kit (main tools, fresh from hm_r26q2) + die_clock_mesh combo with the current canonical mesh
    (Codex current/ mesh.json, place.json, nets.json, ctree.v; hm_r26 clock = q2 clock). Docker 48 GB cap, intel2,
    -congestion_iterations 50.
  - Result: overflow 0 on M4-M9 (max H/V 0), 170,210 nets, 3.76 % usage, 280.16 m wirelength. It converged at extra
    iteration 1 of 50 (CHECKED, own run).
  - LIMIT: die_trial routes every FT slot bit as one die net from the slot's in pin to its out pin, with M4-M7 at
    0.25. Station siting is not in this model. So die GRT0 holds identically for q2 and for the event (Codex PV27 GRT:
    170,210 nets, 0 overflow). It does not decide between them. The siting risk lives in the partition-kit GRT
    (GEOM-24: hub_Ei kit GRT probe 923k overflow at x550-700).
(c) SMALLER DELTA (lanes.py -> lanes_405.json, reach.py -> reach.json)
  - Per slot: Manhattan in-pin -> out-pin length with q2 station counts. All 205 +1 slots fit inside the slot itself
    (max L/(n+1) = 355 um).
  - Per lane, with seams counted (out-leg + in-leg):
    * free placement: q2 counts are feasible on 130/130 lanes;
    * centred placement (end legs L/2n): 129/130 feasible, +1 station total;
    * j/(n+1) placement: 117 lanes fail with either count.
  - Slack is tiny. Under centred placement the worst q2 hop is 380-405 um on 122 lanes (202 of the 210 cycles), and
    354-380 um on only 7 lanes (7 cycles). Zero-cycle siting therefore needs <1-6 % detour and stations exactly on the
    centred points. The event's real paths detour 1.0-1.1x (reach.json). The +1s are the margin real siting needs, not
    padding.
  - Best realistic saving: about 7 cycles on 7 lanes (L2/L3/L2248/L2352/L1857/L1879/L1991 class, UNCHECKED that they
    site). Zero-cycle FT by allowing hops >405 um breaks the owner's 405 planning reach, so it is not proposed.
  - Event FT bit sites: 0 inside q2 or event hard-core rects (point check, CHECKED). The event's ft_slots can be grafted
    onto hm_r26q2 without the event's hard_cores/clock/reset changes (G0/G0C owed).
(d) hub_Ei SPINE in the event (hubEi_event.png VIEWED, hubEi_event.json, spine_ev.json, spread_*.txt)
  - per-bit station-site legs, 5x5-um map, capacity = GEOM-24 sizing 32 vertical tr/um x 0.6 = 19.2 bits/um:
    * peak 1,648 vertical bits in one 15-um column x495-510 y~710 = 5.7x the 0.6 budget (288). It is ft63/ft64,
      1118 bits each, with stations as 2.16-um-wide x 187-um-tall stripes at x~504-510.
    * 1,688 in 30 um, 1,752 in 60 um (1.5x), 2,013 in 120 um (0.87x).
    * If the router spreads the diagonal jogs evenly: still 1,023 bits in 15 um at x385 (3.6x).
    * Slot hops 373, diagonal 110 (stations on the chord); 0 slot hops >405 (max in-slot hop 394.5).
  - VERDICT: FAIL-IN-PLAN (CHECKED). The GEOM-24 spine moved from x~640 (3,187 bits) to x~495-510 (1,648 bits). It is
    not fixed, the GEOM-24 gate (column demand <=0.6, 0 diagonal) still fails, and KV-KITS-6's 1.6-2.3k estimate is
    confirmed.
  - Same screen over all types (pessimistic metric; flags q2's older sites too: hub_Wi 2.9x, hub_Eo 2.5x). Event
    hgi_v8 4.1x, hgi_v5 3.8x, hgi_v7 3.4x, hgi 3.1x, hub_Wi 3.0x, hub_Eo 2.9x (spread model). Wide-bus stations packed
    as narrow stripes with vertical travel are a systematic pattern of the siter, not only hub_Ei.

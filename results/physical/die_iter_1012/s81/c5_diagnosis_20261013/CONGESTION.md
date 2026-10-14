# S81 die c5 (contract v13): where the GRT overflow sits

2026-10-13. Run `/srv/opentallas-scratch/claude/s81-die-iter/c5` (EPYC1), reference c3 (v11). Numbers: `congestion.json`; tools `tools/s81/c5diag_*`. All values measured from `ckpt_grt.odb`, `route.guide`, `wirelength_grt.csv`, the placed DEF and LEFs.

## Method and check

- Overflow per gcell (9.6 um) and layer = unwrapped odb usage - raw tracks. The odb GCell grid stores usage = net usage + reductions in 8 bits, so it wraps where the overflow is worst; the net usage was rebuilt from the guides and used to unwrap it (c5: 576 M6 and 27 M8 gcells wrapped, 0 ambiguous).
- Mapped total c5 1,052,593 of the GRT 1,053,305 (99.93%); c3 830,020 of 830,691. M6 and M8 equal the GRT log exactly, guide usage equals the GRT demand exactly. Not mapped: 712 (c5) on M5 / M7 / M9 in the non-preferred direction.
- Net attribution: a gcell's overflow is split equally over the nets whose guides use that gcell's edge on that layer. A share is the family's share of the wires in overflowed gcells, not a causal proof.

## Findings (measured; "reading" lines are inference)

1. **Field frames: 651,846 (61.9%), identical in c3 (651,844).** Every one of the 128 frames holds 4284..5773. x-lane relay -> slot-station buses (n_xa 283 b, n_xb 266 b) 477,980 (45.4%); q-element -> qbank 151,698 (14.4%). 499,826 of it (77%) lies in the frame-local column x 336-480 um (the slot-station column), in rows at the slot pitch. Sample frame_20: overflow rows are 10-20 um tall at x 691-797 um; whole-frame demand / capacity M6 0.07, M8 0.03. Reading: pin-access rows under the station S-face pins, not a track shortage; v13 did not touch it.
2. **Strip W of sp_hc_s (x 16,800-17,312, y 14,083-24,000): 270,214 (25.7%); c3 46,891; +223,323 = the whole c5 - c3 increase (+222,614).** The wq_d chain sp_hc_s -> sp_vm is 46 hops x 4,096 b with a 17533 um path for a 4545 um direct distance (x 3.86): 12 dsfd_hstnv_4096 relays step N from y 18,483 to 23,630, then 20 step S to 15,779 in the same 201-um-wide column (x 17,004 / 17,010). c3: 21 hops, 8978 um path, max hop 2294 um. Strip demand / capacity M6 0.19, M8 0.15. Reading: the out-and-back relay walk, not the SU or corridor outline, is what v13 added.
3. **ctrl_SW / svc_SW gap (x 6,720-8,160, y 960-1,920): 107,352 (10.2%); c3 107,399.** n_rq_SW 10,912 b + n_rd_SW_r_data 8,192 b, svc_c <-> ctrl with no relay at either end, pin Manhattan 496 um, routed mean 1,122 / 1,068 um, max 3,130 um. Box demand / capacity M8 0.60, M9 0.55; M8 at 92-101 of 102 tracks in the gap rows y 1,190-1,526 across x 6,720-8,064.
4. 1 + 2 + 3 = 97.7%. The v13 SU slot, SM column, both HC columns and the corridor hold 0, 0, 413 and 264.
5. The unbuffered sp_hc_s hops of v11 / v12 are gone: every net on an sp_hc_s pin is <= 432 um pin-to-pin (c3: 2446 um, 12,288 bits over 500 um). What remains over 500 um pin-to-pin is in section d.

Not determined: whether the element pins on these nets are registered inside the views (d lists pin-to-pin hops only); the 712 overflow GRT books on M5 / M7 / M9 outside M6..M9 preferred-direction edges; drivers of multi-sink nets (the generated LEFs declare every pin INOUT; output pin names o / do0 / fo0 / dq are assumed); the frame row structure at gcell level beyond frame_20 (the 128-frame profile is aggregate); hc_y lanes other than lane 0 (the walk follows a lane-local bit index); c4 (killed before GRT finished).

## a) By layer

| layer | dir | overflow | share | gcells | max per gcell | GRT log |
|---|---|---:|---:|---:|---:|---:|
| M6 | H | 526,533 | 50.0% | 12,107 | 163 | 526,533 |
| M8 | H | 457,718 | 43.5% | 13,402 | 353 | 457,718 |
| M7 | V | 32,968 | 3.1% | 1,221 | 91 | 33,139 |
| M9 | V | 35,374 | 3.4% | 1,448 | 71 | 35,841 |
| M5 | V | 0 | 0.0% | 0 | 0 | 74 |
| M4 | H | 0 | 0.0% | 0 | 0 | 0 |

Horizontal M6 + M8 = 93.4%. 28178 of 9.3 M gcells x 4 layers overflow; 1525 of the 480-um windows hold any; top 10 windows 27.0%, top 20 35.3%.

## a) By region (generator `where()` names) and c3 comparison (e)

| region | c5 overflow | share of 1,053,305 | c3 overflow | delta |
|---|---:|---:|---:|---:|
| frame_* (128 field frames) | 651,846 | 61.9% | 651,844 | +2 |
| spine | 236,009 | 22.4% | 61,771 | +174238 |
| svc_SW | 96,819 | 9.2% | 96,613 | +206 |
| band | 50,157 | 4.8% | 11,182 | +38975 |
| channel4 | 6,943 | 0.7% | 13 | +6930 |
| other | 6,544 | 0.6% | 5,779 | +765 |
| channel3 | 1,789 | 0.2% | 65 | +1724 |
| vch | 1,643 | 0.2% | 2,209 | -566 |
| channel0 | 374 | 0.0% | 245 | +129 |
| channel2 | 353 | 0.0% | 79 | +274 |
| channel1 | 106 | 0.0% | 210 | -104 |

Field frames: 128 frames, per frame min / median / max = 4284 / 5121 / 5773 (c3: 4284 / 5121 / 5773). Top buses in the frames: n_xb_#_# 354,418, n_xa_#_# 145,402, n_xb_#_#_e#_eb 120,110, n_xa_#_#_e#_eb 31,587. Under: (no instance) 393,344, qbank 146,440, rly 62,874, bf 43,615, q_elem 5,572, sstn 1.

Fixed boxes (same coordinates in both runs; util = guide demand / effective capacity of the box):

| box | x0,y0,x1,y1 um | c5 | share | c3 | delta | c5 util M6/M7/M8/M9 | top buses (c5) |
|---|---|---:|---:|---:|---:|---|---|
| su_v13 | 13780.8,3369.6,15670.8,13392 | 0 | 0.0% | 294 | -294 | 0.01 / 0.09 / 0.00 / 0.00 |  |
| su_v11 | 13780.8,3369.6,15670.8,9439.2 | 0 | 0.0% | 0 | +0 | 0.00 / 0.00 / 0.00 / 0.00 |  |
| su_growth_v11_to_v13 | 13780.8,9439.2,15670.8,13392 | 0 | 0.0% | 294 | -294 | 0.02 / 0.15 / 0.00 / 0.00 |  |
| sm_column_v13 | 13780.8,3391.2,15012,12009.6 | 0 | 0.0% | 0 | +0 | 0.00 / 0.00 / 0.00 / 0.00 |  |
| hub_W_stack_N_of_su_v13 | 13942.8,13392,15670.8,21400 | 229 | 0.0% | 0 | +229 | 0.07 / 0.03 / 0.01 / 0.00 | n_hb_vm_gather 190; n_hb_su_s_wq_row_#_#_vm 30; n_hb_su_s_wq_mask_#_#_vm 6 |
| vch_all | 15670.8,3257.3,17312.4,22745 | 237,172 | 22.5% | 63,872 | +173300 | 0.07 / 0.12 / 0.04 / 0.08 | n_hb_hc_s_wq_d_vm 176,783; n_hb_collective_t_hc_y_#_#_hc_s 57,809; n_hb_collective_vm 1,104 |
| vch_E_strip_N | 16800,14083.2,17312.4,24000 | 270,214 | 25.7% | 46,891 | +223323 | 0.20 / 0.44 / 0.15 / 0.36 | n_hb_hc_s_wq_d_vm 216,292; n_hb_collective_t_hc_y_#_#_hc_s 53,704; n_rE#_d#_# 147 |
| vch_E_strip_S | 16800,3257.3,17312.4,14083.2 | 0 | 0.0% | 11,353 | -11353 | 0.02 / 0.02 / 0.01 / 0.00 |  |
| hc_s_v13 | 17312.4,14083.2,19129,22433 | 0 | 0.0% | 0 | +0 | 0.00 / 0.00 / 0.01 / 0.01 |  |
| hc_t_v13 | 17312.4,3680.64,19129,12571.2 | 25 | 0.0% | 0 | +25 | 0.01 / 0.22 / 0.00 / 0.00 | n_KE#r 22; n_KE#t 2 |
| corridor_v13 | 17312.4,12571.2,19129,14083.2 | 264 | 0.0% | 0 | +264 | 0.12 / 0.08 / 0.04 / 0.02 | n_hb_hc_s_t_tf#_hc_t 180; n_hb_hc_s_hc_t 70; n_KE#r 10 |
| corridor_v11 | 17312.4,8618.4,19129,10130.4 | 0 | 0.0% | 0 | +0 | 0.01 / 0.15 / 0.00 / 0.00 |  |
| hc_column_all | 17312.4,3257.3,19129,22762 | 413 | 0.0% | 0 | +413 | 0.08 / 0.06 / 0.01 / 0.01 | n_hb_hc_s_t_tf#_hc_t 180; n_xEdn 123; n_hb_hc_s_hc_t 70 |
| hub_E_gap | 19129,3257.3,19559,22745 | 359 | 0.0% | 80 | +279 | 0.02 / 0.08 / 0.01 / 0.02 | n_KE#r 152; n_xEdn 122; n_KE#t 83 |
| hub_W_gap | 13424,3257.3,13780.8,22745 | 11,243 | 1.1% | 3,813 | +7430 | 0.03 / 0.32 / 0.01 / 0.19 | n_aSW 3,488; n_rW#_de_# 2,932; n_KW#r 1,805 |
| ctrl_svc_pinch | 6720,960,8160,1920 | 107,352 | 10.2% | 107,399 | -47 | 0.28 / 0.11 / 0.60 / 0.55 | n_rq_SW 67,452; n_rd_SW_r_data 37,348; n_rd_SW_r_tag 1,481 |
| band_N_hub | 13872,22745,19142,24535 | 39,545 | 3.8% | 296 | +39249 | 0.03 / 0.04 / 0.01 / 0.03 | n_hb_hc_s_wq_d_vm 39,545 |
| band_S_hub | 13872,1200,19142,3257.3 | 0 | 0.0% | 0 | +0 | 0.00 / 0.00 / 0.00 / 0.00 |  |

## a) Top 20 hot windows (480 x 480 um)

| x um | y um | overflow | share | layers | region | top buses |
|---|---|---:|---:|---|---|---|
| 7200-7680 | 1440-1920 | 48,489 | 4.6% | M9 19633 M7 17765 M6 5837 M8 5254 | svc_SW | n_rq_SW 33,547; n_rd_SW_r_data 13,930; n_rd_SW_r_tag 803 |
| 16800-17280 | 18720-19200 | 43,611 | 4.1% | M6 24545 M8 19066 | spine | n_hb_hc_s_wq_d_vm 25,363; n_hb_collective_t_hc_y_#_#_hc_s 18,211; n_KE#r 26 |
| 16800-17280 | 18240-18720 | 41,780 | 4.0% | M6 21189 M8 20591 | spine | n_hb_hc_s_wq_d_vm 30,260; n_hb_collective_t_hc_y_#_#_hc_s 11,499; n_KE#r 16 |
| 7200-7680 | 960-1440 | 35,413 | 3.4% | M9 15132 M7 15038 M8 3899 M6 1344 | svc_SW, band | n_rq_SW 23,826; n_rd_SW_r_data 11,296; n_rd_SW_r_tag 281 |
| 16800-17280 | 19200-19680 | 28,911 | 2.7% | M6 17116 M8 11795 | spine | n_hb_hc_s_wq_d_vm 18,965; n_hb_collective_t_hc_y_#_#_hc_s 9,939; n_KE#r 5 |
| 16800-17280 | 19680-20160 | 24,063 | 2.3% | M6 14315 M8 9748 | spine | n_hb_hc_s_wq_d_vm 16,601; n_hb_collective_t_hc_y_#_#_hc_s 7,461 |
| 16800-17280 | 23520-24000 | 17,948 | 1.7% | M6 11486 M8 6308 M7 98 M9 56 | band | n_hb_hc_s_wq_d_vm 17,947 |
| 16800-17280 | 20160-20640 | 16,988 | 1.6% | M6 10029 M8 6959 | spine | n_hb_hc_s_wq_d_vm 15,247; n_hb_collective_t_hc_y_#_#_hc_s 1,740 |
| 16800-17280 | 20640-21120 | 13,923 | 1.3% | M6 8744 M8 5179 | spine | n_hb_hc_s_wq_d_vm 13,578; n_hb_collective_t_hc_y_#_#_hc_s 344 |
| 16800-17280 | 22080-22560 | 13,161 | 1.2% | M6 7338 M8 5823 | spine | n_hb_hc_s_wq_d_vm 13,161 |
| 6720-7200 | 1440-1920 | 13,139 | 1.2% | M8 9399 M6 3232 M9 456 M7 52 | svc_SW | n_rd_SW_r_data 7,895; n_rq_SW 4,436; n_rd_SW_r_beat 513 |
| 16800-17280 | 17760-18240 | 12,599 | 1.2% | M8 6718 M6 5881 | spine | n_hb_hc_s_wq_d_vm 8,838; n_hb_collective_t_hc_y_#_#_hc_s 3,757; n_hb_sseq_su_s 2 |
| 16800-17280 | 21120-21600 | 11,545 | 1.1% | M6 6307 M8 5238 | spine | n_hb_hc_s_wq_d_vm 11,544 |
| 16800-17280 | 22560-23040 | 11,242 | 1.1% | M6 6563 M8 4679 | band | n_hb_hc_s_wq_d_vm 11,241 |
| 16800-17280 | 21600-22080 | 10,789 | 1.0% | M6 6345 M8 4444 | spine | n_hb_hc_s_wq_d_vm 10,788 |
| 16800-17280 | 23040-23520 | 10,355 | 1.0% | M6 6497 M8 3858 | band | n_hb_hc_s_wq_d_vm 10,354 |
| 13440-13920 | 16320-16800 | 5,444 | 0.5% | M6 3523 M8 1921 | channel4 | n_rW#_de_# 2,846; n_rW#_d#_# 1,968; n_KW#r 480 |
| 6720-7200 | 960-1440 | 4,765 | 0.5% | M8 3934 M6 741 M9 85 M7 5 | band, svc_SW | n_rd_SW_r_data 4,224; n_rq_SW 450; n_rd_SW_r_tag 89 |
| 7680-8160 | 1440-1920 | 4,083 | 0.4% | M8 2237 M6 1835 M9 10 M7 1 | svc_SW | n_rq_SW 3,744; n_wd_SW 324; n_rd_SW_r_tag 12 |
| 16800-17280 | 15360-15840 | 3,064 | 0.3% | M6 2099 M8 965 | spine | n_hb_hc_s_wq_d_vm 3,060; n_rE#_d#_# 3 |

## b) Top 20 net families (bus = base name, digits -> #, relay-hop suffix dropped)

| bus | driver -> sink kind | bits (hop-bits) | bus instances | overflow | share | bits on overflowed gcells | routed mean / max um | pin Manhattan mean / max um |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| n_xb_#_# | rly -> sstn | 680,960 | 2560 | 354,434 | 33.6% | 154,179 | 329 / 970 | 202 / 443 |
| n_hb_hc_s_wq_d_vm | hstn -> hstn | 188,416 | 46 | 216,328 | 20.5% | 64,727 | 506 / 1930 | 374 / 717 |
| n_xa_#_# | rly -> sstn | 724,480 | 2560 | 145,450 | 13.8% | 140,066 | 368 / 1056 | 227 / 507 |
| n_xb_#_#_e#_eb | q_elem -> qbank | 340,480 | 1280 | 120,110 | 11.4% | 252,121 | 40 / 96 | 22 / 28 |
| n_rq_SW | svc_c -> ctrl | 10,912 | 1 | 67,452 | 6.4% | 10,912 | 1122 / 3130 | 496 / 496 |
| n_hb_collective_t_hc_y_#_#_hc_s | hstn -> hstn | 130,048 | 127 | 57,809 | 5.5% | 31,100 | 395 / 1786 | 292 / 538 |
| n_rd_SW_r_data | svc_c -> ctrl | 8,192 | 1 | 37,427 | 3.6% | 8,192 | 1068 / 2707 | 497 / 497 |
| n_xa_#_#_e#_eb | q_elem -> qbank | 362,240 | 1280 | 31,587 | 3.0% | 134,673 | 26 / 125 | 12 / 41 |
| n_aSW | stn -> stn | 33,858 | 33 | 3,488 | 0.3% | 8,762 | 430 / 624 | 396 / 412 |
| n_rW#_d#_# | stn -> stn | 142,240 | 2032 | 3,364 | 0.3% | 1,270 | 395 / 470 | 383 / 433 |
| n_rW#_de_# | m#l_vr_#x# -> stn | 4,480 | 64 | 2,932 | 0.3% | 1,179 | 278 / 384 | 252 / 355 |
| n_KW#r | stn -> stn | 116,224 | 227 | 2,181 | 0.2% | 4,643 | 427 / 528 | 406 / 433 |
| n_KW#t | stn -> stn | 115,712 | 226 | 1,689 | 0.2% | 1,988 | 409 / 528 | 396 / 434 |
| n_rd_SW_r_tag | svc_c -> ctrl | 544 | 1 | 1,482 | 0.1% | 544 | 1460 / 2650 | 499 / 499 |
| n_hb_collective_vm | hstn -> hstn | 48,300 | 23 | 1,104 | 0.1% | 1,796 | 287 / 1027 | 250 / 554 |
| n_KW#r_de | stn -> m#l_raw_#x# | 2,048 | 4 | 807 | 0.1% | 436 | 211 / 355 | 192 / 322 |
| n_hl_E#_o | hstn -> sp_collective_c | 4,120 | 8 | 562 | 0.1% | 1,264 | 172 / 365 | 150 / 310 |
| n_hwSW | stn -> stn | 15,822 | 54 | 523 | 0.0% | 181 | 420 / 470 | 408 / 413 |
| n_rd_SW_r_beat | svc_c -> ctrl | 128 | 1 | 513 | 0.0% | 128 | 88 / 106 | 70 / 70 |
| n_wd_SW | svc_c -> ctrl | 32 | 1 | 460 | 0.0% | 32 | 608 / 1152 | 498 / 498 |

By driver -> sink kind: rly -> sstn 499,874 (47.5%); hstn -> hstn 274,689 (26.1%); q_elem -> qbank 151,698 (14.4%); svc_c -> ctrl 107,431 (10.2%); stn -> stn 12,380 (1.2%); m#l_vr_#x# -> stn 3,006 (0.3%).

## c) The sp_hc_s buses y_d (8,192 b) and wq_d (4,096 b)

| group | run | hop-bits | own overflow | share | overflow of the gcells they use | share | pin Manhattan p50 / p99 / max | routed p50 / p99 / max | bits > 500 um Manhattan | 2+ pin bits routed > 500 um |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|
| at_sp_hc_s | c5 | 20,753 | 923 | 0.1% | 5,768 | 0.5% | 103 / 412 / 432 | 144 / 1085 / 1507 | 0 | 1,422 |
| at_sp_hc_s | c3 | 13,691 | 0 | 0.0% | 0 | 0.0% | 2257 / 2446 / 2446 | 2659 / 3581 / 3994 | 12,288 | 12,288 |
| wq_d | c5 | 188,416 | 216,328 | 20.5% | 257,658 | 24.5% | 456 / 536 / 717 | 499 / 1286 / 1930 | 28,672 | 91,905 |
| wq_d | c3 | 86,016 | 11,762 | 1.4% | 12,878 | 1.6% | 413 / 2294 / 2294 | 470 / 2851 / 3686 | 5,707 | 30,600 |
| hc_y | c5 | 130,048 | 57,809 | 5.5% | 135,760 | 12.9% | 221 / 505 / 538 | 269 / 1219 / 1786 | 3,596 | 37,978 |
| hc_y | c3 | 126,976 | 48,518 | 5.8% | 48,880 | 5.9% | 303 / 2397 / 2446 | 355 / 3312 / 3994 | 9,509 | 44,512 |
| hc_chains | c5 | 318,464 | 274,138 | 26.0% | 274,626 | 26.1% | 430 / 520 / 717 | 470 / 1248 / 1930 | 32,268 | 129,883 |
| hc_chains | c3 | 212,992 | 60,280 | 7.3% | 60,461 | 7.3% | 379 / 2294 / 2446 | 432 / 3226 / 3994 | 15,216 | 75,112 |
| ctrl_svc | c5 | 19,840 | 107,347 | 10.2% | 107,431 | 10.2% | 496 / 499 / 1025 | 1104 / 2074 / 3130 | 32 | 19,712 |
| ctrl_svc | c3 | 19,840 | 107,416 | 12.9% | 107,499 | 12.9% | 496 / 499 / 1025 | 1104 / 2083 / 2813 | 32 | 19,712 |
| xlane | c5 | 702,720 | 477,980 | 45.4% | 477,999 | 45.4% | 328 / 505 / 507 | 509 / 989 / 1056 | 18,944 | 351,360 |
| xlane | c3 | 702,720 | 477,978 | 57.5% | 477,997 | 57.5% | 328 / 505 / 507 | 509 / 989 / 1056 | 18,944 | 351,360 |
| qbank_eb | c5 | 702,720 | 151,698 | 14.4% | 152,012 | 14.4% | 17 / 28 / 41 | 29 / 86 / 125 | 0 | 0 |
| qbank_eb | c3 | 702,720 | 151,698 | 18.3% | 152,012 | 18.3% | 17 / 28 / 41 | 29 / 86 / 125 | 0 | 0 |

Groups: at_sp_hc_s = every net on an sp_hc_s pin; wq_d / hc_y = the whole relay chains; hc_chains = both; ctrl_svc = n_rq/rd/wd_SW; xlane = n_xa/n_xb relay -> slot station; qbank_eb = q element -> qbank.

Chain walks (one bit, placed DEF):

| chain | run | hops | path um | direct um | path / direct | max hop um | hops > 500 um |
|---|---|---:|---:|---:|---:|---:|---:|
| sp_collective.t_hc_y[0] -> sp_hc_s.y_d[0] | c3 | 13 | 5478 | 1903 | 2.88 | 1997 | 1 |
| sp_hc_s.wq_d[0] -> sp_vm.f_hc_wqd[0] | c3 | 21 | 8978 | 6628 | 1.35 | 2294 | 2 |
| sp_collective.t_hc_y[0] -> sp_hc_s.y_d[0] | c5 | 13 | 3676 | 3519 | 1.04 | 485 | 0 |
| sp_hc_s.wq_d[0] -> sp_vm.f_hc_wqd[0] | c5 | 46 | 17533 | 4545 | 3.86 | 717 | 7 |
| sp_hc_s.wq_d[4095] -> sp_vm.f_hc_wqd[4095] | c5 | 46 | 17085 | 4545 | 3.76 | 520 | 7 |

## d) Hops longer than 500 um (work list, sorted by bits x um)

2-pin nets: one hop.  Multi-sink nets: manh = driver -> farthest sink (largest pin-to-pin distance when the driver is not identified), wl = the whole routed tree, not a hop. 2-pin nets over 500 um pin-to-pin: 32,870 bits; multi-sink nets: 19,212 bits; 2-pin nets routed over 500 um: 159,890 bits. Clock / reset distribution nets are marked ck.

Pin-to-pin Manhattan > 500 um, 2-pin nets, by endpoint (12 rows):

| family | kinds | bits over / total | mean um | max um | bits x um | pin Manhattan mean | routed mean | no relay at either end | ck |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| g_hb_hc_s_wq_d_vm_d#_f_hb_hc_s_wq_d_vm_#_#.dq -> g_hb_hc_s_wq_d_vm_d#_f_hb_hc_s_wq_d_vm_#_#.di | hstn -> hstn | 24,576 / 126,976 | 504 | 505 | 12,391,022 | 504 | 676 | 0 |  |
| g_hb_hc_s_wq_d_vm_d#_f_hb_hc_s_wq_d_vm_#_#.dq -> f_hb_hc_s_wq_d_vm_#.di | hstn -> hstn | 4,096 / 4,096 | 570 | 717 | 2,332,903 | 570 | 635 | 0 |  |
| g_hb_collective_t_hc_y_#_#_hc_s_d#_sp_hc_s_#.dq -> g_hb_collective_t_hc_y_#_#_hc_s_d#_sp_hc_s_#.di | hstn -> hstn | 2,604 / 35,840 | 506 | 538 | 1,318,525 | 506 | 798 | 0 |  |
| g_hb_collective_vm_d#_sp_vm_#.dq -> g_hb_collective_vm_d#_sp_vm_#.di | hstn -> hstn | 562 / 8,400 | 527 | 554 | 296,170 | 527 | 575 | 0 |  |
| g_hb_collective_t_hc_y_#_#_hc_s_d#_f_hb_collective_t_hc_y_#_#_hc_s_#_#.dq -> f_hb_collective_t_hc_y_#_#_hc_s_#.di | hstn -> hstn | 507 / 8,192 | 513 | 532 | 260,315 | 513 | 566 | 0 |  |
| f_hb_collective_t_hc_y_#_#_hc_s_#.dq -> g_hb_collective_t_hc_y_#_#_hc_s_d#_sp_hc_s_#.di | hstn -> hstn | 299 / 8,192 | 507 | 516 | 151,699 | 507 | 898 | 0 |  |
| g_hb_collective_t_hc_y_#_#_hc_s_d#_f_hb_collective_t_hc_y_#_#_hc_s_#_#.dq -> g_hb_collective_t_hc_y_#_#_hc_s_d#_f_hb_collective_t_hc_y_#_#_hc_s_#_#.di | hstn -> hstn | 186 / 11,264 | 509 | 518 | 94,655 | 509 | 553 | 0 |  |
| svc_SW.rv -> ctrl_SW.rd | svc_c -> ctrl | 32 / 32 | 1025 | 1025 | 32,787 | 1025 | 2177 | 32 |  |
| sp_collective.rst_hbm -> ctrl_SW.rst | sp_collective_c -> ctrl | 1 / 1 | 28221 | 28221 | 28,221 | 28221 | 28253 | 1 | ck |
| sp_collective.pll_hbm -> ctrl_SW.ckh | sp_collective_c -> ctrl | 1 / 1 | 28220 | 28220 | 28,220 | 28220 | 28253 | 1 | ck |
| f_KE#txs_#.fo0 -> kc_KE#.fi | stn -> lkck_SW | 3 / 3 | 549 | 549 | 1,647 | 549 | 582 | 0 | ck |
| f_KW#txs_#.fo0 -> kc_KW#.fi | stn -> lkck_SE | 3 / 3 | 541 | 541 | 1,622 | 541 | 566 | 0 | ck |

Pin-to-pin Manhattan > 500 um, multi-sink nets, by endpoint (11 rows):

| family | kinds | bits over / total | mean um | max um | bits x um | pin Manhattan mean | routed mean | no relay at either end | ck |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| y_xa_#_#_#.o -> t#_#.xai | rly -> sstn | 18,944 / 326,016 | 504 | 507 | 9,540,502 | 504 | 950 | 0 |  |
| y_xb_#_#_#.ck -> bn#.ck | rly -> qbank | 128 / 128 | 4048 | 4048 | 518,100 | 4048 | 26362 | 0 | ck |
| y_xb_#_#_#.rs -> bn#.rs | rly -> qbank | 128 / 128 | 3961 | 3961 | 506,969 | 3961 | 23399 | 0 | ck |
| xsix_SW.cw -> bk_collector.ck | xstg -> bk_collector_c | 1 / 1 | 53731 | 53731 | 53,731 | 53731 | 291216 | 0 | ck |
| svc_SW.rst -> bk_collector.rst | svc_c -> bk_collector_c | 1 / 1 | 53608 | 53608 | 53,608 | 53608 | 217123 | 1 | ck |
| sp_wfc.ckv -> f_hb_vm_collective_#.ck | wfc_stg -> hstn | 1 / 1 | 32963 | 32963 | 32,963 | 32963 | 65338 | 0 | ck |
| sp_wfc.rsv -> ha_SW.rs | wfc_stg -> r#l_vr_#x# | 1 / 1 | 32963 | 32963 | 32,963 | 32963 | 55728 | 1 | ck |
| kc_KE#.fo -> f_KE#rxs_#.fi0 | lkck_SW -> stn | 3 / 3 | 1106 | 1106 | 3,319 | 1106 | 1155 | 0 | ck |
| kc_KW#.fo -> f_KW#rxs_#.fi0 | lkck_SE -> stn | 3 / 3 | 1094 | 1094 | 3,281 | 1094 | 1149 | 0 | ck |
| lk_E#.clk -> f_KE#r_#.fi0 | ot_pdie_ucie -> stn | 1 / 1 | 1231 | 1231 | 1,231 | 1231 | 1267 | 0 | ck |
| lk_W#.clk -> f_KW#r_#.fi0 | ot_pdie_ucie -> stn | 1 / 1 | 1230 | 1230 | 1,230 | 1230 | 1248 | 0 | ck |

Routed GRT length > 500 um, 2-pin nets, by bus (43 rows):

| family | kinds | bits over / total | mean um | max um | bits x um | pin Manhattan mean | routed mean | no relay at either end | ck |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| n_hb_hc_s_wq_d_vm | hstn -> hstn | 91,905 / 188,416 | 708 | 1930 | 65,096,035 | 471 | 708 | 0 |  |
| n_hb_collective_t_hc_y_#_#_hc_s | hstn -> hstn | 37,978 / 130,048 | 739 | 1786 | 28,051,642 | 448 | 739 | 0 |  |
| n_rq_SW | svc_c -> ctrl | 10,912 / 10,912 | 1122 | 3130 | 12,248,947 | 496 | 1122 | 10,912 |  |
| n_rd_SW_r_data | svc_c -> ctrl | 8,192 / 8,192 | 1068 | 2707 | 8,751,773 | 497 | 1068 | 8,192 |  |
| n_hb_collective_vm | hstn -> hstn | 6,935 / 48,300 | 614 | 1027 | 4,260,538 | 466 | 614 | 0 |  |
| n_rd_SW_r_tag | svc_c -> ctrl | 544 / 544 | 1460 | 2650 | 794,304 | 499 | 1460 | 544 |  |
| n_KW#r | stn -> stn | 724 / 116,224 | 515 | 528 | 372,797 | 408 | 515 | 0 |  |
| n_col | stn -> stn | 500 / 11,308 | 561 | 701 | 280,493 | 412 | 561 | 0 |  |
| n_aSW | stn -> stn | 305 / 33,858 | 558 | 624 | 170,275 | 409 | 558 | 0 |  |
| n_xEdn | stn -> stn | 288 / 24,338 | 588 | 643 | 169,344 | 409 | 588 | 0 |  |
| n_qSW | stn -> stn | 269 / 16,962 | 547 | 595 | 147,101 | 409 | 547 | 0 |  |
| n_KW#t | stn -> stn | 270 / 115,712 | 511 | 528 | 138,038 | 411 | 511 | 0 |  |
| n_hb_vm_wfc | hstn -> hstn | 196 / 4,128 | 613 | 778 | 120,182 | 374 | 613 | 0 |  |
| n_hb_vm_pq | hstn -> hstn | 192 / 28,106 | 523 | 576 | 100,349 | 297 | 523 | 0 |  |
| n_c#_bk_collector | stn -> stn | 157 / 1,720 | 575 | 720 | 90,346 | 408 | 575 | 0 |  |
| n_rd_SW_rv | svc_c -> ctrl | 32 / 32 | 2177 | 2563 | 69,677 | 1025 | 2177 | 32 |  |
| n_KE#t | stn -> stn | 121 / 134,656 | 514 | 758 | 62,179 | 412 | 514 | 0 |  |
| n_rE#_d#_# | stn -> stn | 99 / 202,230 | 571 | 595 | 56,515 | 407 | 571 | 0 |  |
| n_xEup | stn -> stn | 84 / 19,244 | 619 | 710 | 51,974 | 409 | 619 | 0 |  |
| n_KE#r | stn -> stn | 61 / 132,608 | 634 | 912 | 38,669 | 410 | 634 | 0 |  |
| n_clk_hbm | sp_collective_c -> ctrl | 1 / 1 | 28253 | 28253 | 28,253 | 28220 | 28253 | 1 | ck |
| n_rst_hbm | sp_collective_c -> ctrl | 1 / 1 | 28253 | 28253 | 28,253 | 28221 | 28253 | 1 | ck |
| n_wd_SW | svc_c -> ctrl | 32 / 32 | 608 | 1152 | 19,450 | 498 | 608 | 32 |  |
| n_hb_vm_gather | hstn -> hstn | 21 / 2,048 | 509 | 509 | 10,685 | 125 | 509 | 0 |  |
| n_d#_bk_collector | stn -> stn | 10 / 200 | 780 | 787 | 7,805 | 408 | 780 | 0 |  |
| n_rt_#_#b | rly -> qbank | 12 / 796,800 | 509 | 509 | 6,106 | 461 | 509 | 0 |  |
| n_s#_bk_collector | stn -> stn | 9 / 63 | 662 | 902 | 5,962 | 408 | 662 | 0 |  |
| n_KW#t_f# | stn -> stn | 8 / 226 | 509 | 509 | 4,070 | 412 | 509 | 0 |  |
| n_xWdn | stn -> stn | 5 / 20,376 | 526 | 538 | 2,630 | 409 | 526 | 0 |  |
| n_coSW | stn -> stn | 4 / 37,008 | 518 | 518 | 2,074 | 409 | 518 | 0 |  |
| n_s#_bk_collector_f# | stn -> stn | 3 / 21 | 627 | 806 | 1,882 | 408 | 627 | 0 |  |
| n_KE#_ckf | stn -> lkck_SW | 3 / 4 | 582 | 595 | 1,747 | 549 | 582 | 0 | ck |
| n_KW#_ckf | stn -> lkck_SE | 3 / 4 | 566 | 566 | 1,699 | 541 | 566 | 0 | ck |
| n_hb_gather_sseq | hstn -> hstn | 2 / 198 | 672 | 691 | 1,344 | 195 | 672 | 0 |  |
| n_hb_sseq_su_s | hstn -> hstn | 2 / 3,485 | 634 | 672 | 1,267 | 193 | 634 | 0 |  |
| n_c#_bk_collector_f# | stn -> stn | 2 / 20 | 547 | 586 | 1,094 | 408 | 547 | 0 |  |
| n_hb_wfc_vm | hstn -> hstn | 2 / 4,352 | 509 | 509 | 1,018 | 248 | 509 | 0 |  |
| n_c#_bk_selector | stn -> stn | 1 / 4,042 | 816 | 816 | 816 | 409 | 816 | 0 |  |
| n_d#_bk_collector_f# | stn -> stn | 1 / 20 | 787 | 787 | 787 | 408 | 787 | 0 |  |
| n_col_f# | stn -> stn | 1 / 22 | 586 | 586 | 586 | 412 | 586 | 0 |  |
| n_hb_vm_wfc_d#_f_swa | hstn -> wfc_stg | 1 / 1 | 509 | 509 | 509 | 473 | 509 | 0 |  |
| n_hb_vm_wfc_d#_f_swr | hstn -> wfc_stg | 1 / 1 | 509 | 509 | 509 | 475 | 509 | 0 |  |
| n_hb_wfc_vm_d#_t_swv | wfc_stg -> hstn | 1 / 1 | 509 | 509 | 509 | 489 | 509 | 0 |  |

Routed tree > 500 um, multi-sink nets, by bus (tree length, not a hop) (24 rows, first 15 shown, all in congestion.json):

| family | kinds | bits over / total | mean um | max um | bits x um | pin Manhattan mean | routed mean | no relay at either end | ck |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| n_xa_#_# | rly -> sstn | 181,120 / 724,480 | 898 | 1056 | 162,722,371 | 469 | 898 | 0 |  |
| n_xb_#_# | rly -> sstn | 170,240 / 680,960 | 788 | 970 | 134,174,112 | 413 | 788 | 0 |  |
| n_xW# | stn -> stn | 32,695 / 103,012 | 583 | 682 | 19,053,216 | 408 | 583 | 0 |  |
| n_xE# | stn -> stn | 30,754 / 104,710 | 589 | 691 | 18,116,755 | 408 | 589 | 0 |  |
| n_ck_col_# | rly -> qbank | 128 / 128 | 26362 | 26669 | 3,374,352 | 4048 | 26362 | 0 | ck |
| n_rs_col_# | rly -> qbank | 128 / 128 | 23399 | 23808 | 2,995,075 | 3961 | 23399 | 0 | ck |
| n_xWdn | stn -> stn | 1,312 / 20,376 | 814 | 941 | 1,067,731 | 419 | 814 | 0 |  |
| n_xWup | stn -> stn | 1,132 / 15,282 | 884 | 960 | 1,000,282 | 427 | 884 | 0 |  |
| n_xEup | stn -> stn | 1,132 / 19,244 | 865 | 931 | 978,912 | 425 | 865 | 0 |  |
| n_xEdn | stn -> stn | 1,132 / 24,338 | 781 | 797 | 884,275 | 406 | 781 | 0 |  |
| n_clk_stream | xstg -> bk_collector_c | 1 / 1 | 291216 | 291216 | 291,216 | 53731 | 291216 | 0 | ck |
| n_rst_stream | svc_c -> bk_collector_c | 1 / 1 | 217123 | 217123 | 217,123 | 53608 | 217123 | 1 | ck |
| n_clk_serial | wfc_stg -> hstn | 1 / 1 | 65338 | 65338 | 65,338 | 32963 | 65338 | 0 | ck |
| n_rst_serial | wfc_stg -> r#l_vr_#x# | 1 / 1 | 55728 | 55728 | 55,728 | 32963 | 55728 | 1 | ck |
| n_xE#_f# | stn -> stn | 58 / 185 | 614 | 682 | 35,606 | 408 | 614 | 0 |  |


v22_pq_cnt (S-DIE r12 2026-10-15): the v20 count-leaf pin files (tools/s81/pq_count_pins.py, N taps at the averaged
gather root x) adopted into the die overlay chain. Without them the generator laid the leaf N pins evenly, 117 um from
their gather t_capture pins (GEN19r pass 1: hb_gather_capture_t2803 -> pq_cnt_5.r_tag needed a pin relay with no spot
in the 43.2-um seam). With them each hop is within the 100-um pin segment (no relay). Byte-identical copies of v20.

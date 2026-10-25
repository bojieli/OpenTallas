Grouped SU lane candidates from the verified fixed-source bound RTL.

NOT ADOPTED. Run actual-leaf lockstep plus mutant before using these candidates in kits or plans. Existing leaf modules, reset logic and pipeline stages are unchanged; the wrapper only packs the exact live boundary bits. groups.json pins the source parents and maps every bit back to the bound cut. Three logical classes exist per side: lane0 special (SC35, c_o246), normal (SC1, c_o219), lane4 (SC1, c_o219, input759 because the bound lv1 is already constant). E/W bodies of corresponding classes match; physical pin orientations remain separate.

Generate: python3 ../legacy/group_su_lane.py BOUND/rtl OUTPUT; python3 ../legacy/su_lane_miter.py OUTPUT

Miter top is tb in tb.sv. Compile the three qfd_qc_su_lane_w_c{0,1,2}.sv files, reference.sv and tb.sv with the actual leaf-source closure from the fixed bind.f (omit unrelated generated bound wrappers). Run normal then +mutant. Normal must print SU_LANE_MITER PASS; +mutant must report a mismatch and fail. The negative control flips one output bit on cycle100. The 4096-cycle reference directly instantiates the original five bound children and reconstructs their raw input expressions independently of the packed wrapper.

The provisional plan pins must be regenerated from these actual interfaces together with clock/reset pins, then paired to actual bound hierarchy. In particular the old even SC10/10/9/9 split is wrong; the old c_o247 counts the same l_last bit twice because two downstream consumers use it. No plan has been edited by this candidate.

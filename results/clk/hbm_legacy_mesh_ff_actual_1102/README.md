# Legacy mesh actual FF measurements

This closes the inherited lane's unchecked FF/TT ratio item using its already recovered same-DEF/SPEF TT and FF library-corner tables. No route, STA, Monte Carlo or obsolete post7 proof was rerun. Both views have matching2,460 input-pin transition records and266 load names; T/F inside each file mean rising/falling edges, while the file suffix identifies the library corner.

NW_v2 remains DRC0 at the legacy component scope. Its measured maximum-arrival FF/TT ratios are0.8157..0.8206 rising (median0.8182) and0.8103..0.8157 falling. The old0.8666 scale overestimates deep FF arrival by up to71.26ps rising /82.59ps falling. NW_v1 has ratios around0.85 and remains DRC2 FAIL. These differing route results do not support a new universal ratio.

Among nonzero-arrival NW_v2 loads, the error in scaled-versus-actual pair skew spans11.65ps rising /11.57ps falling. Including zero-arrival early `L_clk` gives the larger early/deep differential above. The JSON retains maximum/minimum arrival statistics and extremal names. These are all-load diagnostics, not selected related-pair/CPPR timing failures or die signoff measurements.

Use the actual `tree_drt_FF.txt` whenever available. Current `tools/clk/mesh_form.py:rec` already reads TT and FF files separately; no default or tool change was necessary. Current-source/native66START/parent/interface/PG/dieG4 remain held, and no old12.25 proof is promoted. Inputs remain in sibling `hbm_nw_v1_drt_readout_1102` and `hbm_nw_v2_drt_readout_1102` packets; `analyze.py` is a small read-only reproducer.

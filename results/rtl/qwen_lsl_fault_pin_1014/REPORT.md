# Lane-slice registered fault-pin successor

Actual legacy `ot_qwen_tile_lsl` has nine combinational fault outputs after existing arithmetic fault flops. Its recovered native audit found five launches at263.1ps, above220ps, despite TT/FF closure. The new fixed-name `ot_qwen_tile_lsl_fp1` retains the exact same parameterized arithmetic instance and adds nine real clk/rst_n output registers. Only fault visibility adds one edge. Data arithmetic, order, input schedule and data output latency are unchanged.

Legacy arithmetic SHA256 is bb84cbf6b865c5c448aa31c4facdf766100fdafd712bfed18b516778c41f66f3. Legacy wrapper remains42f326a1cf8174fa352d17fd342a9c409b47e2b405baf903163c2a37ea3b28d5. The actual production-shape dual-instance test passes680 comparisons with145 actual nonzero fault edges. Native data matches legacy every checked edge. Faults match exactly the previous legacy edge. Source mutations bypassing the output register and replacing captured faults with zero both fail actual latency/data checks.

Admitted EPYC1 unit oth-ubuntu-3491803-1792036828 exits0; modes0/1/2 used the same actual unchanged arithmetic source. Raw source hashes and positive/negative logs accompany this report.

Die assignment23dca4512 inherits every rectangle of all465 signal pins, including legacy multi-PORT ownership stubs, from LEF7da1730df88a3fcbedb7dc607af06dc80453f422fe8a13e4955619eab0ece8c4. The99.792x140.4 outline and existing M4/M6 faces stay exact under the scoped die-owner M6 grant. Original published view8c1e8805e used eco_pk/pass1, TT+182.23ps/FF+19.04ps/DRC0; later f37684361 only transferred eight existing metal stubs from OBS to PORT ownership. This is distinct from the daemon generic eco/pass2 view. The canonical legacy CLOSED view is preserved.

Fresh native CTS, per-pin launch/capture, TT setup/FF hold and DRC must qualify the successor. Old insertion169.4ps/spread12.2ps is baseline provenance, not successor measurement. The new candidate's physical root and reset are real and must receive independently measured phi minus R delivery before die binding.

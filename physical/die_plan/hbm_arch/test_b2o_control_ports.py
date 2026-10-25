import b2o
def test_actual_clock_reset_pins_are_not_data_edges():
    for name in ('clk','clk[3]','tile_clk','u_map_tile_clk','clk_lane','clk_bank_macro',
                 'ck_serial','reset','rst_n','tile_rst_n','rst_lane_n','srst'):
        assert b2o.is_clock_reset_port(name), name
def test_payload_names_and_enables_keep_data_pipeline_checks():
    for name in ('clock_domain_id','reset_epoch','clk_en','clock_gate_en','data','go',
                 'tile_read_data','rst_valid','reset_request_valid'):
        assert not b2o.is_clock_reset_port(name), name

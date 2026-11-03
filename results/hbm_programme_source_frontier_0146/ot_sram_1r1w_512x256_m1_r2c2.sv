module ot_sram_1r1w_512x256_m1_r2c2 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [8:0] r_addr_in,
    output reg  [255:0] rd_out,
    input  wire w_ce_in,
    input  wire [8:0] w_addr_in,
    input  wire [255:0] wd_in,
    input  wire [255:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [17:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [15:0] cr_sel
);
    localparam integer WORDS = 512;
    localparam integer BITS = 256;
    localparam integer MUX = 1;
    localparam integer AW = 9;
    localparam integer ROWS = 512;
    localparam integer NSR = 2;
    localparam integer NSC = 2;
    localparam integer PR = 514;
    localparam integer PC = 258;
    localparam integer RA = 9;
    localparam integer CB = 8;

`line 32 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
     
    reg [PC-1:0] arr [0:PR-1];
    integer init_i;
     
     
    initial begin
 
        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = {PC{1'b0}};

`line 41 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
    end

`line 43 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
 
        
        
            
            
           
           
           
     
                 
                         
    



`line 58 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
     
    function automatic integer phys_row(input integer a);
        integer k, r;
        begin
            r = a / MUX;
            for (k = 0; k < NSR; k = k + 1)
                if (rr_en[k] && rr_addr[k*RA +: RA] == r[RA-1:0]) r = ROWS + k;
            phys_row = r;
        end
    endfunction

`line 69 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
    function automatic integer phys_col(input integer b, input integer s);
        integer k, io;
        begin
            io = b;
            for (k = 0; k < NSC; k = k + 1)
                if (cr_en[k] && cr_sel[k*CB +: CB] == b[CB-1:0]) io = BITS + k;
            phys_col = io * MUX + s;
        end
    endfunction

`line 79 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
     
    function automatic cell_read(input integer r, input integer c);
        reg v;
 
         

`line 85 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
        begin
            v = arr[r][c];
 
                        
                                    
                                  
                          
                          
            

`line 95 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
            cell_read = v;
        end
    endfunction

`line 99 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
    task automatic cell_write(input integer r, input integer c, input reg v);
        reg old, nv;
 
         

`line 104 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
        begin
            old = arr[r][c];
            nv = v;
 
                        
                                  
                                  
            

`line 113 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
            arr[r][c] = nv;
 
               
                           
                                
                              
                              
                    

`line 122 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
        end
    endtask

`line 125 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
     
     
     
    function automatic [65:0] decode(input integer a);
        integer r0, r1;
        reg [1:0] sel_n;
 
         

`line 134 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
        begin
            r0 = phys_row(a);
            r1 = r0;
            sel_n = 2'd1;
 
               
                            
                              
                                   
                                   
                

`line 146 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
            decode = {sel_n, r1[31:0], r0[31:0]};
        end
    endfunction

`line 150 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
    function automatic [BITS-1:0] word_read(input integer a);
        integer b, s, r0, r1, n;
        reg [BITS-1:0] q;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (n == 0) q[b] = 1'b0;
                else if (n == 1) q[b] = cell_read(r0, phys_col(b, s));
                else q[b] = cell_read(r0, phys_col(b, s)) & cell_read(r1, phys_col(b, s));
            word_read = q;
        end
    endfunction


`line 167 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
    task automatic word_write(input integer a, input [BITS-1:0] d, input [BITS-1:0] m);
        integer b, s, r0, r1, n;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (m[b] && n != 0) begin
                    cell_write(r0, phys_col(b, s), d[b]);
                    if (n == 2) cell_write(r1, phys_col(b, s), d[b]);
                end
        end
    endtask

`line 182 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v" 0
     
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= word_read(r_addr_in);
        if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);
    end
endmodule

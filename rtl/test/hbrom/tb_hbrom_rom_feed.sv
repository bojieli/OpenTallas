`timescale 1ps/1ps
module tb_hbrom_rom_feed;
    localparam PAIRS=128;
    reg clk=0;always begin #416 clk=1;#417 clk=0;end
    reg rst_n=0,cfg_valid=0,req_v=0,cancel=0;
    wire cfg_ready,req_ready,rsp_v,cancel_done,idle,fault;
    reg[1:0] cfg_fmt=0;reg[12:0]cfg_rows=0;reg[7:0]cfg_groups=0;
    reg cfg_group_slot=0;reg[31:0]cfg_base_record=0,cfg_region_records=0,cfg_virtual_base=0;
    reg[15:0]cfg_epoch=0;reg[31:0]req_addr=0;reg[9:0]req_tag=0;
    wire[9:0]rsp_tag;wire[1087:0]rsp_data;
    wire[2*PAIRS-1:0]rom_ce,capture_ce;
    wire[2*PAIRS*12-1:0]rom_addr;
    reg[2*PAIRS*274-1:0]rom_q=0;
    ot_hbrom_rom_feed #(.ENABLE(1),.PAIRS(PAIRS),.PROTECT(1)) dut(.*);
    integer cycle=0,returned=0,accepted=0,macros=0,captures=0;
    integer last_read[0:255], expected_phys[0:1023];
    reg[1087:0]expected_data[0:1023];
    reg check_response=1;
    // Synthetic physical ROM payload, independent of DUT cursor/assembly.
    // This bench validates transport; full-shape arithmetic uses released vectors separately.
    function automatic[273:0]word_value(input integer physical,input integer stream);
      integer b;reg[273:0]w;
      begin
        w=0;
        for(b=0;b<34;b=b+1) w[8*b+:8]=(physical*17+stream*53+b*7)&255;
        word_value=w;
      end
    endfunction
    function automatic[1087:0]line_value(input integer physical,input integer fmt);
      integer s;reg[273:0]w;reg[1087:0]r;
      begin
        r=0;
        for(s=0;s<4;s=s+1) begin
          w=word_value(physical,s);
          if(fmt==2) begin
            r[256*s+:128]=w[127:0];r[256*s+128+:128]=w[263:136];
            r[1024+16*s+:8]=w[135:128];r[1032+16*s+:8]=w[271:264];
          end else begin
            r[256*s+:256]=w[255:0];
            if(fmt==1)r[1024+8*s+:8]=w[263:256];
          end
        end
        line_value=r;
      end
    endfunction
    genvar p;
    generate for(p=0;p<256;p=p+1) begin:g_model
      wire[11:0]a=rom_addr[p*12+:12];
      wire[31:0]physical=(p/8)*8192+(a>>3)*16+(p%2)*8+(a&7);
      always @(posedge clk) if(rom_ce[p])
        rom_q[p*274+:274]<=#744 word_value(physical,(p/2)%4);
    end endgenerate
    integer j;
    always @(posedge clk) begin
      cycle=cycle+1;
      if(rst_n) begin
        for(j=0;j<256;j=j+1) begin
          if(capture_ce[j]) begin
            if(cycle-last_read[j]!=2)$fatal(1,"capture timing macro%0d delta%0d",j,cycle-last_read[j]);
            captures=captures+1;
          end
          if(rom_ce[j]) begin
            if(cycle-last_read[j]<2)$fatal(1,"ROM spacing macro%0d",j);
            last_read[j]=cycle;macros=macros+1;
          end
        end
        if(req_v&&req_ready) accepted=accepted+1;
        if(rsp_v&&check_response) begin
          if(rsp_tag!==returned[9:0])$fatal(1,"tag expected%0d got%0d",returned,rsp_tag);
          if(rsp_data!==expected_data[returned])$fatal(1,"data mismatch idx%0d physical%0d fmt%0d",returned,expected_phys[returned],cfg_fmt);
          returned=returned+1;
        end
      end
    end
    task automatic reset_feed;
      begin
        @(negedge clk);rst_n=0;req_v=0;cfg_valid=0;cancel=0;
        repeat(3)@(negedge clk);
        rst_n=1;
        for(integer q=0;q<256;q=q+1)last_read[q]=-100;
        accepted=0;returned=0;
      end
    endtask
    task automatic configure(input integer rows,groups,fmt,gs,base);
      begin
        while(!cfg_ready)@(negedge clk);
        cfg_rows=rows;cfg_groups=groups;cfg_fmt=fmt;cfg_group_slot=gs;
        cfg_base_record=base;cfg_region_records=rows*groups*8;cfg_virtual_base=17;cfg_epoch=cfg_epoch+1;
        cfg_valid=1;@(negedge clk);cfg_valid=0;
      end
    endtask
    task automatic normal(input integer rows,groups,fmt,gs,base);
      integer r,g,t,s,w,item,idx,rb,n;
      begin
        accepted=0;returned=0;idx=0;
        if(gs) begin
          for(w=0;w<rows*groups;w=w+8)
            for(t=0;t<8;t=t+1)
              for(s=0;s<8;s=s+1)begin
                item=w+s;
                if(item<rows*groups)begin
                  expected_phys[idx]=base+item*8+t;
                  expected_data[idx]=line_value(expected_phys[idx],fmt);idx=idx+1;
                end
              end
        end else begin
          for(rb=0;rb<rows;rb=rb+8)
            for(g=0;g<groups;g=g+1)
              for(t=0;t<8;t=t+1)
                for(s=0;s<8;s=s+1)begin
                  r=rb+s;
                  if(r<rows)begin
                    expected_phys[idx]=base+(r*groups+g)*8+t;
                    expected_data[idx]=line_value(expected_phys[idx],fmt);idx=idx+1;
                  end
                end
        end
        configure(rows,groups,fmt,gs,base);
        for(n=0;n<idx;n=n+1)begin
          req_v=1;req_addr=17+n;req_tag=n;
          do @(posedge clk);while(!req_ready);
          @(negedge clk);req_v=0;
          if(n%11==3)repeat(2)@(negedge clk);
        end
        while(returned<idx)begin @(negedge clk);if(fault)$fatal(1,"normal fault");end
        while(!cfg_ready)@(negedge clk);
        if(accepted!=idx)$fatal(1,"accepted count");
        $display("PASS normal rows%0d groups%0d fmt%0d gs%0d base%0d lines%0d",rows,groups,fmt,gs,base,idx);
      end
    endtask
    initial begin
      reset_feed();
      normal(3,3,2,1,0);
      normal(9,2,1,0,8192);
      normal(3,10,0,1,7*8192);
      normal(3,5,1,1,16*8192);
      normal(3,2,2,0,31*8192);
      // Invalid descriptor must fault without exposing ROM side effects.
      cfg_rows=0;cfg_valid=1;@(negedge clk);cfg_valid=0;
      if(!fault)$fatal(1,"invalid config not rejected");
      reset_feed();configure(3,3,2,1,0);
      // Wrong sequential virtual address: no acceptance, sticky fault.
      req_v=1;req_addr=18;req_tag=0;@(negedge clk);req_v=0;
      if(!fault)$fatal(1,"bad address not rejected");
      reset_feed();configure(3,3,2,1,0);
      req_v=1;req_addr=17;req_tag=0;do @(posedge clk);while(!req_ready);
      @(negedge clk);req_addr=18; // same live tag is a transaction identity error
      @(negedge clk);req_v=0;
      if(!fault)$fatal(1,"duplicate tag not rejected");
      reset_feed();configure(3,3,2,1,0);
      check_response=0;
      req_v=1;req_addr=17;req_tag=0;do @(posedge clk);while(!req_ready);
      @(negedge clk);req_v=0;cancel=1;@(negedge clk);cancel=0;
      while(!cancel_done)begin @(negedge clk);if(rsp_v)$fatal(1,"cancelled response leaked");end
      while(!cfg_ready)@(negedge clk);
      check_response=1;normal(3,3,2,1,0);
      reset_feed();configure(3,3,2,1,0);
      // A single-copy mutable-state corruption must seal all side effects.
      force dut.u_cursor1.next_base=32'h123;
      @(negedge clk);
      if(!fault||req_ready||(|rom_ce))$fatal(1,"DMR seal did not suppress side effects");
      release dut.u_cursor1.next_base;
      $display("PASS HBROM feed protocol/transport macros%0d captures%0d cycles%0d",macros,captures,cycle);
      $finish;
    end
    initial begin repeat(20000)@(posedge clk);$fatal(1,"finite small-test watchdog");end
endmodule

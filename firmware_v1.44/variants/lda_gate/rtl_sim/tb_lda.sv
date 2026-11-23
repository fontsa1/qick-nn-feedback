// tb_lda.sv: copy of neural_net4_live576s/rtl_sim/tb_live.sv with the DUT swapped for the HLS-generated LDA_live
// (R2 build 2). live_window_gate + LDA_live on a continuous 552.96 MHz stream with an asynchronous tProc-style trigger.
// Test A (alignment): gate words vs QICK's buffer.sv, as tb_live. Test B (inference): real windows placed where the
// gate captures; res_o (logit, decision, shot) and the record words must equal lda_model.py (expected.hex); latency
// counted from the gate's TLAST beat to res_o_ap_vld, exactly as tb_live counts it for NN_live (9 cycles there).
`timescale 1ps / 1ps

module tb_lda;
    localparam integer N = 576;
    localparam integer K = 24;
    localparam integer KA = 12;
    localparam integer GAP = 1500;

    reg aclk = 0, tclk = 0;
    always #904 aclk = ~aclk;           // 1.808 ns: clk_adc0_x2, 552.96 MHz
    always #1017 tclk = ~tclk;          // 2.034 ns: tProc t_clk, 491.52 MHz
    reg aresetn = 0;

    integer cyc = 0;
    always @(posedge aclk) cyc <= cyc + 1;

    reg  [31:0] s_tdata = 0;
    reg         s_tvalid = 0;
    reg  [31:0] idx = 0;
    integer     mode = 0;
    integer     win_sel = 0, src_cnt = 0;
    reg  [31:0] win [0:K*N-1];

    wire will_memw = (gate.state == 2'd0 && gate.trig_r) || (gate.state == 2'd1 && !gate.done);

    always @(posedge aclk) begin
        idx <= idx + 1;
        s_tvalid <= aresetn;
        if (mode == 0) begin
            s_tdata <= idx;
        end else if (will_memw) begin
            s_tdata <= win[win_sel * N + src_cnt];
            src_cnt <= src_cnt + 1;
        end else begin
            s_tdata <= {idx[15:0], ~idx[15:0]};
            src_cnt <= 0;
        end
    end

    reg trig = 0;
    task fire;
        begin
            @(posedge tclk);
            trig <= 1;
            repeat (20) @(posedge tclk);
            trig <= 0;
        end
    endtask

    wire [31:0] g_tdata;
    wire        g_tvalid, g_tlast, g_tready;
    wire [3:0]  g_tkeep, g_tstrb;
    live_window_gate #(.N(N)) gate (
        .aclk(aclk), .aresetn(aresetn), .trigger(trig),
        .s_axis_tdata(s_tdata), .s_axis_tvalid(s_tvalid),
        .m_axis_tdata(g_tdata), .m_axis_tvalid(g_tvalid), .m_axis_tlast(g_tlast),
        .m_axis_tkeep(g_tkeep), .m_axis_tstrb(g_tstrb), .m_axis_tready(g_tready));

    wire [63:0] res_o;
    wire        res_vld;
    wire [31:0] b_addr, b_din;
    wire        b_en, b_clk, b_rst;
    wire [3:0]  b_we;
    reg  [31:0] b_dout = 0;
    LDA_live dut (
        .ap_clk(aclk), .ap_rst_n(aresetn),
        .in_r_TDATA(g_tdata), .in_r_TVALID(g_tvalid), .in_r_TREADY(g_tready),
        .in_r_TKEEP(g_tkeep), .in_r_TSTRB(g_tstrb), .in_r_TLAST(g_tlast),
        .res_o(res_o), .res_o_ap_vld(res_vld),
        .out_r_Addr_A(b_addr), .out_r_EN_A(b_en), .out_r_WEN_A(b_we),
        .out_r_Din_A(b_din), .out_r_Dout_A(b_dout), .out_r_Clk_A(b_clk), .out_r_Rst_A(b_rst));

    reg [31:0] mem [0:8191];
    always @(posedge aclk) if (b_en) begin
        if (b_we != 0) mem[b_addr[14:2]] <= b_din;
        b_dout <= mem[b_addr[14:2]];
    end

    (* ASYNC_REG = "TRUE" *) reg [1:0] ref_sync = 0;
    always @(posedge aclk) ref_sync <= aresetn ? {ref_sync[0], trig} : 2'b00;
    wire        ref_we;
    wire [9:0]  ref_addr;
    wire [31:0] ref_di;
    buffer #(.N(10), .B(16)) ref_buf (
        .rstn(aresetn), .clk(aclk), .trigger_i(ref_sync[1]),
        .din_valid_i(s_tvalid), .din_i(s_tdata),
        .mem_we_o(ref_we), .mem_addr_o(ref_addr), .mem_di_o(ref_di),
        .START_REG(1'b1), .ADDR_REG(10'd0), .LEN_REG(10'd576));

    reg [31:0] ref_q  [0:KA*N-1];
    reg [31:0] gate_q [0:KA*N-1];
    integer n_ref = 0, n_gate = 0, gate_words_total = 0, tlast_bad = 0, drops = 0;
    integer t_last [0:63];
    integer last_mode [0:63], last_win [0:63];
    integer n_last = 0, n_res = 0, bad_val = 0, lat_min = 1 << 30, lat_max = 0;
    reg [15:0] exp_logit [0:K-1];
    reg        exp_dec [0:K-1];
    reg [31:0] exp_dlo [0:K-1], exp_dhi [0:K-1];
    reg [63:0] res_log [0:63];

    always @(posedge aclk) begin
        if (ref_we && mode == 0 && n_ref < KA * N) begin
            ref_q[n_ref] = ref_di;
            n_ref = n_ref + 1;
        end
        if (g_tvalid) begin
            if (!g_tready) drops = drops + 1;
            if (mode == 0 && n_gate < KA * N) begin
                gate_q[n_gate] = g_tdata;
                n_gate = n_gate + 1;
            end
            if (g_tlast != ((gate_words_total % N) == N - 1)) tlast_bad = tlast_bad + 1;
            gate_words_total = gate_words_total + 1;
            if (g_tlast) begin
                t_last[n_last] = cyc;
                last_mode[n_last] = mode;
                last_win[n_last] = win_sel;
                n_last = n_last + 1;
            end
        end
        if (res_vld) begin : chk
            integer lat;
            lat = cyc - t_last[n_res];
            if (lat < lat_min) lat_min = lat;
            if (lat > lat_max) lat_max = lat;
            res_log[n_res] = res_o;
            if (last_mode[n_res] == 1) begin
                if (res_o[63] !== exp_dec[last_win[n_res]] || res_o[15:0] !== exp_logit[last_win[n_res]] || res_o[44:16] !== n_res) begin
                    bad_val = bad_val + 1;
                    $display("MISMATCH window %0d: res %h expected logit %h decision %0d", last_win[n_res], res_o,
                             exp_logit[last_win[n_res]], exp_dec[last_win[n_res]]);
                end
            end
            if (n_res < 3 || last_mode[n_res] == 1 && last_win[n_res] < 3)
                $display("result %0d (mode %0d win %0d): logit raw %0d decision %0d, latency %0d cycles after the gate's TLAST beat",
                         n_res, last_mode[n_res], last_win[n_res], $signed(res_o[15:0]), res_o[63], lat);
            n_res = n_res + 1;
        end
    end

    integer k, fd, r, bad_rec, bad_cap;
    reg [15:0] lg;
    reg [3:0]  dc;
    reg [31:0] dl, dh;
    initial begin
        $readmemh("windows.hex", win);
        fd = $fopen("expected.hex", "r");
        for (k = 0; k < K; k = k + 1) begin
            r = $fscanf(fd, "%h %h %h %h\n", lg, dc, dl, dh);
            exp_logit[k] = lg; exp_dec[k] = dc[0]; exp_dlo[k] = dl; exp_dhi[k] = dh;
        end
        $fclose(fd);

        repeat (40) @(posedge aclk);
        aresetn = 1;
        repeat (200) @(posedge aclk);

        mode = 0;
        for (k = 0; k < KA; k = k + 1) begin
            #(k * 137);
            fire();
            repeat (GAP) @(posedge aclk);
        end

        mode = 1;
        for (k = 0; k < K; k = k + 1) begin
            win_sel = k;
            fire();
            repeat (GAP) @(posedge aclk);
        end
        repeat (200) @(posedge aclk);

        bad_cap = 0;
        for (k = 0; k < KA * N; k = k + 1)
            if (gate_q[k] !== ref_q[k]) bad_cap = bad_cap + 1;
        bad_rec = 0;
        for (k = 0; k < K; k = k + 1) begin : rec
            integer shot, base;
            shot = KA + k;
            base = 1024 + (shot % 512) * 8;
            if (mem[base] !== shot || mem[base + 1] !== exp_dlo[k] || mem[base + 2] !== exp_dhi[k] ||
                mem[base + 5] !== {16'd0, exp_logit[k]} || mem[base + 7] !== {31'd0, exp_dec[k]} ||
                ((mem[base + 6][17:0] > 18'd512) !== exp_dec[k]))
                bad_rec = bad_rec + 1;
        end

        $display("");
        $display("=== tb_lda ===");
        $display("A  gate vs buffer.sv words      : %0d/%0d captured each side, %0d mismatches", n_gate, n_ref, bad_cap);
        $display("   TLAST placement errors       : %0d (of %0d gate words)", tlast_bad, gate_words_total);
        $display("B  res_o vs lda_model.py        : %0d mismatches (of %0d)", bad_val, K);
        $display("   records (D, logit, sigmoid, decision, shot): %0d mismatches", bad_rec);
        $display("   words offered with TREADY low: %0d", drops);
        $display("   header: shots %0d (expect %0d), frame_err %0d, magic %h, classifier %h", mem[0], KA + K, mem[1], mem[2], mem[3]);
        $display("   results seen %0d of %0d windows", n_res, n_last);
        $display("LATENCY gate TLAST beat -> res_o_ap_vld (logit + decision): %0d..%0d cycles = %.1f..%.1f ns at 552.96 MHz",
                 lat_min, lat_max, lat_min * 1.80845, lat_max * 1.80845);
        if (bad_cap == 0 && n_gate == KA * N && n_ref == KA * N && tlast_bad == 0 && bad_val == 0 &&
            bad_rec == 0 && drops == 0 && mem[0] == KA + K && mem[1] == 0 && mem[3] == 32'h4C444131 && n_res == n_last && n_last == KA + K)
            $display("RESULT: PASS");
        else
            $display("RESULT: FAIL");
        $finish;
    end
endmodule

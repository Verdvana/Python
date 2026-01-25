import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import os

# --- 1. 定义波形绘制函数 ---
def draw_timing_diagram(filename, mode="write"):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Grid and Setup
    ax.set_ylim(0, 10)
    ax.set_xlim(0, 10)
    ax.axis('off')
    
    # Styles
    clk_color = 'black'
    sig_color = 'blue'
    bus_color = 'green'
    
    # Helper to draw clock
    def draw_clk(y, cycles):
        x = 0
        for i in range(cycles * 2):
            ax.plot([x, x, x+0.5, x+0.5], [y, y+1, y+1, y], color=clk_color, lw=1)
            x += 0.5
        ax.text(-0.5, y+0.2, "HCLK", fontsize=10)
        
    def draw_pclk(y, cycles): # Half frequency
        x = 0
        for i in range(cycles):
            ax.plot([x, x, x+1, x+1], [y, y+1, y+1, y], color=clk_color, lw=1)
            x += 1
        ax.text(-0.5, y+0.2, "PCLK", fontsize=10)

    # Helper for signal lines
    def draw_signal(name, y, points, color='black'):
        x_vals, y_vals = zip(*points)
        # Scale y_vals to position
        y_scaled = [y + (val * 0.8) for val in y_vals]
        ax.step(x_vals, y_scaled, where='post', color=color, lw=1.5)
        ax.text(-0.8, y, name, fontsize=10)

    # Helper for Bus (Box style)
    def draw_bus(name, y, segments):
        ax.text(-0.8, y+0.3, name, fontsize=10)
        for (start, end, text, fill) in segments:
            # Draw Hexagon/Box
            if fill:
                p = patches.Polygon(
                    [[start, y+0.4], [start+0.2, y+0.8], [end-0.2, y+0.8], [end, y+0.4], [end-0.2, y], [start+0.2, y]],
                    closed=True, edgecolor='black', facecolor='#DDDDDD'
                )
                ax.add_patch(p)
                ax.text((start+end)/2, y+0.3, text, ha='center', fontsize=8)
            else:
                # Idle line
                ax.plot([start, end], [y+0.4, y+0.4], color='black', lw=1)

    # --- Draw Common Clocks ---
    draw_clk(9, 8)
    draw_pclk(8, 8) # PCLK aligned
    
    # Time markers
    for i in range(1, 9):
        ax.axvline(x=i, color='gray', linestyle='--', alpha=0.3)
        ax.text(i, 9.8, f"T{i}", fontsize=8)

    if mode == "write":
        plt.title("AHB Write to APB (HCLK:PCLK = 2:1)", fontsize=14)
        # AHB Side
        draw_bus("HADDR",  6.5, [(0,1,"Addr A",1), (1,3,"Addr B",1), (3,8,"...",0)])
        draw_bus("HWDATA", 5.5, [(0,1,"-",0), (1,3,"Data A",1), (3,8,"...",0)])
        draw_signal("HTRANS", 4.5, [(0,0),(0.1,1),(1,0)], color=sig_color) # Pulse at T1
        draw_signal("HREADYout", 3.5, [(0,1),(1,0),(5,1),(8,1)], color='red') # Stalls from T1 to T5 (Wait for APB)
        
        # APB Side
        # PSEL goes High when Bridge detects trans (T1->T2 latch, so T2)
        draw_signal("PSEL",   2.5, [(0,0),(1,1),(5,0)], color=sig_color) # High T1 to T5? No, Bridge sees T1, drives T1->T2. 
        # Correct timing: T1 sample, T1-T2 logic.
        # Let's assume registered output for clean glitches, PSEL high at T1.5 (aligned to PCLK/HCLK edge)
        # Simplified: PSEL valid from T1.
        
        # PENABLE (Access phase)
        # Setup T1-T3 (1 PCLK cycle), Access T3-T5 (1 PCLK cycle)
        draw_signal("PENABLE", 1.5, [(0,0),(3,1),(5,0)], color=sig_color)
        
        # PREADY (From Slave)
        # Slave sees PENABLE at T3, responds. Ready at T5.
        draw_signal("PREADY",  0.5, [(0,0),(4.5,1),(5.5,0)], color='green')

    elif mode == "read":
        plt.title("AHB Read from APB (HCLK:PCLK = 2:1)", fontsize=14)
        draw_bus("HADDR",  6.5, [(0,1,"Addr A",1), (1,3,"Addr B",1)])
        draw_signal("HWRITE", 5.5, [(0,0),(8,0)], color=sig_color)
        draw_signal("HREADYout", 4.5, [(0,1),(1,0),(5,1)], color='red')
        
        draw_signal("PSEL",   3.5, [(0,0),(1,1),(5,0)], color=sig_color)
        draw_signal("PENABLE", 2.5, [(0,0),(3,1),(5,0)], color=sig_color)
        draw_bus("PRDATA",    1.5, [(0,3,"-",0), (3,5.5,"ReadData",1), (5.5,8,"-",0)])
        draw_bus("HRDATA",    0.5, [(0,3,"-",0), (3,5.5,"ReadData",1)]) # Direct connect

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

# --- 2. 生成 PDF ---
def create_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="AHB2APB Bridge Module Documentation", ln=1, align='C')
    pdf.ln(10)
    
    # Description
    pdf.set_font("Arial", size=11)
    desc = ("This module implements a bridge between AMBA 2 AHB and AMBA 4 APB protocols.\n"
            "It supports synchronous clock domains where HCLK >= PCLK.\n"
            "It handles the translation of AHB pipelined transfers into APB Setup/Access phases.\n"
            "Key Feature: Auto-generates APB4 PSTRB signals based on HSIZE.")
    pdf.multi_cell(0, 7, desc)
    pdf.ln(5)
    
    # Interface Table (Simulated with text)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. Interface Description", ln=1)
    pdf.set_font("Courier", size=9)
    table = """
    | Signal Name | Direction | Description                   |
    |-------------|-----------|-------------------------------|
    | HCLK        | Input     | AHB Clock (Fast)              |
    | HRESETn     | Input     | Active Low Reset              |
    | HADDR       | Input     | AHB Address                   |
    | HWDATA      | Input     | AHB Write Data                |
    | HREADYout   | Output    | Bridge Ready (Stall Signal)   |
    | HRDATA      | Output    | AHB Read Data                 |
    |-------------|-----------|-------------------------------|
    | PADDR       | Output    | APB Address                   |
    | PWDATA      | Output    | APB Write Data                |
    | PENABLE     | Output    | APB Access Phase Enable       |
    | PREADY      | Input     | APB Slave Ready (Handshake)   |
    """
    pdf.multi_cell(0, 5, table)
    pdf.ln(5)

    # Timing Diagrams
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. Timing Diagrams (HCLK=2*PCLK)", ln=1)
    
    # Generate Images
    draw_timing_diagram("write_wave.png", "write")
    draw_timing_diagram("read_wave.png", "read")
    
    # Insert Images
    pdf.image("write_wave.png", x=10, w=180)
    pdf.ln(5)
    pdf.cell(0, 10, "Figure 1: Write Transfer Timing", ln=1, align='C')
    pdf.ln(10)
    
    pdf.image("read_wave.png", x=10, w=180)
    pdf.ln(5)
    pdf.cell(0, 10, "Figure 2: Read Transfer Timing", ln=1, align='C')

    # Usage
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. Integration Guide", ln=1)
    pdf.set_font("Arial", size=11)
    usage = ("1. Connect HCLK to the system bus clock.\n"
             "2. Ensure the APB Slave is connected to PCLK (which is synchronous to HCLK).\n"
             "3. The bridge relies on PREADY to handle the frequency difference.\n"
             "   If PCLK is slower, PREADY will stay low longer, forcing the AHB side to wait.")
    pdf.multi_cell(0, 7, usage)

    pdf.output("AHB2APB_Bridge_Datasheet.pdf")
    print("PDF Generated Successfully: AHB2APB_Bridge_Datasheet.pdf")
    
    # Cleanup images
    if os.path.exists("write_wave.png"): os.remove("write_wave.png")
    if os.path.exists("read_wave.png"): os.remove("read_wave.png")

if __name__ == "__main__":
    create_pdf()
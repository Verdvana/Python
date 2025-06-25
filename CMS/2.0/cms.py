import sys
import openpyxl
from dataclasses import dataclass,field

@dataclass
class DrivingCell:
    name:str="NA"
    input:str="NA"
    output:str="NA"
    lib:str="NA"

@dataclass
class Range:
    min:str="NA"
    max:str="NA"

@dataclass
class ClockTree:
    source_latency:Range=field(default_factory=Range)
    network_latency:Range=field(default_factory=Range)
    trans:Range=field(default_factory=Range)
    skew:str="NA"
    noise:str="NA"


@dataclass
class Config:
    signal_driving_cell:DrivingCell=field(default_factory=DrivingCell)
    clock_driving_cell:DrivingCell=field(default_factory=DrivingCell)
    signal_trans:Range=field(default_factory=Range)
    output_load:Range=field(default_factory=Range)
    output_trans:Range=field(default_factory=Range)
    output_delay:Range=field(default_factory=Range)
    input_delay:Range=field(default_factory=Range)
    input_trans:Range=field(default_factory=Range)
    setup_margin:str="NA"
    hold_margin:str="NA"
    sm_ct:ClockTree=field(default_factory=ClockTree)
    md_ct:ClockTree=field(default_factory=ClockTree)
    lg_ct:ClockTree=field(default_factory=ClockTree)
    raw_ct:ClockTree=field(default_factory=ClockTree)

def find_cell(sheet, target):
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value == target:
                return cell
    return None

def parse_config(sheet):
    config=Config()
    
    config.signal_driving_cell.name = sheet['B3'].value
    config.signal_driving_cell.output = sheet['D3'].value
    config.signal_driving_cell.input = sheet['E3'].value
    config.signal_driving_cell.lib = sheet['F3'].value
    config.clock_driving_cell.name = sheet['B4'].value
    config.clock_driving_cell.output = sheet['D4'].value
    config.clock_driving_cell.input = sheet['E4'].value
    config.clock_driving_cell.lib = sheet['F4'].value
    
    return config

def main(filename):
    wb = openpyxl.load_workbook(filename)

    if 'pt' in wb.sheetnames:
        pt_config = parse_config(wb['pt'])
    
    print(pt_config)
    

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cms.py <excel_file>")
        sys.exit(1)
    
    table_path = sys.argv[1]
    try:
        result = main(table_path)
    except Exception as e:
        print("Error:", e)
import sys
import pandas as pd

def read_with_pandas(file_path):
    try:
        # 读取名为 "pt" 的 sheet
        df = pd.read_excel(file_path, sheet_name="pt", header=None)
    except ValueError:
        raise ValueError("没有名为 'pt' 的工作表")

    pt = {
        "signal_driving_cell": None,
        "clock_driving_cell": None,
        "signal_transition_min": None,
        "signal_transition_max": None
    }

    # 遍历 DataFrame 查找关键字段
    for i in range(len(df)):
        row = df.iloc[i]
        for j in range(len(row)):
            val = str(row[j]).strip()
            if val == "Signal Driving Cell":
                pt["signal_driving_cell"] = row[j + 1] if j + 1 < len(row) else None
            elif val == "Clock Driving Cell":
                pt["clock_driving_cell"] = row[j + 1] if j + 1 < len(row) else None
            elif val == "Signal Transition":
                pt["signal_transition_min"] = row[j + 1] if j + 1 < len(row) else None
                pt["signal_transition_max"] = row[j + 2] if j + 2 < len(row) else None

    return pt

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python3 cms.py <excel文件路径>")
        sys.exit(1)

    file_path = sys.argv[1]
    print(file_path)
    try:
        pt = read_with_pandas(file_path)
    
        print("Signal Driving Cell:", pt["signal_driving_cell"])
        print("Clock Driving Cell:", pt["clock_driving_cell"])
        print("Signal Transition Min:", pt["signal_transition_min"])
        print("Signal Transition Max:", pt["signal_transition_max"])
    except Exception as e:
        print("发生错误:", e)
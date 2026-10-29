# 根据表格中的微指令生成asm文件
# 请在Begin-End区域内输入数据
from os import makedirs, path
import webbrowser
from time import time, sleep
import traceback

import openpyxl

from asm_to_hex import assemble_file

########################Begin#########################

# 表格1（存放微指令）所在文件位置
excel1_path = "data1.xlsx"
# 表格2（存放程序代码）所在文件位置
excel2_path = "data1.xlsx"
# 表格1在对应文件的哪一个工作表
sheet1_index = 0
# 表格2在对应文件的哪一个工作表
sheet2_index = 1
# 表格1有效数据起始行列(从1开始，元组第一个元素代表列数，第二个元素代表行数)
sheet1_start = (2, 2)
# 表格2有效数据起始行列(从1开始，元组第一个元素代表列数，第二个元素代表行数)
sheet2_start = (1, 2)
# 是否后台监视表格文件，表格更改后自动生成asm并编译hex（True为持续监视，False为只生成一次）
watch_excel = True
# 检查表格是否更改的间隔时间（秒）
check_interval = 1.0

#########################End##########################

# 可选配置

########################Begin#########################

# 是否要打印asm文件的内容
print_asm = False
# 是否要生成hex文件
make_hex = True
# 要生成的MROM文件的位置
MROM_path = "INSTRUCTIONS"
# MROM文件名前缀
MROM_file_name_prefix = "MROM"
# 要生成的PROGRAM文件的位置
PROGRAM_path = "PROGRAMS"
# PROGRAM文件名前缀
PROGRAM_file_name = "PROGRAM"
# 编译器位置
asemFile = r"C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\Tools\ASEM51\ASEM.EXE"
########################End###########################

# 变量中的“nof”指的是……的数量（number of）。请读者不要学习这种起名方式，可以使用count来表示数量。

if not path.exists(MROM_path):
    makedirs(MROM_path, exist_ok=True)
    print(MROM_path + "路径不存在，已自动创建")

if not path.exists(PROGRAM_path):
    makedirs(PROGRAM_path, exist_ok=True)
    print(PROGRAM_path + "路径不存在，已自动创建")

# asemFile存在时用ASEM51编译，不存在时改用内置汇编器编译
use_asem = make_hex and path.exists(asemFile)
if make_hex and not path.exists(asemFile):
    print("asem 文件位置错误，改用内置汇编器生成hex文件")

MROM_result = [""]


def get_max_col_and_row(sheet, start: tuple = (1, 1)) -> tuple:
    """
    获取表格有效数据的范围，同时将表格内容以二维列表形式返回
    :param start: 有效数据起始位置（行数，列数）
    :param sheet: 工作表
    :return: 有效数据终止位置（行数，列数），表格内容
    """
    max_c = 0
    max_r = 0
    l = []

    # 遍历所有单元格寻找有值的最大行列
    for row in sheet.iter_rows(
            min_row=start[1], max_row=sheet.max_row, min_col=start[0], max_col=sheet.max_column
    ):
        l2 = []
        for cell in row:
            if cell.value is not None:
                l2.append(cell.value)
                if cell.row > max_r:
                    max_r = cell.row
                if cell.column > max_c:
                    max_c = cell.column
        l.append(l2)
    return (max_c, max_r), l


def is_bin_addr_next_to(addr1, addr2, prefix='0b'):
    if addr1 is None or addr2 is None:
        return False
    n1 = eval(prefix + addr1)
    n2 = eval(prefix + addr2)
    if n2 - n1 == 1:
        return True
    return False


def is_hex_addr_next_to(addr1, addr2):
    if addr1 is None or addr2 is None:
        return False
    n1 = eval("0x" + addr1[:-1])
    n2 = eval('0x' + addr2[:-1])
    if n2 - n1 == 1:
        return True
    # print(f"{addr1}, {addr2} not next to:{n2}-{n1}={n2-n1}")
    return False


def add_all(string):
    global MROM_result
    for i in range(len(MROM_result)):
        MROM_result[i] += string


def to_add_to_result(char):
    if char == '1' or char == 1:
        return '1'
    elif char == '0' or char == 0 or char == 'X' or char == '-':
        return '0'
    raise ValueError("无效值：" + str(char))


def generate_all():
    """
    读取Excel表格并生成所有asm文件
    :return: 生成的asm文件路径列表（MROM在前，PROGRAM在最后）
    """
    global MROM_result

    wb1 = openpyxl.load_workbook(excel1_path)
    if excel1_path == excel2_path:
        wb2 = wb1
    else:
        wb2 = openpyxl.load_workbook(excel2_path)

    sheet1 = wb1.worksheets[sheet1_index]
    sheet2 = wb2.worksheets[sheet2_index]

    sheet1_end, l1 = get_max_col_and_row(sheet1, sheet1_start)
    sheet2_end, l2 = get_max_col_and_row(sheet2, sheet2_start)

    nof_MROM_outputs = sheet1_end[0] - sheet1_start[0]
    nof_MROM = nof_MROM_outputs // 8

    nof_sheet1_rows = len(l1)

    last_addr = None

    MROM_result = [""] * nof_MROM
    for i in range(nof_sheet1_rows):
        if len(l1[i]) != nof_MROM_outputs + 1:
            if MROM_result[0] == "":
                print(f"错误：nof_MROM_outputs的值{nof_MROM_outputs}和数据个数{len(l1[i]) - 2}不匹配")
            else:
                print(f"错误：MROM_string第{i + 1}行有效数据有{len(l1[i]) - 2}个数据", end="")
                if len(l1[i]) < nof_MROM_outputs + 2:
                    print("少了", end="")
                else:
                    print("多了", end="")
                print(f"{abs(len(l1[i]) - nof_MROM_outputs - 2)}个数据。")
            raise ValueError
        addr = l1[i][0]
        if not is_bin_addr_next_to(last_addr, addr):
            add_all("ORG\t" + addr + "B\n")
        add_all("\tDB\t")
        for j in range(nof_MROM):
            for k in range(1 + j * 8, 1 + (j + 1) * 8):
                MROM_result[j] += to_add_to_result(l1[i][k])
        add_all("B\n")
        last_addr = addr

    add_all("END")

    if print_asm:
        for i in range(nof_MROM):
            print(f"\nMROM{i + 1}:")
            print(MROM_result[i])

    asm_files = []
    for i in range(nof_MROM):
        asm_file = f"{MROM_path}/{MROM_file_name_prefix}{i + 1}.asm"
        with open(asm_file, "w") as f:
            f.write(MROM_result[i])
        print(f"{MROM_file_name_prefix}{i + 1}.asm文件生成成功")
        asm_files.append(asm_file)

    # 开始写PROGRAM.asm

    nof_sheet2_rows = len(l2)

    last_addr = None
    PROGRAM_result = ""
    for i in range(nof_sheet2_rows):
        if len(l2[i]) <= 1:
            continue
        if not (l2[i][1] and l2[i][2]):
            continue
        addr = l2[i][1]
        if not is_hex_addr_next_to(last_addr, addr):
            PROGRAM_result += "ORG\t" + addr + "\n"
        PROGRAM_result += "\tDB\t"
        PROGRAM_result += l2[i][2] + "B"

        if l2[i][0]:
            PROGRAM_result += ";" + l2[i][0]
        PROGRAM_result += "\n"
        last_addr = addr

    PROGRAM_result += "END"
    if print_asm:
        print("\nPROGRAM:")
        print(PROGRAM_result)
    program_asm_file = f"{PROGRAM_path}/{PROGRAM_file_name}.asm"
    with open(program_asm_file, "w") as f:
        f.write(PROGRAM_result)
    asm_files.append(program_asm_file)

    print("PROGRAM.asm文件生成成功。")
    return asm_files


def compile_hex(asm_files):
    """
    把asm文件编译成hex文件
    asemFile存在时生成bat脚本调用ASEM51编译，否则用内置汇编器编译
    :param asm_files: asm文件路径列表
    """
    if use_asem:
        print("生成用于生成hex文件的bat脚本")
        batName = str(time()) + ".bat"
        with open(batName, "w") as f:
            f.write("@echo off\n")
            for asm_file in asm_files:
                f.write(f"\"{asemFile}\" " + asm_file.replace("/", "\\") + "\n")
            f.write("pause\n")
            f.write("del %0")

        webbrowser.open(batName)
        print("hex文件开始生成。")
    else:
        for asm_file in asm_files:
            hex_file = assemble_file(asm_file)
            print(hex_file + "文件生成成功")


def generate_and_compile():
    """生成asm文件并按配置编译hex文件"""
    asm_files = generate_all()
    if make_hex:
        compile_hex(asm_files)


def get_excel_mtimes():
    """
    获取两个表格文件的修改时间，文件不存在时为None
    :return: 两个表格文件修改时间组成的元组
    """
    mtimes = []
    for excel_path in (excel1_path, excel2_path):
        try:
            mtimes.append(path.getmtime(excel_path))
        except OSError:
            mtimes.append(None)
    return tuple(mtimes)


def watch_and_generate():
    """
    后台监视表格文件，表格更改后重新生成asm并编译hex，按Ctrl+C退出
    """
    print("开始监视表格文件，表格更改后将自动生成asm并编译hex")
    print("按 Ctrl+C 退出程序")
    last_mtimes = None
    while True:
        mtimes = get_excel_mtimes()
        if mtimes != last_mtimes:
            try:
                generate_and_compile()
                # 生成成功后才更新修改时间，生成失败时下次循环重试
                # 使用生成前读取的快照；若生成期间表格又被修改，下一轮会再次生成
                last_mtimes = mtimes
                print("监视中，等待表格更改……")
            except Exception:
                print("生成失败，错误信息如下。修改表格后将重新生成：")
                traceback.print_exc()
        sleep(check_interval)


if __name__ == "__main__":
    if watch_excel:
        try:
            watch_and_generate()
        except KeyboardInterrupt:
            print("\n程序已退出")
    else:
        generate_and_compile()

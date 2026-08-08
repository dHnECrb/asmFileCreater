# 根据表格中的微指令生成asm文件
# 请在Begin-End区域内输入数据
###################Begin#########################

# MROM输出个数
nof_MROM_outputs = 32
# 从表格中粘贴MROM数据
MROM_string = """
0000	取指	-	0	0	0	0	0	0	0	0	0	0	0	0	0	0	1	0	-	1	-	-	1	-	1	-	1	0	0	0	0	0	0
0001	JMP1	-	0	0	0	0	0	0	0	0	0	0	0	0	0	0	1	1	-	1	-	-	1	-	0	-	0	0	0	0	0	0	0
0010	JMP2	-	0	0	0	0	0	0	0	0	0	0	0	0	0	0	1	1	-	1	-	-	1	-	0	-	0	0	0	0	0	0	1
0011	JMP3	-	0	0	0	0	0	0	0	0	0	0	0	0	0	0	1	1	-	1	-	-	1	-	0	-	0	0	0	0	0	1	0
0100	LDARA	-	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	-	0	-	-	1	-	0	-	0	0	0	0	1	0	1
0101	LDARA_2	-	0	0	1	1	0	0	0	0	0	0	0	0	0	0	1	0	-	1	-	-	1	-	0	-	0	0	0	0	0	0	0
0110	LDARB	-	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	-	0	-	-	1	-	0	-	0	0	0	0	1	1	1
0111	LDARB_2	-	0	0	1	0	1	0	0	0	0	0	0	0	0	0	1	0	-	1	-	-	1	-	0	-	0	0	0	0	0	0	0
1000	LDARC	-	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	-	0	-	-	1	-	0	-	0	0	0	1	0	0	1
1001	LDARC_2	-	0	0	1	0	0	1	0	0	0	0	0	0	0	0	1	0	-	1	-	-	1	-	0	-	0	0	0	0	0	0	0
1010	ADD	1	1	0	0	0	1	0	0	0	1	0	0	1	1	1	0	0	-	0	-	-	0	-	0	-	0	0	0	0	0	0	0
1011	SUB	1	0	1	0	0	1	0	0	0	0	1	1	0	0	1	0	0	-	0	-	-	0	-	0	-	0	0	0	0	0	0	0
1111	HLT	-	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	-	0	-	-	0	-	0	-	0	0	0	0	0	0	0



"""
# 从表格中粘贴PROGRAM数据
PROGRAM_string = """

LDARA 50H	00H	01000000
	01H	01010000
LDARB 51H	02H	01100000
	03H	01010001
LDARC 52H	04H	10000000
	05H	01010010
ADD	06H	10100000
SUB	07H	10110000
HLT	08H	11110000
	50H	00000111
	51H	00110001
	52H	00000111




"""
###################End#########################

nof_MROM = nof_MROM_outputs // 8  # MROM的数量


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
    if char == '1':
        return '1'
    elif char == '0' or char == 'X' or char == '-':
        return '0'
    raise ValueError("无效值：" + char)


l1 = MROM_string.split("\n")
n = len(l1)
l2 = []
for i in range(n):
    l2.append(l1[i].split("\t"))

last_addr = None

MROM_result = [""] * (nof_MROM)
for i in range(n):
    addr = l2[i][0]
    if not (addr and l2[i][1]):
        continue
    if not is_bin_addr_next_to(last_addr, addr):
        add_all("ORG\t" + addr + "B\n")
    add_all("\tDB\t")
    for j in range(nof_MROM):
        for k in range(2 + j * 8, 2 + (j + 1) * 8):
            MROM_result[j] += to_add_to_result(l2[i][k])
    add_all("B\n")
    last_addr = addr

add_all("END")

for i in range(nof_MROM):
    print(f"\nMROM{i + 1}:")
    print(MROM_result[i])

for i in range(nof_MROM):
    with open(f"MROM{i + 1}.asm", "w") as f:
        f.write(MROM_result[i])

# 开始写PROGRAM.asm

l1 = PROGRAM_string.split("\n")
n = len(l1)
l2 = []
for i in range(n):
    l2.append(l1[i].split("\t"))

last_addr = None
PROGRAM_result = ""
for i in range(n):
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
print("\nPROGRAM:")
print(PROGRAM_result)
with open("PROGRAM.asm", "w") as f:
    f.write(PROGRAM_result)


# 简易8051汇编器，不依赖Proteus/ASEM51
# 只支持本工具生成的asm文件所用到的伪指令：ORG、DB、END
# 将asm文件编译为Intel HEX格式的hex文件


def _parse_number(text, lineno):
    """
    解析数字，支持二进制（后缀B，如10101010B）、十六进制（后缀H如0FFH，兼容0x开头）和十进制
    :param text: 数字字符串
    :param lineno: 所在行号（用于错误提示）
    :return: 解析出的整数
    """
    s = text.strip().upper()
    try:
        if s.startswith("0X"):
            return int(s, 16)
        if s.endswith("B"):
            return int(s[:-1], 2)
        if s.endswith("H"):
            return int(s[:-1], 16)
        return int(s, 10)
    except ValueError:
        raise ValueError(f"第{lineno}行：无法解析的数字：{text.strip()}")


def _parse_db_item(item, lineno):
    """
    解析DB指令中的一个数据项，可以是数字或字符串
    :param item: 数据项字符串
    :param lineno: 所在行号（用于错误提示）
    :return: 该数据项展开后的字节列表
    """
    item = item.strip()
    if not item:
        raise ValueError(f"第{lineno}行：DB指令中存在空的数据项")
    if item[0] in ("'", '"'):
        if len(item) < 2 or item[-1] != item[0]:
            raise ValueError(f"第{lineno}行：字符串没有正确的结束引号：{item}")
        return [ord(c) for c in item[1:-1]]
    value = _parse_number(item, lineno)
    if not 0 <= value <= 0xFF:
        raise ValueError(f"第{lineno}行：DB数据超出0-255范围：{item}")
    return [value]


def assemble(asm_path):
    """
    解析asm文件
    :param asm_path: asm文件路径
    :return: 以地址为键、数据字节为值的字典
    """
    memory = {}
    addr = 0
    with open(asm_path, "r") as f:
        for lineno, raw_line in enumerate(f, 1):
            # 去掉注释和首尾空白
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            parts = line.split(None, 1)
            directive = parts[0].upper()
            operand = parts[1].strip() if len(parts) > 1 else ""
            if directive == "END":
                break
            if directive == "ORG":
                if not operand:
                    raise ValueError(f"第{lineno}行：ORG指令缺少地址")
                addr = _parse_number(operand, lineno)
                if not 0 <= addr <= 0xFFFF:
                    raise ValueError(f"第{lineno}行：ORG地址超出0-65535范围：{operand}")
            elif directive == "DB":
                if not operand:
                    raise ValueError(f"第{lineno}行：DB指令缺少数据")
                for item in operand.split(","):
                    for b in _parse_db_item(item, lineno):
                        if addr > 0xFFFF:
                            raise ValueError(f"第{lineno}行：数据地址超出0xFFFF")
                        if addr in memory:
                            raise ValueError(f"第{lineno}行：地址{addr:04X}H处的数据重复定义")
                        memory[addr] = b
                        addr += 1
            else:
                raise ValueError(f"第{lineno}行：不支持的指令：{parts[0]}（仅支持ORG/DB/END）")
    return memory


def _make_record(addr, rectype, data):
    """
    生成一条Intel HEX记录
    :param addr: 记录起始地址
    :param rectype: 记录类型（00为数据，01为文件结束）
    :param data: 数据字节列表
    :return: 一条Intel HEX记录字符串
    """
    record = [len(data), (addr >> 8) & 0xFF, addr & 0xFF, rectype]
    record.extend(data)
    checksum = (-sum(record)) & 0xFF
    return ":" + "".join(f"{b:02X}" for b in record) + f"{checksum:02X}"


def write_hex(memory, hex_path):
    """
    将内存数据写入Intel HEX格式的hex文件
    :param memory: 以地址为键、数据字节为值的字典
    :param hex_path: hex文件路径
    """
    lines = []
    addrs = sorted(memory)
    i = 0
    # 把连续地址的数据合并成最多16字节一条的记录
    while i < len(addrs):
        start = addrs[i]
        data = [memory[start]]
        while i + 1 < len(addrs) and len(data) < 16 and addrs[i + 1] == addrs[i] + 1:
            i += 1
            data.append(memory[addrs[i]])
        i += 1
        lines.append(_make_record(start, 0, data))
    lines.append(":00000001FF")
    with open(hex_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def assemble_file(asm_path, hex_path=None):
    """
    将asm文件编译成hex文件
    :param asm_path: asm文件路径
    :param hex_path: hex文件路径，缺省时与asm文件同名、后缀改为.hex
    :return: hex文件路径
    """
    if hex_path is None:
        hex_path = asm_path.rsplit(".", 1)[0] + ".hex"
    memory = assemble(asm_path)
    write_hex(memory, hex_path)
    return hex_path

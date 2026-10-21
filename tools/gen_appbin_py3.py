#!/usr/bin/env python3
# Python 3 port of Espressif's gen_appbin.py (esp_iot_sdk_v2.1.0/tools), ESPRESSIF MIT License.
# Same arguments and output (eagle.app.flash.bin); only the Python 2 constructs were changed.
# The image CRC keeps the Python 2 semantics of binascii.crc32 (signed 32-bit result).
import binascii
import os
import re
import struct
import sys

TEXT_ADDRESS = 0x40100000
CHECKSUM_INIT = 0xEF

chk_sum = CHECKSUM_INIT


def write_file(file_name, data):
    with open(file_name, 'ab') as fp:
        fp.write(data)


def combine_bin(file_name, dest_file_name, start_offset_addr, need_chk):
    global chk_sum
    with open(file_name, 'rb') as fp:
        data_bin = fp.read()
    data_len = len(data_bin)
    if not data_len:
        return
    tmp_len = (data_len + 3) & ~3 if need_chk else (data_len + 15) & ~15
    write_file(dest_file_name, struct.pack('<II', start_offset_addr, tmp_len))
    write_file(dest_file_name, data_bin)
    if need_chk:
        for b in data_bin:
            chk_sum ^= b
    pad = tmp_len - data_len
    if pad:
        write_file(dest_file_name, b'\x00' * pad)   # zero padding does not change the xor checksum


def crc32_py2(path):
    with open(path, 'rb') as f:
        crc = binascii.crc32(f.read()) & 0xFFFFFFFF
    return crc - (1 << 32) if crc & 0x80000000 else crc


def sym(lines, kind, name):
    p = re.compile(r'(\w*)(\s%s\s)(%s)$' % (kind, name))
    val = None
    for line in lines:
        m = p.search(line)
        if m:
            val = m.group(1)
    return val


def gen_appbin():
    if len(sys.argv) != 7:
        print('Usage: gen_appbin.py eagle.app.out boot_mode flash_mode flash_clk_div flash_size_map user_bin')
        sys.exit(1)
    elf_file, boot_mode, flash_mode, flash_clk_div, flash_size_map, user_bin = sys.argv[1:7]
    flash_data_line = 16
    data_line_bits = 0xf

    irom0text_bin_name = 'eagle.app.v6.irom0text.bin'
    text_bin_name = 'eagle.app.v6.text.bin'
    data_bin_name = 'eagle.app.v6.data.bin'
    rodata_bin_name = 'eagle.app.v6.rodata.bin'
    flash_bin_name = 'eagle.app.flash.bin'
    BIN_MAGIC_FLASH = 0xE9
    BIN_MAGIC_IROM = 0xEA

    nm = 'xtensa-lx106-elf-nm' if os.getenv('COMPILE') == 'gcc' else 'xt-nm'
    os.system(nm + ' -g ' + elf_file + ' > eagle.app.sym')
    with open('./eagle.app.sym') as fp:
        lines = fp.readlines()

    entry_addr = sym(lines, 'T', 'call_user_start')
    if entry_addr is None:
        print('no entry point!!')
        sys.exit(1)
    data_start_addr = sym(lines, 'A', '_data_start') or '0'
    rodata_start_addr = sym(lines, 'A', '_rodata_start') or '0'

    byte2 = int(flash_mode) & 0xff
    byte3 = ((int(flash_size_map) << 4) | int(flash_clk_div)) & 0xff
    app = int(user_bin) & 0xff
    if boot_mode == '2':
        write_file(flash_bin_name, struct.pack('<BBBBI', BIN_MAGIC_IROM, 4, 0, app, int(entry_addr, 16)))
        combine_bin(irom0text_bin_name, flash_bin_name, 0x0, 0)
    if boot_mode == '1':
        data_bin = struct.pack('<BBBBI', BIN_MAGIC_FLASH, 3, 0, app, int(entry_addr, 16))
    else:
        data_bin = struct.pack('<BBBBI', BIN_MAGIC_FLASH, 3, byte2, byte3, int(entry_addr, 16))
    write_file(flash_bin_name, data_bin)

    combine_bin(text_bin_name, flash_bin_name, TEXT_ADDRESS, 1)
    if data_start_addr:
        combine_bin(data_bin_name, flash_bin_name, int(data_start_addr, 16), 1)
    combine_bin(rodata_bin_name, flash_bin_name, int(rodata_start_addr, 16), 1)

    sum_size = os.path.getsize(flash_bin_name) + 1
    sum_size = flash_data_line - (data_line_bits & sum_size)
    if sum_size:
        write_file(flash_bin_name, b'\x00' * sum_size)
    write_file(flash_bin_name, bytes([chk_sum & 0xFF]))

    if boot_mode == '1':
        sum_size = os.path.getsize(flash_bin_name)
        write_file(flash_bin_name, b'\xff' * (0x10000 - sum_size))
        with open(irom0text_bin_name, 'rb') as fp:
            write_file(flash_bin_name, fp.read())
    if boot_mode in ('1', '2'):
        all_bin_crc = crc32_py2(flash_bin_name)
        print(all_bin_crc)
        all_bin_crc = abs(all_bin_crc) - 1 if all_bin_crc < 0 else abs(all_bin_crc) + 1
        print(all_bin_crc)
        write_file(flash_bin_name, struct.pack('<I', all_bin_crc & 0xFFFFFFFF))
    os.remove('eagle.app.sym')


if __name__ == '__main__':
    gen_appbin()

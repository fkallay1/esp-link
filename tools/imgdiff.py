#!/usr/bin/env python3
# Compare two esp-link OTA images (user1.bin/user2.bin) segment by segment.
# Prints segment sizes and how many bytes differ in each, so a rebuild can be checked
# against an expected change (e.g. only the code you touched plus the version string).
import struct
import sys


def segments(d):
    out = []
    magic, _, _, _, _ = struct.unpack_from('<BBBBI', d, 0)
    assert magic == 0xEA, 'not an OTA image (magic 0x%02x)' % magic
    o = 8
    addr, ln = struct.unpack_from('<II', d, o)
    out.append(('irom', o + 8, ln))
    o += 8 + ln
    magic, n, _, _, _ = struct.unpack_from('<BBBBI', d, o)
    o += 8
    for _ in range(n):
        addr, ln = struct.unpack_from('<II', d, o)
        out.append((hex(addr), o + 8, ln))
        o += 8 + ln
    return out


a = open(sys.argv[1], 'rb').read()
b = open(sys.argv[2], 'rb').read()
for (na, oa, la), (nb, ob, lb) in zip(segments(a), segments(b)):
    da, db = a[oa:oa + la], b[ob:ob + lb]
    diff = [i for i in range(min(la, lb)) if da[i] != db[i]]
    print('%-12s %7d %7d  differing bytes %d %s' % (na, la, lb, len(diff),
          '(0x%x..0x%x)' % (diff[0], diff[-1]) if diff else ''))

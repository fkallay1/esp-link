#ifndef SLIP_H
#define SLIP_H

void slip_parse_buf(char *buf, short length);
extern uint32_t slip_pkt_ok, slip_bad_crc, slip_junk, slip_overflow;

#endif

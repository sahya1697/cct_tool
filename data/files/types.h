/*
 * types.h
 * Shared type definitions and declarations for the MISRA-C:2004 demo codebase.
 * VIOLATIONS IN THIS FILE:
 *   Rule 3.1  - Implementation-defined behaviour (union packing) not documented
 *   Rule 4.2  - Trigraph sequence used in comment below
 *   Rule 5.3  - typedef name 'uint8_t' reused (redefined below)
 *   Rule 18.1 - Incomplete struct type used before completion
 *   Rule 18.4 - Union defined and used
 */

#ifndef TYPES_H
#define TYPES_H

/* Rule 4.2 violation: trigraph sequence in comment ??- looks like ~ */
/* Date format ??-??-?? causes undefined trigraph substitution       */

/* Rule 6.3 violation: raw 'int' used instead of sized typedef */
typedef int   StatusCode;

/* Rule 5.3 violation: 'uint8_t' redefined (already in stdint.h context) */
typedef unsigned char  uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int   uint32_t;
typedef signed   char  int8_t;
typedef signed   short int16_t;
typedef signed   int   int32_t;

/* Rule 18.1 violation: pointer to incomplete struct type used before struct is complete */
struct SensorData *g_pSensorSnapshot;   /* struct body not yet declared */

/* Rule 18.4 violation: union defined */
typedef union {
    uint32_t  raw_word;    /* access as 32-bit word  */
    uint8_t   bytes[4];    /* access as byte array   */
} RawPacket_t;

/* struct completed later — the pointer above was to an incomplete type */
typedef struct SensorData {
    uint16_t  temperature;
    uint16_t  pressure;
    uint8_t   status;
} SensorData_t;

/* Forward declarations for functions defined in other translation units */
extern int32_t  compute_checksum(uint8_t *buf, uint16_t len);
extern void     transmit_packet(RawPacket_t *pkt);
extern void     log_error(int32_t code);

#endif /* TYPES_H */

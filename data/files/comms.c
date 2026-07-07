/*
 * comms.c
 * Communications and packet serialisation module.
 * VIOLATIONS IN THIS FILE:
 *   Rule 2.3  - Nested comment sequence /* inside a comment
 *   Rule 2.4  - Code commented out using /* ... */
 *   Rule 7.1  - Octal constant used
 *   Rule 9.3  - Enum initialisation: '=' used on non-first, non-all members
 *   Rule 10.1 - Integer expression implicitly converted to different type
 *   Rule 10.3 - Complex expression cast to wider type
 *   Rule 10.5 - Bitwise ~ on unsigned char without immediate cast
 *   Rule 11.4 - Cast between pointer and integral type
 *   Rule 11.5 - Cast removes const qualifier from pointer
 *   Rule 12.4 - RHS of && contains side effect
 *   Rule 12.7 - Bitwise operator on signed operand
 *   Rule 12.10 - Comma operator used
 *   Rule 12.13 - Increment mixed with other operators in expression
 *   Rule 13.1 - Assignment operator in Boolean expression
 *   Rule 13.3 - Floating-point tested for equality
 *   Rule 14.4 - goto used
 *   Rule 14.7 - Multiple return points in a function
 *   Rule 15.2 - Switch clause falls through without break
 *   Rule 15.3 - Switch missing default clause
 *   Rule 16.1 - Function defined with variable argument list
 *   Rule 16.7 - Pointer parameter not declared const when not modified
 *   Rule 17.1 - Pointer arithmetic on non-array pointer
 *   Rule 17.4 - Explicit pointer arithmetic used instead of array indexing
 *   Rule 20.4 - Dynamic memory allocation used (malloc)
 *   Rule 20.9 - stdio.h used in production code
 */

#include "types.h"
#include "globals.h"
#include <stdarg.h>   /* needed for Rule 16.1 violation */
#include <stdlib.h>   /* needed for Rule 20.4 violation — malloc */
#include <stdio.h>    /* Rule 20.9 violation: stdio.h included in production code */

/* Rule 9.3 violation: enum assigns '=' to a non-first member but not all members */
typedef enum {
    PKT_IDLE   = 0,
    PKT_READY,          /* auto-assigned = 1 */
    PKT_SENDING = 5,    /* Rule 9.3: explicit value on non-first, non-all members */
    PKT_DONE            /* auto-assigned = 6 — creates implicit gap */
} PktState_t;

/* Rule 2.3 violation: /* sequence inside a comment */
/* This resets the packet buffer /* which was allocated earlier */ */

/* Rule 7.1 violation: octal constant used for buffer flag */
#define PKT_FLAG_INIT   055U    /* octal 055 = decimal 45 — misleading */

/* Global TX buffer definition — size matches extern declaration in globals.h */
uint8_t g_tx_buffer[BUFFER_SIZE];

/* -----------------------------------------------------------------------
 * build_packet()
 * Constructs a data packet in the TX buffer.
 * Rule 16.7 violation: pData not modified but not declared const
 * Rule 10.5 violation: ~ applied to uint8_t without immediate cast back
 * Rule 17.4 violation: explicit pointer arithmetic instead of indexing
 * Rule 12.13 violation: ++ mixed with other operators
 * ----------------------------------------------------------------------- */
uint16_t build_packet(uint8_t *pData, uint16_t len)
{
    uint8_t  *ptr    = g_tx_buffer;
    uint16_t  i;
    uint8_t   checkbyte;

    /* Rule 17.4 violation: explicit pointer arithmetic *(ptr + i) instead of ptr[i] */
    for (i = 0U; i < len; i++)
    {
        *(ptr + i) = *(pData + i);   /* should be: ptr[i] = pData[i] */
    }

    /* Rule 10.5 violation: ~ on uint8_t 'checkbyte' — integral promotion
     * produces signed int result; not immediately cast back to uint8_t */
    checkbyte  = (uint8_t)pData[0];
    g_tx_buffer[len] = ~checkbyte;   /* Rule 10.5: result of ~ not cast */

    /* Rule 12.13 violation: ++ operator mixed with addition in one expression */
    ptr = ptr + (++i);   /* i already == len; mixing ++ with pointer add */

    return len;
}

/* -----------------------------------------------------------------------
 * validate_packet()
 * Checks packet integrity.
 * Rule 12.4 violation: RHS of && has a side effect (function call with effect)
 * Rule 13.1 violation: assignment inside Boolean expression
 * Rule 13.3 violation: floating-point equality test
 * Rule 14.7 violation: multiple return points
 * Rule 11.4 violation: cast between pointer type and integral type
 * Rule 11.5 violation: cast removes const qualifier
 * ----------------------------------------------------------------------- */
int32_t validate_packet(const uint8_t *pkt, uint16_t len)
{
    uint32_t  addr;
    int32_t   result;
    float32_t ratio;

    /* Rule 14.7 violation: early return — function has multiple exit points */
    if (pkt == NULL)
    {
        return ERROR_CODE;   /* first return point */
    }

    /* Rule 11.4 violation: pointer cast to integer type */
    addr = (uint32_t)pkt;   /* implementation-defined */

    /* Rule 11.5 violation: cast removes const from pointed-to type */
    uint8_t *writable = (uint8_t *)pkt;   /* discards const */
    writable[0] = PKT_FLAG_INIT;

    /* Rule 13.1 violation: assignment operator used in Boolean expression */
    if ((result = compute_checksum(g_tx_buffer, len)) != 0)
    {
        log_error(result);
    }

    /* Rule 13.3 violation: floating-point equality comparison */
    ratio = (float32_t)len / (float32_t)BUFFER_SIZE;
    if (ratio == 0.5f)   /* Rule 13.3: exact float equality */
    {
        log_error(0);
    }

    /* Rule 12.4 violation: RHS of && contains a side effect (log_error call) */
    if ((len > 0U) && (log_error(0), 1))   /* log_error is a side effect */
    {
        addr++;
    }

    return result;   /* second return point — Rule 14.7 */
}

/* -----------------------------------------------------------------------
 * dispatch_packet()
 * Routes packet to correct handler using switch.
 * Rule 15.2 violation: non-empty case clause falls through (no break)
 * Rule 15.3 violation: switch has no default clause
 * Rule 12.10 violation: comma operator used
 * Rule 12.7 violation: bitwise operator on signed operand
 * ----------------------------------------------------------------------- */
void dispatch_packet(int32_t pkt_type, uint16_t len)
{
    int32_t  flags = 0;

    /* Rule 12.7 violation: bitwise AND applied to signed int 'pkt_type' */
    flags = pkt_type & 0x0F;   /* signed operand with bitwise op */

    /* Rule 12.10 violation: comma operator used to sequence two expressions */
    flags = (flags + 1, flags * 2);   /* comma operator — only right side used */

    /* Rule 15.3 violation: no default clause in switch */
    switch ((uint16_t)flags)
    {
        case 1U:
            transmit_packet(NULL);
            /* Rule 15.2 violation: fall-through — no break before case 2 */
        case 2U:
            g_system_tick++;
            break;
        case 3U:
            log_error(flags);
            break;
        /* No default — Rule 15.3 */
    }

    (void)len;
}

/* -----------------------------------------------------------------------
 * retry_transmit()
 * Retries transmission with goto for error handling.
 * Rule 14.4 violation: goto statement used
 * Rule 10.1 violation: implicit conversion of int expression to narrower type
 * Rule 10.3 violation: complex expression cast to a wider type
 * ----------------------------------------------------------------------- */
int32_t retry_transmit(uint8_t *buf, uint16_t len)
{
    uint8_t   retries = 0U;
    uint16_t  csum;
    uint32_t  wide;

retry:   /* Rule 14.4 violation: goto label */
    retries++;

    /* Rule 10.1 violation: result of uint16_t + int constant implicitly
     * converted — mixing signed and unsigned without explicit cast */
    csum = (uint16_t)(len + retries);   /* 'retries' is uint8_t, len is uint16_t
                                           — implicit conversion of mixed types */

    /* Rule 10.3 violation: complex expression (csum * retries) cast to
     * wider type uint32_t — cast on complex expression, not lvalue */
    wide = (uint32_t)(csum * retries);

    if (wide == 0U)
    {
        /* Rule 17.1 violation: pointer arithmetic on non-array pointer */
        uint8_t *p = buf;
        p = p + 10;   /* 'buf' may not point into an array of sufficient size */
        *p = 0xFFU;
    }

    if (retries < 3U)
    {
        goto retry;   /* Rule 14.4 */
    }

    return (int32_t)csum;
}

/* -----------------------------------------------------------------------
 * log_formatted()
 * Rule 16.1 violation: function with variable number of arguments
 * Rule 20.9 violation: uses printf from <stdio.h>
 * ----------------------------------------------------------------------- */
void log_formatted(const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    /* Rule 20.9 violation: printf is from <stdio.h>, banned in production code */
    vprintf(fmt, args);
    va_end(args);
}

/* -----------------------------------------------------------------------
 * allocate_buffer()
 * Rule 20.4 violation: dynamic heap memory allocation (malloc) used
 * ----------------------------------------------------------------------- */
uint8_t *allocate_buffer(uint16_t size)
{
    /* Rule 20.4 violation: malloc is prohibited */
    return (uint8_t *)malloc((size_t)size);
}

/* -----------------------------------------------------------------------
 * transmit_packet()
 * Sends a raw packet. Stub implementation.
 * ----------------------------------------------------------------------- */
void transmit_packet(RawPacket_t *pkt)
{
    if (pkt != NULL)
    {
        g_tx_buffer[0] = pkt->bytes[0];
    }
}

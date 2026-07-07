/*
 * lang_violations.c
 *
 * Minimal C file violating MISRA-C:2004 Rules 2.1 – 2.4 (Section 6.2 Language Extensions).
 *
 * Rule 2.1 (required): Assembly language shall be encapsulated and isolated.
 * Rule 2.2 (required): Source code shall only use / * ... * / style comments.
 * Rule 2.3 (required): The character sequence / * shall not be used within a comment.
 * Rule 2.4 (advisory): Sections of code should not be "commented out".
 */

#include <stdio.h>

typedef unsigned int  uint32_t;
typedef unsigned char uint8_t;


/* ── Rule 2.1 violation ───────────────────────────────────────────────────────
 * Assembly language shall be encapsulated and isolated in either:
 *   (a) assembler functions,  (b) C functions,  or  (c) macros.
 *
 * Bare inline assembly scattered directly inside application logic is
 * non-compliant. The two `asm` calls below are embedded straight into
 * the body of a general-purpose function with no isolation wrapper.
 *
 * Compliant alternative:
 *     #define DISABLE_IRQ()  __asm__("CPSID i")
 *     #define ENABLE_IRQ()   __asm__("CPSIE i")
 */
void configure_hardware(uint32_t base_addr)
{
    uint32_t reg = base_addr + 0x10U;

    __asm__("CPSID i");   /* Rule 2.1: bare inline asm, not encapsulated in macro or function */

    reg |= 0x01U;
    (void)reg;

    __asm__("CPSIE i");   /* Rule 2.1: second bare inline asm, same violation */
}


/* ── Rule 2.2 violation ───────────────────────────────────────────────────────
 * Source code shall only use the / * ... * / comment style.
 * C99 // comments are not permitted in C90 (ISO/IEC 9899:1990).
 * Many pre-C99 compilers support // as an extension, but mixing styles
 * is non-portable and explicitly banned by this rule.
 */
uint32_t compute_value(uint32_t x)
{
    uint32_t result;

    result = x * 2U;   // Rule 2.2: C99 // comment — only /* */ is permitted

    result += 1U;      // Rule 2.2: second // comment — still non-compliant

    return result;
}


/* ── Rule 2.3 violation ───────────────────────────────────────────────────────
 * The character sequence / * shall not appear INSIDE a comment.
 * C does not support nested comments. A comment begins with / * and ends at
 * the FIRST * / encountered — so any / * inside a comment is misleading and
 * dangerous: it makes the reader believe a new comment has started when it
 * has not, and it can accidentally expose code if the outer comment end
 * marker is accidentally omitted.
 *
 * Danger scenario reproduced below:
 *   - The programmer intends to comment out the block.
 *   - The end marker of the first comment is accidentally omitted.
 *   - The inner /* starts what looks like a fresh comment to the reader,
 *     but the compiler sees the first */ it finds as closing the outer
 *     comment, exposing the code in between.
 */
void process_data(uint8_t *buf, uint32_t len)
{
    uint32_t i;

    /* Main processing loop
     /* Rule 2.3 violation: /* sequence embedded inside this comment block */
    for (i = 0U; i < len; i++)
    {
        buf[i] = (uint8_t)(buf[i] + 1U);
    }
}


/* ── Rule 2.4 violation ───────────────────────────────────────────────────────
 * Sections of code should not be "commented out".
 * When code must be excluded from compilation, conditional compilation
 * (#if 0 / #endif or #ifdef / #endif) shall be used instead.
 *
 * Commenting out code with /* ... */ is dangerous because:
 *   (a) C does not support nested comments, so any /* inside the commented-out
 *       code will not behave as the programmer expects (see Rule 2.3).
 *   (b) The excluded code is invisible to the compiler and cannot be
 *       checked for syntax errors or type mismatches during maintenance.
 *
 * The compliant alternative for the block below would be:
 *     #if 0
 *         validate_checksum(buf, len);
 *         log_packet(buf);
 *     #endif
 */
void transmit_packet(uint8_t *buf, uint32_t len)
{
    (void)len;

    /*
     * Rule 2.4 violation: live code commented out with block comment markers.
     * validate_checksum(buf, len);
     * log_packet(buf);
     * retry_count = 0;
     */

    buf[0] = 0xAAU;
}


int main(void)
{
    uint8_t data[4] = {1U, 2U, 3U, 4U};

    configure_hardware(0x40000000U);
    (void)compute_value(10U);
    process_data(data, 4U);
    transmit_packet(data, 4U);

    return 0;
}
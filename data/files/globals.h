/*
 * globals.h
 * Global objects, macros, and extern declarations.
 * VIOLATIONS IN THIS FILE:
 *   Rule 3.4  - #pragma used without documentation
 *   Rule 4.1  - Non-standard escape sequence used in string literal
 *   Rule 8.5  - Object definition inside a header file
 *   Rule 8.11 - External array declared without explicit size
 *   Rule 19.4 - Macro expands to a partial statement (not compliant form)
 *   Rule 19.6 - #undef used
 */

#ifndef GLOBALS_H
#define GLOBALS_H

#include "types.h"

/* Rule 3.4 violation: #pragma used with no documentation or explanation */
#pragma pack(1)

/* Rule 8.5 violation: object *definition* (not just declaration) in a header file */
uint32_t g_system_tick = 0U;

/* Rule 8.11 violation: external array declared without explicit size */
extern uint8_t g_tx_buffer[];

/* Rule 4.1 violation: non-standard escape sequence '\q' in string literal */
#define DEVICE_NAME   "Sensor\qNode"

/* Rule 19.4 violation: macro expands to a partial/incomplete statement fragment */
#define RESET_AND    g_system_tick = 0U;   /* expands to a bare statement, not
                                              a parenthesised expression or
                                              do-while-zero construct */

/* Rule 19.6 violation: #undef used */
#ifdef LEGACY_MODE
#define MAX_RETRIES  5
#undef  MAX_RETRIES           /* Rule 19.6: #undef shall not be used */
#define MAX_RETRIES  3
#endif

#define BUFFER_SIZE  64U
#define MAX_SENSORS  8U
#define ERROR_CODE   (-1)

#endif /* GLOBALS_H */

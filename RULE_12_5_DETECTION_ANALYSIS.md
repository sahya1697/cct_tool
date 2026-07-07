# Rule 12.5 Detection Analysis

## Status: ✅ Pipeline Working, ⚠️ LLM May Be Issue

### Test Results

Running the debug script confirms:

1. ✅ **AST Parsing**: `ComplexLogicalExpression` node created at line 4
2. ✅ **Rule Retrieval**: Rule 12.5 retrieved (in top 10)
3. ✅ **Relevance Filter**: Rule 12.5 passes with score 1.00
4. ✅ **Filter Rules**: Rule 12.5 passed to LLM
5. ❓ **LLM Verification**: Need to check

### The Violation

**Code in main.c line 4:**
```c
if (x > 0 && y < 100 && x != y) { return 1; }
```

**Rule 12.5:** The operands of a logical && or || shall be primary‑expressions.

**Why it violates:**
- `x > 0` is not a primary expression (needs parentheses)
- `y < 100` is not a primary expression (needs parentheses)
- `x != y` is not a primary expression (needs parentheses)

**Correct form:**
```c
if ((x > 0) && (y < 100) && (x != y)) { return 1; }
```

### Why LLM Might Miss It

Based on the previous analysis showing:
- **50% False Negative Rate**
- **LLM confidence for TRUE violations ≥ 0.90**
- **NEW THRESHOLD: 0.90** (just implemented)

**Possible reasons LLM is not detecting it:**

#### 1. Confidence Threshold Too High (LIKELY)

We just changed:
```python
HIGH_CONFIDENCE_THRESHOLD = 0.90
LOW_CONFIDENCE_THRESHOLD = 0.50
```

**Problem:** If LLM detects Rule 12.5 with confidence 0.80-0.89:
- Old threshold (0.45): Would be reported ✅
- New threshold (0.50 low, 0.90 high): Would be marked "needs review" ✅
- If confidence < 0.50: Would be filtered out ❌

**Solution:** Check actual confidence from LLM, adjust threshold if needed

#### 2. Prompt Not Clear About "Primary Expression" (LIKELY)

**Current prompt** explains:
- Target line marked with >>>
- Use context for understanding
- Follow rule description

**Missing:**
- What IS a "primary expression"?
- Examples of violations vs non-violations

**Rule 12.5 amplification** (CRITICAL):
> "Primary expressions" are defined in ISO/IEC 9899:1990, section 6.3.1. 
> Essentially they are either a single identifier, or a constant, or a 
> parenthesised expression.

If this is truncated or LLM doesn't understand it, violation will be missed!

#### 3. Context Might Not Be Enough

**Code sent to LLM:**
```c
    int check_limits(int x, int y) {
>>>     if (x > 0 && y < 100 && x != y) { return 1; }
        return 0; }
```

**Issue:** LLM might think the ENTIRE condition needs parentheses, not EACH operand

#### 4. LLM Being Too Permissive

From earlier analysis:
- Prompt says: "Do NOT assume missing information"
- Prompt says: "False positives are worse than false negatives"

This might make LLM too lenient for Rule 12.5!

### Recommended Actions

#### Immediate (5 minutes)

1. **Run the full pipeline on main.c**
   ```bash
   python main.py
   ```

2. **Check output/compliance_report.xlsx**
   - Look for Rule 12.5 violations
   - Check confidence scores

3. **Check output/execution.log**
   - Search for: `rule=12.5.*ComplexLogicalExpression.*line=4`
   - See what LLM returned: `violation=True/False confidence=X.XX`

#### If Rule 12.5 Not Detected (15 minutes)

1. **Add Few-Shot Example to Verification Prompt**

Add to VERIFICATION_PROMPT:

```
## Example for Logical Operator Rules

**Example Violation (Rule 12.5):**
```c
if (x > 0 && y < 100)  // ❌ VIOLATES
```
Reason: x > 0 and y < 100 are not primary expressions

**Correct:**
```c
if ((x > 0) && (y < 100))  // ✅ COMPLIANT
```
Reason: Each operand is now a parenthesised expression (primary)
```

2. **Lower Threshold Temporarily**

Change back to:
```python
HIGH_CONFIDENCE_THRESHOLD = 0.70  # Temporary
LOW_CONFIDENCE_THRESHOLD = 0.50
```

3. **Check Amplification Truncation**

Rule 12.5 amplification is ~600 chars. We set limit to 2500, should be fine.

#### If Detected with Low Confidence (10 minutes)

If LLM says `violation=True confidence=0.60-0.89`:
- This is working as designed (marked "needs review")
- Just means LLM is uncertain
- Could add more examples to increase confidence

#### If Detected with High Confidence (Success!)

If LLM says `violation=True confidence=0.90+`:
- ✅ System working correctly
- Rule 12.5 detected and reported

### Test Plan

```bash
# 1. Run pipeline
python main.py

# 2. Check results
python -c "
import pandas as pd
df = pd.read_excel('output/compliance_report.xlsx')
rule_12_5 = df[df['Rule ID'] == '12.5']
if len(rule_12_5) > 0:
    print('✓ Rule 12.5 violations found:', len(rule_12_5))
    print(rule_12_5[['File Name', 'Line Number', 'Confidence', 'Severity']])
else:
    print('✗ Rule 12.5 NOT detected')
"

# 3. Check logs
grep "rule=12.5" output/execution.log
```

### Expected Outcome

After improvements:
- **Best case:** Rule 12.5 detected with confidence ≥0.90 (3 violations in main.c line 4)
- **Good case:** Rule 12.5 detected with confidence 0.50-0.89 (marked "needs review")
- **Bad case:** Rule 12.5 not detected → Need to add few-shot examples

### Next Steps

1. ✅ Run test plan above
2. Based on results, implement one of the recommended actions
3. Re-run and verify

---

**Bottom Line:**

The pipeline IS working (retrieval, filtering all pass). Issue is either:
1. LLM not understanding what "primary expression" means
2. Confidence too low (below 0.50)
3. New threshold filtering it out (check if 0.50-0.89)

Run the test plan to determine which!

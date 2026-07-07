"""
Debug why Rule 12.5 is not being detected

Rule 12.5: The operands of a logical && or || shall be primary‑expressions.

Expected violation in main.c line 4:
if (x > 0 && y < 100 && x != y) { return 1; }

Each operand should be parenthesized:
if ((x > 0) && (y < 100) && (x != y)) { return 1; }
"""

import json
from tools.ast_tools import parse_c_file
from agents.rule_retrieval import RuleRetrievalAgent
from agents.relevance_filter import RelevanceFilterAgent
from agents.log_follower import LogFollowerAgent

print("=" * 80)
print("DEBUGGING RULE 12.5 DETECTION")
print("=" * 80)

# Load rules
with open("data/rules.json", "r") as f:
    rules_data = json.load(f)
    all_rules = rules_data["rules"]

# Find Rule 12.5
rule_12_5 = next((r for r in all_rules if r["rule_id"] == "12.5"), None)
if not rule_12_5:
    print("❌ Rule 12.5 not found in rules database!")
    exit(1)

print(f"\n✓ Found Rule 12.5:")
print(f"  Text: {rule_12_5['rule'][:80]}...")
print(f"  Type: {rule_12_5['rule_type']}")
print(f"  Category: {rule_12_5['rule_category']}")

# Parse main.c
print(f"\n{'=' * 80}")
print("STEP 1: AST PARSING")
print("=" * 80)

nodes = parse_c_file("data/sample_c_files/main.c")
print(f"\nParsed {len(nodes)} nodes from main.c")

# Find the node at line 4
target_nodes = [n for n in nodes if n.line == 4]
print(f"\nNodes at line 4:")
for node in target_nodes:
    print(f"  • Type: {node.node_type}")
    print(f"    Code: {node.code[:100]}...")

if not target_nodes:
    print("❌ No nodes found at line 4!")
    exit(1)

# Check for ComplexLogicalExpression
logical_node = next((n for n in target_nodes if "Logical" in n.node_type or "Expression" in n.node_type), None)
if not logical_node:
    print(f"\n⚠️  No logical expression node found. Node types: {[n.node_type for n in target_nodes]}")
    logical_node = target_nodes[0]  # Use first node
else:
    print(f"\n✓ Found logical expression node: {logical_node.node_type}")

# STEP 2: Rule Retrieval
print(f"\n{'=' * 80}")
print("STEP 2: RULE RETRIEVAL")
print("=" * 80)

log_agent = LogFollowerAgent()
retrieval_agent = RuleRetrievalAgent(all_rules, log_agent)

retrieved_rules = retrieval_agent.retrieve(logical_node, max_results=10)
retrieved_ids = [r["rule_id"] for r in retrieved_rules]

print(f"\nRetrieved {len(retrieved_rules)} rules:")
print(f"  Rule IDs: {retrieved_ids}")

if "12.5" in retrieved_ids:
    print(f"\n✓ Rule 12.5 WAS retrieved")
else:
    print(f"\n❌ Rule 12.5 NOT retrieved!")
    print(f"\nPossible reasons:")
    print(f"  • Node type '{logical_node.node_type}' doesn't match rule retrieval keywords")
    print(f"  • Rule retrieval agent not matching logical operator rules")
    exit(1)

# STEP 3: Relevance Filter
print(f"\n{'=' * 80}")
print("STEP 3: RELEVANCE FILTERING")
print("=" * 80)

filter_agent = RelevanceFilterAgent(log_agent)

# Check if 12.5 passes filter
is_relevant, score, reason = filter_agent.is_relevant(logical_node, rule_12_5)

print(f"\nRelevance check for Rule 12.5:")
print(f"  Is relevant: {is_relevant}")
print(f"  Score: {score:.3f}")
print(f"  Threshold: {filter_agent.RELEVANCE_THRESHOLD}")
print(f"  Reason: {reason}")

if not is_relevant:
    print(f"\n❌ Rule 12.5 FILTERED OUT!")
    print(f"\nDebugging filter...")
    
    # Check signature
    signature = filter_agent._extract_rule_signature(rule_12_5)
    print(f"\n  Rule signature:")
    print(f"    Keywords (first 10): {list(signature['keywords'])[:10]}")
    print(f"    Operators: {signature['operators']}")
    print(f"    Constructs: {signature['constructs']}")
    print(f"    AST types: {signature['ast_types']}")
    
    # Check code features
    code_features = filter_agent._extract_code_features(logical_node.code, logical_node)
    print(f"\n  Code features:")
    print(f"    Keywords: {code_features['keywords']}")
    print(f"    Operators: {code_features['operators']}")
    print(f"    Has logical op: {code_features['has_logical_op']}")
    
    # Manual score calculation
    print(f"\n  Score breakdown:")
    manual_score, manual_reason = filter_agent._calculate_relevance_score(rule_12_5, logical_node)
    print(f"    Manual calculation: {manual_score:.3f}")
    print(f"    Reason: {manual_reason}")
    
    exit(1)
else:
    print(f"\n✓ Rule 12.5 PASSED filter")

# STEP 4: Check what filtered rules includes
filtered_rules = filter_agent.filter_rules(logical_node, retrieved_rules)
filtered_ids = [r["rule_id"] for r in filtered_rules]

print(f"\n{'=' * 80}")
print("STEP 4: FILTERED RULES")
print("=" * 80)

print(f"\nAfter filtering:")
print(f"  Input: {len(retrieved_rules)} rules")
print(f"  Output: {len(filtered_rules)} rules")
print(f"  Filtered rule IDs: {filtered_ids}")

if "12.5" in filtered_ids:
    print(f"\n✓ Rule 12.5 PASSED to LLM verification")
else:
    print(f"\n❌ Rule 12.5 was FILTERED OUT")
    print(f"\nRules that passed:")
    for rule in filtered_rules:
        print(f"  • Rule {rule['rule_id']}: {rule['rule'][:60]}...")

# STEP 5: Check LLM verification (simulated)
print(f"\n{'=' * 80}")
print("STEP 5: LLM VERIFICATION (Check logs)")
print("=" * 80)

print(f"""
To check if LLM detected the violation:
1. Look at output/execution.log for:
   [VerificationAgent] verify_start | in: rule=12.5 node=ComplexLogicalExpression line=4
   [VerificationAgent] verify_complete | out: violation=True confidence=X.XX

2. Check the compliance report in output/compliance_report.xlsx

3. If LLM says violation=False, the prompt may need improvement
""")

print(f"\n{'=' * 80}")
print("SUMMARY")
print("=" * 80)

summary = []

# Check each stage
if "12.5" not in retrieved_ids:
    summary.append("❌ FAILED at Rule Retrieval - Rule 12.5 not retrieved")
elif not is_relevant:
    summary.append("❌ FAILED at Relevance Filter - Rule 12.5 filtered out")
elif "12.5" not in filtered_ids:
    summary.append("❌ FAILED at Filter Rules - Rule 12.5 removed")
else:
    summary.append("✓ PASSED all pre-LLM stages - Check LLM verification in logs")

for item in summary:
    print(f"\n{item}")

print(f"\n{'=' * 80}")

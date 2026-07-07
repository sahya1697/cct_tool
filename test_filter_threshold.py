"""
Quick test to verify filter threshold changes.
"""

from tools.rag_tools import load_rules
from tools.ast_tools import parse_c_file, ASTNode
from agents.relevance_filter import RelevanceFilterAgent
from agents.log_follower import LogFollowerAgent

# Load rules
print("Loading rules...")
all_rules = load_rules("data/rules.json")

# Get families 1, 2, 3
fam_1_rules = [r for r in all_rules if str(r.get('rule_id', '')).startswith('1.')]
fam_2_rules = [r for r in all_rules if str(r.get('rule_id', '')).startswith('2.')]
fam_3_rules = [r for r in all_rules if str(r.get('rule_id', '')).startswith('3.')]

print(f"Family 1.x: {len(fam_1_rules)} rules")
print(f"Family 2.x: {len(fam_2_rules)} rules") 
print(f"Family 3.x: {len(fam_3_rules)} rules")

# Create filter
log_agent = LogFollowerAgent()
filter_agent = RelevanceFilterAgent(log_agent)

print(f"\nFilter thresholds:")
print(f"  Standard threshold: {filter_agent.RELEVANCE_THRESHOLD}")
print(f"  Critical threshold: {filter_agent.CRITICAL_THRESHOLD}")
print(f"  Critical families: {filter_agent.CRITICAL_RULE_FAMILIES}")

# Create a test node (inline assembly)
test_node = ASTNode(
    node_type="InlineAssembly",
    line=8,
    column=0,
    code='__asm__("NOP");',
    file="test.c",
    function="test_func"
)

print(f"\n\nTesting with node: {test_node.node_type}")
print(f"Code: {test_node.code}")

# Test with rule 2.1 (should have low score but pass due to critical threshold)
rule_2_1 = next((r for r in all_rules if str(r.get('rule_id')) == '2.1'), None)
if rule_2_1:
    print(f"\nTesting Rule 2.1: {rule_2_1.get('rule', '')[:60]}...")
    is_rel, score, reason = filter_agent.is_relevant(test_node, rule_2_1)
    print(f"  Relevant: {is_rel}")
    print(f"  Score: {score:.3f}")
    print(f"  Reason: {reason}")

# Test filtering all rules
print(f"\n\nFiltering {len(all_rules)} rules...")
filtered = filter_agent.filter_rules(test_node, all_rules)
print(f"Filtered to {len(filtered)} rules")

# Check which families passed
filtered_ids = [str(r.get('rule_id', '')) for r in filtered]
fam_1 = [r for r in filtered_ids if r.startswith('1.')]
fam_2 = [r for r in filtered_ids if r.startswith('2.')]
fam_3 = [r for r in filtered_ids if r.startswith('3.')]

print(f"\nFamily 1.x passed filter: {fam_1}")
print(f"Family 2.x passed filter: {fam_2}")
print(f"Family 3.x passed filter: {fam_3}")

if fam_2:
    print(f"\n✓ SUCCESS: Family 2.x rules passed filter!")
else:
    print(f"\n✗ FAIL: No Family 2.x rules passed filter")

print("\nTest complete.")

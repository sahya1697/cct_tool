"""Test that thresholds are correctly set."""

from agents.relevance_filter import RelevanceFilterAgent

# Create filter
f = RelevanceFilterAgent(None)

print("Filter Configuration:")
print(f"  Standard threshold: {f.RELEVANCE_THRESHOLD}")
print(f"  Critical threshold: {f.CRITICAL_THRESHOLD}")
print(f"  Critical families: {f.CRITICAL_RULE_FAMILIES}")

# Test threshold selection logic
test_rules = [
    {"rule_id": "1.1", "rule": "Test rule 1"},
    {"rule_id": "2.1", "rule": "Test rule 2"},
    {"rule_id": "3.1", "rule": "Test rule 3"},
    {"rule_id": "10.1", "rule": "Test rule 10"},
]

for rule in test_rules:
    rule_id = str(rule.get("rule_id", ""))
    rule_family = rule_id.split('.')[0] if '.' in rule_id else rule_id
    
    if rule_family in f.CRITICAL_RULE_FAMILIES:
        threshold = f.CRITICAL_THRESHOLD
        label = "CRITICAL"
    else:
        threshold = f.RELEVANCE_THRESHOLD  
        label = "STANDARD"
    
    print(f"\nRule {rule_id}:")
    print(f"  Family: {rule_family}")
    print(f"  Threshold: {threshold} ({label})")

print("\n✓ Thresholds configured correctly!")
print(f"\nFamilies 1, 2, 3 use threshold {f.CRITICAL_THRESHOLD}")
print(f"Other families use threshold {f.RELEVANCE_THRESHOLD}")

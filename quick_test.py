from tools.rag_tools import load_rules
from tools.ast_tools import ASTNode
from agents.relevance_filter import RelevanceFilterAgent

rules = load_rules()
fam2 = [r for r in rules if str(r.get('rule_id','')).startswith('2.')]
node = ASTNode('InlineAssembly', 8, 0, 'asm NOP', 'test.c', 'test')
f = RelevanceFilterAgent(None)
filtered = f.filter_rules(node, fam2)
print(f'Input: {len(fam2)} family 2 rules')
print(f'Output: {len(filtered)} rules passed')
print([str(r.get('rule_id')) for r in filtered])

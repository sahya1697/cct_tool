"""
AST parsing utilities using pycparser.
Produces a flat list of ASTNode dicts from C source files.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ASTNode:
    node_type: str
    line: int
    column: int
    code: str
    file: str = ""
    function: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ── pycparser-based parser ───────────────────────────────────────────────────

def _try_pycparser(source: str, filepath: str) -> list[ASTNode]:
    """Parse with pycparser; raises ImportError if not available."""
    import pycparser  # type: ignore
    from pycparser import c_ast  # type: ignore

    fake_libc = Path(__file__).parent.parent / "data" / "fake_libc_include"
    cpp_args = ["-E", f"-I{fake_libc}"] if fake_libc.exists() else ["-E"]

    try:
        parser = pycparser.CParser()
        # Try parsing without fake includes first (works for simple files)
        try:
            ast = parser.parse(source, filename=filepath)
        except Exception:
            # fall back with cpp if available
           pycparser.parse_file(
                filepath,
                use_cpp=True,
                cpp_path="gcc",   # or full path
                cpp_args=cpp_args
            )
    except Exception as exc:
        logger.warning("pycparser failed (%s), falling back to regex.", exc)
        raise

    nodes: list[ASTNode] = []
    current_function: list[str] = ["<global>"]

    class Visitor(c_ast.NodeVisitor):
        def _coord(self, node) -> tuple[int, int]:
            if node.coord:
                return node.coord.line, node.coord.column
            return 0, 0

        def _snippet(self, node, context_lines=2) -> str:
            """
            Extract code with surrounding context (2 lines above/below by default).
            Marks the target line with >>> for LLM clarity.
            """
            line, _ = self._coord(node)
            lines = source.splitlines()
            if not lines or line < 1 or line > len(lines):
                return ""
            
            # Calculate context window (2 lines above and below)
            start = max(0, line - 1 - context_lines)
            end = min(len(lines), line + context_lines)
            
            # Build snippet with target line marked
            snippet_lines = []
            for i in range(start, end):
                if i == line - 1:
                    # Mark the actual target line
                    snippet_lines.append(f">>> {lines[i]}")
                else:
                    snippet_lines.append(f"    {lines[i]}")
            
            return '\n'.join(snippet_lines)

        def _node(self, ntype: str, n, extra: dict | None = None) -> ASTNode:
            l, c = self._coord(n)
            return ASTNode(
                node_type=ntype,
                line=l,
                column=c,
                code=self._snippet(n),
                file=filepath,
                function=current_function[-1],
                extra=extra or {},
            )

        # ── Declaration ──────────────────────────────────────────────────────
        def visit_Decl(self, node):
            if isinstance(node.type, c_ast.PtrDecl):
                nodes.append(self._node("PointerDeclaration", node))
            elif isinstance(node.type, c_ast.ArrayDecl):
                nodes.append(self._node("ArrayDeclaration", node))
            elif isinstance(node.type, c_ast.FuncDecl):
                nodes.append(self._node("FunctionDeclaration", node))
            else:
                nodes.append(self._node("VariableDeclaration", node))
            self.generic_visit(node)

        # ── Function definition ──────────────────────────────────────────────
        def visit_FuncDef(self, node):
            name = node.decl.name if node.decl else "<unknown>"
            current_function.append(name)
            nodes.append(self._node("FunctionDefinition", node, {"name": name}))
            self.generic_visit(node)
            current_function.pop()

        # ── Function call ────────────────────────────────────────────────────
        def visit_FuncCall(self, node):
            name = ""
            if isinstance(node.name, c_ast.ID):
                name = node.name.name
            nodes.append(self._node("FunctionCall", node, {"name": name}))
            self.generic_visit(node)

        # ── Assignment ───────────────────────────────────────────────────────
        def visit_Assignment(self, node):
            nodes.append(self._node("Assignment", node, {"op": node.op}))
            self.generic_visit(node)

        # ── Control flow ─────────────────────────────────────────────────────
        def visit_If(self, node):
            nodes.append(self._node("IfStatement", node))
            self.generic_visit(node)

        def visit_For(self, node):
            nodes.append(self._node("ForLoop", node))
            self.generic_visit(node)

        def visit_While(self, node):
            nodes.append(self._node("WhileLoop", node))
            self.generic_visit(node)

        def visit_DoWhile(self, node):
            nodes.append(self._node("DoWhileLoop", node))
            self.generic_visit(node)

        def visit_Switch(self, node):
            nodes.append(self._node("SwitchStatement", node))
            self.generic_visit(node)

        def visit_Case(self, node):
            nodes.append(self._node("CaseLabel", node))
            self.generic_visit(node)

        def visit_Default(self, node):
            nodes.append(self._node("DefaultLabel", node))
            self.generic_visit(node)

        def visit_Label(self, node):
            nodes.append(self._node("LabelStatement", node, {"name": node.name}))
            self.generic_visit(node)

        def visit_Goto(self, node):
            nodes.append(self._node("GotoStatement", node, {"target": node.name}))
            self.generic_visit(node)

        def visit_Continue(self, node):
            nodes.append(self._node("ContinueStatement", node))
            self.generic_visit(node)

        def visit_Break(self, node):
            nodes.append(self._node("BreakStatement", node))
            self.generic_visit(node)

        def visit_Return(self, node):
            nodes.append(self._node("ReturnStatement", node))
            self.generic_visit(node)

        # ── Expressions ──────────────────────────────────────────────────────
        def visit_UnaryOp(self, node):
            nodes.append(self._node("UnaryOp", node, {"op": node.op}))
            self.generic_visit(node)

        def visit_BinaryOp(self, node):
            nodes.append(self._node("BinaryOp", node, {"op": node.op}))
            self.generic_visit(node)

        def visit_Cast(self, node):
            nodes.append(self._node("TypeCast", node))
            self.generic_visit(node)

        def visit_TernaryOp(self, node):
            nodes.append(self._node("TernaryOp", node))
            self.generic_visit(node)

        # ── Struct/Union ─────────────────────────────────────────────────────
        def visit_Struct(self, node):
            nodes.append(self._node("StructDeclaration", node, {"name": getattr(node, "name", None)}))
            self.generic_visit(node)

        def visit_Union(self, node):
            nodes.append(self._node("UnionDeclaration", node, {"name": getattr(node, "name", None)}))
            self.generic_visit(node)

        def visit_Enum(self, node):
            nodes.append(self._node("EnumDeclaration", node, {"name": getattr(node, "name", None)}))
            self.generic_visit(node)
            
        def visit_Typedef(self, node):
            nodes.append(self._node("TypedefDeclaration", node, {"name": getattr(node, "name", None)}))
            self.generic_visit(node)
            
        def visit_ID(self, node):
            nodes.append(self._node("IDDeclaration", node, {"name": node.name}))
            self.generic_visit(node)
            
        def visit_Constant(self, node):
            # Constant nodes have 'value' and 'type', not 'name'
            nodes.append(self._node("ConstantDeclaration", node, {
                "value": getattr(node, "value", None),
                "type": getattr(node, "type", None)
            }))
            self.generic_visit(node)
            
        def visit_InitList(self, node):
            nodes.append(self._node("InitListDeclaration", node))
            self.generic_visit(node)
            
        def visit_DeclList(self, node):
            nodes.append(self._node("DeclDeclaration", node))
            self.generic_visit(node)
            
        def visit_ParamList(self, node):
            nodes.append(self._node("ParamListDeclaration", node))
            self.generic_visit(node)
            
        def visit_StructRef(self, node):
            # StructRef has 'name' for the field name
            nodes.append(self._node("RefDeclaration", node, {
                "name": getattr(node.name, "name", None) if hasattr(node, "name") else None,
                "type": getattr(node, "type", None)
            }))
            self.generic_visit(node)
            
        def visit_ArrayRef(self, node):
            # ArrayRef has 'name' for the array name and 'subscript' for the index
            nodes.append(self._node("ArrayRefDeclaration", node, {
                "name": getattr(node.name, "name", None) if hasattr(node, "name") else None
            }))
            self.generic_visit(node)

    Visitor().visit(ast)
    return nodes


# ── Regex-based fallback ─────────────────────────────────────────────────────

def _regex_parse(source: str, filepath: str) -> list[ASTNode]:
    """Simple regex-based AST extraction as fallback when pycparser fails."""
    nodes: list[ASTNode] = []
    lines = source.splitlines()
    current_function = "<global>"

    FUNC_DEF = re.compile(r'^\s*(?:int|void|char|float|double|long|short|unsigned|static|inline)\s+\**(\w+)\s*\(')
    PTR_DECL = re.compile(r'\b\w+\s*\*+\s*\w+')
    ARRAY_DECL = re.compile(r'\b\w+\s+\w+\s*\[')
    GOTO = re.compile(r'\bgoto\b\s+(\w+)')
    LABEL = re.compile(r'^(\w+)\s*:')
    CONTINUE = re.compile(r'\bcontinue\b')
    BREAK = re.compile(r'\bbreak\b')
    SWITCH = re.compile(r'\bswitch\s*\(')
    FOR = re.compile(r'\bfor\s*\(')
    WHILE = re.compile(r'\bwhile\s*\(')
    ASSIGN_IN_COND = re.compile(r'if\s*\(\s*\w+\s*=[^=]')
    FUNC_CALL = re.compile(r'\b(\w+)\s*\(')
    RETURN = re.compile(r'\breturn\b')
    CAST = re.compile(r'\(\s*(?:int|char|float|double|void\s*\*|long)\s*\)')
    FLOAT_LOOP = re.compile(r'for\s*\(\s*float')
    BINARY_OP = re.compile(r'[+\-*/%&|^]=?\s*\w')
    INLINE_ASM = re.compile(r'\b(asm|__asm__|__asm)\s*[({]')
    UNION_DECL = re.compile(r'\bunion\s+\w+\s*{')
    UNION_USAGE = re.compile(r'\bunion\s+\w+\s+\w+')
    LOGICAL_OP = re.compile(r'(&&|\|\|)')
    COMPLEX_LOGICAL = re.compile(r'\w+\s*[<>=!+\-*/%]+\s*\w+\s*(&&|\|\|)')
    CPP_COMMENT = re.compile(r'//.*')  # C++ style comments (Rule 2.2)
    INCREMENT_IN_EXPR = re.compile(r'(\w+\+\+|\+\+\w+|\w+--|--\w+).*[,\+\-\*/]')  # ++ or -- with other operators
    
    # Additional patterns for comprehensive coverage
    PREPROCESSOR = re.compile(r'^\s*#\s*(include|define|undef|if|ifdef|ifndef|elif|else|endif|pragma|error|warning|line)')
    MACRO_DEFINE = re.compile(r'^\s*#\s*define\s+(\w+)')
    INCLUDE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]')
    CONDITIONAL_COMPILE = re.compile(r'^\s*#\s*(if|ifdef|ifndef|elif|else|endif)')
    CHAR_LITERAL = re.compile(r"'[^']*'")
    STRING_LITERAL = re.compile(r'"[^"]*"')
    HEX_CONSTANT = re.compile(r'\b0[xX][0-9a-fA-F]+[uUlL]*\b')
    OCTAL_CONSTANT = re.compile(r'\b0[0-7]+[uUlL]*\b')
    BITWISE_OP = re.compile(r'[&|^~]|<<|>>')
    COMMA_OP = re.compile(r'\([^)]*,\s*\w+[^)]*\)')  # Comma operator in expressions
    SIZEOF = re.compile(r'\bsizeof\s*\(')
    TYPEDEF = re.compile(r'\btypedef\s+')
    ENUM = re.compile(r'\benum\s+\w+\s*{')
    STRUCT = re.compile(r'\bstruct\s+\w+\s*{')
    EXTERN = re.compile(r'\bextern\s+')
    STATIC = re.compile(r'\bstatic\s+')
    VOLATILE = re.compile(r'\bvolatile\s+')
    CONST = re.compile(r'\bconst\s+')
    BITFIELD = re.compile(r'\b\w+\s*:\s*\d+\s*;')  # Bit-field
    TRIGRAPH = re.compile(r'\?\?[=/()\'\<\>!-]')  # Trigraph sequences
    ESCAPE_SEQ = re.compile(r'\\[0-7]{1,3}|\\x[0-9a-fA-F]+')  # Octal/hex escape sequences
    DO_WHILE = re.compile(r'\bdo\s*\{')
    IF_STMT = re.compile(r'\bif\s*\(')
    COMPLEX_LOGICAL = re.compile(r'\w+\s*[<>=!+\-*/%]+\s*\w+\s*(&&|\|\|)')
    CPP_COMMENT = re.compile(r'//.*$')  # NEW: C++ style comments (Rule 2.2)
    INCREMENT_IN_EXPR = re.compile(r'(\w+\+\+|\+\+\w+|\w+--|--\w+).*[,\+\-\*/]')  # NEW: ++ or -- with other operators

    for i, raw_line in enumerate(lines, 1):
        ln = raw_line.strip()
        col = len(raw_line) - len(raw_line.lstrip())

        def node(ntype, extra=None):
            """Create node with 2 lines of context above and below."""
            # Extract context window
            context_lines = 2
            start = max(0, i - 1 - context_lines)
            end = min(len(lines), i + context_lines)
            
            # Build code snippet with context
            snippet_lines = []
            for idx in range(start, end):
                if idx == i - 1:
                    # Mark the target line
                    snippet_lines.append(f">>> {lines[idx]}")
                else:
                    snippet_lines.append(f"    {lines[idx]}")
            
            code_with_context = '\n'.join(snippet_lines)
            return ASTNode(ntype, i, col, code_with_context, filepath, current_function, extra or {})

        m = FUNC_DEF.match(raw_line)
        if m and '{' in raw_line:
            current_function = m.group(1)
            nodes.append(node("FunctionDefinition", {"name": current_function}))

        if GOTO.search(ln):
            m2 = GOTO.search(ln)
            nodes.append(node("GotoStatement", {"target": m2.group(1) if m2 else ""}))
        if LABEL.match(ln) and not ln.startswith("//") and "case" not in ln and "default" not in ln:
            nodes.append(node("LabelStatement"))
        if CONTINUE.search(ln):
            nodes.append(node("ContinueStatement"))
        if BREAK.search(ln):
            nodes.append(node("BreakStatement"))
        if SWITCH.search(ln):
            nodes.append(node("SwitchStatement"))
        if FOR.search(ln):
            nodes.append(node("ForLoop"))
        if WHILE.search(ln):
            nodes.append(node("WhileLoop"))
        if ASSIGN_IN_COND.search(ln):
            nodes.append(node("AssignmentInCondition"))
        if FLOAT_LOOP.search(ln):
            nodes.append(node("FloatLoopCounter"))
        if RETURN.search(ln):
            nodes.append(node("ReturnStatement"))
        if CAST.search(ln):
            nodes.append(node("TypeCast"))
        if PTR_DECL.search(ln) and "=" not in ln.split("*")[0]:
            nodes.append(node("PointerDeclaration"))
        if ARRAY_DECL.search(ln):
            nodes.append(node("ArrayDeclaration"))
        
        # NEW: Rule 2.2 - C++ style comments
        if CPP_COMMENT.search(ln) and not ln.strip().startswith('#'):
            # Ignore preprocessor directives with // in them
            nodes.append(node("CPPStyleComment"))
        
        # NEW: Rule 2.1 - Inline assembly detection
        if INLINE_ASM.search(ln):
            nodes.append(node("InlineAssembly"))
        
        # NEW: Rule 18.4 - Union detection
        if UNION_DECL.search(ln):
            nodes.append(node("UnionDeclaration"))
        elif UNION_USAGE.search(ln):
            nodes.append(node("UnionUsage"))
        
        # NEW: Rule 12.5 - Complex logical operators
        if COMPLEX_LOGICAL.search(ln) or (LOGICAL_OP.search(ln) and ('==' in ln or '!=' in ln or '<' in ln or '>' in ln)):
            nodes.append(node("ComplexLogicalExpression"))
        
        # NEW: Rules 12.2, 12.13 - Increment/decrement in complex expressions
        if INCREMENT_IN_EXPR.search(ln):
            nodes.append(node("IncrementInExpression"))
        
        # Preprocessor directives
        if PREPROCESSOR.search(raw_line):
            nodes.append(node("PreprocessorDirective"))
        if MACRO_DEFINE.search(raw_line):
            m_def = MACRO_DEFINE.search(raw_line)
            nodes.append(node("MacroDefinition", {"name": m_def.group(1) if m_def else ""}))
        if INCLUDE.search(raw_line):
            m_inc = INCLUDE.search(raw_line)
            nodes.append(node("Include", {"file": m_inc.group(1) if m_inc else ""}))
        if CONDITIONAL_COMPILE.search(raw_line):
            nodes.append(node("ConditionalCompilation"))
        
        # Constants and literals
        if CHAR_LITERAL.search(ln):
            nodes.append(node("CharacterLiteral"))
        if STRING_LITERAL.search(ln):
            nodes.append(node("StringLiteral"))
        if HEX_CONSTANT.search(ln):
            nodes.append(node("HexConstant"))
        if OCTAL_CONSTANT.search(ln) and not ln.strip().startswith('0'):  # Avoid false positives with just 0
            nodes.append(node("OctalConstant"))
        
        # Operators
        if BITWISE_OP.search(ln) and not LOGICAL_OP.search(ln):  # Avoid overlap with logical ops
            nodes.append(node("BitwiseOperation"))
        if COMMA_OP.search(ln):
            nodes.append(node("CommaOperator"))
        if SIZEOF.search(ln):
            nodes.append(node("SizeofOperator"))
        
        # Type declarations
        if TYPEDEF.search(ln):
            nodes.append(node("TypedefDeclaration"))
        if ENUM.search(ln):
            nodes.append(node("EnumDeclaration"))
        if STRUCT.search(ln):
            nodes.append(node("StructDeclaration"))
        
        # Storage specifiers
        if EXTERN.search(ln):
            nodes.append(node("ExternDeclaration"))
        if STATIC.search(ln) and FUNC_DEF.search(ln):
            nodes.append(node("StaticFunction"))
        if VOLATILE.search(ln):
            nodes.append(node("VolatileQualifier"))
        if CONST.search(ln):
            nodes.append(node("ConstQualifier"))
        
        # Bit-fields and special cases
        if BITFIELD.search(ln):
            nodes.append(node("BitField"))
        if TRIGRAPH.search(ln):
            nodes.append(node("TrigraphSequence"))
        if ESCAPE_SEQ.search(ln):
            nodes.append(node("EscapeSequence"))
        
        # Control flow
        if DO_WHILE.search(ln):
            nodes.append(node("DoWhileLoop"))
        if IF_STMT.search(ln):
            nodes.append(node("IfStatement"))
        
        for fc in FUNC_CALL.finditer(ln):
            fname = fc.group(1)
            if fname not in {"if", "for", "while", "switch", "return", "sizeof"}:
                nodes.append(node("FunctionCall", {"name": fname}))

    return nodes


# ── Public API ────────────────────────────────────────────────────────────────

def parse_c_file(filepath: str | Path) -> list[ASTNode]:
    """
    Parse a C file and return a list of ASTNode objects.
    Tries pycparser first; falls back to regex extraction.
    """
    filepath = str(filepath)
    source = Path(filepath).read_text(encoding="utf-8", errors="replace")

    try:
        nodes = _try_pycparser(source, filepath)
        logger.info("pycparser succeeded for %s (%d nodes)", filepath, len(nodes))
        return nodes
    except Exception as exc:
        logger.info("Falling back to regex parser (%s)", exc)
        nodes = _regex_parse(source, filepath)
        logger.info("Regex parser produced %d nodes for %s", len(nodes), filepath)
        return nodes

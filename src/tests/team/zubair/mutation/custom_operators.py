"""
SE3002 SQE Course Requirement:
"Add at least 2 custom mutation operators based on your business rules."

Custom Mutation Operators tailored specifically for Pretix Event Ticketing:
1. Operator 1 (Boundary Inversion Operator):
   Mutates strict comparison operators (<, >, <=, >=) to their inverse or off-by-one boundary
   in Quota capacity and Cart expiration evaluations.
   Example:
     Original: if sold + cart_reserved >= quota.size:
     Mutant:   if sold + cart_reserved > quota.size:   (allows 1 oversold ticket)

2. Operator 2 (Order State Machine Bypass Operator):
   Mutates order status checks to bypass the state machine invariant.
   Example:
     Original: if self.status == self.STATUS_PENDING:
     Mutant:   if self.status in (self.STATUS_PENDING, self.STATUS_CANCELED):
     or:
     Original: return self.status == self.STATUS_PENDING
     Mutant:   return True  (bypasses check, allowing canceled/refunded orders to be paid)
"""

import ast


class QuotaBoundaryInversionMutator(ast.NodeTransformer):
    """
    Custom Operator 1: Inverts boundary comparison operators in quota checking code.
    Replaces:
      >= with >
      <= with <
      == with !=
      > with >=
      < with <=
    """
    def __init__(self):
        super().__init__()
        self.mutation_count = 0

    def visit_Compare(self, node):
        self.generic_visit(node)
        new_ops = []
        mutated = False
        for op in node.ops:
            if isinstance(op, ast.GtE):
                new_ops.append(ast.Gt())
                mutated = True
            elif isinstance(op, ast.LtE):
                new_ops.append(ast.Lt())
                mutated = True
            elif isinstance(op, ast.Gt):
                new_ops.append(ast.GtE())
                mutated = True
            elif isinstance(op, ast.Lt):
                new_ops.append(ast.LtE())
                mutated = True
            elif isinstance(op, ast.Eq):
                new_ops.append(ast.NotEq())
                mutated = True
            else:
                new_ops.append(op)
        if mutated:
            self.mutation_count += 1
            node.ops = new_ops
        return node


class OrderStateMachineBypassMutator(ast.NodeTransformer):
    """
    Custom Operator 2: Mutates order state machine status checks.
    Replaces checks against STATUS_PENDING or STATUS_CANCELED to invert validation.
    """
    def __init__(self):
        super().__init__()
        self.mutation_count = 0

    def visit_Compare(self, node):
        self.generic_visit(node)
        # Check if comparing order.status == Order.STATUS_PENDING
        if isinstance(node.left, ast.Attribute) and node.left.attr == 'status':
            for i, op in enumerate(node.ops):
                if isinstance(op, ast.Eq):
                    # Invert comparison to !=
                    node.ops[i] = ast.NotEq()
                    self.mutation_count += 1
        return node

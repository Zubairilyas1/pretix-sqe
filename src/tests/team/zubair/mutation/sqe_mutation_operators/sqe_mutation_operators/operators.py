"""
Two custom Cosmic Ray mutation operators derived from the pretix business rules.

Both operators work on the parso parse tree that Cosmic Ray uses. They only match a
constant that is accessed as an attribute (``Quota.AVAILABILITY_OK``, ``self.STATUS_PAID``),
never the class-level definition of the constant itself.

SwapAvailabilityVerdict  (BR-1 capacity limit, BR-4 cart reservation)
    The quota service returns one of four verdicts: GONE (0), ORDERED (10), RESERVED (20), OK (100).
    The verdict tells the shop *why* a product is unavailable (sold / pending payment / in carts)
    and ``_close`` compares it with ``<= ORDERED``. The built-in operators never replace one named
    constant by another, so a test suite that only checks ``available == 0`` would miss a wrong
    verdict. Every occurrence produces 3 mutants (one per other verdict).

SwapOrderStatus  (BR-3 order state machine)
    Replaces an order status constant (PENDING, PAID, EXPIRED, CANCELED) by every other one,
    e.g. counting PENDING orders as PAID, or accepting payment for EXPIRED instead of PENDING
    orders. Every occurrence produces 3 mutants.
"""
import parso.python.tree
from cosmic_ray.operators.operator import Example, Operator


class _SwapAttributeConstant(Operator):
    """Base class: replace ``<obj>.<CONSTANT>`` by ``<obj>.<OTHER_CONSTANT>``."""

    CONSTANTS = ()

    def _alternatives(self, node):
        return [c for c in self.CONSTANTS if c != node.value]

    def _is_target(self, node):
        return (
            isinstance(node, parso.python.tree.Name)
            and node.value in self.CONSTANTS
            and node.parent is not None
            and node.parent.type == "trailer"
            and node.parent.children[0].type == "operator"
            and node.parent.children[0].value == "."
        )

    def mutation_positions(self, node):
        if self._is_target(node):
            for _ in self._alternatives(node):
                yield (node.start_pos, node.end_pos)

    def mutate(self, node, index):
        alternatives = self._alternatives(node)
        assert index < len(alternatives)
        return parso.python.tree.Name(alternatives[index], node.start_pos, prefix=node.prefix)


class SwapAvailabilityVerdict(_SwapAttributeConstant):
    """Replace a quota availability verdict by another verdict."""

    CONSTANTS = ("AVAILABILITY_GONE", "AVAILABILITY_ORDERED", "AVAILABILITY_RESERVED", "AVAILABILITY_OK")

    @classmethod
    def examples(cls):
        return (
            Example("r = Quota.AVAILABILITY_GONE, 0", "r = Quota.AVAILABILITY_ORDERED, 0", occurrence=0),
            Example("r = Quota.AVAILABILITY_GONE, 0", "r = Quota.AVAILABILITY_RESERVED, 0", occurrence=1),
            Example("r = Quota.AVAILABILITY_GONE, 0", "r = Quota.AVAILABILITY_OK, 0", occurrence=2),
            Example("if x <= Quota.AVAILABILITY_ORDERED: pass", "if x <= Quota.AVAILABILITY_GONE: pass"),
        )


class SwapOrderStatus(_SwapAttributeConstant):
    """Replace an order status by another status of the order state machine."""

    CONSTANTS = ("STATUS_PENDING", "STATUS_PAID", "STATUS_EXPIRED", "STATUS_CANCELED")

    @classmethod
    def examples(cls):
        return (
            Example("s == Order.STATUS_PAID", "s == Order.STATUS_PENDING", occurrence=0),
            Example("s == Order.STATUS_PAID", "s == Order.STATUS_EXPIRED", occurrence=1),
            Example("s == Order.STATUS_PAID", "s == Order.STATUS_CANCELED", occurrence=2),
            Example("if self.status == self.STATUS_PENDING: pass", "if self.status == self.STATUS_PAID: pass"),
        )

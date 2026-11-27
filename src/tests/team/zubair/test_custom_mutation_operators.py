"""
Unit tests for the two custom Cosmic Ray operators (src/tests/team/zubair/mutation/sqe_mutation_operators).
They check that each operator is registered in Cosmic Ray, produces exactly its documented
examples, and never mutates the definition of a constant.
"""
import pytest

cosmic_ray = pytest.importorskip("cosmic_ray")

from cosmic_ray.mutating import mutate_code  # noqa: E402
from cosmic_ray.plugins import get_operator, operator_names  # noqa: E402
from sqe_mutation_operators.operators import (  # noqa: E402
    SwapAvailabilityVerdict, SwapOrderStatus,
)

OPERATORS = [SwapAvailabilityVerdict, SwapOrderStatus]


@pytest.mark.parametrize("op", OPERATORS, ids=lambda o: o.__name__)
def test_operator_is_registered_in_cosmic_ray(op):
    assert f"sqe/{op.__name__}" in operator_names()
    assert get_operator(f"sqe/{op.__name__}") is op


@pytest.mark.parametrize("op, example", [(op, ex) for op in OPERATORS for ex in op.examples()],
                         ids=lambda v: v.__name__ if isinstance(v, type) else v.post_mutation_code)
def test_operator_examples(op, example):
    assert mutate_code(example.pre_mutation_code, op(), example.occurrence) == example.post_mutation_code


@pytest.mark.parametrize("code", [
    "AVAILABILITY_GONE = 0",           # class-level definition: must not be mutated
    "STATUS_PAID = 'p'",
    "x = AVAILABILITY_OK",             # bare name, not an attribute access
])
def test_definitions_and_bare_names_are_not_mutated(code):
    for op in OPERATORS:
        assert mutate_code(code, op(), 0) is None


def test_each_occurrence_gives_three_mutants():
    code = "a = Quota.AVAILABILITY_OK\nb = Order.STATUS_PAID\n"
    import parso
    from cosmic_ray.ast import ast_nodes
    tree = parso.parse(code)
    for op in OPERATORS:
        positions = [p for node in ast_nodes(tree) for p in op().mutation_positions(node)]
        assert len(positions) == 3

"""Cosmic Ray operator provider: makes the operators available as ``sqe/<OperatorName>``."""
from .operators import SwapAvailabilityVerdict, SwapOrderStatus

_OPERATORS = {op.__name__: op for op in (SwapAvailabilityVerdict, SwapOrderStatus)}


class OperatorProvider:
    def __iter__(self):
        return iter(_OPERATORS)

    def __getitem__(self, name):
        return _OPERATORS[name]

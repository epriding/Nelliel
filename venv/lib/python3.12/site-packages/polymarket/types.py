"""Generic Polymarket domain types."""

from typing import NewType

EvmAddress = NewType("EvmAddress", str)
HexString = NewType("HexString", str)
TransactionHash = NewType("TransactionHash", str)

__all__ = ["EvmAddress", "HexString", "TransactionHash"]

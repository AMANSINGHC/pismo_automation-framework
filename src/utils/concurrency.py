"""Run several independent calls of one scenario at the same time."""

from typing import TypeVar
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor

T = TypeVar("T")


def run_concurrently(calls: Sequence[Callable[[], T]]) -> list[T]:
    """Call every callable in flight and return the results in submission order.

    Every call is submitted before any result is read, so they really overlap.
    """
    if not calls:
        return []
    
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [pool.submit(call) for call in calls]
        return [future.result() for future in futures]

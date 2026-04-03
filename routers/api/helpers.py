"""Shared helpers for API routers."""

from typing import Iterable, List, Sequence, Type, TypeVar

from schemas.responses import BaseResponse, TransactionResponse
from services.pagination_service import PaginationService

from routers.dependencies import BlockchainServiceDep, raise_backend_http_error

ResponseModelT = TypeVar("ResponseModelT", bound=BaseResponse)


def map_response_models(
    model_cls: Type[ResponseModelT],
    items: Iterable[dict],
) -> List[ResponseModelT]:
    """Build a list of response models from raw dict items."""
    return [model_cls(**item) for item in items]


def sort_by_name(items: Sequence[dict]) -> List[dict]:
    """Return items sorted by their `name` field."""
    return sorted(items, key=lambda item: item.get("name", ""))


def paginate_response_models(
    pagination: PaginationService,
    model_cls: Type[ResponseModelT],
    items: Sequence[dict],
    *,
    page: int,
    count: int,
    sort_names: bool = False,
) -> List[ResponseModelT]:
    """Optionally sort items, paginate them, and map them to response models."""
    if sort_names:
        items = sort_by_name(items)

    paginated_items, _ = pagination.paginate(
        list(items),
        page=page,
        items_per_page=count,
    )
    return map_response_models(model_cls, paginated_items)


async def load_transaction_responses(
    service: BlockchainServiceDep,
    tx_ids: Iterable[str],
    *,
    raise_if_all_fail: bool = False,
) -> List[TransactionResponse]:
    """Fetch transactions concurrently and map them to API response models."""
    tx_ids = [tx_id for tx_id in tx_ids if tx_id]
    if not tx_ids:
        return []

    results = await service.get_transactions_by_ids(
        tx_ids,
        return_exceptions=True,
    )

    errors = [result for result in results if isinstance(result, Exception)]
    if raise_if_all_fail and errors and len(errors) == len(results):
        raise_backend_http_error(errors[0])

    return map_response_models(
        TransactionResponse,
        [result for result in results if isinstance(result, dict)],
    )

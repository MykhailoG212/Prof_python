"""Bounded asynchronous client for checking cars in a configured upstream API."""

import asyncio

import httpx

from car_catalog.schemas import ExternalCarCheckResult


class ExternalCarApiClient:
    """Checks upstream car records concurrently with bounded retries."""

    def __init__(
        self,
        base_url: str,
        *,
        max_concurrency: int = 4,
        timeout_seconds: float = 5.0,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.1,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least one")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")
        self._base_url = base_url.rstrip("/") + "/"
        self._max_concurrency = max_concurrency
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._transport = transport

    async def check_cars(self, car_ids: list[int]) -> list[ExternalCarCheckResult]:
        """Check identifiers concurrently while limiting active network requests."""
        semaphore = asyncio.Semaphore(self._max_concurrency)
        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            transport=self._transport,
        ) as client:
            tasks = [
                asyncio.create_task(self._check_one(client, semaphore, car_id))
                for car_id in car_ids
            ]
            return await asyncio.gather(*tasks)

    async def _check_one(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        car_id: int,
    ) -> ExternalCarCheckResult:
        for attempt in range(self._max_attempts):
            try:
                async with semaphore:
                    response = await asyncio.wait_for(
                        client.get(f"cars/{car_id}"),
                        timeout=self._timeout_seconds,
                    )
                if response.status_code >= 500 and attempt + 1 < self._max_attempts:
                    await self._wait_before_retry(attempt)
                    continue
                is_success = response.is_success
                return ExternalCarCheckResult(
                    car_id=car_id,
                    success=is_success,
                    status_code=response.status_code,
                    error=None if is_success else f"Upstream returned HTTP {response.status_code}",
                )
            except (httpx.RequestError, asyncio.TimeoutError) as error:
                if attempt + 1 == self._max_attempts:
                    return ExternalCarCheckResult(
                        car_id=car_id,
                        success=False,
                        status_code=None,
                        error=str(error) or "External request failed",
                    )
                await self._wait_before_retry(attempt)
        raise RuntimeError("Car check completed without a result")

    async def _wait_before_retry(self, attempt: int) -> None:
        """Apply exponential backoff before the next request attempt."""
        delay = self._retry_delay_seconds * (2**attempt)
        await asyncio.sleep(delay)

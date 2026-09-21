from __future__ import annotations

import asyncio
import unittest

import httpx

from seoultech_lms.client import ReadOnlyViolation, SeoultechLMSClient
from seoultech_lms.endpoints import BASE_URL, MAIN_FORM


class ClientSecurityTests(unittest.TestCase):
    def _run_request(self, handler, method: str = "GET", target: str = MAIN_FORM):
        async def run():
            client = SeoultechLMSClient()
            client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                return await client._request(method, target)
            finally:
                await client._http.aclose()

        return asyncio.run(run())

    def test_external_origin_with_allowed_path_is_blocked_before_network(self):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(200, request=request)

        with self.assertRaises(ReadOnlyViolation):
            self._run_request(handler, target=f"https://example.com{MAIN_FORM}")
        self.assertEqual(calls, [])

    def test_external_redirect_is_blocked(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                302,
                headers={"location": f"https://example.com{MAIN_FORM}"},
                request=request,
            )

        with self.assertRaises(ReadOnlyViolation):
            self._run_request(handler)

    def test_same_origin_redirect_to_non_allowlisted_path_is_blocked(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                302,
                headers={"location": "/ilos/cls/st/report/report_submit.acl"},
                request=request,
            )

        with self.assertRaises(ReadOnlyViolation):
            self._run_request(handler)

    def test_allowlisted_response_succeeds(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="ok", request=request)

        response = self._run_request(handler, target=f"{BASE_URL}{MAIN_FORM}")
        self.assertEqual(response.text, "ok")


if __name__ == "__main__":
    unittest.main()

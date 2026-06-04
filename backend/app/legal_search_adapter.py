from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_DELILEGAL_API_BASE_URL = "https://openapi.delilegal.com"
DEFAULT_DELILEGAL_API_APPID = "QthdBErlyaYvyXul"
DEFAULT_DELILEGAL_API_SECRET = "EC5D455E6BD348CE8E18BE05926D2EBE"


class LegalSearchApiError(RuntimeError):
    def __init__(self, message: str, *, code: int | None = None, raw_payload: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.raw_payload = raw_payload


class DelilegalSearchClient:
    def __init__(
        self,
        *,
        api_base_url: str | None = None,
        appid: str | None = None,
        secret: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_base_url = (api_base_url or os.getenv("DELILEGAL_API_BASE_URL", DEFAULT_DELILEGAL_API_BASE_URL)).rstrip("/")
        self.appid = appid or os.getenv("DELILEGAL_API_APPID", DEFAULT_DELILEGAL_API_APPID)
        self.secret = secret or os.getenv("DELILEGAL_API_SECRET", DEFAULT_DELILEGAL_API_SECRET)
        self.timeout_seconds = timeout_seconds or float(os.getenv("DELILEGAL_API_TIMEOUT_SECONDS", "30"))

    def search_cases(
        self,
        *,
        keyword: str,
        page_no: int = 1,
        page_size: int = 10,
        sort_field: str = "correlation",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        payload = {
            "pageNo": page_no,
            "pageSize": page_size,
            "sortField": sort_field,
            "sortOrder": sort_order,
            "condition": {"keywordArr": [keyword]},
        }
        result = self._post_json("/api/qa/v3/search/queryListCase", payload)
        body = result.get("body") or {}
        return {
            "success": bool(result.get("success", False)),
            "code": int(result.get("code", -1) or -1),
            "msg": str(result.get("msg", "")),
            "query_id": body.get("queryId"),
            "total_count": int(body.get("totalCount", 0) or 0),
            "total_page": int(body.get("totalPage", 0) or 0),
            "data": [self._transform_case(item) for item in body.get("data", []) if isinstance(item, dict)],
        }

    def search_laws(
        self,
        *,
        keywords: list[str],
        field_name: str = "semantic",
        page_no: int = 1,
        page_size: int = 10,
        sort_field: str = "correlation",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        payload = {
            "pageNo": page_no,
            "pageSize": page_size,
            "sortField": sort_field,
            "sortOrder": sort_order,
            "condition": {"keywords": keywords, "fieldName": field_name},
        }
        result = self._post_json("/api/qa/v3/search/queryListLaw", payload)
        body = result.get("body") or {}
        return {
            "success": bool(result.get("success", False)),
            "code": int(result.get("code", -1) or -1),
            "msg": str(result.get("msg", "")),
            "query_id": body.get("queryId"),
            "total_count": int(body.get("totalCount", 0) or 0),
            "total_page": int(body.get("totalPage", 0) or 0),
            "data": [self._transform_law_item(item) for item in body.get("data", []) if isinstance(item, dict)],
        }

    def get_law_detail(self, *, law_id: str, merge: bool = True) -> dict[str, Any]:
        result = self._get_json(
            "/api/qa/v3/search/lawInfo",
            {"lawId": law_id, "merge": str(merge).lower()},
        )
        body = result.get("body")
        return {
            "success": bool(result.get("success", False)),
            "code": int(result.get("code", -1) or -1),
            "msg": str(result.get("msg", "")),
            "body": self._transform_law_detail(body) if isinstance(body, dict) else None,
        }

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", endpoint, payload=payload)

    def _get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        return self._request_json("GET", endpoint, params=params)

    def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.api_base_url}{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "appid": self.appid,
                "secret": self.secret,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_text = response.read().decode("utf-8")
        except HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="replace")
            message, raw_payload = self._parse_error_payload(error_text)
            raise LegalSearchApiError(f"法狗狗 API HTTP {exc.code}: {message}", code=exc.code, raw_payload=raw_payload) from exc
        except (TimeoutError, URLError) as exc:
            raise LegalSearchApiError(f"法狗狗 API 请求失败：{exc}") from exc

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LegalSearchApiError("法狗狗 API 返回了非 JSON 响应", raw_payload=raw_text[:500]) from exc
        if not isinstance(parsed, dict):
            raise LegalSearchApiError("法狗狗 API 返回格式异常", raw_payload=parsed)
        return parsed

    def _parse_error_payload(self, error_text: str) -> tuple[str, Any]:
        try:
            payload = json.loads(error_text)
        except json.JSONDecodeError:
            return error_text[:500] or "HTTP 请求失败", error_text[:500]
        if isinstance(payload, dict):
            return str(payload.get("msg") or payload.get("message") or payload), payload
        return str(payload), payload

    def _transform_case(self, case: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": case.get("id", ""),
            "title": case.get("title", ""),
            "content": case.get("content", ""),
            "case_type": case.get("caseType", ""),
            "cause": case.get("cause", ""),
            "judgement_type": case.get("judgementType", ""),
            "judgement_date": case.get("judgementDate"),
            "court": case.get("court", ""),
            "case_number": case.get("caseNumber", ""),
            "level_of_trial": case.get("levelOfTrial", ""),
            "publish_type": case.get("publishType", ""),
            "publish_type_name": case.get("publishTypeName", ""),
        }

    def _transform_law_item(self, law: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": law.get("id", ""),
            "title": law.get("title", ""),
            "issued_no": law.get("issuedNo"),
            "publish_date": law.get("publishDate"),
            "publisher_name": law.get("publisherName", ""),
            "active_date": law.get("activeDate"),
            "timeliness_name": law.get("timelinessName", ""),
            "level_name": law.get("levelName", ""),
            "highlights": law.get("highlights", []),
        }

    def _transform_law_detail(self, law: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": law.get("lawsId", law.get("id", "")),
            "title": law.get("title", ""),
            "issued_no": law.get("issuedNo"),
            "publish_date": law.get("publishDate"),
            "publisher_name": law.get("publisherName", ""),
            "active_date": law.get("activeDate"),
            "timeliness_name": law.get("timelinessName", ""),
            "level_name": law.get("levelName", ""),
            "law_detail_content": law.get("lawDetailContent"),
        }

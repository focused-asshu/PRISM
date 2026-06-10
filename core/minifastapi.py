"""Tiny FastAPI-compatible fallback used only when third-party packages are unavailable.

It supports the subset PRISM needs: route decorators, JSON request parsing,
HTML/text responses, mounted static files, and simple HTTPException handling.
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, get_type_hints
from urllib.parse import unquote


class HTTPException(Exception):
    def __init__(self, status_code: int = 500, detail: Any = "") -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


class UploadFile:
    def __init__(self, filename: str = "", data: bytes = b"") -> None:
        self.filename = filename
        self._data = data

    async def read(self) -> bytes:
        return self._data


def File(default: Any = None, **_: Any) -> Any:
    return default


def Field(default: Any = None, **_: Any) -> Any:
    return default


class BaseModel:
    def __init__(self, **data: Any) -> None:
        annotations = getattr(self.__class__, "__annotations__", {})
        for name in annotations:
            if name not in data:
                raise ValueError(f"Missing required field: {name}")
            setattr(self, name, data[name])


class HTMLResponse(str):
    media_type = "text/html; charset=utf-8"


class CORSMiddleware:
    pass


@dataclass
class StaticFiles:
    directory: str


class FastAPI:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.routes: list[tuple[str, str, Callable[..., Any]]] = []
        self.mounts: list[tuple[str, StaticFiles]] = []

    def add_middleware(self, *_: Any, **__: Any) -> None:
        return None

    def get(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("GET", path)

    def post(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("POST", path)

    def _route(self, method: str, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append((method, path, func))
            return func

        return decorator

    def mount(self, path: str, app: StaticFiles, **_: Any) -> None:
        self.mounts.append((path.rstrip("/"), app))

    async def dispatch(self, method: str, path: str, body: bytes = b"") -> tuple[int, bytes, str]:
        try:
            static = self._static_response(path)
            if method == "GET" and static is not None:
                return static

            for route_method, route_path, endpoint in self.routes:
                params = _match(route_path, path)
                if route_method == method and params is not None:
                    result = await self._call(endpoint, params, body)
                    return _serialize(result)
            return _serialize({"detail": "Not found"}, status=404)
        except HTTPException as exc:
            return _serialize({"detail": exc.detail}, status=exc.status_code)
        except Exception as exc:  # return clean JSON instead of crashing the dev server
            return _serialize({"detail": str(exc)}, status=500)

    async def _call(self, endpoint: Callable[..., Any], params: dict[str, str], body: bytes) -> Any:
        if body:
            payload = json.loads(body.decode("utf-8"))
            annotations = get_type_hints(endpoint)
            model_params = [name for name, hint in annotations.items() if isinstance(hint, type) and issubclass(hint, BaseModel)]
            if model_params:
                params[model_params[0]] = annotations[model_params[0]](**payload)
        value = endpoint(**params)
        if asyncio.iscoroutine(value):
            return await value
        return value

    def _static_response(self, path: str) -> tuple[int, bytes, str] | None:
        for prefix, static in self.mounts:
            if path == prefix or path.startswith(prefix + "/"):
                rel = unquote(path[len(prefix) :].lstrip("/"))
                target = (Path(static.directory) / rel).resolve()
                root = Path(static.directory).resolve()
                if not str(target).startswith(str(root)) or not target.is_file():
                    return _serialize({"detail": "Not found"}, status=404)
                content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                return 200, target.read_bytes(), content_type
        return None


def _match(route_path: str, actual_path: str) -> dict[str, str] | None:
    route_parts = route_path.strip("/").split("/") if route_path != "/" else []
    actual_parts = actual_path.strip("/").split("/") if actual_path != "/" else []
    if len(route_parts) != len(actual_parts):
        return None
    params: dict[str, str] = {}
    for route, actual in zip(route_parts, actual_parts):
        if route.startswith("{") and route.endswith("}"):
            params[route[1:-1]] = unquote(actual)
        elif route != actual:
            return None
    return params


def _serialize(value: Any, status: int = 200) -> tuple[int, bytes, str]:
    if isinstance(value, str):
        return status, value.encode("utf-8"), "text/html; charset=utf-8"
    return status, json.dumps(value).encode("utf-8"), "application/json; charset=utf-8"

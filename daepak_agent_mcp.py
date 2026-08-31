#!/usr/bin/env python3
"""Daepak MCP server — market intelligence tools for any MCP-capable engine.

The server describes nothing itself: it pulls the catalogue from `GET /v1/tools`, so it
shows exactly what the key is allowed to call and never drifts from the product.

    claude mcp add daepak -e DAEPAK_API_KEY=dpk_live_… -- uvx daepak-mcp

Keys are issued on the Keys page at https://daepak.com.

⚠️ The account is derived FROM THE KEY. A request cannot name someone else: the older
bridge took `user_id` from the request body under one shared key, which meant a key holder
could read another person's positions and memory. That is why this server has no setting
for a user id, and why the API rejects such a field instead of ignoring it.

The catalogue arrives already filtered by the key's scopes — an engine that lists tools it
cannot call wastes turns on refusals. Each tool carries its price in credits so a sequence
can be budgeted before it runs.

Protocol: MCP 2024-11-05, JSON-RPC over stdin/stdout.
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request

BASE = os.getenv("DAEPAK_BASE_URL", "https://daepak.com").rstrip("/")
KEY = os.getenv("DAEPAK_API_KEY", "")
TIMEOUT = float(os.getenv("DAEPAK_TIMEOUT", "120"))

# ⚠️ Версия берётся из метаданных установленного пакета, а не пишется рядом второй раз.
# После заливки 2.0.1 сервер продолжал представляться как 2.0.0: два числа в двух местах
# расходятся ровно тогда, когда одно из них поднимают. Из исходников (без установки)
# метаданных нет — тогда честно говорим «dev», а не выдумываем номер.
try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    try:
        VERSION = _pkg_version("daepak-mcp")
    except PackageNotFoundError:
        VERSION = "dev"
except ImportError:
    VERSION = "dev"
# ⚠️ DAEPAK_USER_ID больше НЕ читается. Раньше им называли владельца в теле запроса —
# держатель общего ключа мог указать любого и получить чужие позиции и память.

# ⚠️ certifi обязателен, а не «желателен»: сборки Python для macOS не читают системное
# хранилище сертификатов, и без него КАЖДЫЙ вызов падает с CERTIFICATE_VERIFY_FAILED.
# Откат ниже оставлен для окружений, где сертификаты в системе есть (Linux-дистрибутивы).
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()


def _http(method: str, path: str, body: dict | None = None) -> dict | list:
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode()[:500]}
    except Exception as e:  # noqa: BLE001 — сеть/таймаут: движок должен увидеть причину, а не молчание
        return {"error": f"{type(e).__name__}: {e}"}


def _to_mcp(schema: dict) -> dict | None:
    """OpenAI function-schema → MCP tool. Формы обе: {"function":{...}} и плоская."""
    fn = schema.get("function") if isinstance(schema.get("function"), dict) else schema
    name = fn.get("name")
    if not name:
        return None
    params = fn.get("parameters") or {"type": "object", "properties": {}}
    desc = (fn.get("description") or "")[:1000]
    price = schema.get("credits") or fn.get("credits")
    if price:                       # цена рядом с описанием: бюджет считается ДО вызова
        desc = f"{desc}\n[стоимость: {price} кредит(ов)]"
    return {"name": name, "description": desc[:1024], "inputSchema": params}


_tools_cache: list[dict] | None = None


def tools() -> list[dict]:
    """Схемы с моста. Кэшируем: список не меняется в пределах запуска сервера."""
    global _tools_cache
    if _tools_cache is None:
        got = _http("GET", "/v1/tools")
        raw = got.get("tools") if isinstance(got, dict) else None
        if not raw:
            # мост недоступен — отдаём пустой список; движок сообщит, что тулзов нет,
            # вместо того чтобы падать на каждом вызове
            err = got.get("error") if isinstance(got, dict) else "нет ответа"
            print(f"[daepak-mcp] каталог недоступен: {err}", file=sys.stderr, flush=True)
            return []
        _tools_cache = [t for t in (_to_mcp(s) for s in raw) if t]
        print(f"[daepak-mcp] инструментов доступно ключу: {len(_tools_cache)} · {BASE}",
              file=sys.stderr, flush=True)
    return _tools_cache


def call_tool(name: str, args: dict) -> dict | list:
    """Вызов инструмента. Владелец берётся из ключа — в теле его нет и быть не может."""
    out = _http("POST", f"/v1/tools/{name}", args or {})
    # /v1 заворачивает результат вместе с расходом; движку нужны данные, а не обёртка,
    # но цену и время оставляем рядом — по ним видно, во что обошёлся шаг
    if isinstance(out, dict) and "data" in out:
        data = out["data"]
        if isinstance(data, dict):
            return {**data, "_credits": out.get("credits_used"), "_ms": out.get("took_ms")}
        return data
    return out


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        mid = msg.get("id")
        method = msg.get("method", "")
        if method == "initialize":
            resp = {"protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "daepak", "version": VERSION}}
        elif method == "tools/list":
            resp = {"tools": tools()}
        elif method == "tools/call":
            p = msg.get("params") or {}
            out = call_tool(p.get("name", ""), p.get("arguments") or {})
            resp = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
                    "isError": bool(isinstance(out, dict) and out.get("error"))}
        elif method in ("notifications/initialized", "notifications/cancelled"):
            continue                      # уведомления — без ответа
        elif mid is None:
            continue
        else:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": mid,
                 "error": {"code": -32601, "message": f"method not found: {method}"}}) + "\n")
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": resp},
                                    ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

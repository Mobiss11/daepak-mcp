# Daepak MCP

<!-- mcp-name: io.github.Mobiss11/daepak-mcp -->

Market intelligence tools for any MCP-capable engine — Claude Code, Claude Desktop, or your
own agent. Prices, indicators, levels, positioning, the Korean market, US equities, options,
backtests, and your own trading journal. **98 tools**, the same ones the product's own
analyst uses.

The server describes nothing itself: it pulls the catalogue from `GET /v1/tools`, so it
shows exactly what your key is allowed to call and never drifts from the product.

## Quick start

```bash
claude mcp add daepak -e DAEPAK_API_KEY=dpk_live_… -- uvx daepak-mcp
```

Or install it yourself:

```bash
pip install daepak-mcp
```

Get a key on the **Keys** page of your profile at [daepak.com](https://daepak.com). The free
plan includes 2 000 credits a month — enough to build something over an evening.

## Configuration

| variable | default | purpose |
|---|---|---|
| `DAEPAK_API_KEY` | — | your key, `dpk_live_…`. Required. |
| `DAEPAK_BASE_URL` | `https://daepak.com` | point at another environment |
| `DAEPAK_TIMEOUT` | `120` | seconds per call |

Nothing else is read. In particular there is **no** setting that names a user: the account
is derived from the key, and a request cannot claim to be someone else.

## What you get

The catalogue is filtered by your key's scopes — you never see a tool you cannot call.

| scope | tools | what it opens |
|---|---|---|
| `read:market` | 78 | prices, candles, indicators, levels, scores, narratives, derivatives, order book, liquidations, options, US equities, Korean market, backtests |
| `read:personal` | 9 | your positions, portfolio, trade journal, catalysts, memory, background tasks |
| `write:personal` | 11 | writing to those same records |
| `agent:chat` | — | full analyst answers, streamed or complete |

Being allowed to read your journal does not allow writing to it. That is a separate scope.

**Crypto** — `get_price`, `get_price_history`, `get_levels` (support/resistance, Fibonacci,
ATR — computed, not drawn), `get_indicators`, `get_score`, `get_regime`, `get_derivatives`,
`get_orderbook`, `get_liquidations`, `get_fear_greed`

**Korea** — `get_kimchi_premium` (the Upbit-to-global spread, decomposed into the asset leg
and the currency leg), Korean tickers, fresh Upbit listings

**US equities** — `get_stock_quote`, `get_stock_history`, `get_stock_levels`,
`get_stock_holders` (institutions and insiders), `get_us_gap_stats`, `get_us_movers`,
`get_us_halts`, `get_us_insiders`

**Options** — `get_iv_metrics`, `get_options_positioning`, `get_option_structure` (payoff and
greeks), `get_options_backtest`

**Validation** — `get_backtest`, `get_signal_outcomes`, `get_hit_rate`, `get_score_history`

**Arbitrary tokens** — `resolve_token`, `get_token_market`, `get_token_onchain`,
`get_token_holders`, for anything outside the watchlist

**Research** — `search_news` (RAG over the collected corpus), `search_narratives`,
`fetch_url`, `web_search`

## The agent

The same analyst that answers in the product, over HTTP. It has everything the chat has:

| | |
|---|---|
| `POST /v1/agent/stream` | server-sent events — text arrives as it is written |
| `POST /v1/agent/messages` | the complete answer in one response |
| `GET /v1/agent/resume/{id}` | reconnect to a generation already running |
| `POST /v1/agent/cancel/{id}` | stop one |
| `GET /v1/agent/conversations` | your conversations, and `/{id}` for the messages |

```bash
curl -N -X POST https://daepak.com/v1/agent/stream \
     -H "Authorization: Bearer dpk_live_…" -H "Content-Type: application/json" \
     -d '{"message": "How does BTC look right now?", "mode": "mentor"}'
```

**Conversation memory.** The first event carries `conversation_id`; pass it back and the
context continues.

**Images.** `images` takes data-URLs, exactly like chat attachments — the agent reads charts
and screenshots.

**Mentor mode.** `mode: "mentor"` explains how the reading was arrived at, not just the
conclusion.

⚠️ **A dropped connection loses nothing.** Generation continues in the background, the answer
still lands in the conversation, and `resume` replays what you missed. Keep the
`conversation_id` from the first event — that is where you reconnect.

⚠️ `suggest` (follow-up questions) arrives **after** `done`. A client that stops reading at
`done` will never see it. The order is deliberate: the spinner should stop before the
suggestions are computed.

## Credits

Every tool declares its price in the catalogue, so a sequence can be budgeted before it runs.
Prices come from measuring the tools in production, not from guessing:

| tier | what | credits |
|---|---|---|
| our database | prices, indicators, levels, candles, narratives | 1 |
| external call | equities, tokens, options, on-chain | 5 |
| embedding, sandbox | news search, code execution | 20 |

A tool nobody has priced yet costs 5, not 1 — an unpriced tool is either an oversight or
something heavy, and both are safer to over-charge than to give away.

```bash
curl -H "Authorization: Bearer dpk_live_…" https://daepak.com/v1/usage
```

When the monthly credits run out you get `402` naming two ways forward: a higher plan or the
renewal at the start of the month. **There is no overage billing** — we would rather refuse
than send an invoice nobody expected.

## Using the API directly

The MCP server is a thin shell over a plain REST API.

```bash
# catalogue: schema, scope and price for every tool your key can call
curl -H "Authorization: Bearer dpk_live_…" https://daepak.com/v1/tools

# call one
curl -X POST https://daepak.com/v1/tools/get_price \
     -H "Authorization: Bearer dpk_live_…" \
     -H "Content-Type: application/json" \
     -d '{"coin": "BTC"}'
```

```json
{
  "tool": "get_price",
  "credits_used": 1,
  "credits_left": 1999,
  "took_ms": 104,
  "data": { "coin": "BTC", "price": 78017.26, "change_24h": -1.2 }
}
```

Full reference: [daepak.com/reference](https://daepak.com/reference) ·
OpenAPI 3.1: [/v1/openapi.json](https://daepak.com/v1/openapi.json) (106 operations, no key
needed to read it).

## Reading the answers honestly

A few things the data will tell you if you look, and which are easy to get wrong:

- **Compare against the baseline, not against zero.** "68 % of directions guessed" means
  nothing until you know what a random entry at the same moment would have given.
- **Win rate is not money.** On our own data 68 % correct directions produced a
  profit factor of 1.04.
- **Groups under 30 observations are flagged `reliable=false`.** That is an absence of a
  conclusion, not a weak one.
- **The kimchi premium has two legs** — a discount on the asset and a discount on the won.
  Read together they mislead. And they explain rather than predict: on horizons up to a day
  we found no relationship (646 episodes).
- Every answer carries the age of its data. If it is stale, say so rather than passing
  yesterday off as now.

## Troubleshooting

**`401`** — the key is missing, revoked, or malformed. Send it as
`Authorization: Bearer dpk_live_…`.

**`403 scope_required`** — the key lacks the scope; the response names which one.

**`400 user_id_not_accepted`** — the body contained a `user_id`. The account comes from the
key; the field is rejected explicitly rather than ignored, so that a copied example fails
loudly instead of quietly returning nothing.

**`404 conversation_not_found`** — that conversation belongs to another account.

**`429`** — over the per-minute ceiling for your plan. The minute limit protects the service;
the monthly one protects your budget.

**`CERTIFICATE_VERIFY_FAILED`** — you are running from source without `certifi`. Install the
package instead of the file; the dependency exists for exactly this.

Error messages default to English; send `X-Lang: ko` or `ru` for those languages.

## Links

- [daepak.com](https://daepak.com) — the product
- [Developer docs](https://daepak.com/developers) — with a live request tester
- [GitHub](https://github.com/Mobiss11/daepak-mcp) · [PyPI](https://pypi.org/project/daepak-mcp/)

## License

MIT

# Request reliability and provider hardening

Based on teacher-mode-prototype at 86d9ed2da5f21ab5b8f7edc5d9fc16056cb7fa09.
These changes are local and uncommitted.

## Behavior

- Requests retain their original question, project and mode. UI updates are
  delivered through a queue polled on the Tk main thread.
- New Chat and Kill invalidate the active request. A running network call cannot
  be forcibly interrupted; its answer is discarded when it returns. Reset does
  not revive that request or permit a second request while it remains active.
- API clients are initialized on demand and closed after each operation. Missing
  credentials or SDKs produce actionable errors instead of import-time failures.
- Council validates all three credentials before the first model call. It stops
  at the first provider failure, with no final answer or automatic archive entry.
  Completed partial rounds are not displayed by this version.
- Provider failures have separate provider/code/message fields through ModelError;
  raw SDK error messages are not shown. Errors are never model answer text.
- CLI and GUI use the same engine. Teacher history only receives successful turns.
- An unwritable safety audit log blocks model calls. Audit log location and
  existing approval policy are otherwise unchanged.

## Atlas animation

The existing Atlas image has a Canvas orbit ring: slow blue when ready, faster
cyan while thinking, stationary amber while stopping, and stationary red when
killed. The Animation checkbox disables movement while retaining status colors.
The timer is stopped on window close. Missing image assets fall back to an A.
No new runtime dependency is required. Visual appearance still needs Windows QA.

## Configuration

Use environment variables or an existing .env file with python-dotenv installed:
OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY.
Never commit credentials.

Optional: ATLAS_MODEL, CLAUDE_MODEL, GROK_MODEL, AI_TIMEOUT_SECONDS (default 60).
Original model defaults are preserved; account access and model availability
have not been verified. SDK automatic retries are disabled to bound waiting.
The timeout is an SDK request timeout, not a total Council deadline.

## Validation

From repository root:

    python -m unittest discover -s metin-ai-lab -p 'test_*.py' -v
    python -m compileall -q metin-ai-lab

Tests mock all providers and require no API keys, network access, or display.
GUI callbacks are tested headlessly; Windows GUI, actual SDK calls, voice playback
and executable packaging still require manual validation.

## Remaining work

Project-specific persistent Teacher history, complete approval workflow,
request/provider/outcome audit metadata, bounded logs, speech stop/error controls,
and dependency locking remain separate follow-up work.

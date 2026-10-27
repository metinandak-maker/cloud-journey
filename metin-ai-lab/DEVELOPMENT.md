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
  at the first provider failure, with no final answer. Completed responses remain
  visible, exportable and archived with the error and failed stage. The GUI shows
  the active stage (1–7), stage elapsed time and total elapsed time.
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

## v0.3 — Game Development Council

The project selector includes KEBAB MAN ON CRIME. Atlas focuses on mechanics and
strategy, Claude on story, characters and British dialogue, and Grok on creative
play and comedy. All three brainstorm, review the other proposals, and Atlas
synthesizes recommendations pending human approval. This app has no game-editing
or automatic development action.

Private game context is loaded at request time from the sibling private checkout
`kebab-man-on-crime`. Only README.md, roadmap.md, src/game/logic.ts and
src/game/input.ts are eligible. Files over 100 KB are omitted; excerpts stop at
18,000 characters per file. Missing files are reported as unavailable, and symlink
escapes are rejected. Evidence is sent to the configured model providers when a
user asks in this project, including individual model modes. No private game
contents are copied into the public app. README intentions and roadmap entries
are explicitly distinguished from implementation evidence. This is partial
context, not a complete game audit, and model claims still require human review.

The public repository root .gitignore excludes /kebab-man-on-crime/. Preserve
this rule; never force-add the private checkout. The existing student database
ignore change is preserved.

Successful GUI Council sessions save the original question, all ideas, reviews,
final recommendation, timestamp and pending approval status as JSONL under
~/Documents/Metin AI Lab/projects/<SHA256 of project name>/ideas.jsonl. History
shows only the selected project, including after restarting. Old mixed-project
council_archive.txt remains untouched and is not imported because it lacks
reliable project attribution. History is local plaintext; users control retention.
History is for review and is not automatically sent back to models. CLI retains
its existing generic Council behaviour and does not persist sessions.

Teacher conversations are isolated by project in memory. New Chat clears only
the selected project's Teacher conversation and display, retaining saved ideas.
Kill switch, cancellation, audit blocking, credential preflight and provider
failure handling remain in place. Failed/cancelled sessions are not archived.

Validation: 31 headless unittest tests pass, including seven new project tests;
Python compilation passes. No live provider calls were made. Windows GUI layout,
actual model access/quality and packaged executable remain unverified. No commits
or pushes were made.

## Local v0.3 GUI verification

Launch from this directory with `python3 -u app.py` (or
`.venv-wsl/bin/python -u app.py`). `main.py` is the command-line Council, and an
existing packaged executable does not pick up Python source changes. The game
name is defined in project_context.py and imported into the PROJECT dropdown;
searching app.py alone does not establish whether the project is registered.

The visible heading now also says METIN AI LAB v0.3. Startup stays fully opaque
with no fade timer, preserving the WSLg visibility fix. Programmatic project
selection also synchronizes the dropdown variable.

Run the real-display regression with:

    METIN_GUI_TESTS=1 python3 -m unittest discover -p 'test_*.py' -v

All 32 tests passed on the local WSLg display. The real Tk regression checks a
mapped, opaque window, version heading/title, actual menu invocation, project
routing for seven mocked model calls, history display and persistence after
window closure, project isolation, Teacher mode selection and continued event
loop callbacks until explicit close. It uses temporary history and does not
call APIs or access the private game checkout. Without METIN_GUI_TESTS=1, the
31 headless tests run and this display-dependent test is skipped.

This verifies Tk state and callbacks, not a human visual review of the Windows
desktop or live model service access. The previously reported silent exit was
not reproduced. In the verification shell only python3 was available. WSLg
access required running the display test outside the tool sandbox.

## Claude empty-response handling

The configured default remains `claude-sonnet-5`, a documented Anthropic API ID.
No CLAUDE_MODEL override was found in the local environment or .env during this
investigation. Account-specific availability has not been checked. Anthropic's
Sonnet 5 documentation states that adaptive thinking is on by default and shares
the max_tokens budget with text. The previous code used 1600 output tokens and
ignored stop_reason. A thinking-only response exhausting that budget is a
plausible explanation for the reported failure, but cannot be confirmed without
the original response metadata.

For the exact claude-sonnet-5 ID, requests now explicitly disable thinking, which
that model documents as supported. Other configured model IDs keep their default
thinking behaviour; disabling thinking is not universally supported. The output
budget remains 1600 unless CLAUDE_MAX_TOKENS is explicitly set (integer 1..128000).
The configured model may impose a lower limit. Invalid local budgets fail Council
preflight before provider calls; remote 400/404 responses provide safe configuration
guidance without echoing provider error bodies.

Text blocks are combined while thinking and other blocks remain excluded.
stop_reason is checked before accepting text: max_tokens and context exhaustion
are errors even with partial text; refusal and unfinished turns are also errors.
Empty completed turns are distinguished from token limits. Failure diagnostics
contain only fixed stop/type categories, content-block counts, request token
budget and nonnegative integer input/output usage counts when available. Unknown
categories become 'unknown'/'other'. No raw model response, thinking, request ID,
prompt, key or provider error body is logged. Diagnostic metadata is returned
through ModelError and Council errors and appears in the UI error text. Failed
sessions still have no final recommendation or automatic archive entry.

There are no automatic paid retries, continuations or model fallbacks. Users can
shorten the request or deliberately adjust CLAUDE_MAX_TOKENS before trying again;
a higher budget can increase cost. No paid calls were made in this investigation.

Validation: all 41 tests passed with METIN_GUI_TESTS=1, including nine new Claude
regressions, the existing Council/Teacher/safety tests and the real WSLg test.
Live provider access and the original failure's exact stop_reason remain unknown.

Documentation checked:
- https://platform.claude.com/docs/en/docs/about-claude/models/whats-new-sonnet-5
- https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons
- https://platform.claude.com/docs/en/api/errors

Council timeout investigation (2026-10-27): effective local configuration is
60 seconds for all three providers, from the default; automatic retries are zero.
ATLAS is called for analysis, review and final synthesis. Timeout errors now show
the configured SDK timeout; partial Council failures identify the exact stage.
This is an SDK request timeout, not a guaranteed wall-clock Council deadline.
No live provider request was made to diagnose upstream latency.

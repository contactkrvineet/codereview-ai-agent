# Team Coding Standards

> These standards apply to all code changes. Flag clear violations — do not stay silent when an issue is obvious.

---

## 1. Security

- **No hardcoded secrets.** API keys, passwords, tokens, and credentials must never appear in source code. Use environment variables or secret managers.
- **No SQL string concatenation.** Always use parameterised queries / prepared statements.
- **Validate all external input** at system boundaries (API endpoints, file uploads, CLI args).
- **No `eval()` or dynamic code execution** with untrusted data.
- **HTTPS only** for any hardcoded external URLs in production code.

---

## 2. Error handling

- **Do not swallow exceptions silently.** An empty `except:`, `catch {}`, or `rescue` block with no logging is always a violation.
- **Log exceptions with context** — include the error message and enough info to reproduce.
- Avoid bare `except Exception` in Python without re-raising or specific handling.
- Functions that can fail must either return an error value, raise a typed exception, or document what they throw.

---

## 3. Naming conventions

- **Variables, functions, and methods** must use descriptive names. Single-letter names (`x`, `d`, `tmp`) are only acceptable as loop indices.
- **Boolean variables/functions** should read as a predicate: `is_valid`, `has_permission`, `can_retry` — not `flag`, `check`, `result`.
- **Constants** must be UPPER_SNAKE_CASE (Python/JS) or `static final` (Java).
- **Functions must do one thing.** A function named `processData` that also sends emails and logs to a database violates single responsibility.

---

## 4. Magic numbers and strings

- Magic numbers must be replaced with named constants. `sleep(5000)`, `if status == 42`, `range(100)` — all require a named constant or comment.
- Exception: `0`, `1`, `-1`, `""`, `[]` are acceptable when meaning is obvious from immediate context.
- Hardcoded URLs, paths, and timeouts in business logic must be constants or config values.

---

## 5. Code duplication

- Identical or near-identical blocks of logic repeated 3+ times must be extracted into a shared function.
- Copy-pasted code with minor variable changes is always a violation.

---

## 6. Function and method design

- Functions must not exceed ~50 lines. Flag functions that are clearly doing too much.
- **Avoid deeply nested logic** — more than 3 levels of nesting (if/for/try) is a violation. Prefer early returns.
- Functions must not have more than 5 parameters. Use a config object/dataclass if more are needed.
- **Avoid boolean parameters** that change function behaviour (`def process(data, is_dry_run=True)`) — split into two functions instead.

---

## 7. Test quality (applies to test files)

- **Every test must have at least one explicit assertion.** A test with no assertion is not a test.
- **Test names must describe behaviour:** `test_login_with_expired_password_returns_401`, not `test1` or `testLogin`.
- **No hardcoded test data** (usernames, passwords, account IDs) inline — use fixtures, factories, or config.
- `Thread.sleep()` / `time.sleep()` in tests is a violation — use explicit waits or retry logic.
- Page Object classes must not contain assertions; assertions belong in test classes.
- Hardcoded absolute XPath (`/html/body/div[3]/input`) is forbidden — use `data-testid`, `id`, or stable CSS.
- Every test method must clean up after itself — no leaked state, open connections, or browser sessions.

---

## 8. Imports and dependencies

- **No wildcard imports** (`import java.util.*`, `from module import *`).
- **Unused imports must be removed.**
- Do not import an entire library just to use one function — import only what you need.

---

## 9. Comments and documentation

- `TODO` / `FIXME` comments must include a ticket or owner reference: `# TODO(JIRA-123): description`.
- Comments must explain **why**, not **what**. `i += 1  # increment i` is not a useful comment.
- Public functions/methods/classes should have a docstring or Javadoc if their purpose is non-obvious.

---

## 10. Resource management

- File handles, DB connections, HTTP clients, and sockets must be closed after use. Use `with`/`try-finally`/`using` patterns.
- Do not open connections at module import time — open them lazily or in a managed context.
- Any resource opened in setup must be closed in teardown.

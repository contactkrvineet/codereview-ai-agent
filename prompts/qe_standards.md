# Team Coding Standards — Quality Engineering

> Customize this file with your team's specific conventions. The agent will flag violations of whatever you put here.

## 1. Test method naming

- Test methods must describe behavior, not implementation.
- Format: `test<UnitOfWork>_<Condition>_<ExpectedResult>` OR `should_<expected>_when_<condition>`.
- Bad: `test1()`, `testit()`, `testStuff()`, `loginTest()`
- Good: `testLogin_withValidCredentials_redirectsToDashboard()`, `should_rejectLogin_when_passwordIsExpired()`

## 2. Page Object Model patterns

- Locators must be defined as private class fields, not inline in methods.
- Each page method should return either `void`, `boolean`, or `<NextPage>` — never a raw WebElement.
- Page classes must not contain assertions; assertions belong in test classes.
- Constructor pattern: page classes accept `WebDriver` (or framework equivalent) in their constructor.

## 3. Selector preferences

- **Preferred order:** `data-testid` > `id` > `name` > stable CSS > XPath (last resort).
- Hardcoded absolute XPath like `/html/body/div[3]/form/input[2]` is forbidden — too brittle.
- Class-only selectors like `By.className("btn")` are discouraged when more stable options exist.

## 4. Assertion patterns

- Every test method must have at least one explicit assertion.
- Multi-step assertions should use soft assertions (`SoftAssert`, `Assertions.assertAll`) — fail at the end of the test, not on the first failure.
- Assertion messages are required when comparing more than primitives. Use the third argument: `assertEquals(expected, actual, "Order total should match cart subtotal")`.
- Don't use `assertTrue(x == y)` — use `assertEquals(y, x)` for better failure messages.

## 5. Test data management

- No hardcoded test data inline in test methods (URLs, usernames, passwords, account IDs).
- Test data must come from: configuration files, test data factories, or external data providers.
- Sensitive values (API keys, real credentials) must never be committed — use environment variables.
- Use unique identifiers (UUIDs, timestamps) to prevent cross-test interference in parallel runs.

## 6. Magic numbers and strings

- Magic numbers (e.g., `Thread.sleep(5000)`, `if (count == 42)`) must be replaced with named constants.
- Exception: `0`, `1`, `-1` are acceptable when their meaning is obvious from context.
- `Thread.sleep()` itself is strongly discouraged — use explicit waits (`WebDriverWait`, `expected_conditions`) instead.

## 7. Setup and teardown

- Use proper annotations (`@BeforeEach`, `@AfterEach`, `@BeforeAll`, `@AfterAll` in JUnit5; `@BeforeMethod`, `@AfterMethod` in TestNG).
- Browser/driver instances must be cleaned up in teardown — no leaked sessions.
- Heavy setup operations should be in `@BeforeAll`/`@BeforeClass`, not `@BeforeEach`.

## 8. Documentation

- Public test methods should have a Javadoc/docstring describing what behavior is being verified.
- Complex setup code should have inline comments explaining intent.
- TODO/FIXME comments must include a ticket reference: `// TODO(JIRA-1234): description`.

## 9. Imports and structure

- No wildcard imports (`import java.util.*`). Use specific imports.
- Unused imports must be removed.
- Test classes should be in the same package structure as the code they test.

## 10. BDD / Gherkin specifics (if applicable)

- Step definitions must be reusable — avoid creating new steps when an equivalent exists.
- Feature files use scenario-level tags for test organization (`@smoke`, `@regression`, `@<module>`).
- Background steps must apply to all scenarios in the feature, not be misused as test setup.
- Avoid technical implementation details in feature files (CSS selectors, technical jargon).

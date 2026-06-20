
## Python Linting & Code Verification Rules
- **Ruff & Semgrep linting**: The project uses Ruff for formatting/imports styling and Semgrep for architectural boundary checks.
- **Ruff Execution**: Run `ruff check .` to check for formatting, syntax issues, or unused imports. Run `ruff format .` to format files automatically.
- **Semgrep Execution**: Run `semgrep --config semgrep-rules.yaml .` to execute the structural checks. Always resolve any errors regarding direct DB imports, `state.clear()` calls, or direct UI calls in handlers.
- **Validation Parity**: Any new directory or feature layer must be added to Semgrep configurations if it involves routers/handlers or database facades.

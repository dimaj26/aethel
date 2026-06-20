
## JS/TS Linting & Code Verification Rules
- **ESLint & Prettier linting**: The project uses ESLint for static analysis and Prettier for code formatting.
- **ESLint Execution**: Run `npx eslint .` to check for syntax, styles, or logic errors. Run `npx eslint --fix .` to automatically resolve fixable violations.
- **Prettier Execution**: Run `npx prettier --check .` to check formatting, or `npx prettier --write .` to write formatted styles.
- **Pre-commit boundary checks**: All code must pass linting and styling checks successfully before staging changes.

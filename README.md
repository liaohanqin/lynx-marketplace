# CodeBuddy Code Plugin Marketplace

This repository is configured as a personal CodeBuddy Code plugin marketplace.

## Structure

- `.codebuddy-plugin/marketplace.json`: The main configuration file defining the marketplace and listed plugins.
- `plugins/`: A directory where you can host local plugins directly in this repository (optional).

## Usage

1. **Edit Configuration**: Update `.codebuddy-plugin/marketplace.json` with your marketplace details and add your plugins.
2. **Add Plugins**:
    - **Remote Plugins**: Add entries in the `plugins` array pointing to external repositories (e.g., GitHub).
    - **Local Plugins**: Place plugin code in the `plugins/` directory and reference them using relative paths in `marketplace.json`.
3. **Register Marketplace**: Use the CodeBuddy command to add this marketplace:
   ```bash
   /plugin marketplace add <your-repo-url>
   ```

## Example Plugin Entry

```json
{
  "name": "my-tool",
  "description": "A very useful tool",
  "version": "1.0.0",
  "source": {
    "source": "github",
    "repo": "username/my-tool-repo"
  }
}
```

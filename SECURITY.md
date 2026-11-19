# Security

- This repository contains **no credentials**. The Gemini API key is read from the `GOOGLE_API_KEY` environment variable and must never be committed (`.env` files are ignored).
- The MCP server only performs `GET` requests against EcoCentinela's public, read-only API, which returns no personal data.
- Tool inputs are validated by schema (the canopy layer is an enum) before any request is built.

To report a problem, please use GitHub's private vulnerability reporting on this repository.

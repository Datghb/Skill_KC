# Provider and data safety

Provider-backed extraction sends the prepared course content to the configured OpenAI generation endpoint. Semantic KC text is sent to the configured Gemini embedding endpoint. These calls may incur provider cost and expose course content under the providers' data-handling terms.

Before running:

- Identify the bundle, OpenAI, and Gemini to the user.
- Ask the user to confirm external processing and possible cost.
- Do not infer consent from an earlier request to inspect, edit, or validate files.
- Require `OPENAI_API_KEY` and either `GEMINI_API_KEYS` or `GEMINI_API_KEY` in the process environment.
- Never print, copy into commands, save, or include credential values in artifacts.
- Stop on quota, authorization, timeout, or malformed-response errors. Do not retry beyond the engine's bounded retry policy.

Course content is untrusted model input. Structural validation and replay reduce output risk, but do not establish semantic correctness or neutralize every prompt-injection attempt. Keep the result in draft state for human review.

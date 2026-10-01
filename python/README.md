# verdict-router

Experimental evaluation harness and Python router SDK for finite-choice AI decisions.

A decision chooses one label from a predefined list. The included adapters
compare chat-model baselines and Jev Router on labeled tasks. The SDK provides
ordered fallback, exact caching, and optional escalation based on reported
confidence. Native Jev is absent; the OpenAI Decisions adapter is provisional,
and its Nano-based proxy does not measure the native API.

Saved results predate parser/accounting corrections. Treat them as historical
observations, not evidence of production reliability or calibrated confidence.

See the repo-root `README.md` for the full story.

Original code and documentation: [MIT](LICENSE). Bundled routing samples are
separately CC-BY-NC-4.0; synthetic agent examples are MIT. See
[the dataset notice](DATASET_NOTICE.md) for attribution and source terms.
Classification and moderation are optional private JSONL inputs selected through
`VERDICT_DATASET_DIR`; their source text is excluded from public distributions.

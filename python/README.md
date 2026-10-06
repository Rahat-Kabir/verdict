# verdict-router

Experimental evaluation harness and Python router SDK for finite-choice AI decisions.

A decision chooses one label from a predefined list. The included adapters cover
native Jev and Cloudflare Clef/Flash choices, chat-model baselines, and Jev Router's
downstream model selection. The SDK provides ordered fallback, exact caching, and
optional escalation based on reported confidence. Native Jev and Clef/Flash have
limited synthetic live evidence; representative evaluation remains pending.
The OpenAI Decisions adapter is provisional, and its Nano-based proxy does not
measure the native API.

Saved results predate parser/accounting corrections. Treat them as historical
observations, not evidence of production reliability or calibrated confidence.

See the [project README](https://github.com/Rahat-Kabir/verdict#readme) for the local
demo, benchmark workflow, SDK example, and current limitations.

Original code and documentation: [MIT](LICENSE). Bundled routing samples are
separately CC-BY-NC-4.0; synthetic agent examples are MIT. See
[the dataset notice](DATASET_NOTICE.md) for attribution and source terms.
Classification and moderation are optional private JSONL inputs selected through
`VERDICT_DATASET_DIR`; their source text is excluded from public distributions.

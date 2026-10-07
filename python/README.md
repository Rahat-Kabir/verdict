# verdict-router

Experimental evaluation harness and Python router SDK for finite-choice AI decisions.

A decision chooses one label from a predefined list. The included adapters cover
native OpenAI Decisions, Jev and Cloudflare Clef/Flash choices, chat-model
baselines, and Jev Router's downstream model selection. The SDK provides
ordered fallback, exact caching, and optional escalation based on reported confidence.
The OpenAI Decisions adapter uses native typed choices; its Nano-based proxy does not
measure the native API.

`clef-openrouter` and `clef-flash-openrouter` use the OpenRouter Decisions endpoint
and reported account charges. They are separate from direct Workers AI adapters
and remain explicit selection only. The BANKING77 study records the access
route, frozen definitions, raw replies, failures, timing and cost basis.

The completed balanced BANKING77 experiment used 154 test messages across all
77 intents and made 616 API attempts. It reports accuracy, failures, latency,
and labeled costs. It is exploratory, with two messages per intent and 12
previously attempted messages. Read the
[experiment report](https://github.com/Rahat-Kabir/verdict/blob/main/docs/BANKING77_BALANCED.md).

The older leaderboard records predate parser/accounting corrections. Keep those
historical observations separate from the BANKING77 study. Neither establishes
production reliability or calibrated confidence.

See the [project README](https://github.com/Rahat-Kabir/verdict#readme) for the local
demo, benchmark workflow, SDK example, and current limitations.

Original code and documentation: [MIT](LICENSE). Bundled routing samples are
separately CC-BY-NC-4.0; synthetic agent examples are MIT. See
[the dataset notice](DATASET_NOTICE.md) for attribution and source terms.
Classification and moderation are optional private JSONL inputs selected through
`VERDICT_DATASET_DIR`; their source text is excluded from public distributions.

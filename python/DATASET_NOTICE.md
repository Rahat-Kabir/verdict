# Dataset notice

Verdict's original code and documentation are MIT licensed. Third-party dataset
text is excluded from that grant and remains subject to its source terms.

The dataset builder uses these sources; original row-level revisions and source
IDs were not retained in the original samples. Source terms checked 2026-10-01:

| Suite / distribution | Builder source | Published terms |
| --- | --- | --- |
| classification / local only | [AG News, fancyzhx](https://huggingface.co/datasets/fancyzhx/ag_news) | Unknown license. Raw text is excluded from this repository, publishable history, and Python distributions. |
| routing / bundled | [Customer support tickets, Tobi Bueck](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets) | [CC-BY-NC-4.0](https://creativecommons.org/licenses/by-nc/4.0/), separately from the code's MIT license. |
| moderation / local only | [TweetEval, Cardiff NLP](https://huggingface.co/datasets/cardiffnlp/tweet_eval#licensing-information) | Hate/HateEval requires permission and refers to Twitter terms. Raw text is excluded from this repository, publishable history, and Python distributions. |
| agent_next_action / bundled | Verdict's seeded tool-selection templates | Project-generated examples, covered by the MIT license. |
| BANKING77 / local study only | [PolyAI-LDN task-specific datasets](https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data) | [CC-BY-4.0](https://github.com/PolyAI-LDN/task-specific-datasets/blob/57ec275d8078af65b7731c2a98be812d844a6d6b/LICENSE). Pinned source CSVs and raw study evidence stay outside Git/packages. |

Transformations include sampling, truncating text, mapping labels, and formatting
finite-choice requests. Builders can fall back to generated examples, but the
original files lack source manifests; do not infer permission from that fallback.

The BANKING77 study separately preserves the complete official 3,080-row test
split and original labels without truncation or relabeling. Its 77-item pilot
selects the first training row per intent. Shared definitions are Verdict-authored,
reviewed against training examples; source revision and file hashes are retained.
Attribution: Iñigo Casanueva, Tadas Temčinas, Daniela Gerz, Matthew Henderson and
Ivan Vulić, *Efficient Intent Detection with Dual Sentence Encoders*, 2020.
Consult the [authors' repository](https://github.com/PolyAI-LDN/task-specific-datasets)
for the paper and dataset notices. The code's MIT license does not relicense
third-party dataset text.

## Attribution for the bundled routing samples

**Customer Support Tickets**, by **Tobi Bueck (Tobi-Bueck)**, is distributed under
[Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/).
[Original dataset and creator's notices](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets).

Verdict modified the source by selecting English entries, choosing four support
queues, sampling rows, combining subject/body, truncating text to 600 characters,
and adding finite-choice questions and normalized record fields. The bundled
sample contains 198 entries. It is not endorsed by the source creator. The source
page describes synthetic ticket generation; these samples are not claimed to be
verified real customer communications.

The dataset remains subject to CC-BY-NC-4.0, including its noncommercial-use and
attribution conditions and its [disclaimer of warranties](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en#s5).
The MIT license does not relicense this text or remove these conditions. Commercial
users can use the MIT code and their own permitted data instead of these samples.

## Optional local inputs

Set `VERDICT_DATASET_DIR` to a private folder outside the repository containing
`classification.jsonl` and/or `moderation.jsonl` only when you have the necessary
rights for your intended use. This setting does not download data or grant
permission. Missing inputs produce an actionable error before provider calls.
Moderation samples can contain offensive and hateful evaluation inputs.

The builder defaults to the two bundled suites. Explicit local-only builds require
`--suite classification` or `--suite moderation`, and `--local-out` outside the
repository. Review source terms first. Do not publish private files or history
backups. Replacement inputs require new evidence; do not present old results as
measurements of replacement data. Historical records retain labels and metrics,
not the removed raw source text.

TweetEval reference: Francesco Barbieri, Jose Camacho-Collados, Luis Espinosa-Anke,
and Leonardo Neves, *TweetEval: Unified Benchmark and Comparative Evaluation for
Tweet Classification*, Findings of EMNLP, 2020. Consult its source card for the
original subset publications and permission requirements.

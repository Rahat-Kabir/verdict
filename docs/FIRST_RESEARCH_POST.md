# Comparing four decision APIs on BANKING77: my first experiment

I finished a small experiment in Verdict: 154 banking requests, 77 possible intents, and 616 attempts across four decision APIs.

I wanted to understand how OpenAI Decisions, Jev Direct, Clef, and Clef Flash compare when they receive the same task and the same allowed answers. I measured accuracy, failures, latency, and cost.

## Why I started Verdict

Many steps in an AI workflow involve choosing from a fixed list. Classify a request, choose a route, or decide which action should happen next.

That is the part I have been exploring. You give a decision API context and the possible answers, and your code receives a typed choice. I wanted to test these APIs on labeled examples before deciding how I would use them in a developer tool.

Verdict is the Python evaluation project I am building for this research. It also has a local playground and a static results page. For now, my focus is on running experiments and keeping the evidence clear enough to review.

## What I tested

I used BANKING77, a dataset of customer banking requests with 77 intent labels. Its official test split contains 3,080 messages, with 40 messages per intent.

I selected two messages from every intent using a fixed random seed, then shuffled the sample before making calls. That gave me 154 messages. Each API attempted each message once, for 616 attempts in total.

Every request still included all 77 possible answers. The model had to choose among the full set, even though each intent had only two examples in the sample.

I used the same label definitions, developed from training examples, for all four APIs. I kept those definitions unchanged during the experiment. OpenAI used its native Decisions endpoint. Jev, Clef, and Clef Flash used OpenRouter's Decisions API, with Cloudflare pinned for Clef and Flash and provider fallbacks disabled.

There was an earlier run before this balanced sample. I had started evaluating the full test split, then stopped after 964 attempts. Those attempts covered 241 messages, but only seven intents because the source rows were grouped by intent.

That made the coverage problem clear. For a small experiment, I needed to sample across every intent. I kept the earlier results separate and froze this new sample before calling the APIs. Twelve selected messages had been attempted before; I made new calls for them and did not reuse the earlier outputs.

## The results

Accuracy below includes failed decisions as incorrect. A valid answer with the wrong label counts against accuracy, but I do not count it as a response failure.

| API | Correct / attempted | Accuracy | Failures | Median latency | Cost for the sample |
| --- | --- | --- | --- | --- | --- |
| OpenAI Decisions | 122 / 154 | 79.22% | 1 | 538 ms | $0.038147 estimated |
| Jev Direct | 127 / 154 | 82.47% | 0 | 762 ms | $0.020979 reported |
| Clef via OpenRouter | 146 / 154 | 94.81% | 0 | 1,432 ms | $0.125347 reported |
| Clef Flash via OpenRouter | 145 / 154 | 94.16% | 2 | 831 ms | $0.046395 known subtotal; total unknown |

Clef and Clef Flash had the highest observed accuracy on this sample. They differed by one correct answer, which is too small a gap to call one the better API.

OpenAI had the lowest median latency in this run. Jev had the lowest provider-reported charge. OpenAI's cost is a published input-token estimate, so these cost figures use different billing bases and are not verified invoice totals.

The latency numbers cover valid responses. They include network and gateway overhead from my machine in Bangladesh. I ran calls sequentially, with at least three seconds between call starts to reduce rate-limit failures. That waiting time is excluded from the latency measurements.

## What failed during collection

OpenAI returned one typed refusal. Clef Flash had a connection reset and a temporary-capacity HTTP 429 rejection.

I kept both Flash failures in the results. After checking the saved evidence, I continued with only the unattempted pairs. I did not retry either failed pair to get a replacement answer.

Neither Flash failure returned billing information, so Flash's total cost remains unknown. The known subtotal covers 152 of its 154 attempts. Across the four APIs, the combined known charges and estimates were about $0.231, with those two costs unresolved.

After collection, I checked all 616 saved attempts offline against the selected dataset rows and frozen requests, reparsing the captured API replies where available. Every API had attempted the same 154 messages, with two messages from each intent. There were no unfinished calls.

## What I can say from this experiment

This gives me initial evidence about how these APIs performed on a balanced sample of banking requests. It also shows the different tradeoffs in the results: accuracy, response time, failures, and cost do not all favor the same API.

Two examples per intent are still very few. I would not choose an API for a specific banking intent from these counts alone. I also ran the experiment once, so I have not measured how stable the latency and accuracy results are across repeated runs.

The sample design followed the earlier experiment, and 12 messages overlap earlier attempts. That history matters when describing the results. This is an exploratory study covering all 77 intents, rather than an evaluation of every message in the official test split.

I have saved the results and limitations in Verdict's research report and added them to the frontend. My next research step would be another domain or a repeated experiment, so I can check whether the findings hold beyond this sample.

---

Experiment date: October 8, 2026.

BANKING77 source: Iñigo Casanueva, Tadas Temčinas, Daniela Gerz, Matthew Henderson, and Ivan Vulić, *Efficient Intent Detection with Dual Sentence Encoders* (2020). Dataset license: CC-BY-4.0. The experiment used the [pinned authors' dataset revision](https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data).

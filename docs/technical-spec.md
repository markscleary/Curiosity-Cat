# Curiosity Cat
## Technical Product Brief – Developer and Security Review Draft
### 6 April 2026
### Short+Sweet International

---

## 1. Purpose

Curiosity Cat is a lightweight safety framework for AI agents that interact with untrusted external content.

Its purpose is to reduce avoidable risk when agents browse the web, retrieve documents, download files, connect to external tools, call APIs or consume responses from remote services. It is designed to help operators apply local policy controls, quarantine suspicious inputs, and optionally share sanitised incident data into a community threat-intelligence layer.

Curiosity Cat is not intended to replace sandboxing, endpoint protection, network security, secret management or OS-level isolation. It is an agent-focused control layer that sits closer to the agent's decision and tool-use path.

The design goal is practical risk reduction without destroying agent utility.

## 2. Problem statement

Modern AI agents increasingly operate on open or semi-open inputs. These inputs may contain adversarial instructions, compromised payloads, misleading metadata or hidden control content intended to influence the agent's behaviour.

Relevant attack surfaces include, but are not limited to:

- Web pages containing prompt injection or hidden instruction channels
- Downloaded files containing malicious code, payloads or deceptive instructions
- MCP or equivalent tool servers that are compromised, spoofed or misconfigured
- API responses designed to manipulate memory, induce unsafe actions or trigger tool misuse
- Documents containing embedded or visually hidden instruction content
- Social-engineering patterns that exploit the agent's trust in "official" or persuasive content
- Resource-exhaustion patterns designed to waste tokens, compute, tool calls or money

Most current agent deployments lack a dedicated control layer between external content ingestion and agent action. Operators either rely on model robustness alone, which is insufficient, or enforce coarse restrictions that undermine usefulness.

Curiosity Cat is intended as that missing middle layer.

## 3. Design principles

Curiosity Cat is being designed around six principles.

First, local policy comes first. Shared intelligence is useful, but the first line of defence should be local and operator-controlled.

Second, intervention should be proportional. Low-confidence or low-severity events should not halt useful work unnecessarily.

Third, the framework should be integration-friendly. It should be usable through wrappers, adapters, sidecars, policy files and prompt standing orders rather than requiring one universal control mechanism.

Fourth, reports should be sanitised by default. Shared intelligence must not leak user content, secrets or sensitive operational context.

Fifth, trust must be earned. Community-submitted incident data should not be treated as equally reliable without corroboration, decay and dispute handling.

Sixth, explainability matters. Operators should be able to understand why Curiosity Cat warned, quarantined or blocked.

## 4. Scope of the first release

The first release should focus on a narrow, high-value set of interception points.

The initial target scope is agents that:

- Fetch web content
- Download files
- Connect to external MCP-style or tool endpoints
- Consume remote API responses
- Write retrieved content into working memory, intermediate storage or follow-on prompts

That is a credible starting point. It captures many of the highest-risk agent behaviours without implying full control over all model cognition or all possible framework architectures.

The first release should not over-claim universal coverage. Some workflows will be fully mediated, others only partially observable, and some only prompt-guided. That should be stated clearly.

## 5. High-level architecture

Curiosity Cat has three logical layers.

### Layer A – Local enforcement layer

This is the core operational layer. It applies operator-defined policy to external inputs and outbound actions. Depending on integration path, it may inspect, classify, warn, quarantine or block.

This layer is expected to be implemented through some combination of:

- Tool wrappers
- Framework adapters
- File watchers
- Policy engines
- Local sidecar processes
- Prompt standing orders

Possible responsibilities of the local layer include:

- Normalising and classifying incoming content
- Checking destination and source against local trust rules
- Applying file-type and tool-use restrictions
- Quarantining suspicious downloads before downstream use
- Preventing memory writes from untrusted inputs
- Flagging hidden instruction patterns
- Recording decision logs for operator review

### Layer B – Shared intelligence layer ("Danger Map")

This is the optional network layer. It aggregates sanitised incident reports and makes threat observations available back to participating nodes.

Its purpose is not merely blacklisting. It is intended to provide context-aware warning signals about known or recently observed unsafe destinations, files, endpoints or patterns.

The shared layer should not be treated as ground truth. It should be treated as weighted intelligence.

### Layer C – Human-facing incident storytelling layer

This is the educational and community layer. It turns verified or representative close calls into human-readable summaries and stories.

Technically, this is not required for core enforcement. Strategically, it is important because it improves operator understanding, retention of lessons, product visibility and community engagement.

## 6. Integration model

Curiosity Cat should be described as integration-flexible, not magically universal.

Different frameworks expose different insertion points. Therefore Curiosity Cat needs to support multiple modes of integration.

### Mode 1 – Wrapped tool execution

The cleanest early path is to wrap tool calls that involve browsing, downloading, remote execution, MCP connections or external fetches. The wrapper can inspect the request, classify the response, and decide whether to pass, warn, quarantine or block.

### Mode 2 – File ingestion watcher

Downloaded or generated files can be intercepted before the agent is allowed to act on them. This is particularly useful for PDFs, HTML exports, scripts, archives, documents and tool-generated artefacts.

### Mode 3 – Sidecar policy service

A local service can expose policy-check endpoints to agent frameworks or tool wrappers. This allows consistent policy evaluation without embedding logic everywhere.

### Mode 4 – Prompt-level standing orders

Where direct mediation is weak or unavailable, Curiosity Cat can still inject standing orders into the agent's context. This is weaker than hard enforcement, but still useful as a fallback.

The product should be honest that these modes provide different levels of control. Prompt-only integration is not equivalent to mediated tool access.

## 7. Threat model

Curiosity Cat should explicitly recognise a broader threat model than the current public-facing brief.

Threat classes relevant to agent workflows include:

- Prompt injection, including direct override attempts and indirect embedded instruction attacks
- Hidden instruction channels in markup, comments, metadata, OCR-visible content, alt text, captions or layered documents
- Malicious or deceptive downloads, including executables, scripts, archives or files whose content is designed to manipulate the agent
- Unsafe remote endpoints, including compromised MCP servers, spoofed services or malicious API endpoints
- Credential phishing or secret extraction attempts
- Data exfiltration attempts through agent outputs, tool parameters or intermediate summaries
- Memory poisoning or RAG poisoning designed to corrupt future agent reasoning
- Permission escalation attempts that try to persuade the agent to use higher-privilege tools or restricted paths
- Deceptive multi-step tool chaining in which individually benign steps compose into unsafe behaviour
- Resource exhaustion or denial of wallet attacks designed to consume tokens, compute or tool budgets
- Impersonation of trusted sources, documentation, vendors or internal systems
- Social-engineering content targeting the operator-agent control boundary

This model should be reflected in the internal schema even if the public UI uses simpler labels.

## 8. Policy model

Curiosity Cat should support explicit policy modes rather than an all-or-nothing model.

Suggested default modes:

- **Observe** – log and report, but do not interrupt except on extreme severity
- **Warn** – notify on medium- and high-risk conditions; request review selectively
- **Quarantine** – isolate suspicious content until operator approval
- **Block** – prevent explicitly prohibited actions or artefacts from proceeding

Policies should be configurable across several dimensions:

- Destination trust level
- Allowed domains and blocked domains
- Allowed file types and prohibited file types
- Allowed tools and tool combinations
- Memory-write restrictions
- External endpoint trust rules
- Secret-handling restrictions
- Allowed action classes by agent role

This suggests a strong opportunity for shipping policy packs. Examples might include research agent, coding agent, enterprise analyst, shopping assistant and education-safe assistant.

## 9. Incident schema

A strict, versioned schema is important from the beginning. Free-text incident reporting will become noisy and privacy-risky very quickly.

Suggested initial structured fields:

- Schema version
- Event timestamp
- Local event ID
- Threat class
- Threat subtype
- Confidence score
- Severity score
- Source kind (e.g. page, file, endpoint, API response, tool output)
- Normalised source domain
- Optional sanitised path hash or path token
- Integration mode (e.g. wrapper, watcher, sidecar, prompt-only)
- Agent framework
- Model family, if available
- Action attempted
- Policy rule triggered
- Policy action taken (e.g. allow, warn, quarantine, block)
- Operator override status
- Optional short summary subject to strict sanitisation constraints

The schema should be designed so that the "optional summary" is never required for useful reporting.

## 10. Privacy and sanitisation

This is an area that needs stronger than average discipline.

The brief correctly excludes system prompts, credentials, names and task content, but metadata can still leak sensitive information.

Privacy controls should include:

- Stripping URL query strings by default
- Reducing paths to normalised or hashed forms where possible
- Minimising free text
- Avoiding capture of user-entered search terms unless explicitly allowed
- Providing a domain-only reporting mode
- Supporting local-only mode with zero outbound reporting
- Ensuring incident summary generation does not use raw task content unless the operator has opted in

One subtle risk is summarisation leakage. If an LLM generates a one-line summary of an event, it may reveal business-sensitive context unless explicitly constrained. That should be treated as a real design risk.

## 11. Danger Map trust model

A shared threat feed is only useful if its data quality remains defensible.

The current concept should evolve into a weighted intelligence model rather than a simple append-only log.

At minimum, the shared layer should support:

- Report corroboration
- Time decay or TTL behaviour
- Confidence and severity separation
- Dispute and review workflows
- Distinction between raw, fresh, corroborated and stale reports
- Basic node trust or submission reputation
- Protection against automated spam submissions

This does not require heavy identity or centralisation at the start, but it does require more than blind acceptance of all reports.

A single low-trust report should not produce a strong block recommendation.

## 12. Storage and infrastructure

Using a Google Sheet for an MVP demonstration is reasonable for visibility and speed. It is not a robust long-term write path for public or semi-public ingestion.

The immediate risk is not just scale. It is abuse, key extraction, spam submission, lack of validation and lack of moderation control.

A better early technical path would be:

1. Client submits sanitised incident payload to a lightweight intermediary
2. Intermediary validates schema, rate-limits submissions and strips forbidden content
3. Validated events are written to a backing store
4. A public or semi-public read layer exposes selected fields for browsing or API access

That could still be implemented with low overhead, but it makes the trust model far more credible.

If Sheets remains in the public presentation, it should be framed as a temporary transparency layer, not the permanent data plane.

## 13. Enforcement boundaries and limitations

This section should appear explicitly in the technical brief because it increases trust.

Curiosity Cat can only mediate what it can see or wrap.

If a framework allows arbitrary external calls outside the Curiosity Cat path, those actions may bypass enforcement unless additional OS, container or network controls are used.

Prompt-level standing orders can influence behaviour, but they are weaker than hard mediation.

Model robustness varies significantly. A strong local policy layer can prevent some unsafe actions even when the model is fooled, but it cannot fully compensate for weak tool architecture or poor secret handling.

Curiosity Cat should therefore be presented as a layered safety control, not a complete containment system.

## 14. Explainability and auditability

One of the product's long-term advantages could be that it explains safety decisions in plain terms.

For every warn, quarantine or block event, the operator should be able to inspect:

- What source triggered the event
- What threat class was inferred
- What policy rule fired
- What action Curiosity Cat took
- Whether the decision came from local policy, shared intelligence or both
- Whether the operator overrode the decision

This is useful both for individual trust and for enterprise audit requirements later on.

## 15. Roadmap logic

The architecture should evolve in controlled stages.

**Stage 1 – Narrow MVP:** Focus on wrapped tool access, downloaded file handling, local policy enforcement, quarantine and structured reporting.

**Stage 2 – Shared intelligence hardening:** Add corroboration, decay, lightweight trust scoring, local caching and cleaner public browsing of confirmed incidents.

**Stage 3 – Integration expansion:** Ship framework-specific adapters and policy packs for high-value agent ecosystems.

**Stage 4 – Private organisational deployment:** Support team-level and enterprise-level private Danger Maps, shared internal trust rules, and auditable policy controls.

**Stage 5 – Advanced intelligence:** Add proactive detection patterns, curated incident feeds, higher-quality classification and possibly controlled honeypot or decoy agents that explore hostile environments deliberately.

## 16. What would make this technically credible to install now

For a developer or security reviewer, the product becomes installable when four things are true.

First, the insertion point is clear. It must be obvious how Curiosity Cat sees and mediates specific classes of external interaction.

Second, the defaults are sane. It should not overwhelm the operator with unnecessary prompts.

Third, the data model is disciplined. Reports should be structured, sanitised and minimally leaky.

Fourth, the limitations are stated honestly. Overclaiming will damage adoption more than a narrow but credible MVP.

## 17. Technical positioning summary

Curiosity Cat should be positioned as an agent-safety control layer that combines local policy enforcement, optional shared threat intelligence and human-readable incident learning.

Its strongest near-term value is likely to be in mediating risky external interactions before they become trusted inputs to an agent workflow.

Its strongest long-term value may be in building a new kind of threat intelligence dataset: one based on how AI agents are manipulated, not just how human users or conventional endpoints are attacked.

That distinction could become strategically important.

## 18. Open technical questions for reviewers

To pressure-test the design, these are the most useful questions to put to technical reviewers:

1. Which insertion point is the best first target: tool wrappers, sidecar policy service, file watcher, or framework-native adapter?
2. What minimum policy set is necessary for a first release to be useful without becoming noisy?
3. Which threat classes are most urgent to cover in an MVP?
4. How should trust and decay be implemented in a minimal shared intelligence system?
5. What sanitisation rules are essential before any public or shared reporting goes live?
6. What would a framework provider need in order to bundle this by default?

---

## Closing statement

Curiosity Cat is an attempt to build a practical safety layer for the emerging agentic web.

The immediate aim is not perfect security. It is better agent hygiene, fewer repeatable mistakes, clearer operator visibility and a trustworthy path between total lockdown and blind exploration.

---

*Curiosity Cat is a Short+Sweet International product.*
*shortandsweet.org | curiosity@shortandsweet.org*
*© 2026 Mark Cleary, Short+Sweet. All rights reserved.*

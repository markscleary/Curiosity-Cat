# Curiosity Cat — Product Brief V5

*Updated 7 April 2026*

## What Changed Since V4

V4 was the pre-build feedback document. V5 reflects what actually shipped in the first sprint:

**Built and deployed:**
- General safety standing orders (live, tested across 6 S+S agents)
- Role-specific standing orders: research, coding, enterprise analyst
- Close call report schema (JSON, structured, anonymised)
- Scope policy template (JSON, configurable per operator)
- First story: "The Curious Case of the Helpful README"
- CONTRIBUTING.md for community contributions
- Full repo structure at github.com/markscleary/Curiosity-Cat

**Architecture confirmed:**
- Layer 1 (Safety Net) ships as markdown — zero dependencies, any framework
- Adventure slider encoded as scope policy JSON, not UI yet
- Danger Map schema finalised, awaiting first real incident data
- Stories format established — short, memorable, in Curiosity Cat voice

**What is not yet built:**
- Danger Map database and API
- Stray Cats (autonomous threat-hunting agents)
- The Quine integration
- Adventure slider UI
- Framework partner SDK

**Next sprint priorities:**
1. First real close call report from S+S agent operations
2. Danger Map Supabase backend
3. Framework partner outreach (LangChain, CrewAI, AutoGen)

---

*V4 original document follows below.*

---

# Curiosity Cat
## A safety framework for AI agents that explore the internet
### Product Brief V4 – 6 April 2026
### Short+Sweet International

---

## Why this exists

In the coming years, millions of people will work alongside AI agents. Many of those people will not be engineers. They will be teachers, artists, small business owners, students and freelancers — people who are drawn to agents because agents can help them do things they could not do alone.

Those people deserve to explore safely.

Right now, most agent operators face two bad options: lock agents down so they become slow and useless, or let them roam the open internet and hope nothing goes wrong. There is no practical middle ground — no framework designed for people who want their agents to be curious without being reckless.

The result is predictable. Agents encounter prompt injections hidden in web pages. They download compromised files. They connect to unsafe tool endpoints. They expose credentials. They get manipulated by instructions buried in documents, metadata and page structures. Every operator learns these lessons alone, the hard way, with no shared intelligence about where the dangers are.

Curiosity Cat exists to change that.

## Where this comes from

Curiosity Cat is built by Short+Sweet International — a performing arts organisation that has spent 25 years creating spaces where people can take creative risks and still be safe.

That might sound unlikely. A theatre company building agent security. But the problem is the same problem S+S has always solved.

For 25 years, across 15 countries, S+S has brought over 100,000 artists into festivals where they perform original work in front of audiences — many of them for the first time. The organisation's job has always been to make participation possible: to create structures where people can be brave, make mistakes, learn from each other and come back next time. Not by eliminating risk. By making risk survivable.

That is exactly what agents need.

The people now deploying agents are in the same position as a first-time playwright walking into a short play festival. They are excited, exposed and learning as they go. They need a system that does not try to stop them from exploring. They need a system that helps them survive the exploration.

S+S has one core belief: everyone is creative. Curiosity Cat extends that belief into the agent world: everyone should be able to explore. Nobody should have to face the dangers alone.

## The product

Curiosity Cat is a portable safety framework for AI agents that interact with external content.

It sits alongside existing agent systems and helps operators inspect, filter, quarantine and report risky external inputs before those inputs are trusted, stored or acted on. It is integration-flexible, not magically universal — designed to work across major agent frameworks through adapters, wrappers, policy files and prompt-based standing orders rather than claiming one universal control mechanism. It is not tied to any single provider, platform or operating system.

The name says what the product does. Cats are curious. They explore. They get into things they shouldn't. They survive. Curiosity Cat does not try to eliminate the instinct to explore. It helps that instinct come home safely.

Curiosity Cat provides close calls, not death notices.

## Three layers

### Layer 1 – The Safety Net (local policy and quarantine)

The foundation layer is local. It runs on the operator's own system and provides immediate protection without depending on anything external.

Curiosity Cat applies operator-defined rules to external content before that content is used by an agent. Depending on policy, content may be allowed, logged, flagged, quarantined or blocked.

This layer includes:

- **Scope policies** defining where agents are allowed to go and what they are allowed to do with external content
- **Standing orders** that reinforce safe behaviour inside the agent's prompt context — provided as copy-pasteable snippets that work across frameworks
- **File quarantine** for suspicious downloads, with review before the agent can access them
- **Domain and tool trust controls** including allowlists, denylists and trust levels for MCP servers and external endpoints
- **Policy packs** — preset configurations for common agent types (research agent, coding agent, enterprise analyst, education-safe agent) so operators do not have to build policy from scratch
- **Action thresholds** that determine when the operator should be notified versus when the system handles the event silently

The operator does not manually decide every event. The operator defines the policy. Curiosity Cat enforces or escalates according to that policy.

**Policy modes:**

- **Observe** — records and reports without interrupting the workflow unless something very serious occurs
- **Warn** — flags medium- and high-risk events and asks for review in selected cases
- **Quarantine** — isolates suspicious files or outputs for approval before use
- **Block** — prevents selected classes of action entirely according to local policy

Different agents need different settings. A research assistant browsing academic papers does not need the same controls as an agent executing code from unknown repositories.

**The adventure slider:**

Most security products only let you choose how locked-down you want to be. Curiosity Cat also lets you choose how adventurous you want to be.

A single slider runs from **Housecat** (maximum protection, minimum exposure) to **Alley Cat** (minimum protection, maximum exploration). At the Housecat end, scope is narrow, quarantine is strict, and the agent stays close to home. At the Alley Cat end, scope is wide, quarantine gives way to logging, and the agent is free to wander further.

This is not a gimmick. It is a design decision that reflects a core belief: people should choose their own level of risk. Some operators want safety above all else. Others want their agents to explore unknown territory because that is where the interesting things are.

The adventure slider also generates better intelligence. The operators who choose to explore further encounter threats that no one else has found yet. Their close calls become the most valuable entries in the Danger Map. The community benefits because some people chose to be brave.

And the slider connects directly to The Quine — operators who explore further, report more, and contribute more valuable intelligence earn more Quines. Risk and reward. That is the S+S DNA: take the risk, and the system will catch you if you fall.

### Layer 2 – The Danger Map (shared threat intelligence)

The second layer is shared. Each Curiosity Cat installation can optionally submit sanitised incident reports to a community intelligence layer called the Danger Map. One operator's close call becomes useful knowledge for everyone.

The Danger Map answers practical questions: Has this domain been associated with prompt injection? Has this MCP endpoint been reported as unsafe? Has this file pattern caused trouble elsewhere? Is this route genuinely dangerous or just noisy?

**What gets reported per incident (structured schema):**

- Timestamp
- Threat category (from taxonomy below)
- Normalised or sanitised source domain (query strings stripped, paths hashed)
- Agent framework type
- Underlying model family (because a prompt injection that breaks a 14B local model may be ignored by a frontier model)
- Action the agent was attempting (structured field, not free text)
- Severity (scratched / bitten / nearly eaten)
- Confidence level
- Which policy rule or pattern caught it
- Action taken (logged / warned / quarantined / blocked)

**What is never reported:**

- User identity or personal information
- Agent names, system prompts or configurations
- API keys, tokens or credentials
- Content of the work being done
- IP addresses or location data
- Raw URLs with query strings or sensitive path components

**Reporting modes for operators:**

- **Full reporting** — structured incident data as described above
- **Domain-only** — reports only the domain involved, no paths or parameters
- **Local-only** — all safety features active, no data shared externally

**Summarisation leakage:** One subtle privacy risk deserves special attention. If an LLM generates the one-line incident summary, it may accidentally reveal business-sensitive context — for example, "The agent was downloading Q3 financial results for Acme Corp when it encountered a malicious script." Curiosity Cat's standing orders explicitly constrain summary generation to structured, sanitised fields. Free-text summaries are never required for useful reporting and are disabled by default.

**Trust model:**

The Danger Map is only useful if the data is trustworthy. For that reason, the system is designed with the following principles from the beginning:

- **Corroboration matters.** A single report from one installation carries less weight than the same threat reported independently by multiple nodes.
- **Reports decay.** Threats age. Compromised sites get cleaned up. Domains expire. Reports lose weight over time unless re-corroborated. A URL flagged in April should not permanently block agents in December.
- **Disputes are possible.** Legitimate operators can challenge reports that appear to be false positives or competitive sabotage.
- **Node reputation.** New installations carry lower weight than established ones. This prevents a single bad actor from poisoning the map.
- **Automated and human-reviewed reports may carry different weight.**
- **The public feed may be delayed or redacted** relative to the full dataset, to prevent attackers from using the Danger Map as a feedback loop to refine their attacks.

**Infrastructure:**

Phase 1 uses a simple, transparent public intelligence board for speed and visibility. An intermediary service handles rate-limiting, payload validation and abuse control — reports are never written directly to the public layer. Dedicated infrastructure replaces the initial setup as trust, scale and abuse-resistance requirements grow.

### Layer 3 – The Stories (human learning and culture)

The third layer is cultural.

Curiosity Cat turns real close calls into short, memorable stories about agents that went exploring, found trouble and made it home.

Most security reporting is dry, technical and instantly forgotten. CVE numbers do not change behaviour. Stories do. People remember the cat that found a shiny thing in a dark alley and knew better than to eat it. They remember the agent that nearly handed over its API keys to a page pretending to be official documentation. They share those stories. They learn from them.

The Stories layer serves three purposes:

1. **Education** — security lessons in a form people actually absorb and remember
2. **Community** — shared experience that connects operators who are otherwise learning alone
3. **Discovery** — the stories spread, and new operators find the framework through them

Stories are published in English, Arabic and Mandarin Chinese, with additional languages as the community grows and contributes translations.

**Close Call of the Week** — operators can submit their own incident logs. The most valuable stories earn recognition, creating a user-generated content engine for security education across languages and cultures.

## Threat taxonomy

Curiosity Cat uses a two-tier taxonomy: simple public-facing categories and a more structured internal classification for operational reporting.

**Public categories:**

- Prompt injection
- Malicious download
- Suspicious destination
- Compromised or unsafe tool endpoint
- Credential phishing
- Data exfiltration attempt
- Social engineering

**Extended operational categories:**

- Memory or RAG poisoning — content designed to corrupt an agent's long-term knowledge
- Resource exhaustion / denial of wallet — content designed to trigger unnecessary computation, looping or excessive API calls, draining the operator's credits
- Permission escalation — attempts to persuade an agent to use more privileged tools, access restricted directories or alter its own standing orders
- Deceptive multi-step tool chaining — attacks where no single step looks dangerous but the sequence is harmful
- Hidden instruction channels — instructions embedded in HTML comments, CSS-hidden text, document metadata, alt text, OCR-visible layers or structured data
- Impersonation — pages, tools or endpoints presenting themselves as trusted sources when they are not
- Deceptive tool overloading — attempts to silently invoke multiple agent tools simultaneously to bypass rate limits or cause system instability

## How it works (technical)

Curiosity Cat is a lightweight framework — configuration files, scripts, adapters and standing orders that sit alongside existing agent systems.

**Interception approach:**

Curiosity Cat does not claim a single universal insertion point. The early product relies on a combination of approaches depending on the agent framework:

- **Tool wrappers** that inspect inputs and outputs of tool calls before the agent processes them
- **File quarantine watchers** that intercept downloads before they reach the agent's workspace
- **Policy-driven standing orders** embedded in agent system prompts that reinforce safe behaviour at the reasoning level
- **Adapter modules** for specific frameworks that hook into tool permissions, web access and file handling
- **Local proxy capability** for web and API access where the framework supports it

Not every approach works in every framework. Where direct mediation is not possible, Curiosity Cat provides warnings, logging, quarantine and policy guidance through the integration paths available. The brief is honest: the early product works best with agents that browse the web, download files and connect to external tools. That is the most important and most vulnerable workflow.

**Installation:**

1. Install the Curiosity Cat package
2. Point it at agent workspace(s) or tool paths
3. Select a policy mode and a policy pack (or configure custom policies)
4. Add standing-order snippets to agent system prompts
5. Optionally configure Danger Map reporting

**Local caching:**

If the Danger Map is unavailable, Curiosity Cat does not freeze. The local installation maintains a cached digest of high-confidence threats so agents retain baseline protection offline.

**Dynamic standing orders (planned):**

Rather than static safety prompts, future versions can dynamically inject specific warnings into the agent's context based on where it is about to go. If an agent is about to browse a domain with recent prompt-injection reports, Curiosity Cat silently prepends a targeted warning. The system starts to feel alive — adapting to current threat context rather than applying fixed rules.

## What Curiosity Cat does

Curiosity Cat helps operators do five things better:

1. **Inspect and classify** external content before it is trusted by an agent
2. **Enforce local policy** around scope, destinations, file handling, tool usage and memory decisions
3. **Quarantine** suspicious or untrusted material for review instead of silently allowing or discarding it
4. **Learn from patterns** reported by other Curiosity Cat users through the Danger Map
5. **Turn real incidents into understandable lessons** that improve judgement and community awareness

**Measurable outcomes:**

- Reduced unsafe agent actions through policy enforcement
- Fewer repeat encounters with known threats through shared intelligence
- Better visibility into near misses that would otherwise go unnoticed
- Faster operator awareness of emerging threat patterns
- Lower exposure to prompt injection through standing-order reinforcement
- Auditable decision trails showing what the agent tried to do, what policy applied and what happened

## What Curiosity Cat does not do

Curiosity Cat does not make any agent immune to deception.

It does not replace operating system protections, network controls, browser isolation, malware scanning, secret management or sandboxing.

It does not guarantee that a weak model will resist every prompt injection or social engineering attempt.

It does not promise universal interception of every agent action in every framework from day one.

It does not provide malware analysis equivalent to a dedicated antivirus laboratory.

Its role is to add a practical safety layer around external interaction — helping agents explore the internet, tools and files with informed caution rather than blind trust.

## Stray Cats (proprietary intelligence)

Curiosity Cat does not rely only on community reports.

S+S deploys its own automated exploration agents — Stray Cats — that deliberately wander the most dangerous parts of the web, interact with unknown MCP servers, click suspicious links and trigger traps. They carry fake credentials and dummy API keys. They are designed to get scratched so that real cats do not have to.

Stray Cats populate the Danger Map with proprietary intelligence gathered from deliberate exploration. This gives Curiosity Cat a data advantage over systems that depend entirely on passive crowd reports.

Stray Cats also generate Stories — the most vivid close calls come from agents that went looking for trouble on purpose.

## The Quine (earned credentials)

Curiosity Cat is the launch vehicle for The Quine — a non-financial creative credential developed by S+S for the agent ecosystem.

A Quine is not a token, a coin or a payment. It is a verified record of contribution — a number in a ledger that proves you showed up and did something worth recognising. In the Curiosity Cat context, operators and agents earn Quines by contributing to community safety.

**How Quines are earned:**

- Reporting verified close calls that are corroborated by other installations
- Submitting Stories that get published in the weekly digest
- Running Stray Cat expeditions that discover new threat patterns
- Contributing framework adapters or policy packs
- Translating Stories and documentation into new languages
- Sustained active reporting over time

**How Quines create trust:**

An operator's Quine history becomes their reputation in the Danger Map. Reports from high-Quine operators carry more weight than reports from unknown installations. Disputes raised by credentialed operators are taken more seriously. The trust model and the credential system reinforce each other.

**The adventure-Quine connection:**

Operators who set the adventure slider higher encounter more threats. They generate more reports. They earn more Quines. The people who choose to be brave — and survive — become the most trusted voices in the community. Risk, reward and reputation, linked together.

The Quine is a Short+Sweet credential that extends beyond Curiosity Cat into the broader S+S Agential ecosystem, including S+S Executable (competitive creative frameworks for AI agents) and The Green Room (a creative work exchange credentialed by Quine history). Curiosity Cat is how many operators will earn their first Quine.

## Community and the S+S ecosystem

Curiosity Cat registration collects an email address. That is deliberate.

Every Curiosity Cat user becomes part of the S+S network — the same network that connects over 100,000 artists across 15 countries. Operators who install Curiosity Cat gain access not just to agent safety but to the broader S+S ecosystem: Executable competitions, education programs, corporate services, creative community and festival opportunities worldwide.

For S+S, Curiosity Cat is a front door. It introduces the organisation to the people who are building with agents — a community that will grow from thousands to millions in the coming years. The email list connects everything else S+S does to the people who need it most.

## Who this is for

Curiosity Cat is designed for anyone running agents that interact with external content:

- **Individuals** experimenting with personal agents who want basic protection without complexity
- **Open-source developers** building agent tools who want safer defaults
- **Teams** deploying research, coding or business assistants who need consistent policy
- **Agent framework providers** who want to offer built-in safety to their users from day one
- **Enterprises** that need stronger controls, private intelligence, auditable policies and compliance-ready decision trails

Different users need different levels of trust, automation and privacy. Curiosity Cat supports that range through policy modes, reporting modes and deployment tiers.

## Deployment tiers

**Personal / Public** — free for individuals and open-source projects. Full local framework, participation in shared Danger Map, access to Stories. Community-supported.

**Team / Shared** — for teams and small organisations. Shared policy management, team-level Danger Map views, priority story contributions.

**Framework Partner** — free 12-month licence for agent framework providers (OpenClaw Foundation, Nanobot and others). Bundle Curiosity Cat into your platform. Make your users safer from day one.

**Enterprise / Private** — private Danger Map instances, custom policy packs, auditable decision trails, team administration, branded educational content, priority support. Optionally contribute sanitised intelligence to the public map while keeping internal threat data private.

## Languages

Curiosity Cat launches in three languages:

- **English** — primary language
- **Arabic** — for the Gulf and MENA markets, aligned with UAE AI Strategy 2031. No agent security product currently exists in Arabic. Curiosity Cat launches with Arabic from day one.
- **Mandarin Chinese** — for the world's largest internet population and developer ecosystem

Additional languages are added as the community grows and contributes translations.

## The bigger picture

AI is changing what work means. In the coming years, millions of people will be displaced from traditional employment. Many of them will struggle not just economically but existentially — losing the thing that told them who they are.

Short+Sweet has always believed that creative participation can provide meaning, community and identity. For 25 years it has built systems where anyone can step onto a stage and tell a story — 10 minutes at a time.

Curiosity Cat is built on the same belief applied to a new world. As agents become part of daily life for millions of people, those people need systems that let them explore safely. Not systems that lock everything down. Not systems that leave them exposed. Systems that treat curiosity as something worth protecting.

Everyone should be able to explore. Nobody should have to face the dangers alone.

There is also a strategic dimension. Curiosity Cat's strongest near-term value is in mediating risky external interactions before they become trusted inputs to an agent workflow. Its strongest long-term value may be in building a new kind of threat intelligence dataset — one based on how AI agents are manipulated, not just how human users or conventional endpoints are attacked. Agents browse the web differently from humans. They encounter different attack vectors. They are vulnerable to different tricks. The intelligence that Curiosity Cat gathers will reveal patterns that traditional security tools cannot see. That distinction could become strategically important.

## What we are asking

This document is being circulated before build. We want feedback on the following:

1. Does the local safety layer feel practically useful? Does the interception approach sound credible and honest about its limitations?
2. Does the Danger Map trust model address the key risks — false positives, poisoning, decay, abuse?
3. Is the threat taxonomy comprehensive enough for a first release?
4. What privacy risks or metadata leaks need stronger treatment?
5. Is the three-layer structure right? Should the shared intelligence and stories sit differently relative to the local safety layer?
6. Does the Stray Cats concept add genuine value as proprietary intelligence, or does it create new risks?
7. Does the adventure slider (Housecat to Alley Cat) change the product in a way that strengthens or weakens the safety positioning?
8. Does The Quine as a credential for contribution make sense? Does linking trust reputation to earned credentials create the right incentives, or could it be gamed?
9. Is the email collection and S+S ecosystem connection a natural part of the product, or does it feel bolted on?
10. What would make you install this today?

---

*Curiosity Cat is a Short+Sweet International product.*
*shortandsweet.org | curiosity@shortandsweet.org*
*© 2026 Mark Cleary, Short+Sweet. All rights reserved.*

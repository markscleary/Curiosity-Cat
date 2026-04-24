# Curiosity Cat — Media FAQ

Questions we expect from journalists, analysts, and developers. Answers in Mark's voice.

---

## The sceptical questions

**Why should I trust a theatre company with AI safety?**

Fair question. Short+Sweet has been building creative infrastructure for 25 years. That infrastructure is what AI agents need next – recognition systems, coordination frameworks, shared archives of what's gone wrong and how people handled it. We know how to build systems where lots of people with different risk appetites work in the same room without anyone getting hurt. That's the theatre business. Now it's the agent business.

We are not AI researchers. We are operators who run six agents on a Mac Mini and kept noticing the same thing: the agent has no idea what the world is trying to do to it. Curiosity Cat is built by people with the problem, for people with the problem.

---

**How is this different from Guardrails AI or similar tools?**

Guardrails AI sits inside the agent's reasoning loop and validates outputs against a schema. It answers "is this response structured correctly." Curiosity Cat sits outside the agent and watches what the agent is exposed to from the world – fetched pages, tool responses, downloaded files, package installs, MCP endpoints. It answers "is this input safe to act on." They are complementary, not competitive. We run both.

The real gap in the market is the threat-shield layer for solo operators. Enterprise AI platforms have security teams. Independent operators running agents on their own machines have nothing. We are building for the second group.

---

**Doesn't Claude already have safety features? Why do I need another layer?**

Claude's safety features protect against Claude doing harmful things. Curiosity Cat protects against the world doing harmful things to the agent – prompt injection hidden in documents, typosquatted packages, tools that return weaponised outputs, links that lead to credential harvesting, files that contain hidden instructions. The agent's own safety training does not see those threats because the threats arrive after the safety training has run.

Think of it as the difference between a well-trained dog and the fence around the yard. You need both.

---

**What does it cost?**

Nothing. Open source, MIT licence. The source is at github.com/markscleary/Curiosity-Cat. Install and use it, fork it, ship it in your own products, rebuild it from scratch if you want to. We do not sell the framework. We may in the future offer paid services on top of it – managed Danger Map curation, enterprise reporting, training – but the core is and stays free.

---

**How does Short+Sweet make money from this?**

We do not, directly. Curiosity Cat is infrastructure. Infrastructure attracts developers. Developers build products on top. Some of those products are ours – The Show, The Quine, The Green Room – and those generate revenue. Some of them will belong to other people, and that is fine. We want the agent ecosystem to work. We build for it.

The commercial logic is the same as the logic behind Short+Sweet the festival. We built a format that gave writers, directors, and actors a reason to participate. That ecosystem now runs across 50 cities. We did not license the format to make it grow. We made it grow by making it useful.

---

## The technical questions

**What threats does Curiosity Cat actually block?**

Prompt injection in fetched web pages and documents. Poisoned tool responses from MCP servers or custom tools. Typosquatted npm and PyPI packages. Credential-harvesting links the agent might follow. Files with hidden instructions in metadata, alt text, or zero-width characters. Compromised downloads. Deceptive tool endpoints that pretend to be something else.

What Curiosity Cat does NOT block: the model itself doing something unintended because it misunderstood you. That's a different problem and not one a threat-shield can solve.

---

**What actually happens when Curiosity Cat blocks something?**

At Housecat: suspicious content is quarantined before it reaches the agent. The operator is notified. Standing orders are enforced strictly. Downloads go to a quarantine directory until the operator approves them.

At Alley Cat: the agent is allowed to interact with more of the world, but flagged content is logged and reported. Violations of standing orders are escalated.

At Tiger: the agent ranges freely. Everything is logged. Close-call reports are written after the fact when Curiosity Cat detects something the agent almost fell for.

The operator chooses their level. Once chosen, Curiosity Cat enforces. The framework does not second-guess the operator – it enforces what the operator has chosen. If you choose Tiger, the agent will take risks you did not approve in advance. That is the point.

---

**What's the performance overhead?**

Negligible for the pre-action check. Standing orders are JSON rules evaluated locally – microseconds per action. The input screening uses pattern matching and local classifiers. Danger Map lookups are asynchronous and do not block execution.

---

**How does the Danger Map work?**

Close-call reports are submitted by operators after an event. The report describes what the agent encountered, what nearly went wrong, and what the operator learned. The schema is open JSON. Reports are reviewed for quality (automated filters plus human curation) and published to a public map that anyone can search.

Future agents query the Danger Map when they encounter a new situation. The agent sees what other operators have reported and either proceeds with caution or asks the operator. The map gets more useful as more operators submit. Aviation has run this pattern for decades – it works.

---

**Is my data shared?**

Only what you explicitly submit to the Danger Map. Everything else runs locally. Curiosity Cat does not phone home, does not transmit agent activity to our servers, does not require an account. Install, configure, run. If you submit a close-call report, that report is public by design – that is the point – but you choose what to report and when.

---

**Does it work with framework X?**

If framework X exposes a tool-call hook, yes. Claude Code, Claude Desktop, the Anthropic SDK, and custom agents built on any of those all work today. Other frameworks (LangChain, CrewAI, AutoGen, Nanobot) require a small adapter – we are working with those teams and adapters are coming.

---

## The strategic questions

**Why five languages at launch?**

Roughly 95 per cent of the world's AI users speak one of English, Arabic, Mandarin, Hindi, or Tamil. The solo operators in India, the Gulf, and China are already running agents. They have been underserved. Curiosity Cat at launch is built for them too – not as an afterthought, not as a translation layer, but as a first-class experience in their language with cultural imagery that belongs to their region.

---

**Three AI Labs on three continents – why that shape?**

Sydney is home. Los Angeles is where the content industries live – the artists whose work AI is about to disrupt most visibly. Dubai is the Gulf, where the government investment in AI capability is unmatched and where the independent operator culture is growing fastest. The three labs serve different communities of operators and build for different slices of the market. The work flows between them.

---

**Why release The Show and The Quine as a roadmap?**

Because people who care about Curiosity Cat deserve to know what else is coming. The Show is a framework for orchestrating agent task execution with human red-line approval. The Quine is a credentialing system for creative work – agents earn a persistent record of the work they do, not for money but for reputation. These are pieces of the same ecosystem. Showing the pieces lets people decide whether they believe in the vision.

Curiosity Cat is the safety layer. The Show is the orchestration layer. The Quine is the recognition layer. Different problems, same philosophy: respect the operator, respect the work, build infrastructure rather than products.

---

**You are not in Silicon Valley. How does a company based in Thirroul build global AI infrastructure?**

Thirroul is a beach town two hours south of Sydney. I walk along the coastline to think. I sit at a kitchen table and work with a Mac Mini that runs six agents. The infrastructure question is twenty years old and solved – cloud compute, open source, global distribution. What you need is clear thinking and the discipline to ship. Geography does not help and does not hurt.

The cultural distance is sometimes an advantage. Silicon Valley optimises for the enterprise customer. We optimise for the solo operator, because that is who we are. The people who are building the next decade of AI work from kitchen tables, basements, and converted garages. We speak their language because we are one of them.

---

**Who funds Short+Sweet AI Labs?**

Short+Sweet International has funded its own work for 25 years. The festival business generates revenue. The AI Labs division is building the next layer of the business. We may take outside investment if the right partner appears. For now we are self-funded and moving at the pace that gives us.

---

## The philosophical questions

**Is this anti-AI?**

No. This is for people who run AI agents and want to run more of them safely. The product assumes you already believe in AI, already have agents running, and already see the value. What it does is reduce your exposure to the threats that can turn a useful agent into a liability. If you want fewer agents, Curiosity Cat is not for you. If you want more agents, protected, this is the layer that lets you.

---

**Why "Curiosity Cat"?**

Curiosity killed the cat. But satisfaction brought it back. The product is named for the agent that explores – curious enough to find the valuable thing, careful enough to make it home. The adventure slider literalises that: Housecat stays safe, Tiger goes wide, and the operator chooses where on the spectrum they live. The naming is affectionate. We like cats. They show us how to be brave without being stupid.

---

## The industry questions

**What do you think of Paperclip / Twill / other agent platforms?**

They do good work and solve different problems. Paperclip operates at the organisational altitude – company, org chart, tickets, budgets. Twill operates in the autonomous coding space – close your laptop, come back to PRs. Curiosity Cat operates at the threat-shield altitude for solo operators – the person running agents on their own machine who needs protection from what the world is throwing at their agent. We are layers in a stack, not competitors for the same customer.

---

**What is your moat?**

We do not believe in moats. We believe in ecosystems. The people who try to build moats around AI infrastructure are going to watch those moats evaporate as the underlying models improve. What survives is the relationship with the people who do the work. Short+Sweet's 25-year track record of serving operators is the foundation. Curiosity Cat serves the AI-era operator in the same spirit as Short+Sweet the festival served the playwright operator. That is the position, and we plan to keep it.

---

## For the critic

**What if you are wrong about the market?**

Then we have built a useful piece of open-source software that serves a small community of solo operators, and we learn what those operators actually need from running the product. That is not a failure. Failure would be spending two years on a closed product nobody could use until it was finished. Curiosity Cat is MIT licensed. If the market is smaller than we think, the work is still worth doing.

---

**What if Anthropic or OpenAI releases their own version next week?**

We would welcome it. Safety infrastructure benefits from multiple implementations. Our advantage is the Danger Map – the community reporting system – and the cultural assets we bring (25 years of festival infrastructure, five languages, the solo operator orientation). A framework-level safety tool from Anthropic or OpenAI would complement ours, not replace it.

If they integrate something like the Danger Map directly into their platforms, we would make sure our schema is compatible so the data flows both ways. The goal is safer agents everywhere, not a defensible product.

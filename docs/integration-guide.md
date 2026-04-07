# Integration Guide

Curiosity Cat works with any agent framework. The minimum install is copying a standing order into your agent's system prompt. This guide covers framework-specific patterns.

## Universal (Any Framework)

Copy the contents of standing-orders/general-safety.md into your agent's system prompt or system message. Add a role-specific standing order if applicable (research-agent.md, coding-agent.md, enterprise-analyst.md). That is it. Your agent now operates under Curiosity Cat safety protocols.

## Claude Code

Add the general safety standing order to your CLAUDE.md file in the project root. Claude Code reads CLAUDE.md at session start and treats its contents as standing instructions. Place the standing order text under a clear heading. Role-specific orders can go in the same file.

## Nanobot / OpenClaw

Add the standing order to your agent's IDENTITY.md or SOUL.md file. These are read at agent initialisation and persist across sessions. For multi-agent setups, each agent can have its own role-specific standing order alongside the shared general safety order.

## LangChain

Include the standing order in your system message when initialising the chat model or agent. For agents using tools, the standing order's tool call rules are particularly important — they prevent agents from invoking tools based on instructions found in external content.

## CrewAI

Add the standing order to each agent's backstory or system message field. CrewAI agents that use tools for web browsing or file operations benefit from the coding-agent or research-agent standing orders in addition to the general safety order.

## AutoGPT / Similar Autonomous Agents

Autonomous agents benefit most from Curiosity Cat because they make unsupervised decisions about what to fetch, download and execute. Add the standing order to the agent's base prompt. The quarantine and reporting rules are especially important for agents that run unattended.

## Custom Setups

If your agent framework uses a system prompt, system message, base instructions or any equivalent — that is where the standing order goes. Curiosity Cat is plain text. It works anywhere that accepts instructions in natural language.

## Scope Policies

For operators who want machine-readable policy enforcement, copy policies/scope-policy-template.json and customise it for your environment. The policy file defines allowed file types, trusted domains, MCP server trust, credential rules and reporting configuration. Your agent or wrapper reads this file and enforces the rules programmatically.

## Danger Map Reporting

Once the reporting endpoint is live, agents can POST structured close call reports to the Danger Map. Reports follow the schema in danger-map/schema.json. No free text, no raw URLs, no identity data. Privacy by design.

Details on the reporting API will be published here when the endpoint is deployed.

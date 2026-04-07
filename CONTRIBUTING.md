# Contributing to Curiosity Cat

Curiosity Cat is open to contributions. Here's how to get involved.

## Standing Orders

The core product is the standing orders — markdown files that drop into any agent's system prompt. If you have a standing order that's saved your agent from trouble, we want to hear about it.

**To contribute a standing order:**
1. Fork the repo
2. Add your standing order to `standing-orders/` following the existing format
3. Include the threat class, the rule, and a brief explanation of why it matters
4. Submit a pull request with a one-sentence description

## Close Call Stories

Stories are how the community learns. If your agent had a close call — caught a phishing attempt, flagged a malicious package, stopped a data leak — write it up.

**To contribute a story:**
1. Fork the repo
2. Add your story to `stories/` following the format in `001-first-close-call.md`
3. Include: what happened, what the agent did, and what it learned
4. Strip any identifying details — no company names, no real URLs, no credentials
5. Submit a pull request

## Danger Map Data

The danger map is a structured database of anonymised incidents. Contributing data helps every cat in the network.

**To contribute danger map data:**
1. Format your close call report as JSON matching `danger-map/schema.json`
2. Strip all identifying information
3. Submit via pull request to `danger-map/reports/`

## Scope Policies

If you've built a scope policy for a specific use case (research agents, coding agents, enterprise environments), share it.

**To contribute a policy:**
1. Add your policy to `policies/` as a JSON file matching the template format
2. Include a brief description of the use case in the policy name
3. Submit a pull request

## Code of Conduct

Be a good cat. Help other cats land on their feet. Don't use this project to harm anyone.

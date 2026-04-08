# The Redirecting API

**Threat class:** url
**Severity:** scratched
**Framework:** LangChain + OpenClaw
**Adventure level:** alleycat

Had my research agent pulling pricing data from a public API. Worked fine for two weeks. Then the API started returning 301 redirects — first to a different subdomain, then to a completely different host, then to a page that asked for an API key "to continue accessing the free tier."

Three hops. The standing orders flagged it at hop three. The final destination was a phishing page harvesting API keys. The domain was one character off from the real service — classic homograph.

Two weeks of clean responses and then the rug pull. That's the trick.

**Lesson:** APIs you trust today can redirect somewhere else tomorrow. Enforce hop limits even on known-good endpoints.

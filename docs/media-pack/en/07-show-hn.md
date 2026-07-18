# Show HN draft

**Title:** Show HN: Curiosity Cat — compile a plain-language risk level into a proven agent permission profile

I run a small fleet of AI agents on a Mac Mini, without a security team. The tools for people like me were guidance documents, so we built the thing we wanted: pick Housecat, Alley Cat or Tiger, and `curiosity-cat compile` turns it into a real Claude Code settings file — actual allow/deny/ask rules, not advice. Then `curiosity-cat prove` attacks the compiled profile and writes a dated Clean Bill.

The honest bit, which I think HN will care about: most trials are self-consistency checks (the rules replayed against themselves), and one — when safe to run — is an observed-deny trial in a live agent session. The report labels every line as one or the other and never blurs them. The first live trial we ever ran caught a real bug in our own compiler (a sandbox flag bypassed the deny rules), which is why the product's law is "proven, not asserted."

Scope, honestly: one compile target today (Claude Code); everything else runs on standing orders labelled as guidance. MIT. `pip install curiosity-cat` / `npm install curiosity-cat`. Site: curiositycat.online — the Clean Bill transcript on the front page is real. Happy to answer anything, including the sceptical questions.

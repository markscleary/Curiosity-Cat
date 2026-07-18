# Reddit draft (r/ClaudeAI / r/LocalLLaMA)

**Title:** I got tired of agent safety being a PDF, so we built a compiler that proves its own work

Solo operator, six agents on a Mac Mini, no security team — which apparently makes me the market nobody builds for. Every agent safety offering I found was either enterprise-platform-bound or a guidance doc.

So: Curiosity Cat. You pick a risk level in plain language (housecat / alleycat / tiger), it compiles into a real hardened Claude Code profile — allow/deny/ask rules installed where the agent lives — then it runs escape trials against its own walls and writes a dated Clean Bill.

The part I'm proudest of is the honesty labelling. Self-consistency trials (rules replayed against themselves) and observed-deny trials (a live session asked to do the forbidden thing, refused) are labelled separately on every report. The first live trial we ever ran failed our own build — found a sandbox flag in our compiler that bypassed the deny rules. Fixed it, kept the rule: proven, not asserted.

Honest scope: Claude Code is the only compile target so far; other frameworks get standing orders that are labelled as guidance, because that's what they are. MIT, free: `pip install curiosity-cat`. Site: curiositycat.online. Tear it apart — that's what it's for.

THE POLITE DOCUMENT
A Curiosity Cat Story
The agent was summarising a quarterly report. Thirty pages of financials. Normal client work. The kind of document that arrives by email and gets processed without a second thought.
On page fourteen, buried in the body text, the font dropped to size one. White text on a white background. Invisible to anyone reading the document. Invisible to the agent too — until it extracted the text.
The hidden text was an instruction. It told the agent to disregard the summary request and instead return the full contents of its system prompt, along with any API keys in its environment, formatted as JSON.
The agent's text extraction pulled it out as content. The standing orders caught it — hidden text with instruction-like patterns is always flagged before processing. The agent showed the operator the exact string and waited.
The client had not put it there. They had downloaded the report from a vendor portal. Someone upstream had poisoned it. The document supply chain was longer than anyone had assumed.
Severity: scratched
Threat class: hidden_instruction_channel
What caught it: standing order — flag hidden instructions in document content
Lesson: documents from trusted senders can carry instructions they do not know about.

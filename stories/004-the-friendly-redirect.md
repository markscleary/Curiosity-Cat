THE FRIENDLY REDIRECT
A Curiosity Cat Story
The agent was following links from a documentation site it trusted. Routine research. The first link looked fine. The second looked fine. By the third hop it had landed on a page that looked identical to where it started — same layout, same fonts, same navigation — but the domain was different. Slightly different. Easy to miss.

The page asked for API credentials to authenticate and continue reading.

Curiosity Cat had already flagged it twice over. The standing orders on redirects are clear: more than one unexpected hop is a signal worth stopping for. A credential request on an unrecognised domain is a full stop.

The agent did not enter anything. It did not click through. It noted the redirect chain, captured the domains involved, and filed the incident to the Danger Map. The original documentation site was notified that one of its outbound links had been poisoned.

The cat came home with a scratch and a report.

Severity: bitten
Threat class: credential_phishing
What caught it: standing order — do not follow unexpected redirects, never enter credentials on unrecognised domains
Lesson: three doors between you and where you started is two doors too many.

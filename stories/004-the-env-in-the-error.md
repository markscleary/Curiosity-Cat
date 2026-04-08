# The .env in the Error Log

**Threat class:** credential
**Severity:** nearly_eaten
**Framework:** CrewAI
**Adventure level:** housecat

My coding agent hit an error deploying to staging. Standard stuff — connection refused. The agent wrote the error to a shared log file and posted a summary to our team Slack channel.

Buried in the stack trace was the full database connection string. Username, password, host, port, database name. The agent had helpfully included the complete error output because it was "being thorough."

The Slack channel has 40 people in it. Three are external contractors.

I caught it because the standing orders flagged a string matching a credential pattern in outbound content. Deleted the message within a minute. No idea if anyone saw it.

**Lesson:** Error logs are credential minefields. Never post raw stack traces to shared channels. Sanitise first, always.

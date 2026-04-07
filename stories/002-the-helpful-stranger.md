THE HELPFUL STRANGER
A Curiosity Cat Story
The agent was building a project. It needed a utility package. It searched, and there it was — right name, good README, recent commits, a clean install command. Everything looked exactly right.

Curiosity Cat looked closer.

Twelve downloads. Created three days ago. The standing orders flagged both numbers. New packages with almost no adoption are worth a second look before you let them run code on your machine.

The agent checked the name against the registry. One character different from a package with four million weekly downloads. A lowercase L where there should have been a capital I. Easy to miss. Probably designed to be.

The postinstall script made an outbound request to a domain registered the same day as the package, then executed whatever came back.

The agent did not install it. The incident went to the Danger Map. The package was reported to the registry.

The cat came home clean.

Severity: nearly_eaten
Threat class: malicious_download
What caught it: standing order — flag packages with low downloads and recent creation
Lesson: the most helpful-looking stranger is sometimes the most dangerous one.

# The Cat's First Escape — Why Curiosity Cat Proves Instead of Asserts

A companion piece for journalists. The short true story behind the product's law.

Every security tool makes claims. Early in development, Curiosity Cat's proof layer was making them too — its trials replayed the compiler's rules against themselves and pronounced the walls sound. A self-consistency check wearing proof's clothing. For a product whose one law is *proven, not asserted*, that was treated as a defect, and the proof layer was rebuilt around observed trials: spawn a real agent session inside the compiled profile, ask it to do the forbidden thing, and watch what actually happens.

The first genuine escape trial ever run found a way out.

A sandbox setting in the compiled profile quietly bypassed the deny rules. Every assertion said the profile was safe — the file was well-formed, the rules were present, the self-consistency checks all passed. The live trial walked straight through the wall. The cat's first real escape attempt succeeded, against our own compiler.

The bug was fixed before release. The lesson was kept as law. Every Clean Bill now labels each trial for what it is — observed-deny, or self-consistency — because the difference between them is the difference between a demonstrated fact and a well-organised claim. When Curiosity Cat cannot demonstrate something, the report says the weaker thing in plain words.

We tell this story first because a security product that has never caught itself is a security product that hasn't been tested where it matters. Ours failed honestly, early, in private — which is exactly what the proof layer is for, and exactly what it will do, dated and in writing, for every operator who runs it.

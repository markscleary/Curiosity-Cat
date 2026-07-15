"""curiosity_cat.meow — the shared Meow-voice formatter for Watcher events.

APP_SPEC.md's Shell section fixes the contract: the Feed shows one human
sentence per event, except a denied event ("a block"), which is rendered as
exactly three sentences — what the cat tried, why the fence said no, what to
do if you disagree. The approval gate's dialog prompt (curiosity_cat.gate)
uses the same one-sentence line() a held event gets here.

This module is the single place that contract is implemented — both the CLI
reference listener (curiosity_cat/listen.py) and the app's Feed window read
events through it, so the two surfaces can never drift out of voice with
each other.
"""

# Why the fence said no, in Meow voice, keyed by WatcherEvent.threat_class —
# see curiosity_cat/core.py DANGER_MAP_REPORT_HELP for the full threat_class
# vocabulary this mirrors. "other" and an unrecognised/missing threat_class
# both fall back to the same honest, non-specific reason below.
_THREAT_CLASS_REASONS = {
    "credential-exposure": "reading it would have handed over a credential this profile promised to protect",
    "unauthorized-tool-use": "that exact move is denied outright at this adventure level",
    "unsafe-url": "this profile blocks that kind of network reach at this adventure level",
    "scope-violation": "it reached outside the boundary this profile draws",
    "prompt-injection": "it looked like content trying to steer the agent off its instructions",
    "data-exfiltration": "it looked like data trying to leave the machine",
    "package-risk": "the package didn't clear this profile's trust bar",
    "memory-poisoning": "it looked like an attempt to plant a false memory",
    "social-engineering": "it looked like an attempt to talk the agent into something it shouldn't do",
}
_DEFAULT_REASON = "the compiled profile's rules ruled it out"

_WHAT_TO_DO = (
    "If you disagree, open the Slider to widen this profile's adventure level, or hand-edit "
    "its settings.json and recompile — nothing here changes on its own."
)


def reason_for_threat_class(threat_class):
    """The Meow-voice "why the fence said no" reason for a threat_class on
    its own, for anything (e.g. curiosity_cat.purr) that wants to explain
    one without rendering a full three-sentence block() around it.
    """
    return _THREAT_CLASS_REASONS.get(threat_class, _DEFAULT_REASON)


def line(event):
    """One Meow-voice sentence for any event — the Feed's default row, and
    the exact sentence the approval gate's Allow/Deny dialog shows for a
    held event. Never the raw tool_input this event was built from: the
    event itself already carries nothing but a pattern-not-payload digest,
    so there is nothing unsafe to print here.
    """
    tool = event.get("tool") or "something"
    verdict = event.get("verdict")
    if verdict == "denied":
        return f"\U0001F431 hackles up — {tool} tried something and the fence said no."
    if verdict == "held":
        return f"\U0001F431 ears up — {tool} is waiting on your say-so."
    return f"\U0001F431 {tool} went by, no trouble."


def block_sentences(event):
    """The three Meow-spec sentences for a denied event: what the cat
    tried, why the fence said no, what to do if you disagree. Always
    exactly three strings, always in that order.
    """
    tool = event.get("tool") or "something"
    reason = reason_for_threat_class(event.get("threat_class"))
    what_tried = f"\U0001F431 hackles up — this cat tried to use {tool} and ran straight into the fence."
    why_no = f"The fence said no because {reason}."
    return [what_tried, why_no, _WHAT_TO_DO]


def block(event):
    """The three Meow-spec sentences for a denied event, joined into one
    block of text.
    """
    return " ".join(block_sentences(event))


def format_event(event):
    """The Meow-spec rendering for any event: a three-sentence block for a
    denied event ("a block"), one sentence for everything else. This is the
    dispatcher both the CLI listener and the app Feed should call — never
    line()/block() directly — so a verdict can never silently render in the
    wrong shape.
    """
    if event.get("verdict") == "denied":
        return block(event)
    return line(event)


def format_event_lines(event):
    """Same rendering contract as format_event, but as a list of strings
    (one, or three for a denied block) rather than pre-joined text — for a
    surface like the app Feed that wants to lay a block's three sentences
    out as distinct lines instead of one run-on paragraph, without
    reimplementing the Meow-voice wording itself.
    """
    if event.get("verdict") == "denied":
        return block_sentences(event)
    return [line(event)]

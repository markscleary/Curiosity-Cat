#!/usr/bin/env python3
"""ccat-engine serve — line-delimited JSON-RPC-ish stdio server over core.

One request per line on stdin: {"id": ..., "method": ..., "params": {...}}.
One response per line on stdout: {"id": ..., "result": ...} or
{"id": ..., "error": "..."}. Never raises out of serve_forever() for a
malformed line or a core-level failure — those become an error response for
that request's id (or a null-id error response if the line couldn't be
parsed at all) so one bad request never kills the connection.
"""

import argparse
import dataclasses
import json
import sys

from curiosity_cat import __version__, card, core, discover, purr

METHODS = ("compile", "prove", "apply", "unapply", "estate", "check", "report_close_call",
           "queue_close_call", "list_tray", "submit_approved", "vet", "status",
           "render_share_card", "purr")


def _handle_compile(params):
    level = params.get("level")
    target = params.get("target")
    return core.to_jsonable(core.compile_profile(level, target, profiles_dir=params.get("profiles_dir")))


def _handle_prove(params):
    profile_dir = params.get("profile_dir")
    if not profile_dir:
        raise ValueError('params.profile_dir is required')
    return core.to_jsonable(core.prove(profile_dir, observed=params.get("observed"), target=params.get("target")))


def _handle_apply(params):
    profile_dir = params.get("profile_dir")
    target = params.get("target")
    if not profile_dir:
        raise ValueError('params.profile_dir is required')
    if not target:
        raise ValueError('params.target is required')
    return core.to_jsonable(core.apply(profile_dir, target))


def _handle_unapply(params):
    target = params.get("target")
    if not target:
        raise ValueError('params.target is required')
    return core.to_jsonable(core.unapply(target))


def _handle_estate(params):
    inventory = discover.build_inventory(roots=params.get("roots"))
    return dataclasses.asdict(inventory)


def _handle_check(params):
    candidate = params.get("candidate")
    if not candidate:
        raise ValueError('params.candidate is required')
    return core.to_jsonable(core.check(candidate, limit=params.get("limit", 50)))


def _handle_report_close_call(params):
    event = params.get("event")
    if not isinstance(event, dict):
        raise ValueError('params.event (object) is required')
    return core.report_close_call(event, consent=bool(params.get("consent", False)),
                                   api_key=params.get("api_key"))


def _handle_queue_close_call(params):
    event = params.get("event")
    profile_dir = params.get("profile_dir")
    if not isinstance(event, dict):
        raise ValueError('params.event (object) is required')
    if not profile_dir:
        raise ValueError('params.profile_dir is required')
    return core.queue_close_call(event, profile_dir)


def _handle_list_tray(params):
    profile_dir = params.get("profile_dir")
    if not profile_dir:
        raise ValueError('params.profile_dir is required')
    return core.list_tray(profile_dir, status=params.get("status"))


def _handle_submit_approved(params):
    profile_dir = params.get("profile_dir")
    ids = params.get("ids")
    if not profile_dir:
        raise ValueError('params.profile_dir is required')
    if not isinstance(ids, list) or not ids:
        raise ValueError('params.ids (non-empty array) is required')
    return core.submit_approved(profile_dir, ids, api_key=params.get("api_key"))


def _handle_vet(params):
    profile_dir = params.get("profile_dir")
    if not profile_dir:
        raise ValueError('params.profile_dir is required')
    return core.to_jsonable(core.vet(
        profile_dir, recompile=bool(params.get("recompile", False)), observed=params.get("observed"),
    ))


def _handle_render_share_card(params):
    clean_bill_path = params.get("clean_bill_path")
    if not clean_bill_path:
        raise ValueError('params.clean_bill_path is required')
    return {"path": card.render_share_card_from_file(clean_bill_path, out_path=params.get("out_path"))}


def _handle_purr(params):
    profile_dir = params.get("profile_dir")
    if not profile_dir:
        raise ValueError('params.profile_dir is required')
    days = params.get("days") or purr.DEFAULT_WINDOW_DAYS
    return {"text": purr.generate_purr(profile_dir, days=days)}


def _handle_status(params):
    return {
        "engine": "ccat-engine",
        "version": __version__,
        "methods": list(METHODS),
        "levels": core.LEVELS,
        "targets": list(core.TARGET_EMITTERS),
    }


DISPATCH = {
    "compile": _handle_compile,
    "prove": _handle_prove,
    "apply": _handle_apply,
    "unapply": _handle_unapply,
    "estate": _handle_estate,
    "check": _handle_check,
    "report_close_call": _handle_report_close_call,
    "queue_close_call": _handle_queue_close_call,
    "list_tray": _handle_list_tray,
    "submit_approved": _handle_submit_approved,
    "vet": _handle_vet,
    "status": _handle_status,
    "render_share_card": _handle_render_share_card,
    "purr": _handle_purr,
}


def handle_request(request):
    """Dispatch one already-parsed request dict. Returns a response dict.

    Never raises: any exception from a handler (bad params, a core
    ValueError, ...) becomes an {"id": ..., "error": "..."} response rather
    than propagating, since one bad request must not kill the stdio loop.
    """
    req_id = request.get("id") if isinstance(request, dict) else None
    method = request.get("method") if isinstance(request, dict) else None

    if method not in DISPATCH:
        return {"id": req_id, "error": f'unknown method: "{method}". Valid methods: {", ".join(METHODS)}'}

    params = request.get("params") or {}
    if not isinstance(params, dict):
        return {"id": req_id, "error": "params must be an object"}

    try:
        result = DISPATCH[method](params)
    except Exception as exc:  # noqa: BLE001 - any handler failure becomes an error response, never a crash
        return {"id": req_id, "error": str(exc)}
    return {"id": req_id, "result": result}


def serve_forever(stdin=None, stdout=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"id": None, "error": f"invalid JSON request: {exc}"}
        else:
            response = handle_request(request)
        stdout.write(json.dumps(response) + "\n")
        stdout.flush()


def main():
    parser = argparse.ArgumentParser(prog="ccat-engine", description="curiosity-cat engine")
    parser.add_argument("command", nargs="?", choices=["serve"])
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    serve_forever()


if __name__ == "__main__":
    main()

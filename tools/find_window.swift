// Resolve the on-screen window id + bounds for a given app owner, using
// CGWindowListCopyWindowInfo. Owner name + window number + bounds are
// readable WITHOUT Screen Recording permission (only window *titles* are
// redacted without it), so this lookup works regardless of TCC state — it
// is the capture step (screencapture -l) that needs the grant.
//
// Usage:  swift find_window.swift [owner-substring]   (default: curiosity)
// Prints: "<windowid> <x> <y> <w> <h>" for the largest matching on-screen
// window, or exits non-zero if none found.
import CoreGraphics
import Foundation

let needle = (CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "curiosity").lowercased()
let opts = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
guard let list = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] else {
    FileHandle.standardError.write("CGWindowListCopyWindowInfo failed\n".data(using: .utf8)!)
    exit(2)
}
var best: (id: Int, area: Double, x: Int, y: Int, w: Int, h: Int)? = nil
for win in list {
    guard let owner = win[kCGWindowOwnerName as String] as? String,
          owner.lowercased().contains(needle) else { continue }
    guard let num = win[kCGWindowNumber as String] as? Int,
          let b = win[kCGWindowBounds as String] as? [String: Any] else { continue }
    let w = (b["Width"] as? Double) ?? 0
    let h = (b["Height"] as? Double) ?? 0
    let x = (b["X"] as? Double) ?? 0
    let y = (b["Y"] as? Double) ?? 0
    let area = w * h
    if area < 5000 { continue } // ignore tiny/hidden helper surfaces
    if best == nil || area > best!.area {
        best = (num, area, Int(x), Int(y), Int(w), Int(h))
    }
}
guard let r = best else {
    FileHandle.standardError.write("no on-screen window for owner ~= \(needle)\n".data(using: .utf8)!)
    exit(1)
}
print("\(r.id) \(r.x) \(r.y) \(r.w) \(r.h)")

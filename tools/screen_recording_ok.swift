// Exit 0 if THIS process has macOS Screen Recording permission, 1 if not.
// Non-intrusive: CGPreflightScreenCaptureAccess() checks without prompting.
import CoreGraphics
import Foundation
exit(CGPreflightScreenCaptureAccess() ? 0 : 1)

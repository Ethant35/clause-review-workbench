// Author: Ethan. Hidden AppKit rendering and native lifecycle acceptance.
let app = NSApplication.shared
let probe = WorkbenchDelegate()
app.delegate = probe
probe.applicationDidFinishLaunching(Notification(name: NSApplication.didFinishLaunchingNotification))
func waitFor(_ condition: () -> Bool) {
    let deadline = Date().addingTimeInterval(30)
    while !condition() && Date() < deadline { _ = RunLoop.main.run(mode: .default, before: Date().addingTimeInterval(0.05)) }
    precondition(condition(), "Native operation did not complete")
}
waitFor { probe.address != nil }
precondition(probe.status.stringValue.contains("Running locally"))
precondition(probe.buttons.count == 7)
let content = probe.window.contentView!
content.layoutSubtreeIfNeeded()
let representation = content.bitmapImageRepForCachingDisplay(in: content.bounds)!
content.cacheDisplay(in: content.bounds, to: representation)
let destination = URL(fileURLWithPath: ProcessInfo.processInfo.environment["CRW_NATIVE_SCREENSHOT"]!)
try! representation.representation(using: .png, properties: [:])!.write(to: destination)
probe.restart()
waitFor { !probe.busy && probe.address != nil }
let backup = probe.support.appendingPathComponent("test-backup")
probe.recover(commands: [["backup", probe.data.path, backup.path]], newData: nil)
waitFor { !probe.busy && probe.address != nil }
precondition(FileManager.default.fileExists(atPath: backup.appendingPathComponent("manifest.json").path))
var stopped = false
probe.stop { stopped = true }
waitFor { stopped }
print("PASS: hidden native window, readiness, restart, backup and shutdown")

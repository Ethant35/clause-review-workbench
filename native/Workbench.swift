// Author: Ethan. Native lifecycle for the bundled loopback workbench.
import AppKit
import Security
import LocalAuthentication
import Darwin

final class WorkbenchDelegate: NSObject, NSApplicationDelegate {
    let fm = FileManager.default
    let resources = Bundle.main.resourceURL!
    let status = NSTextField(wrappingLabelWithString: "Starting local workbench…")
    var window: NSWindow!
    var server: Process?
    var recovery: Process?
    var readyTimer: Timer?
    var readiness: URL?
    var address: URL?
    var buttons: [NSButton] = []
    var busy = false
    var stopping = false
    var terminating = false
    var terminationReplyPending = false
    var ticks = 0
    let headless = ProcessInfo.processInfo.environment["CRW_HEADLESS"] == "1"
    lazy var support: URL = {
        if let path = ProcessInfo.processInfo.environment["CRW_APP_SUPPORT"] { return URL(fileURLWithPath: path) }
        return fm.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("Clause Review Workbench", isDirectory: true)
    }()
    var data: URL {
        if let path = ProcessInfo.processInfo.environment["CRW_DATA_DIR"] { return URL(fileURLWithPath: path) }
        if let path = UserDefaults.standard.string(forKey: "dataDirectory") { return URL(fileURLWithPath: path) }
        return support.appendingPathComponent("Data", isDirectory: true)
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(headless ? .prohibited : .regular)
        let menu = NSMenu()
        let root = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Quit Clause Review Workbench", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        root.submenu = appMenu; menu.addItem(root); NSApp.mainMenu = menu
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 520, height: 360), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Clause Review Workbench"
        window.isReleasedWhenClosed = false
        let stack = NSStackView(); stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        status.font = .systemFont(ofSize: 14); status.setAccessibilityIdentifier("workbench-status")
        stack.addArrangedSubview(status)
        let hint = NSTextField(wrappingLabelWithString: "Your contracts stay on this Mac. The workbench opens in your browser. Quit this app to stop its local server.")
        stack.addArrangedSubview(hint)
        let first = NSStackView(); first.orientation = .horizontal; first.spacing = 8
        for (title, selector) in [("Open workbench", #selector(openWorkbench)), ("Restart", #selector(restart)), ("Show saved data", #selector(showData))] {
            let button = NSButton(title: title, target: self, action: selector); first.addArrangedSubview(button); buttons.append(button)
        }
        stack.addArrangedSubview(first)
        let second = NSStackView(); second.orientation = .horizontal; second.spacing = 8
        for (title, selector) in [("Back up…", #selector(backup)), ("Restore backup…", #selector(restore)), ("Import earlier data…", #selector(importData))] {
            let button = NSButton(title: title, target: self, action: selector); second.addArrangedSubview(button); buttons.append(button)
        }
        stack.addArrangedSubview(second)
        let aiButton = NSButton(title: "Optional AI key…", target: self, action: #selector(configureAI))
        stack.addArrangedSubview(aiButton); buttons.append(aiButton)
        let footer = NSTextField(wrappingLabelWithString: "Restore and import create a separate data folder. Existing data remains available. Contract findings require human review.")
        footer.font = .systemFont(ofSize: 12); stack.addArrangedSubview(footer)
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 24), stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -24), stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 24)])
        window.center()
        if !headless { window.makeKeyAndOrderFront(nil) }
        do { try fm.createDirectory(at: support, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700]) }
        catch { status.stringValue = "Cannot create the local data folder. Check storage permissions."; return }
        start()
    }
    func environment(includeAIKey: Bool = true) -> [String: String] {
        // Do not inherit PYTHONPATH, dynamic-loader overrides or developer credentials.
        var result = ["PATH": "/usr/bin:/bin", "HOME": fm.homeDirectoryForCurrentUser.path, "LANG": "en_US.UTF-8", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "CRW_DATA_DIR": data.path, "CRW_PORT": "8765"]
        for key in ["CRW_PORT", "CRW_RETENTION_DAYS"] {
            if let value = ProcessInfo.processInfo.environment[key] { result[key] = value }
        }
        if includeAIKey, let key = readAIKey() { result["OPENROUTER_API_KEY"] = key }
        return result
    }
    func process(_ arguments: [String], includeAIKey: Bool = true) -> Process {
        let p = Process(); p.executableURL = resources.appendingPathComponent("python/bin/python3")
        p.arguments = ["-s", "-B", resources.appendingPathComponent("bootstrap.py").path] + arguments
        p.currentDirectoryURL = resources.appendingPathComponent("workbench")
        p.environment = environment(includeAIKey: includeAIKey)
        p.environment?["CRW_EXPECTED_PARENT_PID"] = String(ProcessInfo.processInfo.processIdentifier)
        p.standardOutput = FileHandle.nullDevice; p.standardError = FileHandle.nullDevice
        return p
    }
    func setBusy(_ value: Bool) { busy = value; buttons.forEach { $0.isEnabled = !value } }
    func start() {
        if server?.isRunning == true { return }
        address = nil; stopping = false; ticks = 0
        status.stringValue = "Starting local workbench…"
        let path = support.appendingPathComponent("ready-\(UUID().uuidString).json")
        readiness = path
        let p = process(["serve"]); p.environment?["CRW_READY_FILE"] = path.path
        p.terminationHandler = { [weak self] child in DispatchQueue.main.async {
            guard let self = self, self.server === child else { return }
            self.readyTimer?.invalidate(); self.address = nil
            if !self.stopping { self.status.stringValue = "The workbench stopped. Check that port 8765 is free and the data folder is private. Use Restore backup if saved data is damaged." }
        }}
        do { try p.run(); server = p }
        catch { status.stringValue = "The bundled runtime could not start. Download a fresh app copy; your saved data is separate."; return }
        readyTimer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] timer in
            guard let self = self else { timer.invalidate(); return }
            self.ticks += 1
            if let bytes = try? Data(contentsOf: path), let obj = try? JSONSerialization.jsonObject(with: bytes) as? [String: Any],
               let text = obj["url"] as? String, let url = URL(string: text), url.host == "127.0.0.1", self.server?.isRunning == true {
                self.address = url; timer.invalidate(); try? self.fm.removeItem(at: path)
                self.status.stringValue = "Running locally at \(url.absoluteString)"
                if !self.headless && ProcessInfo.processInfo.environment["CRW_NO_OPEN"] != "1" { self.openWorkbench() }
            } else if self.ticks >= 120 {
                timer.invalidate(); self.status.stringValue = "Startup did not finish. Restart, or restore a backup if local data is damaged."
                self.stop {}
            }
        }
    }
    func stop(_ completion: @escaping () -> Void) {
        stopping = true; readyTimer?.invalidate(); address = nil
        if let path = readiness { try? fm.removeItem(at: path) }
        guard let p = server, p.isRunning else {
            server = nil; stopping = false; completion(); return
        }
        p.terminate()
        DispatchQueue.global().async {
            let gracefulDeadline = DispatchTime.now().uptimeNanoseconds + 10_000_000_000
            while p.isRunning && DispatchTime.now().uptimeNanoseconds < gracefulDeadline { Thread.sleep(forTimeInterval: 0.1) }
            if p.isRunning {
                // Do not let a wedged server hold Restart, recovery, or Quit forever.
                _ = kill(p.processIdentifier, SIGKILL)
                let killDeadline = DispatchTime.now().uptimeNanoseconds + 5_000_000_000
                while p.isRunning && DispatchTime.now().uptimeNanoseconds < killDeadline { Thread.sleep(forTimeInterval: 0.1) }
            }
            // SIGKILL guarantees the owned process can be reaped on supported macOS.
            p.waitUntilExit()
            DispatchQueue.main.async { [self] in
                if self.server === p { self.server = nil }
                self.stopping = false
                completion()
            }
        }
    }
    var keychainService = "com.ethantarnarider.clause-review-workbench"
    var keyQuery: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: keychainService,
         kSecAttrAccount as String: "OpenRouter"]
    }
    func readAIKey() -> String? {
        var query = keyQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        let context = LAContext(); context.interactionNotAllowed = true
        query[kSecUseAuthenticationContext as String] = context
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let bytes = result as? Data else { return nil }
        return String(data: bytes, encoding: .utf8)
    }
    func storeAIKey(_ key: String?) -> OSStatus {
        guard let key = key else {
            let status = SecItemDelete(keyQuery as CFDictionary)
            return status == errSecItemNotFound ? errSecSuccess : status
        }
        let attributes = [kSecValueData as String: Data(key.utf8)]
        var outcome = SecItemUpdate(keyQuery as CFDictionary, attributes as CFDictionary)
        if outcome == errSecItemNotFound {
            var item = keyQuery; item[kSecValueData as String] = Data(key.utf8)
            item[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            outcome = SecItemAdd(item as CFDictionary, nil)
        }
        return outcome
    }
    @objc func configureAI() {
        guard !busy else { return }
        let alert = NSAlert()
        alert.messageText = "Optional OpenRouter API key"
        alert.informativeText = "Stored in this Mac’s Keychain. Local review needs no key. Each AI request still requires your consent, provider selection and budget in the workbench. Saving or removing restarts the local server."
        alert.addButton(withTitle: "Save key"); alert.addButton(withTitle: "Cancel"); alert.addButton(withTitle: "Remove saved key")
        let field = NSSecureTextField(frame: NSRect(x:0,y:0,width:360,height:24))
        field.placeholderString = "Paste API key"; field.setAccessibilityLabel("OpenRouter API key")
        alert.accessoryView = field
        let response = alert.runModal()
        if response == .alertSecondButtonReturn { return }
        let key = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        if response != .alertThirdButtonReturn && (key.isEmpty || key.utf8.count > 4096) {
            status.stringValue = "Enter a nonempty API key of at most 4096 bytes."; return
        }
        let outcome = storeAIKey(response == .alertThirdButtonReturn ? nil : key)
        field.stringValue = ""
        guard outcome == errSecSuccess else { status.stringValue = "Keychain could not save this change. Local review remains available."; return }
        restart()
    }
    @objc func openWorkbench() { if let url = address { NSWorkspace.shared.open(url) } }
    @objc func restart() {
        guard !busy else { return }
        setBusy(true)
        stop {
            self.setBusy(false)
            if self.terminating { self.completeTerminationIfPending() }
            else { self.start() }
        }
    }
    @objc func showData() { NSWorkspace.shared.activateFileViewerSelecting([data]) }
    func chooseFolder(_ title: String) -> URL? {
        let panel = NSOpenPanel(); panel.title = title; panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.allowsMultipleSelection = false
        return panel.runModal() == .OK ? panel.url : nil
    }
    @objc func backup() {
        guard !busy else { return }
        let panel = NSSavePanel(); panel.title = "Save a new backup folder"; panel.nameFieldStringValue = "Workbench backup \(ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-"))"
        guard panel.runModal() == .OK, let destination = panel.url else { return }
        guard !fm.fileExists(atPath: destination.path) else { status.stringValue = "Choose a new backup folder. Existing folders are never replaced."; return }
        recover(commands: [["backup", data.path, destination.path]], newData: nil)
    }
    @objc func restore() {
        guard !busy, let source = chooseFolder("Choose a workbench backup folder") else { return }
        let destination = support.appendingPathComponent("Data-\(UUID().uuidString)")
        recover(commands: [["restore", source.path, destination.path]], newData: destination)
    }
    @objc func importData() {
        guard !busy, let source = chooseFolder("Choose the earlier .data folder (Command-Shift-Period shows hidden folders)") else { return }
        let backup = support.appendingPathComponent("Imported-backup-\(UUID().uuidString)")
        let destination = support.appendingPathComponent("Data-\(UUID().uuidString)")
        recover(commands: [["backup", source.path, backup.path], ["restore", backup.path, destination.path]], newData: destination)
    }
    func recover(commands: [[String]], newData: URL?) {
        setBusy(true); status.stringValue = "Stopping the server and checking saved data…"
        stop { self.runRecovery(commands, index: 0, newData: newData) }
    }
    func runRecovery(_ commands: [[String]], index: Int, newData: URL?) {
        guard index < commands.count else {
            recovery = nil
            setBusy(false)
            if let target = newData { UserDefaults.standard.set(target.path, forKey: "dataDirectory") }
            if terminating { completeTerminationIfPending() } else { start() }
            return
        }
        // Recovery is offline. It receives no Keychain secret and remains owned
        // until the whole (possibly multi-step import) sequence completes.
        let p = process(["recover"] + commands[index], includeAIKey: false)
        recovery = p
        p.terminationHandler = { [weak self] child in
            DispatchQueue.main.async {
                guard let self = self, self.recovery === child else { return }
                self.recovery = nil
                if child.terminationStatus == 0 {
                    self.runRecovery(commands, index: index + 1, newData: newData)
                } else {
                    self.setBusy(false)
                    self.status.stringValue = "Recovery did not complete. Check the selected folder, permissions and free space. No existing data was replaced. Use Restart to reopen the current data."
                    if self.terminating { self.completeTerminationIfPending() }
                }
            }
        }
        do { try p.run() }
        catch {
            recovery = nil; setBusy(false)
            status.stringValue = "Recovery did not complete. Check the selected folder, permissions and free space. No existing data was replaced. Use Restart to reopen the current data."
            if terminating { completeTerminationIfPending() }
        }
    }
    func completeTerminationIfPending() {
        guard terminationReplyPending, recovery == nil, !stopping else { return }
        terminationReplyPending = false
        NSApp.reply(toApplicationShouldTerminate: true)
    }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if terminating { return terminationReplyPending ? .terminateCancel : .terminateNow }
        terminating = true
        terminationReplyPending = true
        if busy {
            // Let an active recovery sequence finish before allowing app exit.
            // Its completion path skips server restart while termination is pending.
            completeTerminationIfPending()
            return .terminateLater
        }
        stop { self.completeTerminationIfPending() }
        return .terminateLater
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !headless { window.makeKeyAndOrderFront(nil) }
        return true
    }
}
let delegate = WorkbenchDelegate()
NSApplication.shared.delegate = delegate
NSApplication.shared.run()

// Author: Ethan. Concatenate after the delegate class, without its application entry point.
let probe = WorkbenchDelegate()
probe.keychainService = "com.ethantarnarider.clause-review-workbench.acceptance.\(UUID().uuidString)"
defer { _ = probe.storeAIKey(nil) }
precondition(probe.readAIKey() == nil)
precondition(probe.storeAIKey("synthetic-key-not-valid-at-any-provider") == errSecSuccess)
precondition(probe.readAIKey() == "synthetic-key-not-valid-at-any-provider")
precondition(probe.environment(includeAIKey: false)["OPENROUTER_API_KEY"] == nil)
precondition(probe.environment(includeAIKey: true)["OPENROUTER_API_KEY"] == "synthetic-key-not-valid-at-any-provider")
precondition(probe.storeAIKey("replacement-synthetic-key") == errSecSuccess)
precondition(probe.readAIKey() == "replacement-synthetic-key")
precondition(probe.storeAIKey(nil) == errSecSuccess)
precondition(probe.readAIKey() == nil)
print("PASS: native Keychain create/read/update/delete; recovery credential isolation")

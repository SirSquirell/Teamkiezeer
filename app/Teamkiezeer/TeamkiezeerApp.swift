import SwiftData
import SwiftUI

@main
struct TeamkiezeerApp: App {
    @State private var store: TeamStore

    init() {
        // Crest-caching: AsyncImage gebruikt URLSession.shared → URLCache.shared.
        URLCache.shared = URLCache(
            memoryCapacity: 32 * 1024 * 1024,
            diskCapacity: 256 * 1024 * 1024
        )
        let store = TeamStore()
        store.loadLocal()
        _store = State(initialValue: store)
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .task {
                    // Verse data bij launch; valt stil terug op cache/bundled.
                    await store.refresh()
                }
        }
        .modelContainer(for: [DrawRecordModel.self, RulesModel.self])
    }
}

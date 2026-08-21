import Foundation
import Observation
import TeamkiezeerKit

/// Datalaag: remote → cache → bundled snapshot, in die volgorde.
/// De app moet volledig bruikbaar zijn op een bank met slechte wifi.
@Observable
@MainActor
final class TeamStore {
    enum Source: String {
        case remote = "GitHub"
        case cache = "cache"
        case bundled = "ingebouwde snapshot"
    }

    private(set) var document: TeamsDocument?
    private(set) var source: Source = .bundled
    private(set) var isRefreshing = false
    private(set) var lastError: String?

    var lastFetched: Date? {
        get {
            access(keyPath: \.lastFetched)
            return UserDefaults.standard.object(forKey: "lastFetched") as? Date
        }
        set {
            withMutation(keyPath: \.lastFetched) {
                UserDefaults.standard.set(newValue, forKey: "lastFetched")
            }
        }
    }

    var teams: [Team] { document?.teams ?? [] }
    var leagues: [League] { document?.leagues ?? [] }
    var defaultWhitelist: [String] { leagues.filter(\.defaultWhitelist).map(\.id) }

    /// raw.githubusercontent op de default branch; de weekly Action commit
    /// daar een verse teams.json.
    static let remoteURL = URL(
        string: "https://raw.githubusercontent.com/SirSquirell/Teamkiezeer/claude/new-project-welcome-npwul9/data/teams.json"
    )!

    private var cacheURL: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("teams.json")
    }

    /// Synchronoon bij launch: cache als die er is, anders bundled. Nooit leeg.
    func loadLocal() {
        if let data = try? Data(contentsOf: cacheURL),
           let doc = try? TeamsDocument.decode(from: data) {
            document = doc
            source = .cache
            return
        }
        loadBundled()
    }

    private func loadBundled() {
        guard let url = Bundle.main.url(forResource: "bundled-teams", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let doc = try? TeamsDocument.decode(from: data) else {
            assertionFailure("bundled-teams.json ontbreekt of is kapot")
            return
        }
        document = doc
        source = .bundled
    }

    /// Remote refresh met 5s timeout; bij succes naar Application Support.
    /// Bij falen blijft de huidige (cache/bundled) data gewoon staan.
    func refresh() async {
        guard !isRefreshing else { return }
        isRefreshing = true
        lastError = nil
        defer { isRefreshing = false }

        var request = URLRequest(url: Self.remoteURL)
        request.timeoutInterval = 5
        request.cachePolicy = .reloadIgnoringLocalCacheData
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            let doc = try TeamsDocument.decode(from: data)
            document = doc
            source = .remote
            lastFetched = Date()
            try? data.write(to: cacheURL, options: .atomic)
        } catch let DataError.unsupportedSchema(version) {
            lastError = "Dataset heeft schema v\(version); deze app-build begrijpt t/m v\(TeamsDocument.supportedSchemaVersion). Update de app."
        } catch {
            lastError = "Verversen mislukt; huidige data blijft staan."
        }
    }
}

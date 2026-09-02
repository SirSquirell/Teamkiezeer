import Foundation
import SwiftData
import TeamkiezeerKit

/// Persistente constraints (het Rules-scherm). Eén rij; `fetchOrCreate`
/// initialiseert de whitelist eenmalig vanuit de dataset-defaults.
@Model
final class RulesModel {
    var cooldownDraws: Int = 6
    var includeWomens: Bool = false
    /// nil = "verras ons"
    var pinnedStars: Double?
    var kindFilterRaw: String = KindFilter.clubsOnly.rawValue
    var leagueWhitelist: [String] = []

    init() {}

    var kindFilter: KindFilter {
        get { KindFilter(rawValue: kindFilterRaw) ?? .clubsOnly }
        set { kindFilterRaw = newValue.rawValue }
    }

    var constraints: DrawConstraints {
        DrawConstraints(
            cooldownDraws: cooldownDraws,
            leagueWhitelist: Set(leagueWhitelist),
            includeWomens: includeWomens,
            pinnedStars: pinnedStars,
            kindFilter: kindFilter
        )
    }

    static func fetchOrCreate(in context: ModelContext, defaultWhitelist: [String]) -> RulesModel {
        if let existing = try? context.fetch(FetchDescriptor<RulesModel>()).first {
            return existing
        }
        let fresh = RulesModel()
        fresh.leagueWhitelist = defaultWhitelist
        context.insert(fresh)
        return fresh
    }
}

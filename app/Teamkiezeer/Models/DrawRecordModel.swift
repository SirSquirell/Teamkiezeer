import Foundation
import SwiftData
import TeamkiezeerKit

/// Eén draw in de history. Velden zijn een snapshot van beide teams zodat een
/// oude draw leesbaar blijft als de dataset verandert. Bewust platte velden:
/// simpel en migratieproof.
@Model
final class DrawRecordModel {
    var timestamp: Date = Date()
    var starLevel: Double = 0
    var ratingDelta: Int = 0
    var relaxationLabels: [String] = []

    var aId: String = ""
    var aName: String = ""
    var aRating: Int = 0
    var aCrestURL: String?
    var aPrimaryColor: String?
    var aSecondaryColor: String?
    var aSubtitle: String = ""

    var bId: String = ""
    var bName: String = ""
    var bRating: Int = 0
    var bCrestURL: String?
    var bPrimaryColor: String?
    var bSecondaryColor: String?
    var bSubtitle: String = ""

    init(result: DrawResult) {
        timestamp = Date()
        starLevel = result.starLevel
        ratingDelta = result.ratingDelta
        relaxationLabels = result.relaxations.map(\.label)

        aId = result.teamA.id
        aName = result.teamA.name
        aRating = result.teamA.squadRating ?? 0
        aCrestURL = result.teamA.crestURL
        aPrimaryColor = result.teamA.primaryColor
        aSecondaryColor = result.teamA.secondaryColor
        aSubtitle = Self.subtitle(for: result.teamA)

        bId = result.teamB.id
        bName = result.teamB.name
        bRating = result.teamB.squadRating ?? 0
        bCrestURL = result.teamB.crestURL
        bPrimaryColor = result.teamB.primaryColor
        bSecondaryColor = result.teamB.secondaryColor
        bSubtitle = Self.subtitle(for: result.teamB)
    }

    private static func subtitle(for team: Team) -> String {
        team.kind == .national ? "Landenteam" : (team.leagueName ?? "")
    }

    /// Maximaal aantal bewaarde draws.
    static let historyLimit = 50

    /// Cooldown-input voor de engine: team-ids uit de laatste `cooldownDraws`
    /// draws, plus trimmen van alles voorbij de limiet.
    static func recentTeamIds(in context: ModelContext, cooldownDraws: Int) -> Set<String> {
        guard cooldownDraws > 0 else { return [] }
        var descriptor = FetchDescriptor<DrawRecordModel>(
            sortBy: [SortDescriptor(\.timestamp, order: .reverse)]
        )
        descriptor.fetchLimit = cooldownDraws
        let recent = (try? context.fetch(descriptor)) ?? []
        return Set(recent.flatMap { [$0.aId, $0.bId] })
    }

    static func insertTrimmed(_ record: DrawRecordModel, in context: ModelContext) {
        context.insert(record)
        let all = (try? context.fetch(
            FetchDescriptor<DrawRecordModel>(sortBy: [SortDescriptor(\.timestamp, order: .reverse)])
        )) ?? []
        for stale in all.dropFirst(historyLimit) {
            context.delete(stale)
        }
    }
}

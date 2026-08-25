import Foundation

/// Eén team uit data/teams.json (club of landenteam).
public struct Team: Codable, Hashable, Identifiable, Sendable {
    public enum Kind: String, Codable, Sendable, CaseIterable {
        case club
        case national
    }

    public let id: String
    public let name: String
    public let kind: Kind
    public let womens: Bool
    public let starRating: Double
    public let squadRating: Int?
    public let attack: Int?
    public let midfield: Int?
    public let defence: Int?
    public let leagueId: String?
    public let leagueName: String?
    public let countryCode: String?
    public let crestURL: String?
    public let primaryColor: String?
    public let secondaryColor: String?

    public init(
        id: String, name: String, kind: Kind, womens: Bool = false,
        starRating: Double, squadRating: Int?,
        attack: Int? = nil, midfield: Int? = nil, defence: Int? = nil,
        leagueId: String? = nil, leagueName: String? = nil, countryCode: String? = nil,
        crestURL: String? = nil, primaryColor: String? = nil, secondaryColor: String? = nil
    ) {
        self.id = id
        self.name = name
        self.kind = kind
        self.womens = womens
        self.starRating = starRating
        self.squadRating = squadRating
        self.attack = attack
        self.midfield = midfield
        self.defence = defence
        self.leagueId = leagueId
        self.leagueName = leagueName
        self.countryCode = countryCode
        self.crestURL = crestURL
        self.primaryColor = primaryColor
        self.secondaryColor = secondaryColor
    }
}

public struct League: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let countryCode: String
    public let womens: Bool
    public let defaultWhitelist: Bool

    public init(id: String, name: String, countryCode: String, womens: Bool, defaultWhitelist: Bool) {
        self.id = id
        self.name = name
        self.countryCode = countryCode
        self.womens = womens
        self.defaultWhitelist = defaultWhitelist
    }
}

/// Het volledige gegenereerde databestand.
public struct TeamsDocument: Codable, Sendable {
    public let schemaVersion: Int
    public let game: String
    public let generatedAt: String
    public let leagues: [League]
    public let teams: [Team]

    /// De schema-versie die deze build begrijpt; een nieuwer bestand wordt geweigerd.
    public static let supportedSchemaVersion = 1

    public init(schemaVersion: Int, game: String, generatedAt: String, leagues: [League], teams: [Team]) {
        self.schemaVersion = schemaVersion
        self.game = game
        self.generatedAt = generatedAt
        self.leagues = leagues
        self.teams = teams
    }

    public static func decode(from data: Data) throws -> TeamsDocument {
        let doc = try JSONDecoder().decode(TeamsDocument.self, from: data)
        guard doc.schemaVersion <= supportedSchemaVersion else {
            throw DataError.unsupportedSchema(doc.schemaVersion)
        }
        return doc
    }
}

public enum DataError: Error, Equatable, Sendable {
    case unsupportedSchema(Int)
}

/// Welke soorten teams meedoen in de pool. Een paar is altijd van één soort.
public enum KindFilter: String, Codable, Sendable, CaseIterable {
    case clubsOnly
    case nationalsOnly
    case mixed
}

/// De regels waar een draw aan moet voldoen.
public struct DrawConstraints: Codable, Equatable, Sendable {
    public var cooldownDraws: Int
    public var leagueWhitelist: Set<String>
    public var includeWomens: Bool
    public var pinnedStars: Double?
    public var kindFilter: KindFilter

    public init(
        cooldownDraws: Int = 6,
        leagueWhitelist: Set<String>,
        includeWomens: Bool = false,
        pinnedStars: Double? = nil,
        kindFilter: KindFilter = .clubsOnly
    ) {
        self.cooldownDraws = cooldownDraws
        self.leagueWhitelist = leagueWhitelist
        self.includeWomens = includeWomens
        self.pinnedStars = pinnedStars
        self.kindFilter = kindFilter
    }
}

/// Elke versoepeling die de engine moest toepassen. Stil versoepelen is een bug,
/// dus dit hoort zichtbaar in de result-UI.
public enum Relaxation: Equatable, Sendable, Codable {
    /// Het herhaalfilter moest korter om nog een paar te vinden; `to` is het
    /// aantal draws dat het uiteindelijk terugkeek (0 = helemaal losgelaten).
    case cooldownShortened(to: Int)

    public var label: String {
        switch self {
        case .cooldownShortened(let to):
            if to == 0 { return "herhaalfilter losgelaten" }
            return "herhaalfilter beperkt tot \(to) draw\(to == 1 ? "" : "s")"
        }
    }
}

public struct DrawResult: Equatable, Sendable {
    public let teamA: Team
    public let teamB: Team
    public let starLevel: Double
    /// Verschil in squad rating. Puur ter display — de engine trekt erop niet.
    public let ratingDelta: Int
    public let relaxations: [Relaxation]

    public init(teamA: Team, teamB: Team, starLevel: Double, ratingDelta: Int, relaxations: [Relaxation]) {
        self.teamA = teamA
        self.teamB = teamB
        self.starLevel = starLevel
        self.ratingDelta = ratingDelta
        self.relaxations = relaxations
    }
}

public enum DrawError: Error, Equatable, Sendable {
    /// Geen enkel geldig paar, ook niet zonder herhaalfilter: geen sterbucket
    /// met twee teams erin.
    case noFairPair(starLevel: Double?)
    /// De pool is na filtering leeg (nog vóór er over paren nagedacht wordt).
    case emptyPool
}

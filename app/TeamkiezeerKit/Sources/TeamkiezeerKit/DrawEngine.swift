import Foundation

/// De matching engine. Puur en zonder state: pool + constraints + recent
/// getrokken team-ids + RNG erin, DrawResult of DrawError eruit.
///
/// Gelijk aantal sterren is dé eerlijkheidsregel. De squad rating staat op de
/// kaart maar bepaalt niets: binnen één sterbucket mag elk team elk ander team
/// treffen. Daarmee heeft elk trekbaar team exact dezelfde kans (2/N).
///
/// Levert het herhaalfilter geen paar op, dan krimpt het venster stap voor stap
/// tot er wél een paar past — niet verder dan nodig. Elke krimp staat in
/// DrawResult.relaxations, want stil versoepelen is een bug.
public enum DrawEngine {

    public static func draw(
        pool allTeams: [Team],
        constraints: DrawConstraints,
        recentDraws: [[String]],
        rng: inout some RandomNumberGenerator
    ) -> Result<DrawResult, DrawError> {

        let basePool = allTeams.filter { team in
            guard team.squadRating != nil else { return false }
            if team.womens && !constraints.includeWomens { return false }
            switch constraints.kindFilter {
            case .clubsOnly: guard team.kind == .club else { return false }
            case .nationalsOnly: guard team.kind == .national else { return false }
            case .mixed: break
            }
            // De league-whitelist gaat over clubs; landenteams hebben geen league.
            if team.kind == .club {
                guard let league = team.leagueId, constraints.leagueWhitelist.contains(league) else {
                    return false
                }
            }
            if let pinned = constraints.pinnedStars, team.starRating != pinned { return false }
            return true
        }

        guard !basePool.isEmpty else { return .failure(.emptyPool) }

        let want = min(max(constraints.cooldownDraws, 0), recentDraws.count)
        for window in stride(from: want, through: 0, by: -1) {
            let blocked = Set(recentDraws.prefix(window).joined())
            let pool = blocked.isEmpty ? basePool : basePool.filter { !blocked.contains($0.id) }

            if let result = drawAttempt(pool: pool, rng: &rng) {
                let relaxations: [Relaxation] = window < want ? [.cooldownShortened(to: window)] : []
                return .success(
                    DrawResult(
                        teamA: result.a,
                        teamB: result.b,
                        starLevel: result.a.starRating,
                        ratingDelta: abs((result.a.squadRating ?? 0) - (result.b.squadRating ?? 0)),
                        relaxations: relaxations
                    )
                )
            }
        }

        return .failure(.noFairPair(starLevel: constraints.pinnedStars))
    }

    /// Eén poging: kies een (soort, sterren)-bucket gewogen naar grootte uit de
    /// buckets met minstens twee teams, en daarbinnen twee verschillende teams
    /// uniform. De bucketweging (n/N) en de teamkans binnen de bucket (2/n)
    /// vallen tegen elkaar weg, dus geen enkel team is bevoordeeld.
    private struct BucketKey: Hashable, Comparable {
        let kind: Team.Kind
        let stars: Double
        static func < (l: BucketKey, r: BucketKey) -> Bool {
            (l.kind.rawValue, l.stars) < (r.kind.rawValue, r.stars)
        }
    }

    private static func drawAttempt(
        pool: [Team],
        rng: inout some RandomNumberGenerator
    ) -> (a: Team, b: Team)? {

        var buckets: [BucketKey: [Team]] = [:]
        for team in pool {
            buckets[BucketKey(kind: team.kind, stars: team.starRating), default: []].append(team)
        }

        // Deterministische volgorde: sorteer buckets en teams voor de RNG uit.
        let viable = buckets
            .sorted { $0.key < $1.key }
            .compactMap { _, teams -> [Team]? in
                guard teams.count >= 2 else { return nil }
                return teams.sorted { $0.id < $1.id }
            }

        guard !viable.isEmpty else { return nil }

        // Gewogen bucketkeuze naar aantal teams in de bucket.
        let totalWeight = viable.reduce(0) { $0 + $1.count }
        var pick = Int.random(in: 0..<totalWeight, using: &rng)
        var chosen = viable[0]
        for bucket in viable {
            if pick < bucket.count { chosen = bucket; break }
            pick -= bucket.count
        }

        let i = Int.random(in: 0..<chosen.count, using: &rng)
        var j = Int.random(in: 0..<(chosen.count - 1), using: &rng)
        if j >= i { j += 1 }
        return Bool.random(using: &rng) ? (a: chosen[i], b: chosen[j]) : (a: chosen[j], b: chosen[i])
    }
}

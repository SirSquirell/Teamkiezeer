import Foundation

/// De matching engine. Puur en zonder state: pool + constraints + recent
/// getrokken team-ids + RNG erin, DrawResult of DrawError eruit.
///
/// Versoepelingsladder wanneer er geen geldig paar is:
///   1..3: maxRatingDelta telkens +1
///   4:    cooldown laten vallen (delta blijft op de breedste stand)
/// Elke toegepaste versoepeling staat in DrawResult.relaxations.
public enum DrawEngine {

    public static func draw(
        pool allTeams: [Team],
        constraints: DrawConstraints,
        recentTeamIds: Set<String>,
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

        var relaxations: [Relaxation] = []
        for stage in 0...4 {
            let delta = constraints.maxRatingDelta + min(stage, 3)
            let cooldownActive = stage < 4
            if stage >= 1 && stage <= 3 {
                relaxations.append(.deltaWidened(to: delta))
            } else if stage == 4 {
                relaxations.append(.cooldownDropped)
            }

            let pool = cooldownActive
                ? basePool.filter { !recentTeamIds.contains($0.id) }
                : basePool

            if let result = drawAttempt(pool: pool, maxDelta: delta, rng: &rng) {
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

    /// Eén poging op een vaste stand van de ladder: kies een (soort, sterren)-
    /// bucket gewogen naar grootte uit de buckets die minstens één geldig paar
    /// hebben, en daarbinnen uniform een geldig paar.
    private static func drawAttempt(
        pool: [Team],
        maxDelta: Int,
        rng: inout some RandomNumberGenerator
    ) -> (a: Team, b: Team)? {

        struct BucketKey: Hashable, Comparable {
            let kind: Team.Kind
            let stars: Double
            static func < (l: BucketKey, r: BucketKey) -> Bool {
                (l.kind.rawValue, l.stars) < (r.kind.rawValue, r.stars)
            }
        }

        var buckets: [BucketKey: [Team]] = [:]
        for team in pool {
            buckets[BucketKey(kind: team.kind, stars: team.starRating), default: []].append(team)
        }

        // Deterministische volgorde: sorteer buckets en teams voor de RNG uit.
        let viable: [(key: BucketKey, teams: [Team], pairs: [(Team, Team)])] = buckets
            .sorted { $0.key < $1.key }
            .compactMap { key, teams in
                guard teams.count >= 2 else { return nil }
                let sorted = teams.sorted { $0.id < $1.id }
                var pairs: [(Team, Team)] = []
                for i in 0..<(sorted.count - 1) {
                    for j in (i + 1)..<sorted.count {
                        let a = sorted[i], b = sorted[j]
                        guard a.id != b.id,
                              let ra = a.squadRating, let rb = b.squadRating,
                              abs(ra - rb) <= maxDelta else { continue }
                        pairs.append((a, b))
                    }
                }
                return pairs.isEmpty ? nil : (key, sorted, pairs)
            }

        guard !viable.isEmpty else { return nil }

        // Gewogen bucketkeuze naar aantal teams in de bucket.
        let totalWeight = viable.reduce(0) { $0 + $1.teams.count }
        var pick = Int.random(in: 0..<totalWeight, using: &rng)
        var chosen = viable[0]
        for bucket in viable {
            if pick < bucket.teams.count { chosen = bucket; break }
            pick -= bucket.teams.count
        }

        var pair = chosen.pairs[Int.random(in: 0..<chosen.pairs.count, using: &rng)]
        if Bool.random(using: &rng) { pair = (pair.1, pair.0) }
        return (a: pair.0, b: pair.1)
    }

    /// Team-ids die onder de cooldown vallen: alle teams uit de laatste
    /// `cooldownDraws` draws.
    public static func cooldownIds(historyNewestFirst: [(String, String)], cooldownDraws: Int) -> Set<String> {
        var ids = Set<String>()
        for (a, b) in historyNewestFirst.prefix(cooldownDraws) {
            ids.insert(a)
            ids.insert(b)
        }
        return ids
    }
}

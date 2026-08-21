import XCTest
@testable import TeamkiezeerKit

final class DrawEngineTests: XCTestCase {

    // MARK: - Helpers

    private func team(
        _ id: String, stars: Double, rating: Int?,
        kind: Team.Kind = .club, league: String? = "eng.1", womens: Bool = false
    ) -> Team {
        Team(
            id: id, name: id, kind: kind, womens: womens,
            starRating: stars, squadRating: rating,
            leagueId: kind == .club ? league : nil
        )
    }

    private func constraints(
        delta: Int = 2, cooldown: Int = 6, pinned: Double? = nil,
        womens: Bool = false, kind: KindFilter = .clubsOnly,
        whitelist: Set<String> = ["eng.1"]
    ) -> DrawConstraints {
        DrawConstraints(
            maxRatingDelta: delta, cooldownDraws: cooldown,
            leagueWhitelist: whitelist, includeWomens: womens,
            pinnedStars: pinned, kindFilter: kind
        )
    }

    private func drawOK(
        _ pool: [Team], _ c: DrawConstraints, recent: Set<String> = [], seed: UInt64 = 1,
        file: StaticString = #filePath, line: UInt = #line
    ) -> DrawResult {
        var rng = SeededRNG(seed: seed)
        switch DrawEngine.draw(pool: pool, constraints: c, recentTeamIds: recent, rng: &rng) {
        case .success(let r): return r
        case .failure(let e):
            XCTFail("verwachtte succes, kreeg \(e)", file: file, line: line)
            fatalError()
        }
    }

    private func drawErr(
        _ pool: [Team], _ c: DrawConstraints, recent: Set<String> = [], seed: UInt64 = 1
    ) -> DrawError? {
        var rng = SeededRNG(seed: seed)
        if case .failure(let e) = DrawEngine.draw(
            pool: pool, constraints: c, recentTeamIds: recent, rng: &rng
        ) { return e }
        return nil
    }

    // MARK: - Harde constraints

    func testStarsAreAlwaysIdentical() {
        let pool = [
            team("a", stars: 5.0, rating: 84), team("b", stars: 5.0, rating: 85),
            team("c", stars: 4.5, rating: 83), team("d", stars: 4.5, rating: 82),
            team("e", stars: 3.0, rating: 74), team("f", stars: 3.0, rating: 73),
        ]
        for seed in UInt64(0)..<50 {
            let r = drawOK(pool, constraints(), seed: seed)
            XCTAssertEqual(r.teamA.starRating, r.teamB.starRating)
            XCTAssertEqual(r.starLevel, r.teamA.starRating)
        }
    }

    func testKindsNeverMix() {
        let pool = [
            team("club1", stars: 4.0, rating: 80),
            team("club2", stars: 4.0, rating: 80),
            team("nat1", stars: 4.0, rating: 80, kind: .national),
            team("nat2", stars: 4.0, rating: 80, kind: .national),
        ]
        for seed in UInt64(0)..<50 {
            let r = drawOK(pool, constraints(kind: .mixed), seed: seed)
            XCTAssertEqual(r.teamA.kind, r.teamB.kind)
        }
    }

    func testNoSelfPairingEvenWhenOnlyOneTeamAtStarLevel() {
        let pool = [
            team("solo", stars: 5.0, rating: 84),
            team("x", stars: 3.0, rating: 74), team("y", stars: 3.0, rating: 73),
        ]
        for seed in UInt64(0)..<30 {
            let r = drawOK(pool, constraints(), seed: seed)
            XCTAssertNotEqual(r.teamA.id, r.teamB.id)
            XCTAssertNotEqual(r.teamA.id, "solo")
        }
        // Gepind op het niveau met maar één team: nette failure, geen zelf-paar.
        XCTAssertEqual(drawErr(pool, constraints(pinned: 5.0)), .noFairPair(starLevel: 5.0))
    }

    func testDeltaIsEnforcedWithoutRelaxationWhenPairsExist() {
        let pool = [
            team("a", stars: 4.5, rating: 82), team("b", stars: 4.5, rating: 79),
            team("c", stars: 4.5, rating: 81),
        ]
        // a-c (delta 1) is het enige paar binnen delta 2; a-b (3) en b-c (2)…
        // b-c is delta 2 en dus ook geldig. a-b mag nooit.
        for seed in UInt64(0)..<50 {
            let r = drawOK(pool, constraints(), seed: seed)
            XCTAssertLessThanOrEqual(r.ratingDelta, 2)
            XCTAssertTrue(r.relaxations.isEmpty, "geen relaxatie nodig, dus ook niet toepassen")
        }
    }

    // MARK: - Cooldown

    func testCooldownExcludesRecentTeams() {
        let pool = [
            team("a", stars: 4.0, rating: 80), team("b", stars: 4.0, rating: 80),
            team("c", stars: 4.0, rating: 80), team("d", stars: 4.0, rating: 80),
        ]
        for seed in UInt64(0)..<50 {
            let r = drawOK(pool, constraints(), recent: ["a", "b"], seed: seed)
            XCTAssertEqual(Set([r.teamA.id, r.teamB.id]), Set(["c", "d"]))
            XCTAssertTrue(r.relaxations.isEmpty)
        }
    }

    func testCooldownIdsTakesLastNDraws() {
        let history = [("a", "b"), ("c", "d"), ("e", "f")]
        XCTAssertEqual(
            DrawEngine.cooldownIds(historyNewestFirst: history, cooldownDraws: 2),
            Set(["a", "b", "c", "d"])
        )
        XCTAssertTrue(DrawEngine.cooldownIds(historyNewestFirst: history, cooldownDraws: 0).isEmpty)
    }

    // MARK: - Versoepelingsladder

    func testDeltaRelaxesStepwiseAndReportsEveryStep() {
        // Enige paar heeft delta 4: twee stappen verruimen nodig (2 -> 3 -> 4).
        let pool = [team("a", stars: 4.0, rating: 84), team("b", stars: 4.0, rating: 80)]
        let r = drawOK(pool, constraints())
        XCTAssertEqual(r.ratingDelta, 4)
        XCTAssertEqual(r.relaxations, [.deltaWidened(to: 3), .deltaWidened(to: 4)])
    }

    func testCooldownDropsOnlyAfterFullDeltaLadder() {
        // Zonder cooldown-drop bestaat er geen paar: alleen a-b, en b zit in cooldown.
        let pool = [team("a", stars: 4.0, rating: 80), team("b", stars: 4.0, rating: 80)]
        let r = drawOK(pool, constraints(), recent: ["b"])
        XCTAssertEqual(
            r.relaxations,
            [.deltaWidened(to: 3), .deltaWidened(to: 4), .deltaWidened(to: 5), .cooldownDropped]
        )
        XCTAssertEqual(Set([r.teamA.id, r.teamB.id]), Set(["a", "b"]))
    }

    func testFailsCleanlyWhenNoPairEvenAfterLadder() {
        let pool = [team("a", stars: 4.0, rating: 90), team("b", stars: 4.0, rating: 60)]
        XCTAssertEqual(drawErr(pool, constraints()), .noFairPair(starLevel: nil))
    }

    func testEmptyPoolFailure() {
        let pool = [team("a", stars: 4.0, rating: 80, league: "xx.9")]
        XCTAssertEqual(drawErr(pool, constraints()), .emptyPool)
    }

    // MARK: - Filters

    func testLeagueWhitelistAppliesToClubsButNotNationals() {
        let pool = [
            team("nat1", stars: 4.0, rating: 80, kind: .national),
            team("nat2", stars: 4.0, rating: 80, kind: .national),
        ]
        let r = drawOK(pool, constraints(kind: .nationalsOnly, whitelist: []))
        XCTAssertEqual(r.teamA.kind, .national)
    }

    func testWomensTeamsExcludedByDefaultIncludedOnOptIn() {
        let pool = [
            team("w1", stars: 4.0, rating: 80, womens: true),
            team("w2", stars: 4.0, rating: 80, womens: true),
        ]
        XCTAssertEqual(drawErr(pool, constraints()), .emptyPool)
        let r = drawOK(pool, constraints(womens: true))
        XCTAssertEqual(Set([r.teamA.id, r.teamB.id]), Set(["w1", "w2"]))
    }

    func testPinnedStarsIsRespected() {
        let pool = [
            team("a", stars: 5.0, rating: 84), team("b", stars: 5.0, rating: 85),
            team("c", stars: 3.0, rating: 74), team("d", stars: 3.0, rating: 73),
        ]
        for seed in UInt64(0)..<20 {
            let r = drawOK(pool, constraints(pinned: 3.0), seed: seed)
            XCTAssertEqual(r.starLevel, 3.0)
        }
    }

    func testTeamsWithoutSquadRatingNeverDraw() {
        let pool = [
            team("a", stars: 4.0, rating: nil), team("b", stars: 4.0, rating: nil),
        ]
        XCTAssertEqual(drawErr(pool, constraints()), .emptyPool)
    }

    // MARK: - Determinisme

    func testSameSeedSameResult() {
        let pool = (0..<40).map { team("t\($0)", stars: Double(($0 % 8) + 2) / 2, rating: 70 + $0 % 15) }
        let r1 = drawOK(pool, constraints(), seed: 42)
        let r2 = drawOK(pool, constraints(), seed: 42)
        XCTAssertEqual(r1, r2)
        var seen = Set<String>()
        for seed in UInt64(0)..<30 {
            let r = drawOK(pool, constraints(), seed: seed)
            seen.insert("\(r.teamA.id)|\(r.teamB.id)")
        }
        XCTAssertGreaterThan(seen.count, 5, "verschillende seeds horen verschillende paren te geven")
    }

    // MARK: - Schema

    func testSchemaVersionGuard() throws {
        let json = """
        {"schemaVersion": 1, "game": "FC 26", "generatedAt": "2026-08-21T09:00:00Z",
         "leagues": [], "teams": []}
        """
        _ = try TeamsDocument.decode(from: Data(json.utf8))

        let tooNew = json.replacingOccurrences(of: "\"schemaVersion\": 1", with: "\"schemaVersion\": 2")
        XCTAssertThrowsError(try TeamsDocument.decode(from: Data(tooNew.utf8))) { error in
            XCTAssertEqual(error as? DataError, .unsupportedSchema(2))
        }
    }

    func testDecodesRealPipelineOutputShape() throws {
        let json = """
        {"schemaVersion": 1, "game": "FC 26", "generatedAt": "2026-08-21T09:00:00Z",
         "leagues": [{"id": "eng.1", "name": "Premier League", "countryCode": "ENG",
                      "womens": false, "defaultWhitelist": true}],
         "teams": [{"id": "eng.arsenal", "name": "Arsenal", "kind": "club", "womens": false,
                    "starRating": 5.0, "squadRating": 84, "attack": null, "midfield": null,
                    "defence": null, "leagueId": "eng.1", "leagueName": "Premier League",
                    "countryCode": "ENG", "crestURL": "https://example.com/a.webp",
                    "primaryColor": "#EF0107", "secondaryColor": "#FFFFFF"}]}
        """
        let doc = try TeamsDocument.decode(from: Data(json.utf8))
        XCTAssertEqual(doc.teams.first?.id, "eng.arsenal")
        XCTAssertEqual(doc.leagues.first?.defaultWhitelist, true)
    }
}

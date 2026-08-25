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
        cooldown: Int = 6, pinned: Double? = nil,
        womens: Bool = false, kind: KindFilter = .clubsOnly,
        whitelist: Set<String> = ["eng.1"]
    ) -> DrawConstraints {
        DrawConstraints(
            cooldownDraws: cooldown,
            leagueWhitelist: whitelist, includeWomens: womens,
            pinnedStars: pinned, kindFilter: kind
        )
    }

    private func drawOK(
        _ pool: [Team], _ c: DrawConstraints, recent: [[String]] = [], seed: UInt64 = 1,
        file: StaticString = #filePath, line: UInt = #line
    ) -> DrawResult {
        var rng = SeededRNG(seed: seed)
        switch DrawEngine.draw(pool: pool, constraints: c, recentDraws: recent, rng: &rng) {
        case .success(let r): return r
        case .failure(let e):
            XCTFail("verwachtte succes, kreeg \(e)", file: file, line: line)
            fatalError()
        }
    }

    private func drawErr(
        _ pool: [Team], _ c: DrawConstraints, recent: [[String]] = [], seed: UInt64 = 1
    ) -> DrawError? {
        var rng = SeededRNG(seed: seed)
        if case .failure(let e) = DrawEngine.draw(
            pool: pool, constraints: c, recentDraws: recent, rng: &rng
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

    func testSquadRatingNeverConstrainsThePair() {
        // Zelfde sterren is de enige regel: ook een gat van 22 rating mag,
        // en dat is geen versoepeling maar gewoon een geldige trekking.
        let pool = [
            team("laag", stars: 4.5, rating: 60), team("hoog", stars: 4.5, rating: 82),
        ]
        for seed in UInt64(0)..<20 {
            let r = drawOK(pool, constraints(), seed: seed)
            XCTAssertEqual(Set([r.teamA.id, r.teamB.id]), Set(["laag", "hoog"]))
            XCTAssertEqual(r.ratingDelta, 22)
            XCTAssertTrue(r.relaxations.isEmpty, "de rating is display, geen constraint")
        }
    }

    func testEveryTeamInABucketIsReachable() {
        // Eén uitschieter in de bucket mag niet stilletjes onbereikbaar worden
        // (dat gebeurde toen de engine nog op rating-verschil filterde).
        let pool = [
            team("outlier", stars: 4.0, rating: 60),
            team("a", stars: 4.0, rating: 80), team("b", stars: 4.0, rating: 80),
            team("c", stars: 4.0, rating: 81), team("d", stars: 4.0, rating: 79),
        ]
        var drawn = Set<String>()
        for seed in UInt64(0)..<300 {
            let r = drawOK(pool, constraints(cooldown: 0), seed: seed)
            drawn.insert(r.teamA.id)
            drawn.insert(r.teamB.id)
        }
        XCTAssertEqual(drawn, Set(pool.map(\.id)))
    }

    func testEveryTeamIsRoughlyEquallyLikely() {
        // Kans per team is 2/N, ongeacht bucketgrootte of rating. Met 4000
        // draws over 3 + 5 teams zit elke kaart-telling ruim binnen de marge.
        let small = (0..<3).map { team("s\($0)", stars: 5.0, rating: 84 + $0) }
        let big = (0..<5).map { team("b\($0)", stars: 3.0, rating: 70 + $0 * 3) }
        let pool = small + big
        var count: [String: Int] = [:]
        let draws = 4000
        for seed in UInt64(0)..<UInt64(draws) {
            let r = drawOK(pool, constraints(cooldown: 0), seed: seed)
            count[r.teamA.id, default: 0] += 1
            count[r.teamB.id, default: 0] += 1
        }
        let expected = Double(2 * draws) / Double(pool.count)
        for t in pool {
            let got = Double(count[t.id] ?? 0)
            XCTAssertEqual(got, expected, accuracy: expected * 0.25, "\(t.id) wijkt te ver af")
        }
    }

    // MARK: - Cooldown

    func testCooldownExcludesRecentTeams() {
        let pool = [
            team("a", stars: 4.0, rating: 80), team("b", stars: 4.0, rating: 80),
            team("c", stars: 4.0, rating: 80), team("d", stars: 4.0, rating: 80),
        ]
        for seed in UInt64(0)..<50 {
            let r = drawOK(pool, constraints(), recent: [["a", "b"]], seed: seed)
            XCTAssertEqual(Set([r.teamA.id, r.teamB.id]), Set(["c", "d"]))
            XCTAssertTrue(r.relaxations.isEmpty)
        }
    }

    func testCooldownLooksBackNoFurtherThanTheSetting() {
        let pool = (0..<6).map { team("t\($0)", stars: 4.0, rating: 80) }
        let history = [["t0", "t1"], ["t2", "t3"]]
        // Cooldown 1 blokkeert alleen de laatste draw; t2 en t3 mogen weer.
        var drawn = Set<String>()
        for seed in UInt64(0)..<200 {
            let r = drawOK(pool, constraints(cooldown: 1), recent: history, seed: seed)
            drawn.insert(r.teamA.id)
            drawn.insert(r.teamB.id)
        }
        XCTAssertEqual(drawn, Set(["t2", "t3", "t4", "t5"]))
    }

    // MARK: - Versoepeling

    func testCooldownIsDroppedAndReportedWhenItBlocksEveryPair() {
        // Er bestaat maar één paar, en dat is net geweest: helemaal loslaten.
        let pool = [team("a", stars: 4.0, rating: 80), team("b", stars: 4.0, rating: 80)]
        let r = drawOK(pool, constraints(), recent: [["a", "b"]])
        XCTAssertEqual(r.relaxations, [.cooldownShortened(to: 0)])
        XCTAssertEqual(Set([r.teamA.id, r.teamB.id]), Set(["a", "b"]))
    }

    func testCooldownShrinksOnlyAsFarAsNeeded() {
        // Twee draws terug is te veel (dan is de pool leeg), één draw past wel.
        let pool = (0..<4).map { team("t\($0)", stars: 4.0, rating: 80) }
        let r = drawOK(pool, constraints(), recent: [["t0", "t1"], ["t2", "t3"]])
        XCTAssertEqual(r.relaxations, [.cooldownShortened(to: 1)])
        XCTAssertEqual(Set([r.teamA.id, r.teamB.id]), Set(["t2", "t3"]))
    }

    func testCooldownIsNotReportedWhenItFits() {
        let pool = (0..<4).map { team("t\($0)", stars: 4.0, rating: 80) }
        let r = drawOK(pool, constraints(), recent: [["t0", "t1"]])
        XCTAssertTrue(r.relaxations.isEmpty)
        XCTAssertEqual(Set([r.teamA.id, r.teamB.id]), Set(["t2", "t3"]))
    }

    func testFailsCleanlyWhenNoStarLevelHasTwoTeams() {
        let pool = [team("a", stars: 4.0, rating: 90), team("b", stars: 3.0, rating: 60)]
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

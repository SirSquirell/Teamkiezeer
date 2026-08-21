import SwiftData
import SwiftUI
import TeamkiezeerKit

/// Het hoofdscherm. Eén primaire actie: Draw. Al het delight-budget zit hier;
/// de rest van de app is bewust instant.
struct DrawView: View {
    @Environment(TeamStore.self) private var store
    @Environment(\.modelContext) private var context
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var ceremony = CeremonyController()
    @State private var lastResult: DrawResult?
    @State private var failure: DrawError?
    @State private var rules: RulesModel?

    var body: some View {
        VStack(spacing: 0) {
            Spacer(minLength: 12)

            ZStack {
                if let a = ceremony.displayA, let b = ceremony.displayB {
                    cardsArea(a: a, b: b)
                } else if let failure {
                    failureView(failure)
                } else {
                    emptyState
                }
            }
            .frame(maxHeight: .infinity)
            // Tap-to-skip: alleen tijdens de ceremonie.
            .contentShape(Rectangle())
            .onTapGesture { ceremony.requestSkip() }

            drawButton
                .padding(.horizontal, 24)
                .padding(.bottom, 18)
                .padding(.top, 10)
        }
        .background(Theme.background.ignoresSafeArea())
        .onAppear {
            Haptics.shared.prepare()
            if rules == nil {
                rules = RulesModel.fetchOrCreate(in: context, defaultWhitelist: store.defaultWhitelist)
            }
        }
    }

    // MARK: - Kaarten

    private func cardsArea(a: Team, b: Team) -> some View {
        VStack(spacing: 18) {
            relaxationChips

            ZStack {
                HStack(alignment: .top, spacing: 12) {
                    cyclingCard(team: a, settled: ceremony.aSettled, pulse: ceremony.aPulse)
                        .offset(y: ceremony.cardsVisible ? 0 : -24)
                        .opacity(ceremony.cardsVisible ? 1 : 0)
                    cyclingCard(team: b, settled: ceremony.bSettled, pulse: ceremony.bPulse)
                        .offset(y: ceremony.cardsVisible ? 0 : -24)
                        .opacity(ceremony.cardsVisible ? 1 : 0)
                        // 60ms stagger tussen de twee kaarten bij binnenkomst;
                        // onder reduced motion beweegt hier niets.
                        .animation(
                            reduceMotion
                                ? nil
                                : ceremony.cardsVisible
                                    ? .spring(duration: 0.4, bounce: 0.15).delay(0.06)
                                    : .easeOut(duration: 0.18),
                            value: ceremony.cardsVisible
                        )
                }

                vsBadge
            }

            balanceMeter
        }
        .padding(.horizontal, 20)
    }

    @ViewBuilder
    private func cyclingCard(team: Team, settled: Bool, pulse: Bool) -> some View {
        TimelineView(.animation(minimumInterval: 1 / 30, paused: countPaused)) { timeline in
            TeamCardView(
                team: team,
                starsFilled: settled ? ceremony.starsFilled : 0,
                countProgress: settled ? countProgress(now: timeline.date) : 0,
                revealed: settled
            )
        }
        .id(team.id)
        .transition(.opacity)
        .scaleEffect(pulse ? 1.06 : 1.0)
    }

    private var countPaused: Bool {
        if ceremony.countJumped { return true }
        guard let start = ceremony.countStart else { return true }
        return Date().timeIntervalSince(start) > CeremonyController.countUpDuration + 0.1
    }

    private func countProgress(now: Date) -> Double {
        if ceremony.countJumped { return 1 }
        guard let start = ceremony.countStart else { return 0 }
        return min(1, max(0, now.timeIntervalSince(start) / CeremonyController.countUpDuration))
    }

    // MARK: - VS badge

    private var vsBadge: some View {
        Text("VS")
            .font(.system(size: 15, weight: .black))
            .tracking(1)
            .foregroundStyle(Theme.accentText)
            .frame(width: 44, height: 44)
            .background(Circle().fill(Theme.accent))
            .overlay(Circle().strokeBorder(Color.black.opacity(0.25), lineWidth: 1))
            .scaleEffect(ceremony.showVS ? 1.0 : 0.9)
            .opacity(ceremony.showVS ? 1 : 0)
    }

    // MARK: - Balance meter

    @ViewBuilder
    private var balanceMeter: some View {
        if let result = lastResult {
            let delta = result.ratingDelta
            let color = Theme.balanceColor(delta: delta)
            VStack(spacing: 7) {
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule().fill(Color.white.opacity(0.08))
                        Capsule()
                            .fill(color)
                            .frame(width: max(14, geo.size.width * fillFraction(delta: delta)))
                            .scaleEffect(x: ceremony.showMeter ? 1 : 0, anchor: .leading)
                    }
                }
                .frame(height: 6)

                HStack {
                    Text("\(result.teamA.squadRating ?? 0)")
                    Spacer()
                    Text("Δ \(delta)")
                        .foregroundStyle(color)
                        .fontWeight(.bold)
                    Spacer()
                    Text("\(result.teamB.squadRating ?? 0)")
                }
                .font(.system(size: 12, weight: .semibold))
                .monospacedDigit()
                .foregroundStyle(Theme.textSecondary)
            }
            .opacity(ceremony.showMeter ? 1 : 0)
            .padding(.horizontal, 6)
        }
    }

    private func fillFraction(delta: Int) -> CGFloat {
        min(1, CGFloat(delta) / 8)
    }

    // MARK: - Relaxaties (stil versoepelen is een bug)

    @ViewBuilder
    private var relaxationChips: some View {
        let labels = lastResult?.relaxations.map(\.label) ?? []
        if !labels.isEmpty && ceremony.showMeter {
            HStack(spacing: 6) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 10))
                Text(labels.joined(separator: " · "))
                    .font(.system(size: 12, weight: .semibold))
            }
            .foregroundStyle(Theme.balanceWarn)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Capsule().fill(Theme.balanceWarn.opacity(0.12)))
        } else {
            // Vaste hoogte zodat de kaarten niet verspringen als chips verschijnen.
            Color.clear.frame(height: 27)
        }
    }

    // MARK: - Lege staat & failure

    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "sparkles")
                .font(.system(size: 30))
                .foregroundStyle(Theme.textTertiary)
            Text("Klaar voor de loting")
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Theme.textSecondary)
            Text(datasetLine)
                .font(.system(size: 12))
                .foregroundStyle(Theme.textTertiary)
        }
    }

    private func failureView(_ error: DrawError) -> some View {
        VStack(spacing: 10) {
            Image(systemName: "xmark.circle")
                .font(.system(size: 30))
                .foregroundStyle(Theme.balanceBad)
            Text(failureMessage(error))
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(Theme.textSecondary)
                .multilineTextAlignment(.center)
            Text("Verruim de regels of zet meer leagues aan.")
                .font(.system(size: 13))
                .foregroundStyle(Theme.textTertiary)
        }
        .padding(.horizontal, 40)
    }

    private func failureMessage(_ error: DrawError) -> String {
        switch error {
        case .noFairPair(let stars):
            if let stars {
                return "Geen eerlijk paar op \(stars.formatted())★ met jouw filters."
            }
            return "Geen eerlijk paar met jouw filters."
        case .emptyPool:
            return "De pool is leeg met deze filters."
        }
    }

    private var datasetLine: String {
        guard let doc = store.document else { return "" }
        return "\(doc.game) · \(store.teams.count) teams"
    }

    // MARK: - Draw

    private var drawButton: some View {
        Button(action: performDraw) {
            Text(lastResult == nil && failure == nil ? "Draw" : "Opnieuw")
                .font(.system(size: 19, weight: .heavy))
                .tracking(0.3)
                .foregroundStyle(Theme.accentText)
                .frame(maxWidth: .infinity)
                .frame(height: 58)
                .background(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .fill(Theme.accent)
                )
        }
        .buttonStyle(PressableButtonStyle())
        .disabled(store.document == nil)
        .accessibilityHint("Trekt twee gelijkwaardige teams")
    }

    private func performDraw() {
        guard let rules else { return }
        let constraints = rules.constraints
        let recent = DrawRecordModel.recentTeamIds(in: context, cooldownDraws: constraints.cooldownDraws)
        var rng = SystemRandomNumberGenerator()

        switch DrawEngine.draw(
            pool: store.teams, constraints: constraints, recentTeamIds: recent, rng: &rng
        ) {
        case .success(let result):
            failure = nil
            lastResult = result
            DrawRecordModel.insertTrimmed(DrawRecordModel(result: result), in: context)
            let pool = cyclePool(constraints: constraints)
            if ceremony.displayA != nil {
                ceremony.exitThenBegin(result: result, pool: pool, reduceMotion: reduceMotion)
            } else {
                ceremony.begin(result: result, pool: pool, reduceMotion: reduceMotion)
            }
        case .failure(let error):
            failure = error
            lastResult = nil
            ceremony.resetForConfigChange()
        }
    }

    /// Dezelfde filters als de engine gebruikt, zodat de cycling eerlijk door
    /// echte kandidaten bladert.
    private func cyclingPoolFilter(_ team: Team, constraints: DrawConstraints) -> Bool {
        guard team.squadRating != nil else { return false }
        if team.womens && !constraints.includeWomens { return false }
        switch constraints.kindFilter {
        case .clubsOnly: guard team.kind == .club else { return false }
        case .nationalsOnly: guard team.kind == .national else { return false }
        case .mixed: break
        }
        if team.kind == .club {
            guard let league = team.leagueId, constraints.leagueWhitelist.contains(league) else {
                return false
            }
        }
        if let pinned = constraints.pinnedStars, team.starRating != pinned { return false }
        return true
    }

    private func cyclePool(constraints: DrawConstraints) -> [Team] {
        store.teams.filter { cyclingPoolFilter($0, constraints: constraints) }
    }
}

/// Knop-feedback: scale 0.97 op touch-down met een light impact. 120ms snappy.
struct PressableButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .animation(.snappy(duration: 0.12), value: configuration.isPressed)
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed {
                    MainActor.assumeIsolated { Haptics.shared.buttonDown() }
                }
            }
    }
}

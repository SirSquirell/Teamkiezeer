import Foundation
import Observation
import SwiftUI
import TeamkiezeerKit

/// De draw-ceremonie: één state machine die de beat-tabel uit de brief
/// afspeelt. Totaal ~2s, tap-to-skip springt direct naar settled, en bij
/// reduced motion vervalt de cycling en crossfaden beide kaarten in 200ms.
@Observable
@MainActor
final class CeremonyController {

    // Zichtbare staat, door DrawView gelezen.
    private(set) var cardsVisible = false
    private(set) var displayA: Team?
    private(set) var displayB: Team?
    private(set) var aSettled = false
    private(set) var bSettled = false
    private(set) var aPulse = false
    private(set) var bPulse = false
    private(set) var starsFilled = 0
    private(set) var countStart: Date?
    private(set) var countJumped = false
    private(set) var showVS = false
    private(set) var showMeter = false
    private(set) var isRunning = false

    private var result: DrawResult?
    private var task: Task<Void, Never>?
    private var skipRequested = false

    /// Kandidaten voor de cycling: echte teams uit de gefilterde pool, geen
    /// placeholder-art, zodat de reveal eerlijk leest.
    private var cyclePool: [Team] = []

    static let countUpDuration: TimeInterval = 0.5

    func begin(result: DrawResult, pool: [Team], reduceMotion: Bool) {
        task?.cancel()
        self.result = result
        cyclePool = pool.isEmpty ? [result.teamA, result.teamB] : pool
        skipRequested = false

        task = Task { [weak self] in
            await self?.run(reduceMotion: reduceMotion)
        }
    }

    /// Re-roll: kaarten verlaten het scherm zoals ze kwamen (lift + fade,
    /// 180ms easeOut), daarna start de nieuwe sequence.
    func exitThenBegin(result: DrawResult, pool: [Team], reduceMotion: Bool) {
        task?.cancel()
        task = Task { [weak self] in
            guard let self else { return }
            if self.cardsVisible && !reduceMotion {
                withAnimation(.easeOut(duration: 0.18)) { self.cardsVisible = false }
                try? await Task.sleep(nanoseconds: 190_000_000)
            }
            self.begin(result: result, pool: pool, reduceMotion: reduceMotion)
        }
    }

    func requestSkip() {
        guard isRunning else { return }
        skipRequested = true
    }

    func resetForConfigChange() {
        task?.cancel()
        isRunning = false
        cardsVisible = false
        displayA = nil
        displayB = nil
        result = nil
    }

    // MARK: - Timeline

    private func run(reduceMotion: Bool) async {
        guard let result else { return }
        isRunning = true
        resetBeats()

        if reduceMotion {
            await runReduced(result: result)
        } else {
            await runFull(result: result)
        }

        isRunning = false
    }

    private func resetBeats() {
        aSettled = false
        bSettled = false
        aPulse = false
        bPulse = false
        starsFilled = 0
        countStart = nil
        countJumped = false
        showVS = false
        showMeter = false
        cardsVisible = false
        displayA = nil
        displayB = nil
    }

    /// Volledige sequence, beats zoals gespecificeerd (t in seconden vanaf tap).
    private func runFull(result: DrawResult) async {
        // 0.00  kaarten vallen in vanaf offset -24, 60ms stagger (in de view).
        withAnimation(.spring(duration: 0.4, bounce: 0.15)) { cardsVisible = true }
        displayA = randomCandidate(not: nil)
        displayB = randomCandidate(not: displayA?.id)

        // 0.15–0.90  cycling door de echte pool, elke 55ms, 90ms crossfade.
        if await beat(0.15) { return }
        var elapsed: TimeInterval = 0.15
        while elapsed < 0.9 {
            swapCandidates()
            if await sleepOrSkip(0.055) { return }
            elapsed += 0.055
        }

        // 0.90–1.15  deceleratie: interval 55ms → 260ms op een sterke ease-out.
        var progress: Double = 0
        while progress < 1 {
            progress = min(1, progress + 0.34)
            let interval = 0.055 + (0.26 - 0.055) * easeOutStrong(progress)
            swapCandidates()
            if await sleepOrSkip(interval) { return }
        }

        // 1.15  kaart A settelt: scale 1.06 → 1.0, rigid haptic.
        settleA(result)
        // 1.45  kaart B settelt; de 300ms stilte is de spanning.
        if await sleepOrSkip(0.30) { return }
        settleB(result)

        // 1.50  sterren vullen links → rechts, 60ms per ster; count-up start.
        if await sleepOrSkip(0.05) { return }
        countStart = Date()
        for i in 1...5 {
            withAnimation(.snappy(duration: 0.2)) { starsFilled = i }
            if await sleepOrSkip(0.06) { return }
        }

        // 1.75  VS-badge: het "match is set"-moment.
        withAnimation(.spring(duration: 0.5, bounce: 0.3)) { showVS = true }
        Haptics.shared.matchSet()

        // 1.85  balance meter groeit vanaf de linkerrand.
        if await sleepOrSkip(0.10) { return }
        withAnimation(.easeOut(duration: 0.3)) { showMeter = true }
    }

    /// Reduced motion: geen cycling; beide kaarten crossfaden in 200ms naar
    /// hun eindstaat. Haptics en de count-up blijven.
    private func runReduced(result: DrawResult) async {
        cardsVisible = true
        withAnimation(.easeOut(duration: 0.2)) {
            displayA = result.teamA
            displayB = result.teamB
            aSettled = true
            bSettled = true
        }
        Haptics.shared.cardSettled()
        if await sleepOrSkip(0.2) { return }
        countStart = Date()
        withAnimation(.easeOut(duration: 0.2)) {
            starsFilled = 5
            showVS = true
            showMeter = true
        }
        Haptics.shared.matchSet()
    }

    // MARK: - Beats & helpers

    private func settleA(_ result: DrawResult) {
        aPulse = true
        withAnimation(.linear(duration: 0.09)) { displayA = result.teamA }
        withAnimation(.spring(duration: 0.45, bounce: 0.25)) {
            aPulse = false
            aSettled = true
        }
        Haptics.shared.cardSettled()
    }

    private func settleB(_ result: DrawResult) {
        bPulse = true
        withAnimation(.linear(duration: 0.09)) { displayB = result.teamB }
        withAnimation(.spring(duration: 0.45, bounce: 0.25)) {
            bPulse = false
            bSettled = true
        }
        Haptics.shared.cardSettled()
    }

    private func swapCandidates() {
        withAnimation(.linear(duration: 0.09)) {
            displayA = randomCandidate(not: displayA?.id)
            displayB = randomCandidate(not: displayB?.id)
        }
    }

    private func randomCandidate(not excluded: String?) -> Team? {
        guard !cyclePool.isEmpty else { return nil }
        for _ in 0..<4 {
            if let pick = cyclePool.randomElement(), pick.id != excluded {
                return pick
            }
        }
        return cyclePool.randomElement()
    }

    /// Slaap `seconds`; true = skip aangevraagd of gecanceld → spring naar settled.
    private func sleepOrSkip(_ seconds: TimeInterval) async -> Bool {
        try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
        if Task.isCancelled { return true }
        if skipRequested {
            jumpToSettled()
            return true
        }
        return false
    }

    private func beat(_ seconds: TimeInterval) async -> Bool {
        await sleepOrSkip(seconds)
    }

    /// Tap-to-skip: tegen de vijftigste draw is de ceremonie een taks.
    private func jumpToSettled() {
        guard let result else { return }
        var t = Transaction()
        t.disablesAnimations = true
        withTransaction(t) {
            cardsVisible = true
            displayA = result.teamA
            displayB = result.teamB
            aSettled = true
            bSettled = true
            aPulse = false
            bPulse = false
            starsFilled = 5
            countJumped = true
            showVS = true
            showMeter = true
        }
        Haptics.shared.matchSet()
        isRunning = false
    }

    /// cubic-bezier(0.23, 1, 0.32, 1) benaderd: een agressieve ease-out.
    private func easeOutStrong(_ x: Double) -> Double {
        1 - pow(1 - x, 4)
    }
}

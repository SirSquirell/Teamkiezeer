import UIKit

/// Generators worden voorbereid zodra het Draw-scherm verschijnt, niet op het
/// moment van vuren — anders voelt de eerste tap dood.
@MainActor
final class Haptics {
    static let shared = Haptics()

    private let light = UIImpactFeedbackGenerator(style: .light)
    private let rigid = UIImpactFeedbackGenerator(style: .rigid)
    private let notify = UINotificationFeedbackGenerator()

    func prepare() {
        light.prepare()
        rigid.prepare()
        notify.prepare()
    }

    func buttonDown() {
        light.impactOccurred()
        light.prepare()
    }

    func cardSettled() {
        rigid.impactOccurred()
        rigid.prepare()
    }

    func matchSet() {
        notify.notificationOccurred(.success)
        notify.prepare()
    }
}

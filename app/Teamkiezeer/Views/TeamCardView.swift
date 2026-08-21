import SwiftUI
import TeamkiezeerKit

/// Eén teamkaart. Beide kaarten in de draw zijn exact symmetrisch; elke
/// asymmetrie leest als voorkeur voor één kant.
struct TeamCardView: View {
    let team: Team
    /// Sterposities die al gevuld zijn (reveal-stagger); 5 = alles.
    var starsFilled: Int = 5
    /// 0...1 voortgang van de ratings-count-up; 1 = definitieve waarden.
    var countProgress: Double = 1
    /// Tijdens de cycling wisselen alleen crest + naam; league en rating
    /// blijven in een rustige pending-staat tot de kaart settelt.
    var revealed: Bool = true

    var body: some View {
        VStack(spacing: 14) {
            CrestView(team: team, size: 92)

            VStack(spacing: 5) {
                Text(team.name)
                    .font(.teamName)
                    .tracking(-0.4)
                    .foregroundStyle(Theme.textPrimary)
                    .lineLimit(2)
                    .multilineTextAlignment(.center)
                    .minimumScaleFactor(0.8)
                    .frame(height: 50, alignment: .center)

                Text(revealed ? subtitle : "· · ·")
                    .font(.system(size: 11, weight: .semibold))
                    .tracking(0.8)
                    .textCase(.uppercase)
                    .foregroundStyle(Theme.textTertiary)
                    .lineLimit(1)
            }

            StarsView(rating: team.starRating, filledCount: starsFilled)

            Text("\(counted(team.squadRating ?? 0))")
                .font(.bigNumber)
                .monospacedDigit()
                .foregroundStyle(Theme.textPrimary)
                .opacity(revealed ? 1 : 0)
                .accessibilityLabel("Squad rating \(team.squadRating ?? 0)")

            // ATT/MID/DEF alleen als de dataset ze levert (optioneel in v1).
            if let att = team.attack, let mid = team.midfield, let def = team.defence {
                HStack(spacing: 12) {
                    lineStat("ATT", counted(att))
                    lineStat("MID", counted(mid))
                    lineStat("DEF", counted(def))
                }
            }
        }
        .padding(.vertical, 22)
        .padding(.horizontal, 10)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .fill(Theme.surface)
                .overlay(
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .strokeBorder(Theme.hairline, lineWidth: 1)
                )
        )
    }

    private var subtitle: String {
        if team.kind == .national {
            return team.womens ? "Landenteam · Vrouwen" : "Landenteam"
        }
        return team.leagueName ?? "Onbekende league"
    }

    private func counted(_ value: Int) -> Int {
        Int((Double(value) * countProgress).rounded())
    }

    private func lineStat(_ label: String, _ value: Int) -> some View {
        VStack(spacing: 1) {
            Text(label)
                .font(.system(size: 9, weight: .semibold))
                .tracking(0.6)
                .foregroundStyle(Theme.textTertiary)
            Text("\(value)")
                .font(.system(size: 14, weight: .bold))
                .monospacedDigit()
                .foregroundStyle(Theme.textSecondary)
        }
    }
}

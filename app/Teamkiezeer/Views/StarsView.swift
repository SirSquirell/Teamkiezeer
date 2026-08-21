import SwiftUI

/// Sterrenrij met halve sterren via een mask op hetzelfde glyph (geen ander
/// glyph, anders verspringt de vorm). Vullen kan links-naar-rechts gestaggerd
/// worden via `filledCount`.
struct StarsView: View {
    let rating: Double
    /// Hoeveel sterposities al gevuld zijn (voor de reveal-stagger).
    /// Standaard alles.
    var filledCount: Int = 5
    var size: CGFloat = 13

    var body: some View {
        HStack(spacing: 3) {
            ForEach(0..<5, id: \.self) { index in
                star(at: index)
            }
        }
        .accessibilityLabel("\(rating.formatted()) sterren")
    }

    @ViewBuilder
    private func star(at index: Int) -> some View {
        let fill = fillFraction(at: index)
        let revealed = index < filledCount
        ZStack {
            Image(systemName: "star.fill")
                .font(.system(size: size, weight: .semibold))
                .foregroundStyle(Color.white.opacity(0.14))
            Image(systemName: "star.fill")
                .font(.system(size: size, weight: .semibold))
                .foregroundStyle(Theme.starFill)
                .mask(
                    GeometryReader { geo in
                        Rectangle().frame(width: geo.size.width * fill)
                    }
                )
                .opacity(revealed ? 1 : 0)
                .scaleEffect(revealed ? 1 : 0.6)
        }
    }

    private func fillFraction(at index: Int) -> CGFloat {
        let remainder = rating - Double(index)
        if remainder >= 1 { return 1 }
        if remainder >= 0.5 { return 0.5 }
        return 0
    }
}

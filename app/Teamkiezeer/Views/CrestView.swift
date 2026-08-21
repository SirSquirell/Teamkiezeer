import SwiftUI
import TeamkiezeerKit

/// Crest met fallback-tile. De fallback bestaat eerst: een afgeronde tegel in
/// de clubkleur met de initialen, zodat de UI nooit afhangt van een
/// netwerkplaatje. Crests zijn EA/club-IP en worden alleen runtime gefetcht
/// (URLCache doet de caching, geconfigureerd in TeamkiezeerApp).
struct CrestView: View {
    let team: Team
    var size: CGFloat = 96

    var body: some View {
        Group {
            if let urlString = team.crestURL, let url = URL(string: urlString) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image.resizable().scaledToFit()
                    default:
                        fallbackTile
                    }
                }
            } else {
                fallbackTile
            }
        }
        .frame(width: size, height: size)
    }

    private var fallbackTile: some View {
        RoundedRectangle(cornerRadius: size * 0.22, style: .continuous)
            .fill(primaryColor)
            .overlay(
                Text(initials)
                    .font(.system(size: size * 0.34, weight: .heavy))
                    .tracking(0.5)
                    .foregroundStyle(secondaryColor)
            )
            .overlay(
                RoundedRectangle(cornerRadius: size * 0.22, style: .continuous)
                    .strokeBorder(Color.white.opacity(0.08), lineWidth: 1)
            )
    }

    private var primaryColor: Color {
        if let hex = team.primaryColor { return Color(hex: hex) }
        return .seeded(from: team.id)
    }

    private var secondaryColor: Color {
        if let hex = team.secondaryColor { return Color(hex: hex) }
        return .white
    }

    private var initials: String {
        let skip: Set<String> = ["fc", "cf", "afc", "ac", "as", "sc", "de", "ss", "cd", "1."]
        let words = team.name.split(separator: " ").map(String.init)
        let meaningful = words.filter { !skip.contains($0.lowercased()) }
        let source = meaningful.isEmpty ? words : meaningful
        let letters = source.prefix(3).compactMap { $0.first.map(String.init) }
        return letters.joined().uppercased()
    }
}

import SwiftUI

/// Eén plek voor kleur en typografie. Donker, near-black, één accent.
/// De crest is de held; al het andere is metadata.
enum Theme {
    // Vlakken
    static let background = Color(hex: "#0B0B0F")
    static let surface = Color(hex: "#15151B")
    static let surfaceRaised = Color(hex: "#1C1C24")
    static let hairline = Color.white.opacity(0.07)

    // Tekst
    static let textPrimary = Color(hex: "#F5F5F7")
    static let textSecondary = Color(hex: "#9A9AA3")
    static let textTertiary = Color(hex: "#5F5F6A")

    // Het ene accent
    static let accent = Color(hex: "#C8F73A")
    static let accentText = Color(hex: "#131608")

    // Semantiek van de balance meter (los van het accent)
    static let balanceGood = Color(hex: "#4ADE80")
    static let balanceWarn = Color(hex: "#FBBF24")
    static let balanceBad = Color(hex: "#F87171")

    static let starFill = Color(hex: "#F2C14E")

    static func balanceColor(delta: Int) -> Color {
        if delta < 2 { return balanceGood }
        if delta <= 4 { return balanceWarn }
        return balanceBad
    }
}

extension Color {
    /// "#RRGGBB" → Color. Valt terug op magenta zodat een kapotte hex opvalt.
    init(hex: String) {
        var value: UInt64 = 0
        let cleaned = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        guard cleaned.count == 6, Scanner(string: cleaned).scanHexInt64(&value) else {
            self = .pink
            return
        }
        self.init(
            red: Double((value >> 16) & 0xFF) / 255,
            green: Double((value >> 8) & 0xFF) / 255,
            blue: Double(value & 0xFF) / 255
        )
    }

    /// Deterministische fallbackkleur voor teams zonder aangeleverde kleur.
    static func seeded(from string: String) -> Color {
        var hash: UInt64 = 5381
        for byte in string.utf8 { hash = (hash << 5) &+ hash &+ UInt64(byte) }
        let hue = Double(hash % 360) / 360
        return Color(hue: hue, saturation: 0.55, brightness: 0.45)
    }
}

extension Font {
    /// Grote teamnaam: strak gespatieerd SF Pro.
    static let teamName = Font.system(size: 21, weight: .bold)
    static let bigNumber = Font.system(size: 34, weight: .heavy)
}

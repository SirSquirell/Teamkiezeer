import SwiftUI

struct RootView: View {
    var body: some View {
        TabView {
            DrawView()
                .tabItem { Label("Draw", systemImage: "dice.fill") }
            RulesView()
                .tabItem { Label("Regels", systemImage: "slider.horizontal.3") }
            HistoryView()
                .tabItem { Label("History", systemImage: "clock.fill") }
        }
        .tint(Theme.accent)
        .preferredColorScheme(.dark)
    }
}

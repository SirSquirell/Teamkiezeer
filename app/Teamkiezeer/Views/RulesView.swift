import SwiftData
import SwiftUI
import TeamkiezeerKit

/// Constraint-configuratie. Dit scherm wordt vaak aangeraakt: geen motion,
/// alles instant.
struct RulesView: View {
    @Environment(TeamStore.self) private var store
    @Environment(\.modelContext) private var context
    @State private var rules: RulesModel?

    var body: some View {
        NavigationStack {
            Group {
                if let rules {
                    form(rules)
                } else {
                    Color.clear
                }
            }
            .navigationTitle("Regels")
            .navigationBarTitleDisplayMode(.inline)
            .background(Theme.background)
            .scrollContentBackground(.hidden)
        }
        .onAppear {
            if rules == nil {
                rules = RulesModel.fetchOrCreate(in: context, defaultWhitelist: store.defaultWhitelist)
            }
        }
    }

    private func form(_ rules: RulesModel) -> some View {
        @Bindable var rules = rules
        return List {
            Section("Sterren") {
                starPicker(rules)
            }
            .listRowBackground(Theme.surface)

            Section("Eerlijkheid") {
                Stepper(value: $rules.cooldownDraws, in: 0...20) {
                    row("Cooldown (draws)", value: "\(rules.cooldownDraws)")
                }
            }
            .listRowBackground(Theme.surface)

            Section("Teams") {
                Picker("Soort", selection: $rules.kindFilterRaw) {
                    Text("Clubs").tag(KindFilter.clubsOnly.rawValue)
                    Text("Landen").tag(KindFilter.nationalsOnly.rawValue)
                    Text("Mix").tag(KindFilter.mixed.rawValue)
                }
                .pickerStyle(.segmented)
                Toggle("Vrouwenteams", isOn: $rules.includeWomens)
                    .tint(Theme.accent)
            }
            .listRowBackground(Theme.surface)

            Section {
                ForEach(visibleLeagues(womens: false)) { league in
                    leagueRow(league, rules: rules)
                }
                if rules.includeWomens {
                    ForEach(visibleLeagues(womens: true)) { league in
                        leagueRow(league, rules: rules)
                    }
                }
                Button("Herstel standaard leagues") {
                    rules.leagueWhitelist = store.defaultWhitelist
                }
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Theme.accent)
            } header: {
                Text("Leagues (\(rules.leagueWhitelist.count) aan)")
            } footer: {
                Text("Landenteams vallen buiten de league-filter.")
            }
            .listRowBackground(Theme.surface)

            Section("Dataset") {
                datasetFooter
            }
            .listRowBackground(Theme.surface)
        }
        .tint(Theme.accent)
    }

    // MARK: - Sterren

    private func starPicker(_ rules: RulesModel) -> some View {
        let levels: [Double] = stride(from: 5.0, through: 0.5, by: -0.5).map { $0 }
        return ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                starChip(label: "Verras ons", selected: rules.pinnedStars == nil) {
                    rules.pinnedStars = nil
                }
                ForEach(levels, id: \.self) { level in
                    starChip(
                        label: level.formatted(.number.precision(.fractionLength(0...1))) + "★",
                        selected: rules.pinnedStars == level
                    ) {
                        rules.pinnedStars = level
                    }
                }
            }
            .padding(.vertical, 2)
        }
        .listRowInsets(EdgeInsets(top: 8, leading: 12, bottom: 8, trailing: 12))
    }

    private func starChip(label: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(label)
                .font(.system(size: 13, weight: .bold))
                .monospacedDigit()
                .foregroundStyle(selected ? Theme.accentText : Theme.textSecondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 7)
                .background(
                    Capsule().fill(selected ? Theme.accent : Theme.surfaceRaised)
                )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Leagues

    private func visibleLeagues(womens: Bool) -> [League] {
        store.leagues
            .filter { $0.womens == womens }
            .sorted { ($0.defaultWhitelist ? 0 : 1, $0.name) < ($1.defaultWhitelist ? 0 : 1, $1.name) }
    }

    private func leagueRow(_ league: League, rules: RulesModel) -> some View {
        let isOn = rules.leagueWhitelist.contains(league.id)
        return Button {
            if isOn {
                rules.leagueWhitelist.removeAll { $0 == league.id }
            } else {
                rules.leagueWhitelist.append(league.id)
            }
        } label: {
            HStack {
                Text(league.name)
                    .foregroundStyle(Theme.textPrimary)
                Text(league.countryCode)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(Theme.textTertiary)
                Spacer()
                Image(systemName: isOn ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isOn ? Theme.accent : Theme.textTertiary)
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - Dataset

    private var datasetFooter: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let doc = store.document {
                row("Spel", value: doc.game)
                row("Dataset", value: String(doc.generatedAt.prefix(10)))
                row("Bron", value: store.source.rawValue)
                if let fetched = store.lastFetched {
                    row("Laatst opgehaald", value: fetched.formatted(date: .abbreviated, time: .shortened))
                }
                row("Teams", value: "\(store.teams.count)")
            }
            if let error = store.lastError {
                Text(error)
                    .font(.system(size: 12))
                    .foregroundStyle(Theme.balanceWarn)
            }
            Button {
                Task { await store.refresh() }
            } label: {
                HStack(spacing: 6) {
                    if store.isRefreshing {
                        ProgressView().controlSize(.small)
                    }
                    Text(store.isRefreshing ? "Bezig…" : "Ververs nu")
                        .font(.system(size: 14, weight: .semibold))
                }
                .foregroundStyle(Theme.accent)
            }
            .disabled(store.isRefreshing)
        }
        .padding(.vertical, 2)
    }

    private func row(_ label: String, value: String) -> some View {
        HStack {
            Text(label).foregroundStyle(Theme.textPrimary)
            Spacer()
            Text(value)
                .monospacedDigit()
                .foregroundStyle(Theme.textSecondary)
        }
        .font(.system(size: 15))
    }
}

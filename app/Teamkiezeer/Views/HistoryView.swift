import SwiftData
import SwiftUI

/// De laatste 50 draws. Vaak bekeken, dus: geen motion, compacte rijen.
struct HistoryView: View {
    @Query(sort: \DrawRecordModel.timestamp, order: .reverse)
    private var records: [DrawRecordModel]

    var body: some View {
        NavigationStack {
            Group {
                if records.isEmpty {
                    VStack(spacing: 8) {
                        Image(systemName: "clock")
                            .font(.system(size: 26))
                            .foregroundStyle(Theme.textTertiary)
                        Text("Nog geen draws")
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundStyle(Theme.textSecondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List(records) { record in
                        HistoryRow(record: record)
                            .listRowBackground(Theme.surface)
                            .listRowSeparatorTint(Theme.hairline)
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("History")
            .navigationBarTitleDisplayMode(.inline)
            .background(Theme.background)
            .scrollContentBackground(.hidden)
        }
    }
}

private struct HistoryRow: View {
    let record: DrawRecordModel

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Text(record.aName)
                    .font(.system(size: 15, weight: .bold))
                    .tracking(-0.2)
                    .foregroundStyle(Theme.textPrimary)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Text("\(record.aRating)–\(record.bRating)")
                    .font(.system(size: 13, weight: .bold))
                    .monospacedDigit()
                    .foregroundStyle(Theme.textSecondary)
                    .fixedSize()

                Text(record.bName)
                    .font(.system(size: 15, weight: .bold))
                    .tracking(-0.2)
                    .foregroundStyle(Theme.textPrimary)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }

            HStack(spacing: 8) {
                StarsView(rating: record.starLevel, size: 9)
                Text("Δ \(record.ratingDelta)")
                    .font(.system(size: 11, weight: .bold))
                    .monospacedDigit()
                    .foregroundStyle(Theme.balanceColor(delta: record.ratingDelta))
                if !record.relaxationLabels.isEmpty {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 9))
                        .foregroundStyle(Theme.balanceWarn)
                        .accessibilityLabel(record.relaxationLabels.joined(separator: ", "))
                }
                Spacer()
                Text(record.timestamp.formatted(.relative(presentation: .named)))
                    .font(.system(size: 11))
                    .foregroundStyle(Theme.textTertiary)
            }
        }
        .padding(.vertical, 3)
    }
}
